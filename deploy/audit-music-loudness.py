"""Bounded, read-only FFmpeg input loudness measurements. No program commands.

Explicit local files only. Reports input LUFS/LRA/dBTP, never normalized output.
Short excerpts are labelled and are not whole-track loudness measurements.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def measure(path, seconds=60, ffmpeg='ffmpeg'):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {'.wav','.flac','.mp3','.m4a','.aac','.ogg'}:
        raise ValueError('Choose an existing local audio file, not a symlink')
    if not 10 <= seconds <= 300:
        raise ValueError('Measurement duration must be 10 to 300 seconds')
    started=time.monotonic()
    args=[ffmpeg,'-hide_banner','-nostdin','-threads','1','-filter_threads','1',
          '-protocol_whitelist','file,pipe','-i',str(path.resolve()),'-t',str(seconds),
          '-map','0:a:0','-vn','-sn','-dn','-af',
          'loudnorm=I=-23:TP=-2:LRA=7:print_format=json','-f','null','-']
    if os.name!='nt' and shutil.which('nice'):args=['nice','-n','15',*args]
    result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE,text=True,timeout=120,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:
        raise RuntimeError('Audio measurement failed; original file unchanged')
    blocks=re.findall(r'\{\s*"input_i"[\s\S]*?\}',result.stderr)
    if not blocks:raise ValueError('FFmpeg did not report input loudness')
    raw=json.loads(blocks[-1])
    metrics={key:float(raw[field]) for key,field in [('integrated_lufs','input_i'),('true_peak_dbtp','input_tp'),('loudness_range_lu','input_lra')]}
    valid=all(math.isfinite(v) for v in metrics.values())
    return {'file':path.name,'maximum_excerpt_seconds':seconds,'measured_in_seconds':round(time.monotonic()-started,3),
            'status':'measured' if valid else 'no measurable loudness',
            **{k:v if math.isfinite(v) else None for k,v in metrics.items()},
            'basis':'Input excerpt before station volume/ducking. No normalization applied.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',type=Path,nargs='+')
    parser.add_argument('--seconds',type=int,default=60)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if len(args.files)>8:parser.error('At most eight files per audit')
    inputs={p.resolve() for p in args.files}
    if args.output.resolve() in inputs or args.output.suffix!='.json':parser.error('Output must be a separate JSON report')
    rows=[]
    for path in args.files:
        try:rows.append(measure(path,args.seconds))
        except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
            rows.append({'file':path.name,'status':'unavailable','error':type(exc).__name__})
    report={'created_at':time.time(),'files':rows,'program_changed':False,
            'limits':'Excerpts do not establish complete-track loudness. No output target or compliance claim; -23 LUFS is only the analysis filter setting.'}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
