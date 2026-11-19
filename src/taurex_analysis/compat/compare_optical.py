from taurex_analysis.postprocess.optical_cli import *
from taurex_analysis.postprocess.optical_cli import main as _main
from .paths import PLANET
import sys

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    return _main(['--plot-config', str(PLANET/'inputs/optical_plot.json'), '--constraints', str(PLANET/'inputs/optical_constraints.csv'), '--geometry', str(PLANET/'inputs/optical_geometry.json'), '--output', str(PLANET/'optical_comparison')] + list(argv))
