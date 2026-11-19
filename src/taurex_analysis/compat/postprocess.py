import argparse
from pathlib import Path
import numpy as np
def best_sample_index(saved, config, provenance):
    if 'logl' in saved:
        return int(np.argmax(saved['logl']))
    # Nestle 0.2.1 appends all final live points in their original order.
    # Their log-volumes are identical; max(weight) is therefore max(likelihood).
    # Every discarded point has likelihood <= every final live point.
    if provenance['versions']['nestle'] != '0.2.1':
        raise ValueError('Cannot recover best sample without logl for this Nestle version')
    weights = saved['weights']
    nlive = config['nlive']
    if not 0 < nlive <= len(weights) or not np.all(np.isfinite(weights)) or np.any(weights < 0):
        raise ValueError('Invalid saved Nestle weights/live-point count')
    if not np.any(weights[-nlive:] > 0):
        raise ValueError('Final live-point weights underflowed')
    return len(weights)-nlive+int(np.argmax(weights[-nlive:]))

def main():
    parser=argparse.ArgumentParser(description='Analyze a saved posterior without sampling')
    parser.add_argument('results',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--posterior-draws',type=int,default=0)
    args=parser.parse_args()
    from taurex_analysis.postprocess.predictions import process
    from taurex_analysis.plotting.runner import plot
    output=process(args.results,args.output or args.results/'analysis',dict(bands=['CHEOPS','TESS'],posterior_draws=args.posterior_draws))
    plot(output)
