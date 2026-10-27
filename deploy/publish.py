"""Start the program output on the existing MediaMTX server."""
from amcp import command
print(command('ADD 1-1 STREAM "rtmp://192.0.2.10:1935/skycam-program" -codec:v h264_nvenc -preset:v p1 -tune:v ll -b:v 35000k -maxrate:v 35000k -bufsize:v 70000k -g:v 120 -bf:v 0 -codec:a aac -channel_layout:a stereo -filter:a pan=stereo|c0=c0|c1=c1 -b:a 192k -ar:a 48000 -format flv'))
