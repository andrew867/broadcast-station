# SPDX-License-Identifier: Apache-2.0
"""Validate station settings and generate matching native channel timing."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skycam.station_config import load,StationConfig


def engine_config(config,template):
    root=ET.parse(template).getroot()
    if config.output.headless:
        html=root.find('html')
        if html is not None:
            backend=html.find('angle-backend')
            if backend is None:backend=ET.SubElement(html,'angle-backend')
            backend.text='vulkan'
            debug=html.find('remote-debugging-port')
            if debug is not None:debug.text='0'
    log=root.find('./paths/log-path')
    if log is not None:log.set('disabled','true') # Docker captures and rotates the console log.
    producer=root.find('./ffmpeg/producer')
    if producer is not None:
        for old in list(producer.findall('camera-prefixes')):producer.remove(old)
        prefixes=ET.SubElement(producer,'camera-prefixes')
        for base in dict.fromkeys([config.inputs.camera_base,config.inputs.camera_shared_base,config.inputs.camera_rtmp_base]):
            ET.SubElement(prefixes,'prefix').text=base.rstrip('/')+'/'
    fps=config.output.profile[-4:]
    for index,channel in enumerate(root.findall('./channels/channel')):
        node=channel.find('video-mode')
        node.text=config.output.profile if index<3 else node.text[:-4]+fps
        consumers=channel.find('consumers')
        if consumers is not None:
            if config.output.headless:
                for screen in list(consumers.findall('screen')):consumers.remove(screen)
            for audio in list(consumers.findall('system-audio')):consumers.remove(audio)
            if index==0 and config.output.desktop_audio:
                audio=ET.SubElement(consumers,'system-audio')
                ET.SubElement(audio,'delay').text='200ms'
    port=root.find('./controllers/tcp/port')
    if port is not None:port.text=str(config.output.amcp_port)
    ET.indent(root)
    return ET.tostring(root,encoding='unicode')+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config',type=Path)
    parser.add_argument('--engine-output',type=Path)
    args=parser.parse_args();config=load(args.config)
    if args.engine_output:
        if args.engine_output.exists():raise SystemExit('Output already exists; choose a new path')
        args.engine_output.parent.mkdir(parents=True,exist_ok=True)
        args.engine_output.write_text(engine_config(config,Path(__file__).parents[1]/'deploy/casparcg.config'))
    print(json.dumps({'valid':True,'schema_version':config.schema_version,'profile':config.output.profile,
                     'enabled_providers':[k for k,v in config.providers.items() if v],
                     'required_secret_roles':sorted(config.secrets),'publishing':config.output.publish}))


if __name__=='__main__':main()
