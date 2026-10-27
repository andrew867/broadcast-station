from .branding import BRAND
"""Non-camera scenes share persistent native sources and normal PGM/PVW takes."""
MAP_SCENES={
 'map':{'channel':8,'name':'2D airspace / Avalon','location':'AVALON AIRSPACE'},
 'map-island':{'channel':18,'name':'2D airspace / Newfoundland','location':'NEWFOUNDLAND AIRSPACE'},
 'radar-east':{'channel':19,'name':'Radar + aircraft / East','location':'EASTERN NEWFOUNDLAND RADAR'},
 'radar-island':{'channel':20,'name':'Radar + aircraft / Island','location':'NEWFOUNDLAND RADAR'},
 'weather':{'channel':17,'name':"Local weather / St. John's",'location':"ST. JOHN'S WEATHER",'reference':'weather-card.svg'},
}

DIRECT_SCENES={
 "power-history":{"name":"Electricity / daily peak history","location":"ISLAND INTERCONNECTED SYSTEM","kind":"card","reference":"station-card.svg"},
 "power-report":{"name":"Electricity / daily report and outlook","location":"ISLAND INTERCONNECTED SYSTEM","kind":"card","reference":"station-card.svg"},
 "power-supply":{"name":"Electricity / demand and generation","location":"NEWFOUNDLAND & LABRADOR","kind":"card","reference":"station-card.svg"},
 "map-ocean":{"name":"Atlantic approaches / aircraft and boats","location":"ATLANTIC APPROACHES","kind":"card","reference":"station-card.svg"},
 "marine":{"name":"Coastal marine forecast / East Coast","location":"NEWFOUNDLAND MARINE WEATHER","kind":"card","reference":"weather-card.svg"},
 "moon":{"name":"Tonight's sky / lunar phase","location":"ST. JOHN'S SKY","kind":"card","reference":"daylight-card.svg"},
 "emergency-alerts":{"name":"Emergency information / full details","location":"NEWFOUNDLAND & LABRADOR","kind":"card","reference":"station-card.svg"},
 "power-outages":{"name":"Power outages / NL Power + NL Hydro","location":"UTILITY INFORMATION","kind":"card","reference":"station-card.svg"},
 "flight-spotlight":{"name":"Flight spotlight","location":"RECEIVED AIRCRAFT","kind":"card","reference":"station-card.svg"},
 "radar-history-east":{"name":"Radar history / East","location":"RECENT RADAR HISTORY","kind":"card","reference":"station-card.svg"},
 "radar-history-island":{"name":"Radar history / Island","location":"RECENT RADAR HISTORY","kind":"card","reference":"station-card.svg"},
 "camera-timelapse":{"name":"Camera timelapse","location":"RECENT CAMERA SNAPSHOTS","kind":"card","reference":"station-card.svg"},
 "tides":{"name":"Harbour tides / St. John's","location":"CHS TIDE PREDICTIONS","kind":"card","reference":"station-card.svg"},
 "markets":{"name":"Markets","location":"MARKET WATCH","kind":"card","reference":"station-card.svg"},
 "advertisement":{"name":"Advertisement / sponsor message","location":"SPONSORED MESSAGE","kind":"card","reference":"station-card.svg"},
 "community-notices":{"name":"Community noticeboard","location":"LOCAL COMMUNITY","kind":"card","reference":"station-card.svg"},
 "yyt-arrivals":{"name":"YYT arrivals","location":"ST. JOHN'S INTERNATIONAL AIRPORT","kind":"card","reference":"yyt-arrivals-card.svg"},
 "yyt-departures":{"name":"YYT departures","location":"ST. JOHN'S INTERNATIONAL AIRPORT","kind":"card","reference":"yyt-departures-card.svg"},
 "daylight":{"name":"Daylight & sky / St. John's","location":"ST. JOHN'S DAYLIGHT","kind":"card","reference":"daylight-card.svg"},
 "station-info":{"name":"About the station","location":BRAND.tagline,"kind":"card","reference":"station-card.svg"},
 "weather-alerts":{"name":"Weather alert pages","location":"NEWFOUNDLAND & LABRADOR"}
}

from .station_config import CONFIG
DIRECT_SCENES['daylight'].update(name='Daylight & sky / '+CONFIG.location.name,location=CONFIG.location.name.upper())
DIRECT_SCENES['moon']['location']=CONFIG.location.name.upper()
if CONFIG.regional_preset=='none':
    MAP_SCENES['map'].update(name='2D airspace / Local area',location='LOCAL AIRSPACE')
    MAP_SCENES['map-island'].update(name='2D airspace / Regional',location='REGIONAL AIRSPACE')
    DIRECT_SCENES['map-ocean'].update(name='Wide area / aircraft and boats',location='WIDE AREA AIRSPACE')
