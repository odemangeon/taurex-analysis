"""Independent retrieval, post-processing and plotting commands."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    dispatch = {'predictive': 'predictive_cli', 'compare-optical': 'optical_cli', 'compare-tint': 'tint_cli'}
    if argv and argv[0] in dispatch:
        from importlib import import_module
        return import_module('taurex_analysis.postprocess.'+dispatch[argv[0]]).main(argv[1:])
    parser=argparse.ArgumentParser(prog='taurex-analysis')
    commands=parser.add_subparsers(dest='command',required=True)
    retrieve=commands.add_parser('retrieve',help='Run a configured sampler; no plots')
    retrieve.add_argument('experiment',type=Path)
    retrieve.add_argument('--output',type=Path,required=True)
    mode=retrieve.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--smoke',action='store_true')
    post=commands.add_parser('postprocess',help='Evaluate an existing posterior; no sampling or plots')
    post.add_argument('results',type=Path);post.add_argument('--output',type=Path,required=True)
    post.add_argument('--config',type=Path)
    plot=commands.add_parser('plot',help='Render saved predictions without model dependencies')
    plot.add_argument('analysis',type=Path);plot.add_argument('--output',type=Path)
    plot.add_argument('--config',type=Path,help='Plotting settings JSON')
    prepare=commands.add_parser('prepare',help='Prepare responses and the validated stellar grid')
    prepare.add_argument('inputs',type=Path)
    prepare.add_argument('--nircam-literature',help='Complete bin catalog relative to inputs')
    publish=commands.add_parser('publish-filters',help='Publish an immutable shared response bundle')
    publish.add_argument('inputs',type=Path)
    publish.add_argument('--library',type=Path,required=True)
    for command in dispatch:
        commands.add_parser(command,help='Run '+command+' analysis')
    args=parser.parse_args(argv)
    if args.command=='retrieve':
        from .config import load
        from .retrieval.runner import retrieve
        config=load(args.experiment)
        if args.smoke:
            config['smoke']=True
            config['sampler']['settings'].update(nlive=20,tol=2.)
            if config['model']['family']=='atmosphere':
                config['model']['settings']['atmosphere']['nlayers']=12
                config['opacity_stride']=300
        output=retrieve(config,args.output,check=args.check)
    elif args.command=='postprocess':
        from .postprocess.predictions import process
        options=json.loads(args.config.read_text()) if args.config else {}
        output=process(args.results,args.output,options)
    elif args.command=='publish-filters':
        from .data.filter_library import publish
        output=publish(args.inputs,args.library)
    elif args.command=='prepare':
        from .data.preparation import prepare
        prepare(args.inputs,args.nircam_literature)
        output=args.inputs
    else:
        from .plotting.runner import plot
        output=plot(args.analysis,args.output,config=json.loads(args.config.read_text()) if args.config else None)
    print(f'Saved to {output}')
