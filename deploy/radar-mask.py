import cv2,numpy as np
for kind in ['east','island']:
 src=cv2.imread('work/radar-'+kind+'.jpg');hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV)
 land=((hsv[:,:,0]<53)&(hsv[:,:,1]>35)&(hsv[:,:,2]>20)).astype('uint8')*255
 land[:105]=0
 land=cv2.morphologyEx(land,cv2.MORPH_CLOSE,np.ones((3,3),'uint8'))
 n,l,stats,c=cv2.connectedComponentsWithStats(land)
 big=[i for i in range(1,n) if stats[i,4]>1000]
 mask=np.isin(l,big).astype('uint8')*255
 cv2.imwrite('work/radar-'+kind+'-land.png',mask)
