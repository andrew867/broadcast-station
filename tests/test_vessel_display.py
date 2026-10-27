from PIL import Image,ImageDraw
from skycam.map_renderer import MapRenderer,vessel_groups
from skycam.ais import Ais
from tests.test_ais import report,NOW


def vessel(i,x=500,y=500,speed=0,stale=False):
    return {'mmsi':str(316000000+i),'name':f'Boat {i}','lat':x,'lon':y,'sog':speed,
            'heading':None,'cog':90,'age_s':310 if stale else 10,'stale':stale,'trail':[]}


def test_cluster_conserves_individuals_and_never_hides_moving_vessel():
    rows=[vessel(i,x=47.56+i*.00001,y=-52.70) for i in range(30)]+[vessel(40,x=47.56,y=-52.70,speed=10),vessel(41,x=47.56,y=-52.70,speed=2),vessel(42,x=47.56,y=-52.70,stale=True),vessel(43,x=-1)]
    point=lambda lat,lon:(500+(lat-47.56)*1000,500+(lon+52.70)*1000)
    groups=vessel_groups(rows,point,lambda x,y:x>0 and y>0)
    assert [g['members'][0]['mmsi'] for g in groups[:2]]==['316000040','316000041']
    assert len(groups)==4
    assert sum(len(g['members']) for g in groups)==33
    assert len(groups[2]['members'])==30
    assert groups[3]['stale']
    assert all((g['x'],g['y'])==point(g['members'][0]['lat'],g['members'][0]['lon']) for g in groups)


def test_label_budget_goes_to_underway_before_alphabetical_stationary(tmp_path):
    m=MapRenderer(tmp_path,lambda:{})
    m.point=lambda x,y:(x,y)
    # Eight alphabetical stationary boats previously exhausted the label budget.
    rows=[vessel(i,x=400+300*i,y=1300) for i in range(8)]+[vessel(99,x=1700,y=700,speed=10.9)]
    rows[-1]['name']='ZZ Offshore'
    d=ImageDraw.Draw(Image.new('RGB',(3840,2160)))
    m.draw_vessels(d,{'vessels':rows,'connected':True},[],False)
    assert m.status['boats']['moving_fresh']==1
    assert m.status['boats']['in_view']==9
    assert m.status['boats']['labelled_mmsi'][0]=='316000099'


def test_message_count_is_separate_from_vessel_count(tmp_path):
    a=Ais(tmp_path);a.ingest(report(),NOW+1);a.ingest(report(),NOW+2)
    d=a.public(NOW+3)
    assert d['received']==2 and d['counts']=={'recent':1,'fresh':1,'moving_fresh':0,'older':0}


def test_wide_map_does_not_merge_offshore_boats_kilometres_apart():
    rows=[vessel(1,x=46.6,y=-49,speed=0),vessel(2,x=46.62,y=-49,speed=0)]
    groups=vessel_groups(rows,lambda lat,lon:(1000+lat,1000+lon),lambda x,y:True)
    assert len(groups)==2


def test_island_harbour_labels_consolidate_motion_and_age_but_not_offshore():
    from skycam.map_renderer import HARBOUR_LABEL_AREAS
    rows=[]
    for i,(south,north,west,east) in enumerate(HARBOUR_LABEL_AREAS):
        for j in range(3):
            rows.append(vessel(i*10+j,x=(south+north)/2+j*.0001,y=(west+east)/2,speed=4 if j==1 else 0,stale=j==2))
    rows += [vessel(90,x=46.6,y=-49),vessel(91,x=46.62,y=-49)]
    groups=vessel_groups(rows,lambda lat,lon:(lat,lon),lambda x,y:True,True)
    assert len(groups)==6 and sum(len(g['members']) for g in groups)==14
    harbours=[g for g in groups if 'harbour' in g]
    assert len(harbours)==4 and all(len(g['members'])==3 and not g['stale'] for g in harbours)
    assert len(vessel_groups(rows,lambda lat,lon:(lat,lon),lambda x,y:True))>6


def test_island_draws_single_tag_and_retains_hull_count(tmp_path):
    m=MapRenderer(tmp_path,lambda:{},scene='map-island',zoom=7,view_scale=.85)
    rows=[vessel(i,x=47.56+i*.0002,y=-52.70,speed=i,stale=i==2) for i in range(4)]
    d=ImageDraw.Draw(Image.new('RGB',(3840,2160)))
    m.draw_vessels(d,{'vessels':rows,'connected':True},m.occupied(),False)
    assert m.status['boats']['label_categories']['harbour']==1
    assert m.status['boats']['individual_symbols']==4
    assert m.status['boats']['harbour_clusters']==[{'area':0,'vessels':4}]


def test_stationary_boat_keeps_label_when_moving_budget_full(tmp_path):
    m=MapRenderer(tmp_path,lambda:{});m.point=lambda x,y:(x,y)
    rows=[vessel(i,x=400+(i%4)*800,y=400+(i//4)*350,speed=10) for i in range(12)]
    rows+=[vessel(99,x=1800,y=1550,speed=0)]
    d=ImageDraw.Draw(Image.new('RGB',(3840,2160)))
    m.draw_vessels(d,{'vessels':rows,'connected':True},[],False)
    assert '316000099' in m.status['boats']['labelled_mmsi']
    assert m.status['boats']['label_categories']['stationary']==1
    assert m.status['boats']['individual_symbols']==13


def test_group_retains_each_stationary_hull_and_unknown_speed(tmp_path):
    m=MapRenderer(tmp_path,lambda:{});m.point=lambda lat,lon:(int(1000+(lat-47.56)*100000),int(900+(lon+52.7)*100000))
    rows=[vessel(i,x=47.56+i*.0004,y=-52.70,speed=None if i==2 else 0) for i in range(3)]
    image=Image.new('RGB',(3840,2160),'black');d=ImageDraw.Draw(image)
    m.draw_vessels(d,{'vessels':rows,'connected':True},[],False)
    m.vessel_symbols(d,{'vessels':rows},False)
    for v in rows:
        x,y=m.point(v['lat'],v['lon'])
        assert image.getpixel((x,y))==(0,125,110)


def test_landmarks_include_four_offshore_fields_and_edge_hibernia(tmp_path):
    from skycam.map_renderer import LANDMARKS
    m=MapRenderer(tmp_path,lambda:{},scene='map-island',zoom=7,view_scale=.85)
    d=ImageDraw.Draw(Image.new('RGB',(3840,2160)))
    boxes=m.landmarks(d,False,m.occupied())
    assert {'HIBERNIA','HEBRON','TERRA NOVA','WHITE ROSE'}<=set(m.status['landmarks']['labelled'])
    # Previous hard-coded x<3200 gate lost an otherwise visible reference.
    m.point=lambda lat,lon:(3500,1000)
    m.landmarks(d,False,m.occupied())
    assert 'HIBERNIA' in m.status['landmarks']['labelled']


def test_field_labels_avoid_reserved_aircraft_and_own_symbols(tmp_path):
    from skycam.map_renderer import LANDMARKS
    m=MapRenderer(tmp_path,lambda:{},scene='map-ocean',zoom=6,view_scale=.65)
    x,y=m.point(LANDMARKS[2][1],LANDMARKS[2][2])
    plane=(x-200,y+70,x-140,y+130)
    d=ImageDraw.Draw(Image.new('RGB',(3840,2160)))
    m.landmarks(d,False,m.occupied()+[plane])
    def overlaps(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
    for box in m.status['landmarks']['label_boxes']:
        assert not overlaps(box,plane)
        for name,lat,lon,kind in LANDMARKS:
            px,py=m.point(lat,lon)
            assert not overlaps(box,(px-18,py-18,px+18,py+18))
