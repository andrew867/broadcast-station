"""Treat missing or damaged generated images as cache misses, not valid assets."""
from functools import lru_cache
from PIL import Image

@lru_cache(maxsize=256)
def _verified(path,mtime_ns,size,expected_size):
    try:
        with Image.open(path) as image:
            if expected_size is not None and image.size!=expected_size:return False
            image.verify()
        return True
    except (OSError,ValueError,SyntaxError):return False

def valid_image(path,expected_size=None):
    try:
        stat=path.stat()
        return stat.st_size>0 and _verified(str(path),stat.st_mtime_ns,stat.st_size,expected_size)
    except OSError:return False
