import numpy as np
from PIL import Image, ImageDraw
from skycam.tracking import Tracks
from skycam.map_renderer import draw_aircraft_symbol

def test_missing_category_retains_recent_report_but_not_indefinitely():
 t=Tracks();base={'hex':'abc123','flight':'CHI13','lat':47.5,'lon':-52.7,'alt_geom':2000,'seen_pos':0}
 t.ingest({'now':1000,'aircraft':[dict(base,category='A7')]},1000)
 for now in (1001,1020,1100,1121):
  t.ingest({'now':now,'aircraft':[base]},now)
  assert t.history['abc123'][-1]['category']==('A7' if now<=1120 else '')
 t.ingest({'now':1122,'aircraft':[dict(base,category='A2')]},1122)
 assert t.history['abc123'][-1]['category']=='A2'

def test_helicopter_has_a_distinct_shape_at_downscaled_tv_size():
 images=[]
 for category in ('A1','A7'):
  image=Image.new('RGB',(100,100),'#101c25')
  draw_aircraft_symbol(ImageDraw.Draw(image),50,50,0,category,'#ff995e','white')
  images.append(np.asarray(image.resize((25,25))))
 assert np.count_nonzero(images[0]!=images[1])>100
