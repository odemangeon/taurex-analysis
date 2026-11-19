# Temperature profiles and parameter names

`model.family` selects `blackbody` or `atmosphere`. Atmospheric models explicitly
select a temperature `profile` and its `parameterization` in
`model.settings.temperature`. These choices define the physical relationships;
**only `priors` selects which independent parameters are free**.

## Guillot with tied visible opacities

```json
{
  "profile": "guillot2010",
  "parameterization": "tied_gamma",
  "parameters": {
    "T_irr": 1800,
    "T_int": 100,
    "kappa_irr": 0.001,
    "log10_gamma": -0.3010299956639812
  }
}
```

This object belongs inside `model.settings.temperature`.
The model derives both visible opacities as
`kappa_v1 = kappa_v2 = kappa_ir * 10**log10_gamma`.
At the values above, each is 0.0005 m²/kg. Supplying `kappa_v1`, `kappa_v2` or
`alpha` in this parameterization is rejected: the opacities are derived, and
alpha has no effect when the channels are identical.

| Physical quantity | Key in `parameters` | Key in `priors` | Units / coordinate |
| --- | --- | --- | --- |
| Irradiation temperature | `T_irr` | `T_irr` | K |
| Internal temperature | `T_int` | `T_int_guillot` | K |
| Infrared opacity | `kappa_irr` | `log10_kappa_ir` | Initial m²/kg; fitted log10 of numerical value in m²/kg |
| Visible/infrared ratio | `log10_gamma` | `log10_gamma` | log10 of dimensionless ratio |

`kappa_irr` is the initialization spelling (two final r characters).
`kappa_ir` is an internal Python attribute, not this JSON initialization key.
When fitting `log10_kappa_ir`, gamma is preserved as infrared opacity changes.
Both quantities may be fixed, or either or both may have priors.

## Standard Guillot

Use `profile: "guillot2010"` and `parameterization: "standard"`.

| Initialization key | Prior key | Meaning |
| --- | --- | --- |
| `T_irr` | `T_irr` | Irradiation temperature, K |
| `T_int` | `T_int_guillot` | Internal temperature, K |
| `kappa_irr` | `kappa_irr` | Infrared opacity, m²/kg |
| `kappa_v1` | `kappa_v1` | First visible opacity, m²/kg |
| `kappa_v2` | `kappa_v2` | Second visible opacity, m²/kg |
| `alpha` | `alpha` | Dimensionless channel partition |

This parameterization does not expose `log10_gamma` or `log10_kappa_ir`.
An omitted parameterization defaults to `standard`. Specify scientific values
explicitly rather than relying on inherited TauREx defaults.

## Isothermal atmosphere

```json
{
  "profile": "isothermal",
  "parameterization": "standard",
  "parameters": {"T": 1800}
}
```

`T` is the name in both initialization and priors, in kelvin. This is an
atmospheric radiative-transfer model with a constant temperature profile; it is
not the `blackbody` model family. Other isothermal parameterizations are rejected.

## Blackbody

The independent parameters are `T_day` (kelvin) and `radius_ratio`
(dimensionless). Use `model.fixed` to set explicit fixed values and omit those
names from `priors`. Without explicit values, the initial temperature is 1800 K
and the radius ratio is read from `system.json`.

## Chemistry and radius

Atmospheric models also support `radius_ratio` and the selected chemistry
backend's fitted parameters.

| Quantity | FastChem initialization | Prior name |
| --- | --- | --- |
| Metallicity | `metallicity` | `metallicity` or `log10_metallicity` |
| C/O | `ratio_elements: ["C"]`, `ratios_to_o: [0.55]` | `C_O_ratio` |

Initialization is inside `model.settings.chemistry.settings`; backend is
`fastchem`. Do not fit both metallicity coordinates simultaneously. The
logarithmic coordinate is base 10 relative to the solver's reference metallicity.
Other elemental ratios are exposed by the installed FastChem implementation;
inspect its `fitting_parameters()` rather than guessing names.

## Discovery and historical compatibility

Component `fitting_parameters()` mappings are the authoritative fitted names.
The atmospheric wrapper exposes only the selected fitted subset, so inspecting
that wrapper alone does not enumerate every possible parameter. There is not yet
a `parameters` discovery CLI command or a machine-readable parameter registry.

Flat temperature configurations remain accepted for old saved runs. In that
legacy format, presence of `log10_gamma` selects the tied model and supplied
visible opacities are overwritten. New experiments should use the explicit form.
