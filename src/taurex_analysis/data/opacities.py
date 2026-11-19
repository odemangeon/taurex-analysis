"""Explicitly requested opacity downloads; importing this module does no I/O."""
from pathlib import Path
from urllib.request import urlretrieve
import gzip
import shutil


def prepare_opacities(directory, urls):
    root=Path(directory)
    root.mkdir(parents=True,exist_ok=True)
    for url in urls:
        path=root/url.rsplit('/',1)[-1]
        destination=path.with_suffix('') if path.suffix=='.gz' else path
        if destination.exists():
            continue
        temporary=Path(str(path)+'.part')
        urlretrieve(url,temporary)
        temporary.replace(path)
        if path.suffix=='.gz':
            temporary=Path(str(destination)+'.part')
            with gzip.open(path,'rb') as source, temporary.open('wb') as output:
                shutil.copyfileobj(source,output)
            temporary.replace(destination)
            path.unlink()
