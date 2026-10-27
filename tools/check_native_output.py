# SPDX-License-Identifier: Apache-2.0
"""Exercise isolated native video, graphics and audio with desktop or headless rendering."""
import argparse,json,os,secrets,shutil,socket,subprocess,tempfile,time,uuid,sys
from pathlib import Path
import xml.etree.ElementTree as ET


def run(args,timeout=30):
    return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True,timeout=timeout)


def amcp(port,command):
    with socket.create_connection(('127.0.0.1',port),timeout=4) as connection:
        connection.settimeout(10);connection.sendall((command+'\r\n').encode());reply=connection.recv(8192)
    if not reply.startswith((b'200 ',b'201 ',b'202 ')):raise RuntimeError('Native command rejected: '+reply[:200].decode(errors='replace'))


def check(image,evidence,headless=False,gpu='software',profile='720p3000'):
    evidence.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    identity='station-native-smoke-'+uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix='station-native-') as folder:
        home=Path(folder)
        for name in ('media','logs','data','templates','runtime','music','engine-data'):(home/name).mkdir()
        config=ET.parse(root/'deploy/casparcg.config');channels=config.getroot().find('channels')
        for channel in list(channels)[1:]:channels.remove(channel)
        channels[0].find('video-mode').text=profile
        channels[0].find('consumers').clear()
        if headless:
            config.getroot().find('html/angle-backend').text='vulkan'
            config.getroot().find('html/remote-debugging-port').text='0'
            config.getroot().find('log-level').text='info'
        config.getroot().find('paths/log-path').set('disabled','true')
        config.write(home/'casparcg.config',encoding='utf-8',xml_declaration=True)
        (home/'runtime/native-smoke.html').write_text('<!doctype html><html><head><style>html,body{margin:0;background:transparent}section{position:absolute;left:32px;top:32px;width:800px;height:160px;background:#123456;color:white;font:48px sans-serif}p{margin:40px}</style></head><body><section><p>Station graphics test</p></section></body></html>')
        run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','ffv1','-threads','1','-c:a','pcm_s16le',str(home/'music/source.mkv')])
        environment={**os.environ,'STATION_HOME':str(home),'STATION_UID':str(os.getuid()),'STATION_GID':str(os.getgid())}
        compose=['docker','compose','-f',str(root/'compose.station.yaml')]
        xvfb=None;log=None
        if not headless:
            auth=home/'xauthority';auth.touch();display=':99'
            run(['xauth','-f',str(auth),'add',display,'.',secrets.token_hex(16)])
            sys.path.insert(0,str(root))
            from tools.stationctl import prepare_xauthority
            container_auth=prepare_xauthority(home,display,auth)
            environment.update(DISPLAY=display,STATION_XAUTHORITY=str(container_auth))
            compose+=['-f',str(root/'compose.desktop.yaml')]
        else:
            compose+=['-f',str(root/'compose.headless.yaml')]
        contract=json.loads(subprocess.check_output(compose+['config','--format','json'],env=environment,text=True))
        mounts=[]
        for mount in contract['services']['engine']['volumes']:
            assert mount['type']=='bind'
            mounts+=['-v',mount['source']+':'+mount['target']+(':ro' if mount.get('read_only') else '')]
        if not headless:
            log=(evidence/'native-smoke-display.log').open('w')
            xvfb=subprocess.Popen(['Xvfb',display,'-screen','0','1280x720x24','-auth',str(auth),'-nolisten','tcp'],stdout=log,stderr=log)
        options=[]
        if gpu=='software':options+=['--cpus','2','-e','LIBGL_ALWAYS_SOFTWARE=1','-e','LP_NUM_THREADS=2']
        elif gpu=='nvidia':options+=['--gpus','all','-e','NVIDIA_DRIVER_CAPABILITIES=all']
        elif gpu=='intel':options+=['--device','/dev/dri/renderD128','--group-add',str(Path('/dev/dri/renderD128').stat().st_gid)]
        if headless:
            if gpu!='nvidia':options+=['-e','EGL_PLATFORM=surfaceless']
            options+=['--entrypoint','env']
            tail=['-u','DISPLAY','-u','WAYLAND_DISPLAY','-u','XAUTHORITY','/usr/bin/casparcg-server-2.5','/workspace/casparcg.config']
        else:
            options+=['-e','DISPLAY='+display,'-e','XAUTHORITY=/tmp/station.xauthority'];tail=[]
        try:
            for _ in range(30):
                if headless:break
                if xvfb.poll() is not None:raise RuntimeError('Isolated display did not start')
                if Path('/tmp/.X11-unix/X99').exists():break
                time.sleep(.2)
            run(['docker','run','-d','--name',identity,'--user',f'{os.getuid()}:{os.getgid()}','--memory','3g','--read-only','--tmpfs','/tmp:rw,size=512m','--shm-size','512m','--cap-drop','ALL','--security-opt','no-new-privileges','-p','127.0.0.1::5250','-e','LD_PRELOAD=/usr/lib/station/cef-mallinfo-compat.so:/usr/lib/station/uc-image-copy.so',*options,*mounts,image,*tail])
            port=int(run(['docker','port',identity,'5250/tcp']).strip().rsplit(':',1)[1])
            deadline=time.monotonic()+60
            while True:
                try:amcp(port,'VERSION');break
                except (OSError,RuntimeError):
                    if time.monotonic()>deadline:raise
                    time.sleep(1)
            amcp(port,'PLAY 1-10 "/workspace/media/music/source.mkv" LOOP')
            amcp(port,'PLAY 1-20 [HTML] "file:///workspace/runtime/native-smoke.html"')
            time.sleep(8)
            encoder='h264_nvenc -preset:v p1' if gpu=='nvidia' else 'libx264 -preset:v ultrafast -threads:v 2'
            amcp(port,'ADD 1-1 FILE "/workspace/runtime/program.mkv" -codec:v '+encoder+' -codec:a pcm_s16le -ar:a 48000 -format matroska')
            time.sleep(12)
            amcp(port,'REMOVE 1-1');time.sleep(1)
            output=home/'runtime/program.mkv'
            data=json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(output)]))
            (evidence/'native-smoke-probe.json').write_text(json.dumps(data,indent=2))
            shutil.copyfile(output,evidence/'native-smoke.mkv')
            video=next(s for s in data['streams'] if s['codec_type']=='video')
            audio=next(s for s in data['streams'] if s['codec_type']=='audio')
            size={'720p3000':(1280,720),'1080p3000':(1920,1080),'2160p3000':(3840,2160)}[profile]
            assert (video['width'],video['height'])==size and int(video['nb_read_frames'])>=60
            assert audio['sample_rate']=='48000' and int(audio['nb_read_frames'])>0
            run(['ffmpeg','-v','error','-xerror','-i',str(output),'-f','null','-'])
            levels=run(['ffmpeg','-hide_banner','-i',str(output),'-vn','-af','volumedetect','-f','null','-'])
            assert 'max_volume: -inf' not in levels and 'max_volume:' in levels
            pixels=subprocess.check_output(['ffmpeg','-v','error','-ss','2','-i',str(output),'-vf','crop=16:16:40:40','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],timeout=30)
            assert len(pixels)==16*16*3
            colour=[sum(pixels[channel::3])/(16*16) for channel in range(3)]
            assert all(abs(actual-expected)<15 for actual,expected in zip(colour,(18,52,86))), 'CEF graphics marker was not rendered'
            run(['ffmpeg','-v','error','-ss','2','-i',str(output),'-frames:v','1',str(evidence/'native-smoke.png')])
            engine_log=run(['docker','logs','--tail','250',identity])
            if headless:
                assert 'Initializing OpenGL Device (EGL)' in engine_log
                if gpu in ('intel','nvidia'):
                    vendor=[line for line in engine_log.splitlines() if 'Initialized OpenGL ' in line]
                    assert any(gpu.lower() in line.lower() for line in vendor), 'Expected hardware OpenGL vendor not found'
            result={'passed':True,'scope':'Bounded native video, CEF graphics, mix and encode smoke; not full-rundown or long-term performance qualification','headless':headless,'gpu':gpu,'encoder':'h264_nvenc' if gpu=='nvidia' else 'libx264','video_frames':int(video['nb_read_frames']),'size':list(size),'audio_rate':48000,'audio_present':True,'decode_errors':False,'cef_graphics_present':True,'graphics_marker_rgb':colour}
            (evidence/'native-smoke.json').write_text(json.dumps(result,indent=2))
            print(json.dumps(result))
        finally:
            try:(evidence/'native-smoke-engine.log').write_text(run(['docker','logs','--tail','120',identity]))
            except Exception:pass
            subprocess.run(['docker','rm','-f',identity],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if xvfb is not None:xvfb.terminate();xvfb.wait(timeout=10)
            if log is not None:log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image');parser.add_argument('--evidence',type=Path,default=Path('evidence'))
    parser.add_argument('--headless',action='store_true');parser.add_argument('--gpu',choices=['software','nvidia','intel'],default='software');parser.add_argument('--profile',choices=['720p3000','1080p3000','2160p3000'],default='720p3000')
    args=parser.parse_args()
    if args.gpu!='software' and not args.headless:parser.error('Hardware acceptance currently requires --headless')
    check(args.image,args.evidence,args.headless,args.gpu,args.profile)
