# SPDX-License-Identifier: Apache-2.0
"""Validate full-stack settings before any playout process starts."""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skycam.station_config import CONFIG,CONFIG_PATH,bootstrap,secret
from tools.station_config import engine_config

def main():
    bootstrap()
    if not CONFIG_PATH:raise ValueError('STATION_CONFIG is required')
    if not CONFIG.output.playout:raise ValueError('Set output.playout to true only for the intended full station')
    if CONFIG.output.amcp_port!=5250 or CONFIG.output.amcp_host!='engine' or CONFIG.output.studio_url!='http://studio:8765':
        raise ValueError('The Compose stack uses engine and http://studio:8765 as internal service names')
    if CONFIG.inputs.camera_base==CONFIG.inputs.camera_shared_base:raise ValueError('Camera upstream and fan-out URLs must differ')
    roles=[k for k,p in [('aisstream','ais'),('finnhub','markets')] if CONFIG.providers.get(p) and k in CONFIG.secrets]
    if CONFIG.output.publish and 'publish_url' in CONFIG.secrets:roles.append('publish_url')
    for role in roles:secret(role)
    root=CONFIG_PATH.parent
    for name in ['data','runtime','music','logs','engine-data','templates']:
        if not (root/name).is_dir():raise ValueError('Station folders are incomplete; run stationctl init or prepare')
    output=root/'casparcg.config';temporary=output.with_suffix('.tmp')
    temporary.write_text(engine_config(CONFIG,Path(__file__).parents[1]/'deploy/casparcg.config'))
    temporary.replace(output)
    print(json.dumps({'valid':True,'profile':CONFIG.output.profile,'publishing':CONFIG.output.publish,'hdmi':CONFIG.output.hdmi}))

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit('Launch validation failed: '+str(exc))
