"""Runtime smoke checks for the conditional information-screen feature set."""

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


NEW_CARDS = (
    "weather-timeline",
    "nl-travel",
    "harbour-watch",
    "tonights-sky",
    "morning-briefing",
    "evening-briefing",
    "community-calendar",
)


def main() -> None:
    from skycam import app as application
    from skycam.community_cards import CommunityCards
    from skycam.feature_scenes import FeatureScenes

    routes = {route.path for route in application.app.routes}
    expected_routes = {
        "/director",
        "/api/director/status",
        "/api/director/take/{camera}",
        "/api/travel",
        "/api/space-weather",
        "/api/scene-confidence",
    }
    missing = expected_routes - routes
    if missing:
        raise RuntimeError(f"missing routes: {sorted(missing)}")

    output = Path(os.environ["STATION_VALIDATION_OUTPUT"]) if os.environ.get("STATION_VALIDATION_OUTPUT") else None
    if output:output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="station-information-wave-") as folder:
        data = Path(folder)
        cards = CommunityCards(data)
        for scene in NEW_CARDS:
            path = cards.path(scene, datetime(2026, 10, 28, 14, tzinfo=timezone.utc))
            with Image.open(path) as image:
                if image.size != (3840, 2160):
                    raise RuntimeError(f"{scene}: wrong image size {image.size}")
                image.verify()
            if output:shutil.copyfile(path,output/(scene+".png"))

        feature = FeatureScenes(data, lambda: {"aircraft": [], "healthy": False}, {})
        replay = feature.path("last-hour")
        with Image.open(replay) as image:
            if image.size != (1920, 1080):
                raise RuntimeError(f"last-hour: wrong image size {image.size}")
            image.verify()
        if output:shutil.copyfile(replay,output/"last-hour.png")

        if output:
            from skycam import daylight
            from skycam.information_graphics import briefing_image,calendar_image,harbour_image,sky_image,travel_image,weather_timeline_image
            from skycam.moon_card import public as moon_public
            now=datetime(2026,10,28,14,tzinfo=timezone.utc);stamp=now.timestamp()
            weather={'forecast_available':True,'current_available':True,'temperature_c':7,'condition':'Cloudy with sunny breaks','wind_direction':'W','wind_kmh':28,'visibility_km':24,'fetched_at':stamp,
                     'forecasts':[{'period':'This afternoon','temperatures':[{'value':8}],'summary':'Cloudy with sunny breaks. Wind west 30 km/h.'},{'period':'Tonight','temperatures':[{'value':2}],'summary':'Partly cloudy with a chance of showers.'},{'period':'Thursday','temperatures':[{'value':10}],'summary':'A mix of sun and cloud.'}]}
            travel={'available':True,'checked_at':stamp,'summary':'3 travel items requiring attention','events':[{'road':'Trans-Canada Highway','description':'One lane closed near Exit 41'}],'roads':[{'road':'Route 10','condition':'Wet with fog patches','location':'Southern Shore'}],'ferries':[{'service':'Bell Island service','status':'Running on a revised schedule','details':'Check departure times'}],'winds':[],'advisories':[]}
            outages={'fresh':True,'checked_at':stamp,'active':[{'id':'sample'}]}
            tides={'available':True,'events':[{'kind':'HIGH','at':datetime(2026,10,28,16,tzinfo=timezone.utc).isoformat(),'value':1.2},{'kind':'LOW','at':datetime(2026,10,28,22,tzinfo=timezone.utc).isoformat(),'value':0.3}]}
            marine={'available':True,'groups':[{'name':'East Coast Cape St. Francis and south','fields':{'wind':'West 25 knots diminishing this evening','weatherVisibility':'Fog patches dissipating near noon'}}]}
            fixtures={
                'sample-weather-timeline':weather_timeline_image(weather),
                'sample-nl-travel':travel_image(travel),
                'sample-harbour-watch':harbour_image({'ais':{'counts':{'fresh':18,'moving_fresh':7,'older':5}},'tides':tides,'marine':marine}),
                'sample-tonights-sky':sky_image({'daylight':daylight.public(now),'moon':moon_public(now),'weather':weather,'space':{'available':True,'current':{'sub_auroral':'quiet'},'forecast_24h':{'sub_auroral':'unsettled intervals'}},'location':"St. John's"}),
                'sample-morning-briefing':briefing_image({'weather':weather,'travel':travel,'outages':outages,'location':"St. John's"},'morning'),
                'sample-evening-briefing':briefing_image({'weather':weather,'travel':travel,'outages':outages,'location':"St. John's"},'evening'),
                'sample-community-calendar':calendar_image([{'approved':True,'starts_at':datetime(2026,10,30,18,tzinfo=timezone.utc).isoformat(),'ends_at':datetime(2026,10,30,20,tzinfo=timezone.utc).isoformat(),'title':'Community clean-up and food drive','location':'St. John’s Community Centre','credit':'Community calendar'}],now),
            }
            for name,image in fixtures.items():image.save(output/(name+'.png'),format='PNG',compress_level=1)

    print("information-wave-runtime-ok")


if __name__ == "__main__":
    main()
