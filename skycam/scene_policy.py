"""Automatic playout eligibility and operator-facing source confidence."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


class ScenePolicy:
    """Keep source health separate from manual scene availability."""

    def __init__(self, *, weather=None, travel=None, marine=None, tides=None,
                 ais=None, notices=None, outages=None, alerts=None, features=None):
        self.weather=weather;self.travel=travel;self.marine=marine;self.tides=tides
        self.ais=ais;self.notices=notices;self.outages=outages;self.alerts=alerts
        self.features=features

    @staticmethod
    def _result(state='current', detail='Available', checked_at=None, exceptional=False):
        return {'state':state,'current':state=='current','exceptional':bool(exceptional),
                'detail':detail,'checked_at':checked_at}

    def scene(self, scene, now=None):
        now=time.time() if now is None else now
        try:
            from .sources import CAMERAS,QUADS
            if scene in CAMERAS or scene in QUADS:
                confidence=self.features.confidence() if self.features else {}
                rows={row.get('id'):row for row in confidence.get('sources',[]) if isinstance(row,dict) and row.get('id')}
                members=QUADS.get(scene,[scene]);states=[];checked=[]
                for camera in members:
                    config=CAMERAS.get(camera,{})
                    row=rows.get(camera,{})
                    stamp=row.get('at') or 0
                    if stamp:checked.append(stamp)
                    if not config.get('enabled'):
                        states.append('unavailable')
                    elif row.get('fresh'):
                        states.append('current')
                    elif stamp and 0<=now-stamp<=180:
                        states.append('cached')
                    else:
                        states.append('unavailable')
                usable=sum(state!='unavailable' for state in states)
                current=sum(state=='current' for state in states)
                state='current' if current else 'cached' if usable else 'unavailable'
                if scene in QUADS:
                    detail=f'{current} current, {usable-current} held of {len(members)} camera pictures'
                else:
                    detail={'current':'Recent decoded picture','cached':'Holding last decoded picture','unavailable':'No recent decoded picture'}[state]
                return self._result(state,detail,max(checked) if checked else None)
            if scene in ('weather','weather-timeline'):
                data=self.weather.public(now) if self.weather else {}
                good=bool(data.get('forecast_available'))
                return self._result('current' if good else 'unavailable',
                    'Official forecast is current' if good else 'Official forecast unavailable',data.get('fetched_at'))
            if scene in ('morning-briefing','evening-briefing'):
                weather=self.weather.public(now) if self.weather else {}
                travel=self.travel.public(now) if self.travel else {}
                outages=self.outages.public(now) if self.outages else {}
                sources=sum((bool(weather.get('forecast_available')),bool(travel.get('available')),bool(outages.get('fresh'))))
                checked=max(weather.get('fetched_at') or 0,travel.get('checked_at') or 0,outages.get('checked_at') or 0) or None
                return self._result('current' if sources else 'unavailable',
                    f'{sources} of 3 briefing sources current' if sources else 'Briefing sources unavailable',checked)
            if scene=='nl-travel':
                data=self.travel.public(now) if self.travel else {}
                good=bool(data.get('available'));exceptional=bool(data.get('exceptional'))
                return self._result('current' if good else 'unavailable',
                    data.get('summary') or ('Travel data is current' if good else 'Travel data unavailable'),data.get('checked_at'),exceptional)
            if scene=='harbour-watch':
                marine=self.marine.public(now) if self.marine else {}
                tides=self.tides.public(now) if self.tides else {}
                ais=self.ais.public(now) if self.ais else {}
                good=bool(marine.get('available') or tides.get('available') or ais.get('counts',{}).get('fresh'))
                return self._result('current' if good else 'unavailable',
                    'Marine, tide or vessel data is current' if good else 'Harbour data unavailable',
                    max(marine.get('checked_at') or 0,tides.get('checked_at') or 0,ais.get('last_position_at') or 0) or None)
            if scene=='tonights-sky':
                return self._result('current','Astronomical calculations are available',now)
            if scene in ('community-calendar','community-notices'):
                instant=datetime.fromtimestamp(now,timezone.utc)
                items=(self.notices.public(instant).get('items') or []) if self.notices else []
                horizon=instant+timedelta(days=21)
                rows=[]
                for item in items:
                    if not item.get('approved'):continue
                    start=datetime.fromisoformat(item['starts_at']) if item.get('starts_at') else instant
                    end=datetime.fromisoformat(item['ends_at']) if item.get('ends_at') else horizon
                    if end>=instant and start<=horizon:rows.append(item)
                return self._result('current' if rows else 'unavailable',
                    f'{len(rows)} approved upcoming item'+('s' if len(rows)!=1 else '') if rows else 'No approved upcoming items',now)
            if scene=='power-outages':
                data=self.outages.public(now) if self.outages else {}
                rows=data.get('active') or []
                return self._result('current' if data.get('fresh') else 'cached' if rows else 'unavailable',
                    f'{len(rows)} current outage'+('s' if len(rows)!=1 else ''),data.get('checked_at'),bool(rows))
            if scene in ('weather-alerts','emergency-alerts'):
                data=self.alerts.public(now) if self.alerts else {}
                rows=[*(data.get('alerts') or data.get('items') or []),*(data.get('immediate') or [])]
                return self._result('current' if rows else 'unavailable',
                    f'{len(rows)} current alert'+('s' if len(rows)!=1 else ''),data.get('checked_at'),bool(rows))
            if scene=='last-hour':
                data=self.features.public().get('timelapse',{}) if self.features else {}
                count=data.get('frames',data.get('count',len(data.get('entries',[]))))
                return self._result('current' if count else 'unavailable',
                    f'{count} recent picture'+('s' if count!=1 else '') if count else 'No recent pictures',now)
        except (KeyError,TypeError,ValueError,OSError,RuntimeError):
            return self._result('unavailable','Source check failed')
        return self._result()

    def cue_eligible(self, scene, condition='auto'):
        status=self.scene(scene)
        if condition=='always':return True
        if condition=='when-exception':return status['exceptional']
        if condition=='when-current':return status['current']
        from .sources import CAMERAS,QUADS
        controlled={*CAMERAS,*QUADS,
            'weather','weather-timeline','morning-briefing','evening-briefing','nl-travel',
            'harbour-watch','community-calendar','community-notices','power-outages',
            'weather-alerts','emergency-alerts','last-hour'}
        return status['state']!='unavailable' or scene not in controlled

    def clock_eligible(self, condition):
        if condition=='always':return True
        if condition=='camera-degraded':
            try:return any(not row.get('fresh') for row in self.features.confidence().get('sources',[]))
            except (AttributeError,KeyError,TypeError,ValueError,OSError,RuntimeError):return False
        mapping={'power-outages':'power-outages','weather-alerts':'weather-alerts','travel-exceptions':'nl-travel'}
        return self.scene(mapping.get(condition,condition))['exceptional']

    def public(self, scenes):
        return {'checked_at':time.time(),'scenes':{scene:self.scene(scene) for scene in scenes}}
