# SPDX-License-Identifier: Apache-2.0
"""Resume a prepared desktop or headless station without building or downloading."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import preflight


def atomic_status(home,**values):
    target=home/'runtime/login-start.json';target.parent.mkdir(exist_ok=True)
    temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps({'at':time.time(),**values},indent=2))
    temporary.replace(target)


def resume(home,gpu,timeout=240):
    if (home/'runtime/maintenance').exists():
        atomic_status(home,state='maintenance',errors=[]);return 0
    deadline=time.monotonic()+timeout
    while True:
        if (home/'runtime/maintenance').exists():
            atomic_status(home,state='maintenance',errors=[]);return 0
        errors,_,_=preflight(home,gpu)
        if not errors:break
        atomic_status(home,state='waiting',errors=errors)
        if time.monotonic()>=deadline:
            atomic_status(home,state='failed',errors=errors);return 1
        time.sleep(5)
    if (home/'runtime/maintenance').exists():
        atomic_status(home,state='maintenance',errors=[]);return 0
    atomic_status(home,state='starting',errors=[])
    # Discard raw launch logs because a provider failure can contain a secret URL.
    try:
        result=subprocess.run([sys.executable,str(ROOT/'tools/stationctl.py'),'resume',str(home),'--gpu',gpu],
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=240)
        ok=result.returncode==0
    except (OSError,subprocess.TimeoutExpired):ok=False
    atomic_status(home,state='started' if ok else 'failed',errors=[] if ok else ['Station launch failed; inspect service status'])
    return 0 if ok else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('home',type=Path);parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    if sys.platform!='linux':raise SystemExit('Station startup requires Linux')
    import fcntl
    home=args.home.resolve();runtime=home/'runtime'
    if not runtime.is_dir():raise SystemExit('Prepare the station before installing automatic startup')
    with (runtime/'login-start.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        raise SystemExit(resume(home,args.gpu))


if __name__=='__main__':main()
