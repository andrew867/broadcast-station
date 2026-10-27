"""Synthetic surveyed scene, explicitly not a real St. John's calibration."""
import cv2
import numpy as np
from skycam.geometry import ecef, enu_rotation
from skycam.models import CameraRequest


def geodetic(p):
    x,y,z = p
    a,e2 = 6378137.,6.6943799901413165e-3
    lon=np.arctan2(y,x); radius=np.hypot(x,y); lat=np.arctan2(z,radius*(1-e2))
    for _ in range(12):
        n=a/np.sqrt(1-e2*np.sin(lat)**2)
        height=radius/np.cos(lat)-n
        lat=np.arctan2(z,radius*(1-e2*n/(n+height)))
    return float(np.degrees(lat)),float(np.degrees(lon)),float(height)


def scene(outlier=False):
    width,height,f=1280,720,850.
    k=np.array([[f,0,width/2],[0,f,height/2],[0,0,1.]])
    distortion=np.array([-.12,.025,0.,0.,0.])
    pitch=np.radians(10)
    rotation=np.array([[1,0,0],[0,np.sin(pitch),-np.cos(pitch)],[0,np.cos(pitch),np.sin(pitch)]])
    rvec=cv2.Rodrigues(rotation)[0].ravel()
    origin=ecef(47.0,-52.0,233-20)
    basis=enu_rotation(47.0,-52.0)
    points=[]
    for row in range(4):
        for col in range(5):
            xn=-.65+col*.325
            yn=-.34+row*.2266667
            depth=900+row*570+col*230
            enu=rotation.T @ (np.array([xn,yn,1.])*depth)
            lat,lon,alt=geodetic(origin+basis.T@enu)
            uv=cv2.projectPoints(np.array([enu]),rvec,np.zeros(3),k,distortion)[0].reshape(2)
            points.append({'name':f'SYNTHETIC {row+1}-{col+1}','x':float(uv[0]),'y':float(uv[1]),
                           'lat':lat,'lon':lon,'altitude_msl_m':alt+20,
                           'validation':(row,col) in [(0,1),(1,4),(2,0),(3,3)]})
    if outlier:
        points[7]['x']+=80
        points[7]['y']-=50
    req=CameraRequest(name='SYNTHETIC test scene, not a real camera',width=width,height=height,
        site={'lat':47.0,'lon':-52.0,'altitude_msl_m':233,'geoid_separation_m':-20,'verified':True},
        landmarks=points,fit_distortion=True)
    return req,{'K':k.tolist(),'rvec':rvec.tolist(),'distortion':distortion.tolist()}
