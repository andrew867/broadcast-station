from PIL import Image
import pytest
from skycam.commercial import Commercial,CommercialConfig,CommercialWrite,Advertisement

def test_background_preserves_ad_shape_and_falls_back(tmp_path):
    c=Commercial(tmp_path)
    photo=tmp_path/'portrait.png';Image.new('RGB',(200,400),'red').save(photo)
    row=c.import_file(photo,'portrait.png')
    c.save(CommercialWrite(expected_revision=0,config=CommercialConfig(advertisement=Advertisement(
        enabled=True,asset_id=row['id'],background_color='#003355'))))
    im=c.image(False)
    assert im.getpixel((10,10))==(0,51,85)
    assert im.getpixel((1920,500))==(255,0,0)
    assert im.getpixel((1000,500))==(0,51,85)
    bg=tmp_path/'bg.png';Image.new('RGB',(400,200),'green').save(bg)
    backdrop=c.import_file(bg,'bg.png')
    config=c.config.model_copy(deep=True);config.advertisement.background_asset_id=backdrop['id']
    c.save(CommercialWrite(expected_revision=1,config=config))
    assert c.image(False).getpixel((10,10))==(0,128,0)
    with pytest.raises(ValueError,match='Unselect'):c.delete(backdrop['id'])
    c.file(backdrop['id'],True).unlink()
    assert c.background().getpixel((10,10))==(0,51,85)

def test_background_cannot_be_video_or_invalid_colour(tmp_path):
    with pytest.raises(ValueError):Advertisement(background_color='red;bad')
    c=Commercial(tmp_path);id='a'*32
    c.items=[{'id':id,'kind':'video'}]
    with pytest.raises(ValueError,match='Background artwork'):
        c.save(CommercialWrite(expected_revision=0,config=CommercialConfig(
            advertisement=Advertisement(background_asset_id=id))))
