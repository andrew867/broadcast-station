from .public_errors import public_error
from .station_config import CONFIG, secret
"""Persistent ingest, two off-air scene buses, and one uninterrupted program bus.

1: program (5 music, 10 whole scene, 21 ticker)
2/3: alternate scene banks, with no output consumers
4..7: native-sized camera playout at 30p, allocated to program and preview
8: native map frames on layer 10, aircraft refreshed at 1 Hz
Only channel 1 is mixed/encoded. A scene is routed as one draw-frame tree.
"""
import asyncio
import json
from pathlib import Path
import os
import socket
import threading
import time
import xml.etree.ElementTree as ET
from .sources import CAMERAS, QUADS
from .map_scenes import MAP_SCENES, DIRECT_SCENES
from .graphics import render, loading_card, recovery_badge
from .camera_recovery import PicturePolicy
from .resource_budget import GraphicsBudget
from .flight_features import audio_levels
from .transport_health import transport_fault
from .output_timing import PROGRAM_FPS,PROGRAM_MODE,PROGRAM_FORMAT,ENCODED_FPS,publishing_video,transition_frames

ENABLED=os.environ.get('SKYCAM_PLAYOUT')=='1' and os.environ.get('STATION_OFFLINE','1')=='0'
LOCK=threading.RLock()
STATUS={'enabled':ENABLED,'connected':False,'ready':False,'cameras':{},'error':None}
REGIONS={}
MAP_REFRESH={}
DIRECT_MEDIA={}
DIRECT_OVERLAY={}
SCENE_DECORATE=None
DECORATION_KEY=None
_last_used={};WARM_INPUTS=0
_loaded=set();_source_health={};_slates=set()
_slate_visible={}
_heartbeat={};_last={};_changed={};_advances={};_retry={}
_delivery_progress={}
_native_metrics={}
_transport={};_transport_recovered={}
_picture_policies={};_recovery_badges={}
_ready=False;_bank=2;_camera=None;_prepared=None;_hold_since=None
_retiring=None
_output_samples=[];_output_change=0;_last_publish=0;_screen_retry=0
CAMERA_AUDIO=False
CAMERA_TRANSPORT=os.environ.get('SKYCAM_CAMERA_TRANSPORT','rtsp')
if CAMERA_TRANSPORT not in ('rtmp','rtsp'):raise ValueError('Unknown camera transport')
_graphics_budget=GraphicsBudget()

def command(text,xml=False,lines=1):
    with socket.create_connection((CONFIG.output.amcp_host,CONFIG.output.amcp_port),timeout=3) as s:
        s.settimeout(3);s.sendall((text+'\r\n').encode());data=b''
        while True:
            chunk=s.recv(65536)
            if not chunk:break
            data+=chunk
            if not xml and data.count(b'\r\n')>=lines:break
            if xml and b'<?xml' in data:
                try:ET.fromstring(data[data.index(b'<?xml'):]);break
                except ET.ParseError:pass
    reply=data.decode(errors='replace')
    if not reply.startswith(('200 ','201 ','202 ')):raise RuntimeError('CasparCG command failed, response '+reply[:3] if reply else 'No reply from CasparCG')
    return reply

def info(channel):
    result=command(f'INFO {channel}',xml=True)
    return ET.fromstring(result[result.index('<?xml'):])

def heartbeat(region):
    if region not in {*REGIONS,*MAP_SCENES}:raise ValueError('Unknown graphics region')
    _heartbeat[region]=time.monotonic()

def graphics_region(region):
    layer,height,y=REGIONS[region]
    command(f'PLAY 1-{layer} [HTML] "{CONFIG.output.studio_url}/broadcast?region={region}&width=3840&height={height}"')
    command(f'MIXER 1-{layer} FILL 0 {y/2160:.9f} 1 {height/2160:.9f}')
    _heartbeat[region]=time.monotonic()

def screen():
    if not CONFIG.output.hdmi:return
    x,y,w,h=CONFIG.output.screen_rect
    command(f'ADD 1-3 SCREEN {CONFIG.output.screen} GPU BORDERLESS NON_INTERACTIVE X {x} Y {y} WIDTH {w} HEIGHT {h} NAME "Station Program"')

def publish():
    global _last_publish
    if not CONFIG.output.publish:return
    destination=secret('publish_url') or CONFIG.output.publish_url
    if not destination:raise ValueError('Publishing needs a destination')
    if any(ord(c)<33 or c in '\"' for c in destination):raise ValueError('Invalid publishing destination')
    from urllib.parse import urlsplit
    scheme=urlsplit(destination).scheme
    if scheme not in ('rtmp','rtmps','srt','udp'):raise ValueError('Unsupported publishing transport')
    mux='mpegts' if scheme in ('srt','udp') else 'flv'
    tuning='-preset:v p1 -tune:v ll -surfaces:v 8 -delay:v 0' if CONFIG.output.encoder=='h264_nvenc' else f'-preset:v {CONFIG.output.x264_preset} -tune:v zerolatency'
    kbps=CONFIG.output.bitrate_kbps
    video_filter,scan_options=publishing_video(PROGRAM_MODE)
    command(f'ADD 1-1 FILE {json.dumps(destination)} -codec:v {CONFIG.output.encoder} -filter:v {video_filter} {scan_options} {tuning} -b:v {kbps}k -maxrate:v {kbps}k -bufsize:v {kbps*2}k -g:v {round(ENCODED_FPS*2)} -bf:v 0 -codec:a aac -channel_layout:a stereo -filter:a pan=stereo|c0=c0|c1=c1 -b:a 192k -ar:a 48000 -format {mux}')
    _last_publish=time.monotonic()

def source_layer(camera):return 10
def source_channel(camera):return CAMERAS[camera]['channel']
def required(camera):return set(QUADS[camera]) if camera in QUADS else {camera} if camera in CAMERAS else set()

def source_picture(camera,live):
    # Commit both visibility changes on one engine frame. A late-arriving video
    # must not show through its loading underlay in a routed scene dissolve.
    ch=source_channel(camera)
    command(f'MIXER {ch}-1 OPACITY {int(not live)} DEFER')
    command(f'MIXER {ch}-10 OPACITY {int(live)} DEFER')
    command(f'MIXER {ch} COMMIT')
    _slate_visible[camera]=not live


def reload_camera(camera):
    # Reconnection touches only this ingest producer, never the output or music.
    _retry[camera]=time.monotonic()
    source_picture(camera,False)
    _picture_policies.pop(camera,None)
    command(f'PLAY {source_channel(camera)}-{source_layer(camera)} {json.dumps(CAMERAS[camera][CAMERA_TRANSPORT])} SCALE_MODE FILL')
    _loaded.add(camera)
    _transport_recovered[camera]=time.time()
    _retry[camera]=time.monotonic();_last[camera]=None;_advances[camera]=0;_changed.pop(camera,None)

def observe_sources(root,now,camera_only=None):
    for camera in ([camera_only] if camera_only else CAMERAS):
        # Media time can advance at EOF or from audio while video is dead.
        # The patched engine reports only video frames actually delivered.
        node=root.find(f'.//layer_{source_layer(camera)}/foreground/file/video-frame')
        decoded=root.find(f'.//layer_{source_layer(camera)}/foreground/file/source-video-frame')
        # Filters can duplicate a keyframe to channel cadence. Those duplicates
        # must never reset the held-picture age or make a dead source ready.
        if decoded is not None and decoded.text is not None and int(decoded.text)>=0:node=decoded
        value=float(node.text) if node is not None else None
        delivered=root.find(f'.//layer_{source_layer(camera)}/foreground/file/video-frame')
        delivered=float(delivered.text) if delivered is not None else None
        previous=_last.get(camera)
        progress=_delivery_progress.get(camera,{})
        reset=(previous is None or value is None or delivered is None or value<previous
               or (progress.get('frame') is not None and delivered<progress['frame']))
        if reset:
            progress={}
            _changed.pop(camera,None)
            _advances[camera]=0
        else:
            if value>previous:progress['decoded_at']=now
            if progress.get('frame') is not None and delivered>progress['frame']:progress['delivered_at']=now
            if 'decoded_at' in progress and 'delivered_at' in progress:
                fresh_at=min(progress['decoded_at'],progress['delivered_at'])
                if fresh_at>_changed.get(camera,float('-inf')):
                    _changed[camera]=fresh_at
                    _advances[camera]=_advances.get(camera,0)+1
        progress['frame']=delivered
        _delivery_progress[camera]=progress
        _last[camera]=value
        age=now-_changed.get(camera,now-999)
        moving=value is not None and _advances.get(camera,0)>=2 and age<2.5
        def metric(name):
            n=root.find(f'.//layer_{source_layer(camera)}/foreground/file/{name}')
            try:return int(n.text) if n is not None else None
            except (TypeError,ValueError):return None
        _native_metrics[camera]={'decoded_dropped':metric('decoded-dropped'),
            'delivered_video_frame':delivered,'decoded_video_frame':value,
            'corrupt_discarded':metric('corrupt-discarded'),'decoded_queue_depth':metric('decoded-queue-depth'),
            'decoded_queue_age_ms':metric('decoded-queue-age-ms'),'observed_at':time.time(),
            'recovery_mode':metric('recovery-mode'),'recovery_episodes':metric('recovery-episodes'),
            'recovery_skipped':metric('recovery-skipped'),'recovery_errors':metric('recovery-errors')}
        STATUS['cameras'][camera]={'moving':moving,'ready':moving,'video_frame':value,
            'frame_age_s':round(age,2) if age<900 else None,'stalled_seconds':round(age,1),
            'state':'ready' if moving else 'warming' if now-_retry.get(camera,0)<5 else 'reconnecting'}

def read_source_health():
    global _source_health,_transport
    path=Path(os.environ.get('SKYCAM_DATA',Path(__file__).parent.parent/'data'))/'source-health.json'
    try:
        data=json.loads(path.read_text());now=time.time()
        if now-data['checked_at']>3:raise ValueError('Source monitor is stale')
        _source_health=data['cameras']
        STATUS['network']=data.get('network')
    except (OSError,ValueError,KeyError):_source_health={}
    try:
        transport=json.loads((path.parent/'runtime/camera-transport.json').read_text())
        if time.time()-transport['checked_at']>5:raise ValueError('Stale transport observer')
        _transport=transport['paths']
    except (OSError,ValueError,KeyError):pass  # Retain known damage until a decoder has been renewed.
    for camera in CAMERAS:
        h=dict(_source_health.get(camera,{}));age=time.time()-h.get('last_frame_at',0)
        h['ready']=bool(h.get('ready') and 0<=age<2.5);h['moving']=h['ready']
        h['frame_age_s']=round(age,2) if age<900 else None
        if not h['ready']:h['state']='reconnecting'
        _source_health[camera]=h
        h['native_metrics']=dict(_native_metrics.get(camera,{})) if camera in _loaded else None
        h['transport']=dict(_transport.get(CAMERAS[camera]['media_path'],{}))
        STATUS['cameras'][camera]=h

def available(camera):
    # Scene availability is independent of the camera connection. Missing
    # pictures have a permanent loading underlay and reconnect in the background.
    return camera in {*CAMERAS,*QUADS,*MAP_SCENES,*DIRECT_SCENES}

def ensure_inputs(camera):
    # The small independent reader is the readiness gate. Opening a missing
    # source in the native engine can stall its route even behind a slate.
    read_source_health()
    for key in required(camera):
        _last_used[key]=time.monotonic()
        ch=source_channel(key)
        if key not in _slates:
            path=loading_card(key)
            command(f'PLAY {ch}-1 "/workspace/data-web/graphics/{path.name}"')
            badge=recovery_badge()
            command(f'PLAY {ch}-11 "/workspace/data-web/graphics/{badge.name}"')
            command(f'MIXER {ch}-11 OPACITY 0');_recovery_badges[key]=False
            source_picture(key,key in _loaded)
            _slates.add(key)
        if CAMERAS[key]['enabled'] and _source_health.get(key,{}).get('ready') and key not in _loaded and time.monotonic()-_retry.get(key,0)>30:
            try:reload_camera(key)
            except (RuntimeError,OSError) as exc:
                _retry[key]=time.monotonic()
                STATUS['source_error']=public_error(exc)[:160]


def retire_stalled_input(key,now):
    """Keep the slate route, but remove a decoder with no new picture for 8s."""
    if key not in _loaded:return False
    # A restarted controller can adopt a producer that was already stalled.
    # Give that producer one fixed grace period. Using now as a default on
    # every check would move the deadline forever and strand its loading card.
    adopted_at=_retry.setdefault(key,now)
    if now-_changed.get(key,adopted_at)<=8:return False
    if key in _slates:source_picture(key,False)
    command(f'CLEAR {source_channel(key)}-10')
    _loaded.discard(key);_last.pop(key,None);_changed.pop(key,None);_advances.pop(key,None)
    _native_metrics.pop(key,None);_picture_policies.pop(key,None)
    STATUS['cameras'].setdefault(key,{})['recovery_note']='Decoder released; waiting for recent independently decoded pictures'
    return True

def reset_source(camera):
    global _prepared
    if ENABLED and _ready:
        command(f'CLEAR {source_channel(camera)}')
    _last_used.pop(camera,None);_loaded.discard(camera);_slates.discard(camera);_slate_visible.pop(camera,None)
    _changed.pop(camera,None);_last.pop(camera,None);_retry.pop(camera,None);_prepared=None
    _transport_recovered.pop(camera,None)
    _picture_policies.pop(camera,None);_recovery_badges.pop(camera,None)
    STATUS['cameras'].pop(camera,None)

def release_unused():
    # Independent health readers stay connected to every enabled source. Keep
    # only the full-resolution program/preview inputs. Never
    # evict a route while either scene bank still needs it.
    protected=required(_camera)|required(_prepared['camera'] if _prepared else None)
    if _retiring:protected|=required(_retiring['camera'])
    keep=set(protected)
    for key in sorted(_loaded-protected,key=lambda k:_last_used.get(k,0),reverse=True):
        if len(keep)<WARM_INPUTS:keep.add(key)
    for key in list(_loaded-keep):
        command(f'CLEAR {source_channel(key)}-10')
        _loaded.discard(key);_retry.pop(key,None);_last.pop(key,None);_changed.pop(key,None);_advances.pop(key,None)
        if key in _slates:source_picture(key,False)


def prime_inputs(camera):
    # A disconnected feed never prevents taking the complete scene. Healthy
    # newly loaded producers get a bounded off-air warmup, checked by advancing
    # decoded media time rather than connection success.
    read_source_health()
    pending={key for key in required(camera) if key in _loaded and _source_health.get(key,{}).get('ready') and (_slate_visible.get(key,True) or time.monotonic()-_changed.get(key,0)>2.5)}
    deadline=time.monotonic()+8
    while pending and time.monotonic()<deadline:
        for key in list(pending):
            try:
                observe_sources(info(source_channel(key)),time.monotonic(),key)
                if transport_fault(_transport.get(CAMERAS[key]['media_path']),_transport_recovered.get(key,0),time.time()):
                    pending.remove(key);continue
                now=time.monotonic();age=now-_changed[key] if key in _changed else None
                mode=(_native_metrics.get(key) or {}).get('recovery_mode') or 0
                display=_picture_policies.setdefault(key,PicturePolicy()).update(now,_last.get(key),age,key in _loaded,mode)
                if display!='loading':
                    if _slate_visible.get(key):source_picture(key,True)
                    badge=display in ('held','recovering')
                    if _recovery_badges.get(key)!=badge:
                        command(f'MIXER {source_channel(key)}-11 OPACITY {int(badge)}');_recovery_badges[key]=badge
                    pending.remove(key)
            except (RuntimeError,OSError,ET.ParseError):pending.remove(key)
        if pending:time.sleep(.06)

def state_key(state):return state.model_dump_json()+json.dumps(QUADS.get(state.camera,[]))+json.dumps({k:CAMERAS[k] for k in sorted(required(state.camera))},sort_keys=True)

def finish_handover():
    """Confirm the new native route before retiring the old scene.

Finish an overloaded dissolve with a prepared cut. Failed confirmation keeps
both banks and their camera inputs protected until a later retry succeeds.
"""
    global _retiring
    if not _retiring:return
    pending=_retiring;bank=pending['destination'];frames=pending['frames']
    fallback=pending.get('fallback_cut',False);began=time.monotonic()
    def confirmed():
        foreground=info(1).find('.//layer_10/foreground')
        if foreground is None:return False
        return foreground.find('transition') is None and foreground.findtext('route/channel')==str(bank)
    deadline=began+max(1.,frames/PROGRAM_FPS*2)
    while not confirmed():
        if time.monotonic()>=deadline:
            if fallback:
                STATUS['transition_error']='New program route not confirmed; outgoing bank retained'
                raise RuntimeError(STATUS['transition_error'])
            command(f'LOADBG 1-10 route://{bank}');time.sleep(.08)
            command('PLAY 1-10');fallback=True;pending['fallback_cut']=True;deadline=time.monotonic()+1
        time.sleep(.025)
    command(f'CLEAR {pending["bank"]}')
    result={'at':time.time(),'camera':_camera,'seconds':round(time.monotonic()-pending['started'],3),
            'requested_frames':frames,'fallback_cut':fallback}
    STATUS['transition']=result
    STATUS['transition_history']=(STATUS.get('transition_history',[])+[result])[-24:]
    STATUS.pop('transition_error',None);_retiring=None


def prepare(camera,state):
    """Prepare only the unused bank. A failure leaves the program bank untouched."""
    global _prepared
    with LOCK:
        if not _ready:raise RuntimeError('Playout is reconnecting')
        finish_handover()
        if not available(camera):raise ValueError('Unknown scene')
        try:ensure_inputs(camera)
        except Exception:
            release_unused();raise
        direct_path=DIRECT_MEDIA[camera]() if camera in DIRECT_MEDIA else None
        key=state_key(state)+json.dumps(direct_path,sort_keys=True)+(str(DECORATION_KEY()) if DECORATION_KEY else '')
        if _prepared and _prepared['key']==key:return _prepared
        if camera in MAP_REFRESH:MAP_REFRESH[camera]()
        prime_inputs(camera)
        bank=3 if _bank==2 else 2
        command(f'CLEAR {bank}');command(f'MIXER {bank} CLEAR')
        if isinstance(direct_path,dict):
            if direct_path.get('background'):command(f'PLAY {bank}-9 {json.dumps(direct_path["background"])}')
            command(f'LOAD {bank}-10 {json.dumps(direct_path["path"])}'+(' LOOP' if direct_path.get('loop') else '')+' SCALE_MODE FIT')
            command(f'MIXER {bank}-10 FILL .07 .025 .86 .86')
            command(f'MIXER {bank}-10 VOLUME 0')
        elif direct_path:command(f'PLAY {bank}-10 {json.dumps(direct_path)}')
        elif camera in MAP_SCENES:command(f'PLAY {bank}-10 route://{MAP_SCENES[camera]["channel"]}-10')
        else:
            for i,input_id in enumerate(QUADS[camera] if camera in QUADS else [camera]):
                layer=10+i
                command(f'PLAY {bank}-{layer} route://{source_channel(input_id)}')
                if camera in QUADS:command(f'MIXER {bank}-{layer} FILL {(i%2)*.5} {(i//2)*.5} .5 .5')
                command(f'MIXER {bank}-{layer} VOLUME 0')
        path=DIRECT_OVERLAY[camera]() if camera in DIRECT_OVERLAY else '/workspace/data-web/graphics/'+render(state).name
        command(f'PLAY {bank}-20 {json.dumps(path)}')
        if SCENE_DECORATE:SCENE_DECORATE(bank,camera)
        # LOADBG keeps the entire scene off air while its route receives frames.
        command(f'LOADBG 1-10 route://{bank}')
        time.sleep(.12)
        _prepared={'bank':bank,'camera':camera,'key':key,'at':time.monotonic(),'video':isinstance(direct_path,dict)}
        STATUS['preview']={'camera':camera,'ready':True,'channel':bank}
        release_unused()
        return _prepared

def take(camera,frames=30,state=None):
    global _bank,_camera,_prepared,_hold_since,_retiring
    if not ENABLED:raise ValueError('Live playout is enabled only on the broadcast host')
    frames=transition_frames(frames)
    with LOCK:
        prepared=prepare(camera,state)
        bank=prepared['bank'];old=_bank;old_camera=_camera
        if prepared.get('video'):command(f'PLAY {bank}-10')
        # The background route was primed above. LOADBG again is unnecessary for
        # a cut; a MIX producer is loaded and primed for a dissolve.
        if frames:
            command(f'LOADBG 1-10 route://{bank} MIX {frames} LINEAR');time.sleep(.08)
        command('PLAY 1-10')
        _retiring={'bank':old,'camera':old_camera,'destination':bank,'frames':frames,'started':time.monotonic()}
        _bank=bank;_camera=camera;_prepared=None;_hold_since=None
        STATUS['program']={'camera':camera,'channel':bank,'held':False}
        STATUS['preview']=None
        finish_handover()
        release_unused()
    return {'camera':camera,'accepted':True,'note':'Complete scene taken to program. Picture and graphics switch together.'}

def update_graphics(state):
    if ENABLED and _ready:take(state.camera,0,state)

def refresh_graphics():
    pass  # Native ticker reads the saved broadcast state.

def bootstrap(state,root):
    global _ready,_bank,_camera,_prepared,_retiring
    # Adopt an existing routed program after an operator-service restart.
    node=root.find('.//layer_10/foreground/route/channel')
    if node is not None and int(node.text) in (2,3):
        _bank=int(node.text);_camera=state.camera;_ready=True
    else:
        _bank=2;_camera=None;_ready=True;_retiring=None
    _prepared=None
    _loaded.clear();_slates.clear()
    for camera in CAMERAS:
        if info(source_channel(camera)).find('.//layer_10/foreground/file/time') is not None:_loaded.add(camera)
    ensure_inputs(state.camera)
    release_unused()
    if root.find('.//port_1') is None:publish()
    STATUS['ndi']={'enabled':root.find('.//port_900') is not None,'name':'SkyCam Program HD','channel':1,'format':f'720p{PROGRAM_FPS}'}
    if root.find('.//port_3') is None and root.find('.//port_601') is None:screen()
    STATUS.update(connected=True,ready=True,graphics_epoch=STATUS.get('graphics_epoch',0)+1,program={'camera':_camera,'channel':_bank,'held':False})

def check(state):
    global _ready,_output_change,_screen_retry,_hold_since
    now=time.monotonic()
    with LOCK:
        try:root=info(1)
        except (OSError,RuntimeError,ET.ParseError) as exc:
            _ready=False;STATUS.update(connected=False,ready=False,error=public_error(exc)[:200],checked_at=time.time());STATUS['output']={**(STATUS.get('output') or {}),'moving':False,'measured_fps':None};return None
        # Do not timestamp the counter before waiting behind a long prepare.
        now=time.monotonic()
        if _retiring and (root.find('.//layer_10/foreground/route') is not None or root.find('.//layer_10/foreground/transition') is not None):
            try:finish_handover();release_unused()
            except (OSError,RuntimeError,ET.ParseError) as exc:STATUS['transition_error']=public_error(exc)[:200]
        STATUS['camera_transport']=CAMERA_TRANSPORT
        if _ready and root.find('.//layer_10/foreground/route/channel') is None and root.find('.//layer_10/foreground/transition') is None and _camera is not None:_ready=False
        if not _ready:
            try:bootstrap(state,root)
            except Exception as exc:STATUS.update(error=public_error(exc)[:200],ready=False);_ready=False;return None
        # Source failures are deliberately outside the program connection state.
        for key in list(_loaded):
            try:observe_sources(info(source_channel(key)),now,key)
            except (OSError,RuntimeError,ET.ParseError) as exc:STATUS['source_error']=public_error(exc)[:200]
        read_source_health()
        # A failed native decoder reveals its loading underlay. The program
        # route, all other quadrants, ticker and music remain running.
        wanted=required(_camera)|required(_prepared['camera'] if _prepared else None)
        active={key for key in (_loaded|wanted) if key in CAMERAS and CAMERAS[key]['enabled']}
        for key in active:
            try:
                fault=transport_fault(_transport.get(CAMERAS[key]['media_path']),_transport_recovered.get(key,0),time.time())
                if fault:
                    mode=(_native_metrics.get(key) or {}).get('recovery_mode')
                    if mode is not None and mode>=0:
                        # One bounded command file per source, atomically replaced.
                        # Native video decoder resets references and gates keyframes;
                        # no camera connection, scene bank or audio restart is needed.
                        folder=Path(os.environ.get('SKYCAM_DATA',Path(__file__).parent.parent/'data'))/'runtime/camera-recovery'
                        folder.mkdir(parents=True,exist_ok=True)
                        name=CAMERAS[key]['media_path']
                        path=folder/(name.encode('utf-8').hex()+'.txt');tmp=path.with_suffix('.tmp')
                        tmp.write_text(str(int(time.time()*1000)),encoding='ascii');tmp.replace(path)
                        _transport_recovered[key]=time.time()
                        STATUS['cameras'].setdefault(key,{})['recovery_note']='Isolated keyframe recovery after reported transport loss'
                    else:
                        # Older engine stays fail-closed until explicitly upgraded.
                        if key in _slates and not _slate_visible.get(key):source_picture(key,False)
                        if fault=='reload' and now-_retry.get(key,0)>10:reload_camera(key)
                        continue
                retire_stalled_input(key,now)
                if key not in _loaded and now-_retry.get(key,0)>30:
                    ensure_inputs(key)
            except (RuntimeError,OSError) as exc:
                _retry[key]=now
                STATUS['cameras'].setdefault(key,{})['recovery_error']=public_error(exc)[:160]
        for key in CAMERAS:
            h=STATUS['cameras'].setdefault(key,{})
            fault=transport_fault(_transport.get(CAMERAS[key]['media_path']),_transport_recovered.get(key,0),time.time())
            mode=(_native_metrics.get(key) or {}).get('recovery_mode') or 0
            age=now-_changed[key] if key in _changed else None
            policy=_picture_policies.setdefault(key,PicturePolicy())
            display=policy.update(now,_last.get(key),age,key in _loaded,mode)
            if fault:display='loading' # unsupported engine or failed command write
            h['native_ready']=display=='live'
            h['native_frame_age_s']=round(age,2) if age is not None else None
            h['video_frame']=_last.get(key)
            h['playout_active']=key in active
            h['display']=display if key in active else 'ready / standby' if h.get('ready') else 'reconnecting'
            if display in ('held','recovering'):
                h['state']='signal recovering'
                h['recovery_note']='Last picture held, up to 8 seconds' if display=='held' else 'Keyframes only; normal decoding resumes after 15 quiet seconds'
            visible=display=='loading'
            if key in _slates and _slate_visible.get(key)!=visible:source_picture(key,not visible)
            badge=display in ('held','recovering')
            if key in _slates and _recovery_badges.get(key)!=badge:
                command(f'MIXER {source_channel(key)}-11 OPACITY {int(badge)}');_recovery_badges[key]=badge
        fallback=state.camera if _camera is None else None
        STATUS['audio']=audio_levels(root)
        STATUS['ndi']={'enabled':root.find('.//port_900') is not None,'name':'SkyCam Program HD','channel':1,'format':f'720p{PROGRAM_FPS}'}
        out=root.find('.//output/port/port_1/file/frame');count=int(out.text) if out is not None else None
        if count is not None:
            if not _output_samples or count!=_output_samples[-1][1]:_output_change=now
            if _output_samples and count<_output_samples[-1][1]:_output_samples.clear()
            _output_samples.append((now,count))
            while len(_output_samples)>1 and now-_output_samples[0][0]>10:_output_samples.pop(0)
        fps=(count-_output_samples[0][1])/(now-_output_samples[0][0]) if count is not None and len(_output_samples)>1 else None
        STATUS['output']={'frames':count,'measured_fps':round(fps,2) if fps is not None else None,'moving':count is not None and now-_output_change<3,
                          'target_fps':PROGRAM_FPS,'format':PROGRAM_FORMAT}
        if (count is None or now-_output_change>12) and now-_last_publish>15:
            try:publish()
            except (RuntimeError,OSError) as exc:STATUS['output']['error']=public_error(exc)[:160]
        if root.find('.//port_3') is None and root.find('.//port_601') is None and now-_screen_retry>15:
            _screen_retry=now
            try:screen()
            except (RuntimeError,OSError) as exc:STATUS['screen_error']=public_error(exc)[:160]
        for region in REGIONS:
            if now-_heartbeat.get(region,now)>20:
                try:graphics_region(region)
                except (RuntimeError,OSError) as exc:STATUS['graphics_error']=public_error(exc)[:160]
        STATUS.update(connected=True,ready=True,error=None,checked_at=time.time())
        STATUS['graphics_memory']=_graphics_budget.check(command,now)
        return fallback

async def watch(broadcast,apply):
    if not ENABLED:return
    while True:
        try:
            fallback=await asyncio.to_thread(check,broadcast.state)
            if fallback:
                await asyncio.to_thread(apply,fallback,None,0)
                STATUS['recovery_note']='Source failure or startup: selected '+fallback
        except Exception as exc:
            # No output teardown for source, graphics, or controller failures.
            STATUS['recovery_error']=public_error(exc)[:200]
        await asyncio.sleep(.5)
