from skycam.source_frames import FrameReader,FRAME_BYTES,WIDTH,HEIGHT,write_thumbnail


def test_only_complete_frames_advance_health_and_partial_bytes_are_retained():
    reader=FrameReader();first=b'a'*FRAME_BYTES;second=b'b'*FRAME_BYTES
    assert reader.feed(first[:-1])==(0,None)
    count,frame=reader.feed(first[-1:]+second[:123])
    assert count==1 and frame==first and len(reader.pending)==123
    count,frame=reader.feed(second[123:]+first+second[:7])
    assert count==2 and frame==first and len(reader.pending)==7


def test_nv12_confidence_picture_is_readable_without_a_second_decoder(tmp_path):
    from PIL import Image
    frame=bytes([100])*(WIDTH*HEIGHT)+bytes([128])*(WIDTH*HEIGHT//2)
    target=tmp_path/'camera.jpg';write_thumbnail(frame,target)
    with Image.open(target) as picture:
        assert picture.size==(WIDTH,HEIGHT)
        r,g,b=picture.getpixel((100,100))
        assert abs(r-g)<3 and abs(g-b)<3 and 80<r<120
    assert not target.with_suffix('.tmp').exists()
