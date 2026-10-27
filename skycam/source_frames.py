"""Bounded frame assembly and occasional confidence pictures from one NV12 stream."""
from pathlib import Path

WIDTH,HEIGHT=640,360
FRAME_BYTES=WIDTH*HEIGHT*3//2


class FrameReader:
    def __init__(self):
        self.pending=bytearray()

    def feed(self,chunk):
        self.pending.extend(chunk)
        count=len(self.pending)//FRAME_BYTES
        if not count:return 0,None
        end=count*FRAME_BYTES
        latest=bytes(self.pending[end-FRAME_BYTES:end])
        del self.pending[:end]
        return count,latest


def write_thumbnail(frame,path):
    import cv2
    import numpy as np
    pixels=np.frombuffer(frame,dtype=np.uint8).reshape(HEIGHT*3//2,WIDTH)
    picture=cv2.cvtColor(pixels,cv2.COLOR_YUV2BGR_NV12)
    ok,encoded=cv2.imencode('.jpg',picture,[cv2.IMWRITE_JPEG_QUALITY,80])
    if not ok:raise ValueError('Confidence picture encoding failed')
    path=Path(path);tmp=path.with_suffix('.tmp')
    tmp.write_bytes(encoded.tobytes());tmp.replace(path)
