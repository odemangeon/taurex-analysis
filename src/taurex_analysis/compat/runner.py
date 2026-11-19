"""Translate historical run.py arguments to the package workflow."""
import argparse
import json
from pathlib import Path
from .paths import PLANET, INPUTS
from taurex_analysis.config import resolve
from taurex_analysis.data.measurements import read_selection


def main(folder, argv=None):
    folder=Path(folder)
    atmospheric=folder.name.startswith('guillot')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=folder/'config.json')
    parser.add_argument('--selection',type=Path,default=folder/'selection.txt')
    parser.add_argument('--measurements',type=Path,default=INPUTS/'measurements.csv')
    parser.add_argument('--inputs',type=Path,default=INPUTS)
    parser.add_argument('--bands',nargs='+');parser.add_argument('--output',type=Path)
    parser.add_argument('--nlive',type=int);parser.add_argument('--tol',type=float)
    parser.add_argument('--seed',type=int);parser.add_argument('--temperature-bounds',nargs=2,type=float,default=[500,4000])
    parser.add_argument('--fix-radius',action='store_true')
    parser.add_argument('--posterior-draws',type=int,default=256 if atmospheric else 0)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--check',action='store_true');mode.add_argument('--smoke',action='store_true')
    args=parser.parse_args(argv)
    system=json.loads((args.inputs/'system.json').read_text())
    config=dict(schema_version=1,inputs=str(args.inputs.resolve()),measurements=str(args.measurements.resolve()),
        selection=args.bands if args.bands is not None else read_selection(args.selection),seed=args.seed if args.seed is not None else 149026)
    if atmospheric:
        settings=json.loads(args.config.read_text());bounds=settings['fit']
        config['seed']=args.seed if args.seed is not None else settings['seed']
        settings['opacity_paths']=[str((args.config.resolve().parent/p).resolve()) for p in settings['opacity_paths']]
        settings['cia_path']=str((args.config.resolve().parent/settings['cia_path']).resolve())
        config['model']=dict(family='atmosphere',settings=settings)
        nlive,tol=settings['nlive'],settings['tolerance']
    else:
        bounds={'T_day':args.temperature_bounds}
        if not args.fix_radius: bounds['radius_ratio']=[.04,.07]
        config['model']=dict(family='blackbody');nlive,tol=600,.1
    config['priors']={name:dict(type='gaussian',mean=system['radius_ratio_mean'],sigma=system['radius_ratio_sigma']) if name=='radius_ratio' else dict(type='uniform',bounds=value) for name,value in bounds.items()}
    config['sampler']=dict(backend='nestle',settings=dict(nlive=args.nlive if args.nlive is not None else nlive,tol=args.tol if args.tol is not None else tol,method='multi'))
    if args.smoke:
        config['smoke']=True;config['sampler']['settings'].update(nlive=20,tol=2.)
        if atmospheric:
            config['model']['settings']['atmosphere']['nlayers']=12;config['opacity_stride']=300
    config=resolve(config,folder)
    output=args.output or folder/('check' if args.check else 'smoke_results' if args.smoke else 'results')
    from taurex_analysis.retrieval.runner import retrieve
    retrieve(config,output,check=args.check)
    if not args.check:
        from taurex_analysis.postprocess.predictions import process
        from taurex_analysis.plotting.runner import plot
        analysis=process(output,output/'analysis',dict(bands=['CHEOPS','TESS'],posterior_draws=24 if args.smoke else args.posterior_draws))
        plot(analysis)
    print(f'Saved to {output}')
