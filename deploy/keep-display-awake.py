"""Hold KDE's idle inhibitors while CasparCG is running, release on service stop."""
import dbus
import subprocess
import time

bus=dbus.SessionBus()
power=dbus.Interface(bus.get_object('org.freedesktop.PowerManagement','/org/freedesktop/PowerManagement/Inhibit'),'org.freedesktop.PowerManagement.Inhibit')
screen=dbus.Interface(bus.get_object('org.freedesktop.ScreenSaver','/ScreenSaver'),'org.freedesktop.ScreenSaver')
cookies=None
try:
    while True:
        running=subprocess.run(['docker','inspect','--format={{.State.Running}}','skycam-caspar'],capture_output=True,text=True).stdout.strip()=='true'
        if running and cookies is None:
            cookies=(power.Inhibit('SkyCam broadcast','Keep the HDMI program output visible'),screen.Inhibit('SkyCam broadcast','HDMI program output'))
            screen.SimulateUserActivity()
        elif not running and cookies is not None:
            power.UnInhibit(cookies[0]);screen.UnInhibit(cookies[1]);cookies=None
        time.sleep(10)
finally:
    if cookies:
        power.UnInhibit(cookies[0]);screen.UnInhibit(cookies[1])
