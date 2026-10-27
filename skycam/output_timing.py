"""Keep animation timing and encoding aligned with the native program profile."""
from pathlib import Path
import xml.etree.ElementTree as ET

FORMATS={'720p3000':'1280x720p30','720p6000':'1280x720p60',
         '1080p3000':'1920x1080p30','1080i5994':'1920x1080i59.94',
         '2160p3000':'3840x2160p30','2160p6000':'3840x2160p60'}


def clock_fps(mode):
    if mode not in FORMATS:raise ValueError('Unsupported program timing: '+str(mode))
    return 60000/1001 if mode=='1080i5994' else 60 if mode.endswith('6000') else 30


def encoded_fps(mode):
    return clock_fps(mode)/2 if mode=='1080i5994' else clock_fps(mode)


def publishing_video(mode):
    # CasparCG's FILE consumer receives one full image per field tick. Pair
    # successive temporal samples into top/bottom fields, not just an i label.
    if mode=='1080i5994':
        return 'format=yuv420p,tinterlace=mode=interleave_top', '-flags:v +ilme+ildct -top:v 1'
    return 'format=bgra',''

def program_mode(path):
    mode=ET.parse(path).findtext('./channels/channel/video-mode')
    if mode not in FORMATS:raise ValueError('Unsupported program timing: '+str(mode))
    return mode

def program_fps(path):
    return clock_fps(program_mode(path))

def output_format(mode):
    return FORMATS[mode]

from .station_config import CONFIG,CONFIG_PATH
PROGRAM_MODE=CONFIG.output.profile if CONFIG_PATH else program_mode(Path(__file__).parents[1]/'deploy/casparcg.config')
PROGRAM_FPS=clock_fps(PROGRAM_MODE)
ENCODED_FPS=encoded_fps(PROGRAM_MODE)
PROGRAM_FORMAT=output_format(PROGRAM_MODE)

def transition_frames(frames,fps=PROGRAM_FPS):
    # The existing operator API uses 60-Hz frame units. Preserve its duration.
    return max(1,round(frames*fps/60)) if frames else 0
