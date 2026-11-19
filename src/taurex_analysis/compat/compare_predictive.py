from taurex_analysis.postprocess.predictive_cli import *
from taurex_analysis.postprocess.predictive_cli import main as _main
import sys

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    return _main(['--seed', '149026'] + list(argv))
