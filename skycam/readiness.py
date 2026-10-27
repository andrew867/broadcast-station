"""Read-only operator checks. These are observations, not an airworthiness claim."""
import time
import math
from .output_timing import PROGRAM_FPS

def program_moving(playout, now=None):
    now=time.time() if now is None else now
    return bool(playout.get('connected') and playout.get('ready') and
                0 <= now-playout.get('checked_at',0) < 5 and
                (playout.get('output') or {}).get('moving'))

def snapshot(playout, receiver, map_state, music, rundown, now=None, camera_ids=None, map_states=None):
    now=time.time() if now is None else now
    checks=[]
    def add(key,label,level,detail):checks.append(dict(id=key,label=label,level=level,detail=detail))
    moving=program_moving(playout,now)
    add('program','Program output','ok' if moving else 'error',
        'Encoded frame counter is advancing' if moving else 'No recent moving output confirmed; check TV and relay')
    fps=playout.get('output',{}).get('measured_fps') if moving else None
    if type(fps) not in (int,float) or not math.isfinite(fps):fps=None
    cadence_ok=fps is not None and abs(fps-PROGRAM_FPS)<=max(1,PROGRAM_FPS*.02)
    add('cadence','Frame rate','ok' if cadence_ok else 'warning',
        f'{fps:.1f} fps measured, target {PROGRAM_FPS}' if fps is not None else 'Waiting for a fresh frame-rate measurement')
    resources=playout.get('graphics_memory',{})
    if resources:
        add('graphics_memory','Graphics buffer cache','warning' if resources.get('error') else 'ok',
            resources.get('error') or f"Unused GPU {resources.get('device_bytes',0)/1048576:.0f} MB / host {resources.get('host_bytes',0)/1048576:.0f} MB; native cache limit {resources.get('budget_per_pool_bytes',0)/1048576:.0f} MB each")
    for camera in camera_ids if camera_ids is not None else ('cam1','cam2','cam3','cam4'):
        source=playout.get('cameras',{}).get(camera,{})
        good=moving and (source.get('native_ready',False) if source.get('playout_active',True) else source.get('ready',False))
        add(camera,camera.upper(),'ok' if good else 'warning',
            ('Recent decoded picture' if source.get('playout_active',True) else 'Source decoded and ready; playout on demand') if good else 'Picture not confirmed; scene remains selectable with loading panel')
    renderers=map_states if map_states is not None else {'map':map_state}
    needed={(playout.get('program') or {}).get('camera','map'),(playout.get('preview') or {}).get('camera')}
    labels={'map':'Avalon airspace map','map-island':'Newfoundland airspace map','radar-east':'East radar','radar-island':'Island radar','weather':'Local weather board'}
    for scene,renderer in renderers.items():
        active=scene in needed
        recent=0<=now-renderer.get('updated_at',0)<(60 if scene=='weather' else 10)
        good=renderer.get('ready') and not renderer.get('error') and (recent or not active)
        detail=renderer.get('error') or ('Renderer is updating' if good and active else 'Ready in standby; refreshes when selected' if good else 'No recent picture confirmed' if active else 'Renderer is not ready')
        add(scene,labels.get(scene,scene),'ok' if good else 'warning',detail)
    add('receiver','Aircraft data','ok' if receiver.get('healthy') else 'warning',
        'Receiver data is fresh' if receiver.get('healthy') else 'Receiver unavailable or stale; old map positions fade out')
    add('music','Music','warning' if music.get('error') else 'ok',
        str(music['error']) if music.get('error') else ('Playing: '+str(music['current']) if music.get('enabled') and music.get('current') else 'Music paused or waiting for a track'))
    add('rundown','Rotation','warning' if rundown.get('error') or rundown.get('resume_pending') else 'ok',
        rundown.get('error') or ('Automatic rotation running' if rundown.get('enabled') else rundown.get('note','Manual hold')))
    return {'checked_at':now,'state':'attention' if any(c['level']=='error' for c in checks) else 'limited' if any(c['level']=='warning' for c in checks) else 'healthy',
            'checks':checks,'limits':'Controller observations only. Listen to HDMI and YouTube to confirm audio and end-to-end delivery.'}
