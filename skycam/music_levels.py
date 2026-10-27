"""Offline, bounded whole-track gain matching. Original files are never changed.

Run on the host: python -m skycam.music_levels /path/to/music --limit 100
Outputs live in .skycam-levels beneath that folder, outside the original list.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import wave

FORMATS={'.mp3','.wav','.flac','.ogg','.m4a','.aac'}
TARGET=-26.0


def fingerprint(path):
    s=path.stat()
    return {'size':s.st_size,'mtime_ns':s.st_mtime_ns}


def gain_for(lufs,peak,target=TARGET):
    if not all(math.isfinite(v) for v in (lufs,peak,target)):
        raise ValueError('Silent or unmeasurable track')
    return min(target-lufs,-3-peak,12.0)


def run(args,timeout=180):
    if os.name!='nt' and shutil.which('nice'):args=['nice','-n','15',*args]
    result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,text=True,timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:raise RuntimeError('Audio preparation failed; original retained')
    return result


def measure(path):
    r=run(['ffmpeg','-hide_banner','-nostdin','-threads','1','-filter_threads','1',
           '-protocol_whitelist','file,pipe','-i',str(path),'-vn','-sn','-dn',
           '-map','0:a:0','-af','aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-26:TP=-3:LRA=7:print_format=json','-f','null','-'])
    blocks=re.findall(r'\{\s*"input_i"[\s\S]*?\}',r.stderr)
    if not blocks:raise ValueError('No loudness measurement')
    value=json.loads(blocks[-1])
    return float(value['input_i']),float(value['input_tp'])


class LevelLibrary:
    def __init__(self,folder):
        self.folder=Path(folder);self.cache=self.folder/'.skycam-levels';self.rows={}

    def refresh(self):
        try:
            if self.cache.is_symlink():raise ValueError('Linked level cache')
            path=self.cache/'manifest.json'
            if path.stat().st_size>512000:raise ValueError('Oversized manifest')
            data=json.loads(path.read_text(encoding='utf-8'))
            if data.get('schema')!=1 or not isinstance(data.get('tracks'),dict):raise ValueError('Invalid manifest')
            self.rows={k:v for k,v in data['tracks'].items() if isinstance(k,str) and isinstance(v,dict)}
        except (OSError,ValueError):self.rows={}

    def ready(self,name):
        row=self.rows.get(name,{})
        try:
            original=self.folder/name;filename=row['output']
            if Path(name).name!=name or original.is_symlink():return None
            if not re.fullmatch(r'level-[a-f0-9]{24}\.wav',filename):return None
            path=self.cache/filename
            if path.is_symlink() or fingerprint(original)!=row['source_stat']:return None
            if path.stat().st_size!=row['output_size'] or not row.get('verified'):return None
            return filename
        except (OSError,KeyError,TypeError):return None

    def original(self,filename):
        return next((name for name,row in self.rows.items() if row.get('output')==filename),filename)


def prepare(path,library,target=TARGET):
    if Path(path).is_symlink() or library.cache.is_symlink():raise ValueError('Linked files are not supported')
    path=Path(path).resolve()
    if path.parent!=library.folder.resolve() or path.suffix.lower() not in FORMATS:
        raise ValueError('Choose an original local music file')
    before=fingerprint(path)
    info=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-of','json',str(path)]).stdout)
    duration=float(info['format']['duration'])
    if not math.isfinite(duration) or not 1<=duration<=1200:raise ValueError('Track must be 1 second to 20 minutes')
    if shutil.disk_usage(path.parent).free<duration*192000+500_000_000:raise ValueError('Insufficient preparation space')
    lufs,peak=measure(path);gain=gain_for(lufs,peak,target)
    with path.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
    key=hashlib.sha256(f'{digest}:{gain:.6f}:48k-stereo-v1'.encode()).hexdigest()[:24]
    library.cache.mkdir(exist_ok=True)
    output=library.cache/f'level-{key}.wav';tmp=output.with_suffix('.tmp')
    try:
        run(['ffmpeg','-hide_banner','-nostdin','-v','error','-threads','1','-filter_threads','1',
             '-protocol_whitelist','file,pipe','-i',str(path),'-map','0:a:0','-vn','-sn','-dn',
             '-af',f'aformat=sample_rates=48000:channel_layouts=stereo,volume={gain:.6f}dB','-ar','48000','-ac','2','-c:a','pcm_s16le','-f','wav','-y',str(tmp)])
        with wave.open(str(tmp),'rb') as w:
            if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(48000,2,2):raise ValueError('Prepared format mismatch')
            if abs(w.getnframes()/48000-duration)>1:raise ValueError('Prepared duration mismatch')
        after_lufs,after_peak=measure(tmp)
        if not math.isfinite(after_lufs) or not math.isfinite(after_peak) or after_peak> -2.5:
            raise ValueError('Prepared level check failed')
        if abs(after_lufs-(lufs+gain))>.3:raise ValueError('Prepared loudness differs from prediction')
        if fingerprint(path)!=before:raise ValueError('Original changed while preparing')
        tmp.replace(output)
        row={'source_stat':before,'source_sha256':digest,'output':output.name,'output_size':output.stat().st_size,
             'input_lufs':lufs,'input_peak_dbtp':peak,'gain_db':round(gain,6),'output_lufs':after_lufs,
             'output_peak_dbtp':after_peak,'target_lufs':target,'duration_seconds':duration,'verified':True}
        library.rows[path.name]=row
        manifest=library.cache/'manifest.tmp';manifest.write_text(json.dumps({'schema':1,'tracks':library.rows},indent=2),encoding='utf-8')
        manifest.replace(library.cache/'manifest.json')
        return row
    finally:tmp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('--limit',type=int,default=8)
    args=parser.parse_args()
    if not args.folder.is_dir() or args.folder.is_symlink() or not 1<=args.limit<=100:parser.error('Local folder and limit 1 to 100 required')
    lib=LevelLibrary(args.folder);lib.refresh();report=[]
    files=sorted(p for p in args.folder.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() in FORMATS)
    for path in files[:args.limit]:
        if lib.ready(path.name):report.append({'file':path.name,'status':'already prepared'});continue
        try:report.append({'file':path.name,'status':'prepared',**prepare(path,lib)})
        except Exception as exc:report.append({'file':path.name,'status':'unavailable','reason':str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__})
        print(json.dumps(report[-1]),flush=True)
    if lib.cache.exists():
        (lib.cache/'last-report.json').write_text(json.dumps({'at':time.time(),'files':report,'originals_changed':False},indent=2),encoding='utf-8')


if __name__=='__main__':main()
