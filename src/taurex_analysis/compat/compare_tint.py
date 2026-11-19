from taurex_analysis.postprocess.tint_cli import *
from taurex_analysis.postprocess.tint_cli import main as _main
from .paths import PLANET
import sys

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    return _main(['--results', *map(str, sorted(PLANET.glob('guillot_fullopacity_gamma_kappaIR_metalCO_*/results'))), '--output', str(PLANET/'tint_comparison')] + list(argv))
