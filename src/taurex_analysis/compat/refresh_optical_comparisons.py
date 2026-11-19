"""Resume band postprocessing for configured runs, then refresh all comparisons."""
import json, subprocess, sys
from pathlib import Path
def main():
    from .paths import PLANET as root
    configs=sorted((root/'inputs').glob('optical_plot*.json'))
    folders=sorted({(config.parent/entry['results']).resolve() for config in configs for entry in json.loads(config.read_text())['models'] if entry.get('enabled',True)})
    failed=[]
    for folder in folders:
     if (folder/'optical_postprocess_provenance.json').exists():
      print(f'Already updated: {folder.parent.name}',flush=True)
      continue
     print(f'Updating: {folder.parent.name}',flush=True)
     result=subprocess.run([sys.executable,str(root/'postprocess_optical.py'),str(folder)])
     if result.returncode:
      failed.append(str(folder))
    for config in configs:
     suffix=config.stem.removeprefix('optical_plot')
     subprocess.run([sys.executable,str(root/'compare_optical.py'),'--plot-config',str(config),'--output',str(root/f'optical_comparison{suffix}')],check=True)
    print(f'Completed. Failed posterior updates: {failed}',flush=True)
