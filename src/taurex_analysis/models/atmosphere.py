from pathlib import Path
import numpy as np
from taurex.model import ForwardModel, EmissionModel
from taurex.temperature import Guillot2010
from taurex.planet import Planet
from taurex.cache import OpacityCache, CIACache, GlobalCache
from taurex.opacity import HDF5Opacity
from taurex.contributions import AbsorptionContribution, CIAContribution, HydrogenIon
from taurex.core import fitparam
from taurex.exceptions import InvalidModelException



from .photometry import PhotometricModel
from .temperature import TiedGuillot2010, create_temperature
from .emission import SurfaceEmission, layer_fluxes
from .chemistry import create as create_chemistry

class AtmosphericPhotometry(ForwardModel):
    def __init__(self, rows, config, inputs, stride=1, filters_path=None):
        super().__init__(config.get('model_name', 'GuillotEquilibriumPhotometry'))
        self.config, self.rows = config, rows
        self.photometry = PhotometricModel(rows, inputs, filters_path=filters_path)
        self.grid = self.photometry.grid
        self.system = self.photometry.system
        self.filters = self.photometry.filters
        self.opacity_files = {}
        # Explicit cache population prevents extra local TiO/HCN/NH3 opacities
        # from silently joining the requested absorber set.
        cache = OpacityCache()
        cache.clear_cache()
        GlobalCache()['xsec_path'] = None
        GlobalCache()['opacity_method'] = 'xsec'
        candidates = {}
        for directory in config['opacity_paths']:
            directory = Path(directory)
            if not directory.is_absolute():
                raise ValueError('Opacity paths must be resolved by the configuration loader')
            for path in sorted(directory.glob('*.h5')):
                opacity = HDF5Opacity(path, in_memory=False)
                candidates[opacity.moleculeName] = path
                opacity._spec_dict.close()
        missing = set(config['absorbers']) - candidates.keys()
        if missing:
            raise FileNotFoundError(f'Missing opacity tables: {sorted(missing)}')
        self.opacities = []
        for gas in config['absorbers']:
            path = candidates[gas]
            self.opacity_files[gas] = str(path.resolve())
            op = HDF5Opacity(path, interpolation_mode='linear', in_memory=True)
            cache.add_opacity(op)
            self.opacities.append(op)
        CIACache().set_cia_path(config['cia_path'])
        self.tp = create_temperature(config['temperature'])
        if isinstance(self.tp, TiedGuillot2010):
            if {'kappa_irr', 'kappa_v1', 'kappa_v2', 'alpha'} & config['fit'].keys():
                raise ValueError('tied_gamma requires log10_kappa_ir for fitting IR opacity; visible opacities are derived')
        if {'metallicity', 'log10_metallicity'} <= config['fit'].keys():
            raise ValueError('Fit metallicity or log10_metallicity, not both')
        self.chem = create_chemistry(config['chemistry'])
        self.chem.determine_active_inactive()
        if set(self.chem.activeGases) != set(config['absorbers']):
            raise ValueError(f'Wrong active chemistry species: {self.chem.activeGases}')
        contributions = [AbsorptionContribution(), CIAContribution(cia_pairs=config['cia_pairs'])]
        if config.get('hminus', False):
            if not config['chemistry'].get('settings', config['chemistry']).get('with_ions', False):
                raise ValueError('H-minus requires equilibrium chemistry with ions')
            contributions.append(HydrogenIon())
        self.atmosphere = SurfaceEmission(
            planet=Planet(**config['planet']), temperature_profile=self.tp,
            chemistry=self.chem, contributions=contributions, **config['atmosphere'])
        self.atmosphere.build()
        native = self.atmosphere.nativeWavenumberGrid
        # Keep the full resolution for retrieval; stride is smoke-test only.
        native = native[(native >= 1e4/25.1) & (native <= 1e4/.2999)]
        # Preserve both coverage endpoints when thinning a smoke-test grid.
        native = np.unique(np.r_[native[::stride], native[-1]])
        self.atmosphere._native_grid = native
        self.wavelength = 1e4/native[::-1]
        for op in self.opacities:
            if native[0] < op.wavenumberGrid[0] or native[-1] > op.wavenumberGrid[-1]:
                raise ValueError(f'Spectral coverage insufficient: {op.moleculeName}')
        # Only fitted measurements and the optical prediction bands need coverage.
        required_bands = {row['band'] for row in rows}
        for name in sorted(required_bands):
            wave, _, _ = self.filters[name]
            if wave[0] < self.wavelength[0] or wave[-1] > self.wavelength[-1]:
                raise ValueError(f'Atmospheric wavelength coverage insufficient: {name}')
        # Forward component parameter access without enabling unwanted defaults.
        allowed = self.tp.fitting_parameters() | self.chem.fitting_parameters()
        allowed['radius_ratio'] = self.photometry.fitting_parameters()['radius_ratio']
        for name, bounds in config['fit'].items():
            if name not in allowed or len(bounds) != 2 or not bounds[0] < bounds[1]:
                raise ValueError(f'Invalid fit parameter/bounds: {name}')
            _, label, getter, setter, _, _, _ = allowed[name]
            def get(this, getter=getter):
                return getter()
            def set_(this, value, setter=setter):
                setter(value)
                this._state = None
            self.add_fittable_param(name, label.replace('$','').replace('\\\\','\\'),
                                   get, set_, 'linear', True, bounds)
        self._state = None

    def build(self):
        pass

    def evaluate(self):
        if self._state is not None:
            return
        self.atmosphere.initialize_profiles()
        t, p = self.atmosphere.temperatureProfile, self.atmosphere.pressureProfile
        for op in self.opacities:
            if t.min() < op.temperatureGrid.min() or t.max() > op.temperatureGrid.max():
                raise InvalidModelException(f'TP outside {op.moleculeName} temperature table')
            if p.min() < op.pressureGrid.min() or p.max() > op.pressureGrid.max():
                raise InvalidModelException(f'TP outside {op.moleculeName} pressure table')
        _, flux, _, _ = self.atmosphere.model()
        self.flux = flux[::-1]
        if not np.all(np.isfinite(self.flux)) or np.any(self.flux <= 0):
            raise InvalidModelException('Nonpositive or invalid surface flux')
        self._state = True

    def stellar_flux(self, wavelength):
        return self.photometry.stellar_flux(wavelength)

    def surface_flux(self, wavelength):
        self.evaluate()
        if np.min(wavelength) < self.wavelength[0] or np.max(wavelength) > self.wavelength[-1]:
            raise ValueError('Requested spectrum outside atmospheric coverage')
        return np.interp(wavelength, self.wavelength, self.flux)

    def spectrum(self, wavelength):
        return self.photometry.radius_ratio**2 * self.surface_flux(wavelength)/self.stellar_flux(wavelength)

    def integrate_flux(self, name, flux):
        # Union also retains atmospheric lines between stellar/response samples.
        wave, weight, denom = self.filters[name]
        wave = np.union1d(wave, self.wavelength[(self.wavelength > wave[0]) & (self.wavelength < wave[-1])])
        weights = np.interp(wave, self.filters[name][0], weight)
        value = np.trapezoid(np.interp(wave, self.wavelength, flux)*weights, wave)
        return self.photometry.radius_ratio**2 * value/denom

    def band_depth(self, name):
        self.evaluate()
        return self.integrate_flux(name, self.flux)

    def model(self, wngrid=None, cutoff_grid=True):
        if wngrid is not None and not np.array_equal(wngrid, self.grid):
            raise ValueError('Use spectrum() for continuous wavelengths')
        return self.grid, np.array([self.band_depth(r['band']) for r in self.rows]), None, {}

    def contributions(self, names):
        self.evaluate()
        atm = self.atmosphere
        dtau = np.zeros((atm.nLayers, len(atm.nativeWavenumberGrid)))
        for layer in range(atm.nLayers):
            for contribution in atm.contribution_list:
                # Output at row zero; start/end select the physical layer.
                contribution.contribute(atm, layer, layer+1, 0, 0,
                    atm.densityProfile, dtau[layer:layer+1], path_length=atm.deltaz)
        layer, boundary = layer_fluxes(dtau, atm.temperatureProfile,
            atm.nativeWavenumberGrid, atm._mu_quads, atm._wi_quads)
        np.testing.assert_allclose((layer.sum(axis=0)+boundary)[::-1], self.flux,
                                   rtol=2e-4, atol=1e-12)
        bands = np.array([[self.integrate_flux(b, f[::-1]) for b in names] for f in layer])
        bottom = np.array([self.integrate_flux(b, boundary[::-1]) for b in names])
        total = bands.sum(axis=0)+bottom
        return bands/total, bottom/total
