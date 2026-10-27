"""Optional network consumers. Does not replace the main RTMP output."""
import argparse,json,socket,xml.etree.ElementTree as ET
SRT_URL='srt://192.0.2.10:8890?streamid=publish:skycam-program-srt&pkt_size=1316&latency=200000'
SRT_COMMAND=('ADD 1-4 FILE "'+SRT_URL+'" -codec:v h264_nvenc -filter:v format=bgra '
 '-preset:v p1 -tune:v ll -surfaces:v 8 -delay:v 0 -b:v 35000k -maxrate:v 35000k '
 '-bufsize:v 70000k -g:v 120 -bf:v 0 -codec:a aac -channel_layout:a stereo '
 '-filter:a pan=stereo|c0=c0|c1=c1 -b:a 192k -ar:a 48000 -format mpegts')
def command(value):
 with socket.create_connection(('127.0.0.1',5250),timeout=5) as s:
  s.settimeout(1);s.sendall((value+'\r\n').encode());data=b''
  while True:
   try:
    chunk=s.recv(65536)
    if not chunk:break
    data+=chunk
   except socket.timeout:break
 reply=data.decode(errors='replace')
 if not reply.startswith(('200 ','201 ','202 ')):raise RuntimeError(reply.strip())
 return reply
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['status','ndi-on','ndi-off','srt-on','srt-off']);a=p.parse_args().action
 if a=='ndi-on':
  print(command('ADD 1-900 NDI NAME "SkyCam Program HD" WIDTH 1280 HEIGHT 720'))
 elif a=='ndi-off':print(command('REMOVE 1-900'))
 elif a=='srt-on':print(command(SRT_COMMAND))
 elif a=='srt-off':print(command('REMOVE 1-4'))
 else:
  for channel in [1]:
   reply=command(f'INFO {channel}');node=ET.fromstring(reply[reply.index('<?xml'):]);output=node.find('output')
   print(f'Channel {channel}: '+ET.tostring(output,encoding='unicode'))
