from .bounded_http import bounded_get
from .station_config import bootstrap, CONFIG, provider_enabled, clock_label
from .public_errors import public_error
bootstrap()
from .network_policy import install_offline_guard
install_offline_guard()
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import socket
import time
import uuid
import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from .models import CameraRequest
from .calibration import solve
from .geometry import project, site_frame
from .tracking import Tracks
from .flight_features import trail_segments
from .feature_scenes import FeatureScenes,FeatureConfig,SCENES as FEATURE_SCENES
from .broadcast import Broadcast, BroadcastState
from .sources import CAMERAS, QUADS, CATALOG, CameraSpec, QuadSpec, scene_rows
from . import playout
from .performance import Performance
from .rundown import Rundown, RundownConfig
from .camera_rotation import CameraRotation, RotationConfig
from .rundown_library import RundownLibrary,LibraryWrite,LibraryRevision,LibraryConflict
from .weather import Weather
from .weather_renderer import WeatherRenderer
from .music import Music, MusicConfig
from .outages import Outages,OutageConfig
from .power_system import PowerSystem
from .power_reports import PowerReports
from .map_renderer import MapRenderer
from .map_scenes import MAP_SCENES,DIRECT_SCENES
from .radar_renderer import RadarRenderer
from .native_ticker import NativeTicker
from .aircraft_graphics import AircraftGraphics
from .readiness import snapshot, program_moving
from .map_theme import MapTheme, MapThemeRequest
from .camera_tools import CameraTools
from .alerts import Alerts
from .alert_graphics import AlertPages
from .alert_presentation import AlertPresentation,PresentationConfig
from .alert_audio import AlertAudio
from .community_cards import CommunityCards, SCENES as CARD_SCENES
from . import daylight
from .flights import Flights
from .markets import Markets
from .marine import Marine
from .ais import Ais,AisConfig
from .tides import Tides
from .commercial import Commercial,CommercialWrite,MAX_UPLOAD
from . import format_defaults
from .notices import NoticeBoard,NoticeWrite,Notice
from .program_clock import ProgramClock,ClockWrite,ClockConfig,ClockRule
from .dayparts import Dayparts,DaypartWrite
from .aircraft_metadata import AircraftMetadata
from .rendered_preview import RenderedPreview,SnapshotBusy

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('SKYCAM_DATA', ROOT/'data'))
FEED = os.environ.get('SKYCAM_FEED', 'http://192.0.2.30:8080/skyaware/data/aircraft.json')
tracks = Tracks()
aircraft_metadata=AircraftMetadata()
rendered_preview=RenderedPreview(DATA)
from .performance_history import PerformanceHistory
performance = Performance(history=PerformanceHistory(DATA/'performance-history'))
solve_lock = asyncio.Lock()
broadcast = Broadcast(DATA)
map_theme = MapTheme(DATA)

def next_program_state(camera,scene=None):
    if camera not in {*CAMERAS,*QUADS,*MAP_SCENES,*DIRECT_SCENES}:raise ValueError('Unknown camera')
    update={'camera':camera,'location':(DIRECT_SCENES[camera]['location'] if camera in DIRECT_SCENES else MAP_SCENES[camera]['location'] if camera in MAP_SCENES else CONFIG.location.name.upper() if camera in QUADS else CAMERAS[camera]['location'])}
    if scene is not None:update['scene']=scene
    return broadcast.state.model_copy(update=update)

def prepare_program(camera,scene):
    return playout.prepare(camera,next_program_state(camera,scene))

def take_program(camera,scene=None,frames=30):
    with playout.LOCK:
        next_state=next_program_state(camera,scene)
        result=playout.take(camera,frames,next_state)
        broadcast.save(next_state)
        return result

rundown=Rundown(DATA,take_program,playout.available,prepare_program,lambda:program_moving(playout.STATUS))
music=Music(DATA)
camera_tools=CameraTools(DATA,CATALOG)
rundown_library=RundownLibrary(DATA)
program_clock=ProgramClock(DATA,rundown_library.export)
rundown.clock=program_clock
dayparts=Dayparts(DATA,rundown_library.export)
rundown.dayparts=dayparts
weather=Weather(DATA)
alerts=Alerts(DATA,enabled=provider_enabled('alerts') and os.environ.get('STATION_OFFLINE','1')=='0')
alert_pages=AlertPages(DATA,alerts)
playout.DIRECT_MEDIA['weather-alerts']=alert_pages.media
emergency_pages=AlertPages(DATA,alerts,'emergency-alerts')
playout.DIRECT_MEDIA['emergency-alerts']=emergency_pages.media
flights=Flights(DATA)
notices=NoticeBoard(DATA)
commercial=Commercial(DATA)
camera_rotation=CameraRotation(DATA,CAMERAS)
rundown.eligible=lambda scene:bool(commercial.eligible('advertisement')) if scene=='advertisement' else bool(notices.active()) if scene=='community-notices' else camera_rotation.eligible(scene)
playout.DIRECT_MEDIA['advertisement']=commercial.media
playout.DIRECT_OVERLAY['advertisement']=commercial.overlay
playout.SCENE_DECORATE=commercial.decorate
playout.DECORATION_KEY=lambda:(commercial.revision,bool(commercial.eligible('advertisement')),bool(commercial.eligible('sponsor')))
markets=Markets(DATA)
marine=Marine(DATA)
ais=Ais(DATA)
tides=Tides(DATA)
outages=Outages(DATA,enabled=provider_enabled('outages') and os.environ.get('STATION_OFFLINE','1')=='0')
power_system=PowerSystem(DATA)
power_reports=PowerReports(DATA)
program_clock.eligible=lambda condition:condition=='always' or (condition=='power-outages' and outages.eligible())
community_cards=CommunityCards(DATA,flights,notices,markets,tides,outages)
community_cards.marine=marine
community_cards.power_system=power_system
community_cards.power_reports=power_reports
community_cards.market_timing=lambda:rundown.scene_timing('markets')
community_cards.outage_map=MapRenderer(DATA,lambda:{},'outage-map',center=(49,-56),zoom=7,view_scale=1.2)
outages.warm_map=community_cards.warm_outage_map
for card in CARD_SCENES:playout.DIRECT_MEDIA[card]=lambda card=card:community_cards.prepare_media(card)
def take_alert_followup(cue):
    if not alert_pages.select(cue['token']):return False
    take_program('weather-alerts','standard',0 if rundown._active_config().transition=='cut' else 30)
    return True
rundown.followups=alert_pages.followups
rundown.followup_take=take_alert_followup
rundown.followup_valid=alert_pages.valid
map_renderer=MapRenderer(DATA,lambda:map_data(),view_scale=1.2)
map_renderers={'map':map_renderer,
 'map-island':MapRenderer(DATA,lambda:map_data(),'map-island',18,zoom=7,view_scale=.85),
 'radar-east':RadarRenderer(DATA,lambda:map_data(),'east',19),
 'radar-island':RadarRenderer(DATA,lambda:map_data(),'island',20),
 'weather':WeatherRenderer(DATA,weather)}
playout.MAP_REFRESH.update({id:renderer.ensure for id,renderer in map_renderers.items()})
features=FeatureScenes(DATA,lambda:map_data(),map_renderers)
for feature in FEATURE_SCENES:playout.DIRECT_MEDIA[feature]=lambda feature=feature:features.media(feature)

alert_audio=AlertAudio(DATA,music)
alert_presentation=AlertPresentation(DATA,lambda:alerts.public(include_resources=True),outages.public,alert_audio)
ticker=NativeTicker(DATA,broadcast,alerts.public,outages.banner,alert_presentation)
ticker.suppress=lambda:playout._camera=='advertisement' and bool(commercial.eligible('advertisement')) and not commercial.config.advertisement.show_ticker
aircraft_graphics=AircraftGraphics(DATA,broadcast,lambda camera:frame(camera))


async def poll():
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        while True:
            try:
                response = await bounded_get(client,FEED, headers={'Cache-Control':'no-cache'})
                response.raise_for_status()
                tracks.ingest(response.json())
            except Exception as exc:
                tracks.error = f'{type(exc).__name__}: {public_error(exc)[:180]}'
            await asyncio.sleep(.5)


@asynccontextmanager
async def lifespan(app):
    DATA.mkdir(parents=True, exist_ok=True)
    CATALOG.initialize()
    for retired in CATALOG.retired:archive_deleted_profile(retired)
    for camera, source in CAMERAS.items():
        path = DATA/f'{camera}.json'
        if not path.exists():
            draft = CameraRequest(name=source['name'],width=source['width'],height=source['height'])
            if not source['site_known']:
                draft.site.lat=draft.site.lon=draft.site.altitude_msl_m=0
            path.write_text(json.dumps({'request':draft.model_dump(),'calibration':None,
                'calibration_error':None,'saved_at':time.time()},indent=2),encoding='utf-8')
    if os.environ.get('STATION_OFFLINE','1') != '0':
        yield
        return
    task=asyncio.create_task(poll()) if provider_enabled('adsb') else None
    metadata_task=asyncio.create_task(aircraft_metadata.watch()) if provider_enabled('metadata') else None
    news_task=asyncio.create_task(broadcast.poll()) if provider_enabled('news') else None
    playout_task = asyncio.create_task(playout.watch(broadcast,take_program))
    rundown_task = asyncio.create_task(rundown.watch())
    rotation_task = asyncio.create_task(camera_rotation.watch())
    performance_task=asyncio.create_task(performance.watch(lambda:playout.STATUS))
    music_task = asyncio.create_task(music.watch())
    weather_task=asyncio.create_task(weather.watch()) if provider_enabled('weather') else None
    flights_task=asyncio.create_task(flights.watch()) if provider_enabled('flights') else None
    markets_task=asyncio.create_task(markets.watch()) if provider_enabled('markets') else None
    marine_task=asyncio.create_task(marine.watch()) if provider_enabled('marine') else None
    ais_task=asyncio.create_task(ais.watch()) if playout.ENABLED and provider_enabled('ais') else None
    tides_task=asyncio.create_task(tides.watch()) if provider_enabled('tides') else None
    outages_task=asyncio.create_task(outages.watch()) if provider_enabled('outages') else None
    power_task=asyncio.create_task(power_system.watch()) if provider_enabled('power') else None
    report_task=asyncio.create_task(power_reports.watch()) if provider_enabled('power_reports') else None
    commercial_task=asyncio.create_task(commercial.watch())
    alerts_task=asyncio.create_task(alerts.watch()) if playout.ENABLED and provider_enabled('alerts') else None
    emergency_pages_task=asyncio.create_task(emergency_pages.watch()) if playout.ENABLED else None
    ticker_task=asyncio.create_task(ticker.watch())
    alert_pages_task=asyncio.create_task(alert_pages.watch()) if playout.ENABLED else None
    cards_task=asyncio.create_task(community_cards.watch()) if playout.ENABLED else None
    features_task=asyncio.create_task(features.watch()) if playout.ENABLED else None
    aircraft_task=asyncio.create_task(aircraft_graphics.watch())
    map_tasks=[asyncio.create_task(r.watch()) for r in map_renderers.values()]
    map_tasks += [asyncio.create_task(r.fetch_watch()) for r in map_renderers.values() if isinstance(r,RadarRenderer) and provider_enabled('radar')]
    yield
    if task:task.cancel()
    if metadata_task:metadata_task.cancel()
    if news_task:news_task.cancel()
    playout_task.cancel()
    rundown_task.cancel()
    rotation_task.cancel()
    performance_task.cancel()
    music_task.cancel()
    if weather_task:weather_task.cancel()
    if flights_task:flights_task.cancel()
    if markets_task:markets_task.cancel()
    if marine_task:marine_task.cancel()
    if ais_task:ais_task.cancel()
    if tides_task:tides_task.cancel()
    if outages_task:outages_task.cancel()
    if power_task:power_task.cancel()
    if report_task:report_task.cancel()
    commercial_task.cancel()
    if alerts_task:alerts_task.cancel()
    for map_task in map_tasks:map_task.cancel()
    ticker_task.cancel()
    if emergency_pages_task:emergency_pages_task.cancel()
    if alert_pages_task:alert_pages_task.cancel()
    if cards_task:cards_task.cancel()
    if features_task:features_task.cancel()
    aircraft_task.cancel()
    try:
        await (task if task else asyncio.sleep(0))
    except asyncio.CancelledError:
        pass
    try:
        await (news_task if news_task else asyncio.sleep(0))
    except asyncio.CancelledError:
        pass


from .branding import BRAND, branded_html
app = FastAPI(title=BRAND.product_name, lifespan=lifespan)
from .request_limits import RequestLimits
app.add_middleware(RequestLimits)
from .source_delivery import router as source_router
app.include_router(source_router)

@app.exception_handler(RequestValidationError)
async def invalid_request(request,exc):
    # Pydantic's default response includes submitted values and exception context.
    # Keep field guidance without echoing media URLs, keys or arbitrary input.
    errors=[]
    for item in exc.errors()[:40]:
        location=[part if isinstance(part,int) or (isinstance(part,str) and re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]{0,47}',part)) else '[field]' for part in item['loc']]
        errors.append({'loc':location,'type':item['type'],'msg':public_error(ValueError(item['msg']))})
    return JSONResponse({'detail':errors},status_code=422)

@app.get('/api/station-config')
def station_config_public():
    return {'schema_version':CONFIG.schema_version,'offline':os.environ.get('STATION_OFFLINE','1')!='0','location':CONFIG.location.model_dump(),
            'clock_label':clock_label(),'output_profile':CONFIG.output.profile,'providers':CONFIG.providers,
            'configured_secret_roles':sorted(CONFIG.secrets),'changes_require_restart':True}

@app.get('/api/branding')
def branding():
    return BRAND.model_dump()

@app.get('/api/branding/logo')
def brand_logo():
    from .branding import logo_path
    path=logo_path()
    if path is None:raise HTTPException(404,'No custom logo configured')
    return FileResponse(path)

@app.get('/api/release-mode')
def release_mode():
    return {'offline':os.environ.get('STATION_OFFLINE','1')!='0','playout':playout.ENABLED,'release_ready':False}



def preview_read_only():
    return os.environ.get('STATION_OFFLINE','1') != '0'

@app.middleware('http')
async def local_edits(request: Request, call_next):
    # Browser cross-origin writes are rejected; no CORS is enabled. Default bind
    # is loopback; deployment also binds the private operator IP explicitly.
    # This is a trusted operator-network service, not an Internet service.
    if request.method not in ('GET','HEAD','OPTIONS'):
        if preview_read_only():
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Offline release preview is read-only'}, status_code=503)
        origin = request.headers.get('origin')
        if request.headers.get('x-skycam-edit') != '1' or (origin and origin != str(request.base_url).rstrip('/')):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Same-origin operator edit required'}, status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def camera_path(camera):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', camera):
        raise HTTPException(400, 'Use a camera ID with lowercase letters, digits, underscores or hyphens')
    return DATA/f'{camera}.json'


def read_camera(camera):
    path = camera_path(camera)
    if not path.exists():
        raise HTTPException(404, 'Camera has not been saved')
    return json.loads(path.read_text(encoding='utf-8'))


@app.get('/api/health')
def health():
    return {'host':socket.gethostname(),'time':time.time(),'feed':FEED,**tracks.status()}


@app.get('/api/cameras')
def cameras():
    records=[]
    for p in sorted(DATA.glob('*.json')):
        record=json.loads(p.read_text(encoding='utf-8'))
        if 'request' in record:records.append({'id':p.stem,**record})
    return records


@app.get('/api/cameras/{camera}')
def camera_get(camera: str):
    return read_camera(camera)


async def calculate(body):
    try:
        async with solve_lock:
            return await run_in_threadpool(solve, body)
    except ValueError as exc:
        raise HTTPException(422, public_error(exc)) from exc


@app.post('/api/solve')
async def calibration_solve(body: CameraRequest):
    return await calculate(body)


@app.put('/api/cameras/{camera}')
async def camera_save(camera: str, body: CameraRequest):
    path = camera_path(camera)
    result, calibration_error = None, None
    if body.landmarks:
        try:
            result = await calculate(body)
        except HTTPException as exc:
            if body.approved:
                raise
            calibration_error = exc.detail
    if body.approved and (body.reference_only or result is None or not result['acceptable']):
        raise HTTPException(422, 'Approval requires a verified site, geoid separation, and passing fit and validation checks')
    record = {'request':body.model_dump(),'calibration':result,
              'calibration_error':calibration_error,'saved_at':time.time()}
    DATA.mkdir(parents=True, exist_ok=True)
    # Preserve previous revisions; do not replace operator history.
    if path.exists():
        backups = DATA/'revisions'
        backups.mkdir(exist_ok=True)
        (backups/f'{camera}-{time.time_ns()}.json').write_bytes(path.read_bytes())
    temporary = DATA/f'.{camera}-{uuid.uuid4().hex}.tmp'
    temporary.write_text(json.dumps(record, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)
    return record


@app.get('/api/frame/{camera}')
def frame(camera: str):
    record = read_camera(camera)
    req = CameraRequest.model_validate(record['request'])
    calibration = record['calibration']
    now = time.time()
    target = now-req.video_delay_s
    status = tracks.status(now)
    response = {'camera':camera,'width':req.width,'height':req.height,'server_time':now,
                'target_time':target,'video_delay_s':req.video_delay_s,
                'feed':status,'labels':[],'state':'uncalibrated','expires_in_ms':750}
    if not req.approved or not calibration or not calibration['acceptable']:
        return response
    if not status['healthy']:
        response['state'] = 'feed_unavailable'
        return response
    response['state'] = 'live'
    origin, basis = site_frame(req.site)
    for p in tracks.positions(target, now):
        enu = basis @ (p['pos']-origin)
        distance = float(np.linalg.norm(enu))
        if distance > 200000 or enu[2] <= 0:
            continue
        pixels, depth = project([enu], calibration)
        x,y = map(float, pixels[0])
        if depth[0] <= 0 or not (0 <= x < req.width and 0 <= y < req.height):
            continue
        response['labels'].append({k:p[k] for k in ['hex','callsign','altitude_ft','speed_kt','mode','position_age_s']} |
                                  {'x':x,'y':y,'range_km':distance/1000})
    return response


@app.get('/')
def index():
    return branded_html(ROOT/'skycam/static/index.html')


@app.get('/overlay')
def overlay():
    return branded_html(ROOT/'skycam/static/overlay.html')


@app.get('/guide')
def operator_guide():return branded_html(ROOT/'skycam/static/guide.html')


@app.get('/cameras')
def camera_manager():return branded_html(ROOT/'skycam/static/cameras.html')

@app.get('/studio')
@app.get('/studio/{page}')
def studio(page:str='live'):
    return branded_html(ROOT/'skycam/static/studio.html')


@app.get('/broadcast')
def program_graphics():
    return branded_html(ROOT/'skycam/static/broadcast.html')


@app.get('/api/broadcast')
def broadcast_get():
    return {**broadcast.public(),'playout_enabled':playout.ENABLED,'playout':playout.STATUS,'map_renderer':map_renderer.status,'ticker':ticker.status,'camera_sources':list(CAMERAS.values()),'quad_scenes':QUADS,'scenes':scene_rows()}


@app.post('/api/program/take/{camera}')
def program_take(camera: str):
    if not playout.available(camera):raise HTTPException(404,'Unknown scene')
    # Match the scheduler's lock order, but never queue an operator click
    # behind a long source warmup. Rejected clicks do not pause the rundown.
    if not rundown.lock.acquire(blocking=False):
        raise HTTPException(409,'Scene preparation is already in progress. Current program continues; try again shortly.')
    try:
        if not playout.LOCK.acquire(blocking=False):
            raise HTTPException(409,'Playout is busy. Current program continues; try again shortly.')
        try:
            rundown.pause('Manual take paused rotation')
            return take_program(camera)
        except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(503,public_error(exc)) from exc
        finally:playout.LOCK.release()
    finally:rundown.lock.release()

@app.get('/api/camera-rotation')
def camera_rotation_get():return camera_rotation.public()

@app.put('/api/camera-rotation')
def camera_rotation_put(body:RotationConfig):
    camera_rotation.save(body);return camera_rotation.public()

@app.get('/api/rundown')
def rundown_get():return rundown.public()

@app.get('/outages')
def outages_page():return branded_html(ROOT/'skycam/static/outages.html')

@app.get('/power')
def power_page():return branded_html(ROOT/'skycam/static/power.html')

@app.get('/api/power')
def power_get():return power_system.public()

@app.get("/api/power/reports")
def power_reports_get(report_date:str|None=Query(default=None,pattern=r"^\d{4}-\d{2}-\d{2}$")):return power_reports.public(report_date)

@app.get('/api/outages')
def outages_get():return outages.public()

@app.put('/api/outages')
def outages_put(body:OutageConfig):
    outages.save(body);return outages.public()

@app.get('/clock')
def clock_page():return branded_html(ROOT/'skycam/static/clock.html')

@app.get('/notices')
def notices_page():return branded_html(ROOT/'skycam/static/notices.html')

@app.get('/api/program-clock')
def clock_get():return {**program_clock.public(),'playout':rundown.public()}

@app.get('/api/dayparts')
def dayparts_get():return {**dayparts.public(),'playout':rundown.public()}

@app.put('/api/dayparts')
def dayparts_put(body:DaypartWrite):
    library_call(dayparts.save,body)
    return dayparts_get()

@app.put('/api/program-clock')
def clock_put(body:ClockWrite):
    library_call(program_clock.save,body)
    return clock_get()

@app.post('/api/program-clock/examples')
def clock_examples():
    # Add reusable examples only. Never replace an existing operator playlist.
    ids={}
    specs=[(name,format_defaults.BLOCKS[name]) for name in ('Short local forecast','Extended local weather')]
    for name,cues in specs:
        current=rundown_library.public();found=next((r for r in current['items'] if r['name'].casefold()==name.casefold()),None)
        if found:ids[name]=found['id'];continue
        body=LibraryWrite(name=name,expected_revision=current['revision'],config=RundownConfig(cues=[{'camera':c,'seconds':s} for c,s in cues]))
        ids[name]=library_call(rundown_library.save,body)['saved_id']
    return {'playlists':ids}

@app.get('/api/program-format')
def format_get():return format_defaults.public(rundown,program_clock,rundown_library)

@app.post('/api/program-format')
def format_apply(body:format_defaults.FormatWrite):return library_call(format_defaults.apply,DATA,rundown,program_clock,rundown_library,body)

@app.get('/commercial')
def commercial_page():return branded_html(ROOT/'skycam/static/commercial.html')

@app.get('/api/commercial')
def commercial_get():return commercial.public()

@app.put('/api/commercial')
def commercial_put(body:CommercialWrite):return library_call(commercial.save,body)

@app.post('/api/commercial/assets')
async def commercial_upload(request:Request,name:str):
    temp=commercial.folder/(uuid.uuid4().hex+'.upload')
    try:
        size=0
        with temp.open('wb') as f:
            async for chunk in request.stream():
                size+=len(chunk)
                if size>MAX_UPLOAD:raise HTTPException(413,'Maximum upload is 100 MiB')
                f.write(chunk)
            f.flush();os.fsync(f.fileno())
        return await run_in_threadpool(library_call,commercial.import_file,temp,name)
    finally:temp.unlink(missing_ok=True)

@app.post('/api/commercial/playlist')
def commercial_playlist():
    if not commercial.eligible('advertisement'):raise HTTPException(422,'Save an enabled, eligible asset first')
    library=rundown_library.public();name='Sponsor message'
    old=next((r for r in library['items'] if r['name']==name),None)
    body=LibraryWrite(expected_revision=library['revision'],name=name,config=RundownConfig(cues=[{'camera':'advertisement','seconds':commercial.config.advertisement.hold_seconds}]))
    saved=library_call(rundown_library.save,body,old['id'] if old else None)
    return {'name':name,'saved_id':saved['saved_id']}

@app.get('/api/commercial/assets/{asset_id}')
def commercial_asset(asset_id:str,poster:bool=False):
    return FileResponse(library_call(commercial.file,asset_id,poster))

@app.delete('/api/commercial/assets/{asset_id}')
def commercial_delete(asset_id:str):return library_call(commercial.delete,asset_id)

@app.get('/api/commercial/sponsor/{scene}')
def sponsor_preview(scene:str):
    if not playout.available(scene):raise HTTPException(404,'Unknown scene')
    from fastapi.responses import Response
    from io import BytesIO
    output=BytesIO();commercial.sponsor_image(scene).save(output,format='PNG')
    return Response(output.getvalue(),media_type='image/png')

@app.post('/api/notices/images')
async def notice_image_upload(request:Request):
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>16*1024*1024:raise HTTPException(413,'Image exceeds 16 MiB')
    return await run_in_threadpool(library_call,notices.upload,bytes(raw))

@app.get('/api/notices/images/{identifier}')
def notice_image_get(identifier:str):return FileResponse(library_call(notices.image_path,identifier))

@app.post('/api/notices/images/clean-unused')
def notice_image_clean():return library_call(notices.clean_unused)

@app.post('/api/notices/playlist')
def notice_playlist():
    library=rundown_library.public();name='Community information'
    old=next((r for r in library['items'] if r['name']==name),None)
    if old:return {'saved_id':old['id'],'name':name}
    body=LibraryWrite(expected_revision=library['revision'],name=name,config=RundownConfig(cues=[{'camera':'community-notices','seconds':60}]))
    saved=library_call(rundown_library.save,body)
    return {'name':name,'saved_id':saved['saved_id']}

@app.get('/api/notices')
def notices_get():return notices.public()

@app.put('/api/notices')
def notices_put(body:NoticeWrite):return library_call(notices.save,body)

@app.delete('/api/notices/{notice_id}')
def notices_delete(notice_id:str,body:LibraryRevision):return library_call(notices.delete,notice_id,body.expected_revision)

@app.post('/api/notices/preview')
def notices_preview(body:Notice):
    from .community_cards import notice_image,notice_pages
    from fastapi.responses import Response
    from io import BytesIO
    buffer=BytesIO();notice_image(notice_pages([body.model_dump(mode='json')])[0],notices.assets).save(buffer,format='PNG')
    return Response(buffer.getvalue(),media_type='image/png')


def library_call(action,*args):
    try:return action(*args)
    except LibraryConflict as exc:raise HTTPException(409,public_error(exc)) from exc
    except KeyError as exc:raise HTTPException(404,public_error(exc)) from exc
    except ValueError as exc:raise HTTPException(422,public_error(exc)) from exc
    except (RuntimeError,OSError) as exc:raise HTTPException(503,public_error(exc)) from exc

def validate_library_views(body):
    missing=sorted({cue.camera for cue in body.config.cues if not playout.available(cue.camera)})
    if missing:raise HTTPException(422,'Unknown views: '+', '.join(missing))

@app.get('/api/rundown-library')
def library_get():return library_call(rundown_library.public)

@app.post('/api/rundown-library')
def library_create(body:LibraryWrite):
    validate_library_views(body);return library_call(rundown_library.save,body)

@app.put('/api/rundown-library/{item_id}')
def library_update(item_id:str,body:LibraryWrite):
    validate_library_views(body);return library_call(rundown_library.save,body,item_id)

@app.delete('/api/rundown-library/{item_id}')
def library_delete(item_id:str,body:LibraryRevision):
    return library_call(rundown_library.delete,item_id,body.expected_revision)

@app.post('/api/rundown-library/undo')
def library_undo(body:LibraryRevision):return library_call(rundown_library.undo,body.expected_revision)

@app.get('/api/rundown-library/{item_id}/export')
def library_export(item_id:str):return library_call(rundown_library.export,item_id)

@app.get('/api/weather')
def weather_get():return weather.public()

@app.get('/api/tides')
def tides_get():return tides.public()

@app.get('/api/markets')
def markets_get():return markets.public()

@app.get('/api/marine')
def marine_get():return marine.public()

@app.get('/ais')
def ais_page():return branded_html(ROOT/'skycam/static/ais.html')

@app.get('/api/ais')
def ais_get():return ais.public()

@app.put('/api/ais')
def ais_put(body:AisConfig):ais.save(body);return ais.public()

@app.get('/api/moon')
def moon_get():
    from .moon_card import public
    return public()

@app.get('/api/daylight')
def daylight_get():return daylight.public()

@app.get('/api/flights/{direction}')
def flights_get(direction:str):
    try:return flights.public(direction)
    except ValueError as exc:raise HTTPException(404,public_error(exc)) from exc

@app.get('/api/readiness')
def readiness_get():
    result=snapshot(playout.STATUS,tracks.status(),map_renderer.status,music.public(),rundown.public(),camera_ids=list(CAMERAS),map_states={scene:renderer.status for scene,renderer in map_renderers.items()})
    try:
        guard=json.loads((DATA/'runtime/watchdog.json').read_text(encoding='utf-8'))
        fresh=0<=time.time()-guard['checked_at']<20
        note=guard.get('note','Unknown recovery state')
        if guard.get('recovery_budget',{}).get('remaining') == 0:
            note += '; automatic recovery limit reached, operator attention required'
        good=fresh and not guard.get('maintenance') and not guard.get('error') and ('Watching' in note or 'Startup' in note)
        good=good and guard.get('recovery_budget',{}).get('remaining') != 0
        result['checks'].append({'id':'watchdog','label':'Automatic recovery','level':'ok' if good else 'warning','detail':note if fresh else 'Watchdog status is stale; check the host service'})
        result['watchdog']=guard
        if not good and result['state']=='healthy':result['state']='limited'
    except (OSError,ValueError,KeyError):
        result['checks'].append({'id':'watchdog','label':'Automatic recovery','level':'warning','detail':'Host watchdog status unavailable'})
        if result['state']=='healthy':result['state']='limited'
    return result

@app.put('/api/rundown')
def rundown_put(body:RundownConfig):
    if any(not playout.available(c.camera) for c in body.cues):raise HTTPException(422,'Rundown contains an unknown camera or scene')
    rundown.save(body);return rundown.public()

@app.post('/api/rundown/{action}')
async def rundown_action(action:str):
    try:await run_in_threadpool(rundown.action,action)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(503,public_error(exc)) from exc
    return rundown.public()


@app.get('/api/sources')
def sources():
    return list(CAMERAS.values())

@app.get('/api/scenes')
def scenes():return scene_rows()

@app.post('/api/source-catalog/{camera}/probe')
async def camera_probe(camera:str):
    try:return await run_in_threadpool(camera_tools.probe,camera)
    except Exception as exc:raise HTTPException(422,public_error(exc)[:240]) from exc

@app.post('/api/source-catalog/{camera}/capture')
async def camera_capture(camera:str):
    try:return await run_in_threadpool(camera_tools.capture,camera)
    except Exception as exc:raise HTTPException(422,public_error(exc)[:240]) from exc

@app.post('/api/source-catalog/{camera}/reference')
async def camera_reference(camera:str,request:Request):
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>16*1024*1024:raise HTTPException(413,'Image exceeds 16 MiB')
    try:return await run_in_threadpool(camera_tools.store,camera,bytes(raw))
    except Exception as exc:raise HTTPException(422,public_error(exc)[:240]) from exc

@app.get('/samples/{name}')
def reference_image(name:str):
    # Only catalogue-assigned local filenames are served from writable storage.
    if any(c['reference']==name for c in CAMERAS.values()) and '/' not in name and '\\' not in name and name not in ('.','..'):
        path=camera_tools.folder/name
        if path.is_file():return FileResponse(path)
    if '/' not in name and '\\' not in name and name not in ('.','..'):
        path=ROOT/'samples'/name
        if path.is_file():return FileResponse(path)
    raise HTTPException(404,'Reference image unavailable')

@app.get('/api/source-catalog')
def source_catalog():return CATALOG.public()

def ensure_source_profile(source):
    path=camera_path(source['id'])
    if not path.exists():
        req=CameraRequest(name=source['name'],width=source['width'],height=source['height'])
        req.site.lat=req.site.lon=req.site.altitude_msl_m=0
        path.write_text(json.dumps({'request':req.model_dump(),'calibration':None,'calibration_error':None,'saved_at':time.time()},indent=2),encoding='utf-8')

@app.post('/api/source-catalog')
def source_create(body:CameraSpec):
    try:
        with playout.LOCK:
            row=CATALOG.create(body);ensure_source_profile(row)
            if playout.ENABLED and playout.STATUS.get('ready'):
                playout.ensure_inputs(row['id']);playout.release_unused()
            return row
    except ValueError as exc:raise HTTPException(422,public_error(exc))

@app.put('/api/source-catalog/{camera}')
def source_update(camera:str,body:CameraSpec):
    try:
        with playout.LOCK:
            old=CAMERAS.get(camera)
            if old is None:raise ValueError('Unknown camera')
            if body.id!=camera:raise ValueError('Existing camera ID cannot be changed')
            changed=any(old[k]!=getattr(body,k) for k in ('media_path','width','height'))
            if changed:
                path=camera_path(camera)
                if path.exists():
                    record=json.loads(path.read_text(encoding='utf-8'));revisions=DATA/'revisions';revisions.mkdir(exist_ok=True)
                    (revisions/f'{camera}-{time.time_ns()}.json').write_bytes(path.read_bytes())
                    if old['width']!=body.width or old['height']!=body.height:record['request']['landmarks']=[]
                    record['request'].update(approved=False,reference_only=True,width=body.width,height=body.height)
                    record.update(calibration=None,calibration_error='Source changed; calibration needs review',saved_at=time.time())
                    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2),encoding='utf-8');tmp.replace(path)
            row=CATALOG.update(camera,body)
            if changed or old['enabled']!=body.enabled:
                playout.reset_source(camera)
                if playout.ENABLED and playout.STATUS.get('ready'):playout.ensure_inputs(camera)
            if camera in playout.required(broadcast.state.camera):
                state=next_program_state(broadcast.state.camera);playout.update_graphics(state);broadcast.save(state)
            return row
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,public_error(exc))

def archive_deleted_profile(camera):
    path=camera_path(camera)
    if path.exists():
        folder=DATA/'revisions';folder.mkdir(exist_ok=True)
        path.replace(folder/f'deleted-{camera}-{time.time_ns()}.json')

@app.delete('/api/source-catalog/{camera}')
def source_delete(camera:str):
    try:
        with rundown.lock,playout.LOCK:
            if camera not in CAMERAS:raise ValueError('Unknown camera')
            if camera in playout.required(broadcast.state.camera) or camera in playout.required(playout._prepared['camera'] if playout._prepared else None):raise ValueError('Camera is in program or preview; take another scene first')
            if any(c.camera==camera for c in rundown.config.cues):raise ValueError('Remove this camera from the rundown first')
            if any(camera in ids for ids in QUADS.values()):raise ValueError('Remove this camera from its quad first')
            playout.reset_source(camera);CATALOG.delete(camera);archive_deleted_profile(camera)
            return {'deleted':camera,'calibration_history_retained':True}
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(409,public_error(exc))

@app.put('/api/quad-scenes/{scene}')
def quad_update(scene:str,cameras:list[str]):
    try:
        with playout.LOCK:
            CATALOG.save_quad(scene,cameras)
            if broadcast.state.camera==scene:playout.update_graphics(broadcast.state)
            return {'id':scene,'cameras':QUADS[scene]}
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,public_error(exc))


@app.post('/api/quad-scenes')
def quad_create(body:QuadSpec):
    try:
        with playout.LOCK:
            CATALOG.write_quad(body,create=True)
            return {'id':body.id,'name':body.name,'cameras':QUADS[body.id]}
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,public_error(exc))


@app.patch('/api/quad-scenes/{scene}')
def quad_edit(scene:str,body:QuadSpec):
    try:
        with playout.LOCK:
            if body.id!=scene:raise ValueError('Existing quad ID cannot be changed')
            CATALOG.write_quad(body)
            if broadcast.state.camera==scene:playout.update_graphics(broadcast.state)
            return {'id':scene,'name':body.name,'cameras':QUADS[scene]}
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,public_error(exc))


@app.delete('/api/quad-scenes/{scene}')
def quad_delete(scene:str):
    try:
        with rundown.lock,playout.LOCK,rundown_library.lock:
            if (broadcast.state.camera==scene or playout._camera==scene
                    or (playout._prepared or {}).get('camera')==scene
                    or (playout._retiring or {}).get('camera')==scene):
                raise ValueError('Quad is in program or preview; take another scene first')
            configs=[rundown.config]
            for running in (rundown.block,rundown.daypart):
                if running and 'config' in running:configs.append(running['config'])
            if any(c.camera==scene for config in configs for c in config.cues):
                raise ValueError('Remove this quad from the active rundown or block first')
            library=rundown_library.public()
            if any(c['camera']==scene for item in library['items'] for c in item['config']['cues']):
                raise ValueError('Remove this quad from saved rundowns first')
            CATALOG.delete_quad(scene)
            return {'deleted':scene}
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(409,public_error(exc))


@app.put('/api/broadcast')
def broadcast_put(body: BroadcastState):
    try:
        with playout.LOCK:
            if body.camera!=broadcast.state.camera:
                body=body.model_copy(update={'camera':broadcast.state.camera,'location':broadcast.state.location})
            scene_fields=('camera','location','kicker','headline','subline','scene','show_lower','show_aircraft')
            if any(getattr(body,k)!=getattr(broadcast.state,k) for k in scene_fields):
                playout.update_graphics(body)
            broadcast.save(body)
    except (ValueError,RuntimeError,OSError) as exc:
        raise HTTPException(503,public_error(exc)) from exc
    return {**broadcast.public(),'playout_enabled':playout.ENABLED,'playout':playout.STATUS,'map_renderer':map_renderer.status,'ticker':ticker.status}


app.mount('/static', StaticFiles(directory=ROOT/'skycam/static'), name='static')
app.mount('/samples', StaticFiles(directory=ROOT/'samples'), name='samples')

@app.post('/api/program/heartbeat/{region}')
def graphics_heartbeat(region: str):
    try:playout.heartbeat(region)
    except ValueError as exc:raise HTTPException(400,public_error(exc))
    return {'ok':True}

@app.get('/api/music')
def music_get():return music.public()

@app.get('/api/alerts')
def alerts_get():return {**alerts.public(),'presentation':alert_presentation.public()}

@app.put('/api/alert-presentation')
def alert_presentation_put(body:PresentationConfig):
    alert_presentation.save(body);return alert_presentation.public()

@app.get('/alerts')
def alerts_page():return branded_html(ROOT/'skycam/static/alerts.html')

@app.put('/api/music')
def music_put(body:MusicConfig):
    try:music.save(body)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(503,public_error(exc))
    return music.public()

@app.get('/scene')
def scene_page():return branded_html(ROOT/'skycam/static/scene.html')

@app.get('/api/map')
def map_data():
    now=time.time();status=tracks.status(now);items=[]
    for q in list(tracks.history.values()):
        if not q:continue
        p=q[-1];age=max(0,now-p['time'])
        if age>60 or 'lat' not in p:continue
        stale=not status['healthy'] or age>5
        metadata=aircraft_metadata.lookup(p['hex'])
        items.append({k:p[k] for k in ['hex','callsign','lat','lon','track','altitude_ft']}|
            {'category':p.get('category',''),'aircraft_type':p.get('aircraft_type') or metadata.get('aircraft_type',''),'registration':p.get('registration') or metadata.get('registration',''),'metadata_source':metadata.get('metadata_source',''),'speed_kt':p.get('speed_kt'),'age_s':round(age,1),'stale':stale,'opacity':max(.25,1-age/80) if stale else 1,
             'trail_segments':trail_segments(list(q),now),
             'trail':[[v['lat'],v['lon']] for v in list(q) if 'lat' in v and now-v['time']<60]})
    return {'healthy':status['healthy'],'aircraft':items,'server_time':now,'theme':map_theme.public(),'ais':ais.public(now)}

@app.get('/api/aircraft-metadata')
def metadata_status():return aircraft_metadata.public()

@app.get('/api/map/theme')
def map_theme_get():return map_theme.public()

@app.put('/api/map/theme')
def map_theme_put(body:MapThemeRequest):
    map_theme.save(body)
    return map_theme.public()


@app.post('/api/music/{action}')
async def music_action(action:str,request:Request):
    try:
        body=await request.json()
        return await run_in_threadpool(music.action,action,body.get('track'))
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,public_error(exc))


@app.get('/map-view')
def map_view():return branded_html(ROOT/'skycam/static/map-view.html')

@app.get('/api/maps')
def map_status():return {key:{**MAP_SCENES[key],**value.status} for key,value in map_renderers.items()}

@app.get('/api/maps/{scene}/image')
async def map_image(scene:str,page:int|None=Query(default=None,ge=0,le=99)):
    if scene in FEATURE_SCENES:
        path=await run_in_threadpool(features.path,scene)
        return FileResponse(path,media_type='image/png',headers={'Cache-Control':'no-store'})
    if scene=='advertisement':
        path=await run_in_threadpool(commercial.cached,'ad-preview',commercial.image)
        return FileResponse(path,media_type='image/png')
    if scene in CARD_SCENES:
        path=await run_in_threadpool(community_cards.path,scene,page_override=page)
        return FileResponse(path,media_type='image/png')
    renderer=map_renderers.get(scene)
    if renderer is None:raise HTTPException(404,'Unknown map scene')
    await run_in_threadpool(renderer.ensure)
    return FileResponse(renderer.frames/'preview.jpg',media_type='image/jpeg')


@app.get('/confidence')
def confidence_page():return branded_html(ROOT/'skycam/static/confidence.html')

@app.get('/api/features')
def features_get():return features.public()

@app.put('/api/features')
def features_put(body:FeatureConfig):
    try:features.save(body)
    except ValueError as exc:raise HTTPException(400,public_error(exc))
    return features.public()

@app.get('/api/confidence')
def confidence_get():return features.confidence()

@app.post('/api/confidence/rendered/{kind}')
def confidence_rendered(kind:str):
    try:return rendered_preview.capture(kind)
    except SnapshotBusy as exc:raise HTTPException(409,public_error(exc))
    except ValueError as exc:raise HTTPException(422,public_error(exc))

@app.get('/api/confidence/rendered/{name}')
def confidence_rendered_file(name:str):
    try:return FileResponse(rendered_preview.file(name),media_type='image/jpeg')
    except (ValueError,FileNotFoundError) as exc:raise HTTPException(404,public_error(exc))

@app.get('/api/performance')
def performance_get():return performance.public()

@app.get('/api/performance/history')
def performance_history_get():return performance.history.public()

@app.get('/api/confidence/camera/{camera}')
def confidence_camera(camera:str):
    if camera not in CAMERAS:raise HTTPException(404,'Unknown camera')
    path=features.thumbnail(camera)
    try:picture=path.read_bytes()
    except FileNotFoundError:raise HTTPException(404,'No decoded thumbnail yet')
    # The health reader atomically replaces this file. Snapshot bytes before
    # forming headers so a replacement cannot change Content-Length mid-send.
    return Response(picture,media_type='image/jpeg',headers={'Cache-Control':'no-store'})


@app.get('/api/storage-health')
def storage_health():
    try:
        path=DATA/'storage-health.json'
        if path.stat().st_size>8192:raise ValueError('Invalid storage status')
        value=json.loads(path.read_text())
        if not isinstance(value,dict):raise ValueError('Invalid storage status')
        value['stale']=time.time()-value.get('at',0)>900
        return value
    except (OSError,ValueError,TypeError):return {'stale':True,'error':'Storage monitor has not reported'}
