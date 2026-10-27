"""Isolated test defaults are established before application imports."""
import atexit
import os
from tempfile import TemporaryDirectory

_data=TemporaryDirectory(prefix='station-tests-')
atexit.register(_data.cleanup)
os.environ['SKYCAM_DATA']=_data.name
os.environ['STATION_OFFLINE']='1'
os.environ['SKYCAM_PLAYOUT']='0'
os.environ['STATION_ALLOWED_HOSTS']='testserver,test'
for key in ('AISSTREAM_API_KEY','FINNHUB_API_KEY','FLIGHTAWARE_API_KEY','AEROAPI_KEY','STATION_BRAND_FILE'):
    os.environ.pop(key,None)


# Existing geographic fixtures explicitly exercise the Newfoundland regional preset.
from pathlib import Path
import json
_test_config=Path(_data.name)/"station.json"
_test_config.write_text(json.dumps({"location":{"name":"Test region","latitude":47.56,"longitude":-52.71,"timezone":"America/St_Johns"},"output":{"profile":"2160p3000"}}))
os.environ["STATION_CONFIG"]=str(_test_config)
