from PIL import Image
from skycam.image_cache import valid_image
from skycam.native_ticker import NativeTicker
from skycam.broadcast import Broadcast

def test_missing_empty_truncated_and_wrong_size_are_cache_misses(tmp_path):
    p=tmp_path/'graphic.png'
    assert not valid_image(p)
    p.write_bytes(b'');assert not valid_image(p)
    Image.new('RGB',(40,20)).save(p)
    assert valid_image(p,(40,20))
    assert not valid_image(p,(20,40))
    p.write_bytes(p.read_bytes()[:40]);assert not valid_image(p)

def test_ticker_replaces_broken_cache_without_manual_removal(tmp_path):
    ticker=NativeTicker(tmp_path,Broadcast(tmp_path))
    p=ticker.folder/'bar.png';p.write_bytes(b'')
    ticker.save_image(Image.new('RGB',(3840,224)),'bar')
    assert valid_image(p,(3840,224))
    p.write_bytes(b'not an image')
    ticker.save_image(Image.new('RGB',(3840,224)),'bar')
    assert valid_image(p,(3840,224))
