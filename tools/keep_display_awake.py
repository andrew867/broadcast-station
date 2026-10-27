# SPDX-License-Identifier: Apache-2.0
"""Hold KDE idle inhibitors only while this station's HDMI engine is running."""
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import compose


def needs_inhibit(home,gpu):
    if (home/'runtime/maintenance').exists():return False
    if not json.loads((home/'station.json').read_text()).get('output',{}).get('hdmi'):return False
    result=subprocess.run(compose(home,gpu)+['ps','--status','running','-q','engine'],capture_output=True,text=True,timeout=10)
    return result.returncode==0 and bool(result.stdout.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('home',type=Path);parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    # Optional host dependency, never needed by the web/engine containers.
    import dbus
    bus=dbus.SessionBus()
    power=dbus.Interface(bus.get_object('org.freedesktop.PowerManagement','/org/freedesktop/PowerManagement/Inhibit'),'org.freedesktop.PowerManagement.Inhibit')
    screen=dbus.Interface(bus.get_object('org.freedesktop.ScreenSaver','/ScreenSaver'),'org.freedesktop.ScreenSaver')
    cookies=[]
    try:
        while True:
            try:running=needs_inhibit(args.home.resolve(),args.gpu)
            except (OSError,ValueError,subprocess.SubprocessError):running=False
            if running and not cookies:
                for interface in (power,screen):cookies.append((interface,interface.Inhibit('Station playout','HDMI program output')))
                screen.SimulateUserActivity()
            elif not running:
                while cookies:
                    interface,cookie=cookies.pop();interface.UnInhibit(cookie)
            time.sleep(10)
    finally:
        while cookies:
            interface,cookie=cookies.pop();interface.UnInhibit(cookie)


if __name__=='__main__':main()
