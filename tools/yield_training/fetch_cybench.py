"""Extract selected India files from the pinned CY-Bench ZIP using HTTP ranges."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import shutil
import urllib.request
import zipfile

URL = 'https://zenodo.org/api/records/13838912/files/cybench-data.zip/content'
SIZE = 12652190560

class RemoteZip(io.RawIOBase):
    def __init__(self):
        self.position = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else (self.position if whence == 1 else SIZE) + offset
        return self.position
    def read(self, size=-1):
        size = min(size if size >= 0 else SIZE-self.position, SIZE-self.position)
        if size <= 0: return b''
        # Windows' managed HTTP client uses the system trust configuration.
        # Certificate verification remains enabled in both implementations.
        if shutil.which('pwsh'):
            with tempfile.TemporaryDirectory(prefix='sage-cybench-range-') as temporary:
                destination=Path(temporary)/'range.bin'
                command=f"$ErrorActionPreference='Stop'; $r=Invoke-WebRequest -Uri '{URL}' -Headers @{{Range='bytes={self.position}-{self.position+size-1}'}} -TimeoutSec 60 -OutFile '{destination}' -PassThru; if($r.StatusCode -ne 206){{throw 'Server did not honor HTTP range'}}; $r.Headers['Content-Range']"
                response=subprocess.run(['pwsh','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
                if not response.stdout.strip().startswith(f'bytes {self.position}-'):
                    raise RuntimeError(f'Unexpected range: {response.stdout.strip()}')
                result=destination.read_bytes()
        else:
            req = urllib.request.Request(URL, headers={'Range':f'bytes={self.position}-{self.position+size-1}', 'User-Agent':'SageYieldResearch/1.0'})
            with urllib.request.urlopen(req,timeout=60) as response:
                if response.status != 206:
                    raise RuntimeError('Source does not honor HTTP ranges; refusing full 12.6GB download')
                content_range=response.headers.get('Content-Range','')
                if not content_range.startswith(f'bytes {self.position}-'):
                    raise RuntimeError(f'Unexpected range: {content_range}')
                result=response.read(size)
        if len(result)!=size: raise RuntimeError('Incomplete source range')
        self.position += len(result)
        return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('data/training/cybench_india_v1_2'))
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--variables',nargs='+',default=['yield','crop_calendar','ndvi','soil'])
    args=parser.parse_args()
    with zipfile.ZipFile(RemoteZip()) as archive:
        entries=[info for info in archive.infolist() if '/IN/' in info.filename and not info.is_dir()]
        print(json.dumps([{'name':info.filename,'bytes':info.file_size,'compressed_bytes':info.compress_size} for info in entries],indent=2),flush=True)
        if args.list: return
        args.output.mkdir(parents=True,exist_ok=True)
        manifest={'record':'https://zenodo.org/records/13838912','version':'1.2','archive_url':URL,'archive_size':SIZE,'files':[]}
        for entry in entries:
            variable=Path(entry.filename).name.rsplit('_',2)[0]
            if variable not in args.variables: continue
            destination=args.output/Path(entry.filename).name
            if not destination.exists():
                print(f'Downloading {entry.filename}',flush=True)
                content=archive.read(entry)
                destination.write_bytes(content)
            manifest['files'].append({'archive_path':entry.filename,'name':destination.name,'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
            (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if not manifest['files']: raise RuntimeError('No India data found in archive')

if __name__ == '__main__': main()
