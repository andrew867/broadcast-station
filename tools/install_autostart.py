# SPDX-License-Identifier: Apache-2.0
"""Install or remove this user's desktop-login station startup entry."""
import argparse,hashlib,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def quote_exec(value):
    if any(ord(c)<32 for c in value):raise ValueError('Control characters are not supported in startup paths')
    # Desktop Entry Exec quoting, including literal field-code percent signs.
    value=value.replace('%','%%')
    for c in ('\\','"','`','$'):value=value.replace(c,'\\'+c)
    return '"'+value.replace('\\','\\\\')+'"'


def entry(home,gpu,python=sys.executable):
    command=[python,str(ROOT/'tools/session_start.py'),str(home),'--gpu',gpu]
    return '[Desktop Entry]\nType=Application\nName=Station playout\nComment=Resume the prepared station after desktop login\nExec='+ ' '.join(map(quote_exec,command))+'\nTerminal=false\nX-GNOME-Autostart-enabled=true\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['install','remove']);parser.add_argument('home',type=Path);parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    if sys.platform!='linux':raise SystemExit('Desktop startup requires Linux')
    home=args.home.resolve()
    if not (home/'compose.env').is_file():raise SystemExit('Run stationctl check or start successfully first')
    folder=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart'
    name='station-'+hashlib.sha256(str(home).encode()).hexdigest()[:10]+'.desktop'
    target=folder/name
    if args.action=='remove':target.unlink(missing_ok=True);print('Desktop startup entry removed; running services unchanged');return
    folder.mkdir(parents=True,exist_ok=True)
    target.write_text(entry(home,args.gpu),encoding='utf-8');target.chmod(0o600)
    print('Startup installed for the next desktop login. Keep this checkout and station directory in place.')


if __name__=='__main__':main()
