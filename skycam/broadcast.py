from .public_errors import public_error
from .station_config import CONFIG
from .branding import BRAND
"""Local broadcast state and attributed, time-bounded RSS headlines."""

import asyncio

from datetime import datetime, timezone

from email.utils import parsedate_to_datetime

import json

import html

from itertools import zip_longest

import time

from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import xml.etree.ElementTree as ET

import httpx

from pydantic import Field

from .models import StrictModel
from .language_policy import english,xml_language

SOURCES = {

    'vocm': ('VOCM','https://vocm.com/feed/'),

    'ntv': ('NTV','https://ntv.ca/feed/'),

    'cbc_nl': ('CBC Newfoundland & Labrador','https://www.cbc.ca/webfeed/rss/rss-canada-newfoundland'),

    'cbc_canada': ('CBC Canada','https://www.cbc.ca/webfeed/rss/rss-canada'),

    'bbc_world': ('BBC World','https://feeds.bbci.co.uk/news/world/rss.xml'),
    'good_news': ('Good News Network','https://www.goodnewsnetwork.org/feed/'),
    'positive_news': ('Positive News','https://www.positive.news/feed/'),

}

COMMUNITY_SOURCES = {'good_news', 'positive_news'}
SOURCE_AGE = {'good_news':72*3600, 'positive_news':7*24*3600}
EXCLUDED_CATEGORIES = {'this day in history','on this day','horoscopes','good gifts','sponsored'}


def interleave(groups):
    unique={}
    for row in zip_longest(*groups):
        for item in row:
            if item:unique.setdefault(item['title'].casefold(),item)
    return list(unique.values())


def mix_headlines(groups, mode):
    if mode=='standard':return interleave(list(groups.values()))[:16]
    community=interleave([v for k,v in groups.items() if k in COMMUNITY_SOURCES])
    general=interleave([v for k,v in groups.items() if k not in COMMUNITY_SOURCES])
    result={}; c=g=0
    while len(result)<16 and (c<len(community) or g<len(general)):
        for _ in range(2 if mode=='uplifting' else 1):
            if c<len(community):
                item=community[c];c+=1;result.setdefault(item['title'].casefold(),item)
        if g<len(general):
            item=general[g];g+=1;result.setdefault(item['title'].casefold(),item)
    return list(result.values())[:16]


def parse_feed(content,key,now):
    root=ET.fromstring(content);items=[];name=SOURCES[key][0]
    channel=root.find('channel')
    feed_language=xml_language(channel,xml_language(root)) if channel is not None else xml_language(root)
    for item in root.findall('.//item')[:40]:
        language=xml_language(item,feed_language)
        if not english(language):continue
        title=html.unescape(' '.join((item.findtext('title') or '').split()))[:220]
        link=(item.findtext('link') or '').strip()
        categories={(n.text or '').strip().casefold() for n in item.findall('category')}
        if key in COMMUNITY_SOURCES and categories & EXCLUDED_CATEGORIES:continue
        try:date=parsedate_to_datetime(item.findtext('pubDate') or '').timestamp()
        except (ValueError,TypeError,AttributeError):continue
        if title and link.startswith('https://') and -300<=now-date<=SOURCE_AGE.get(key,36*3600):
            label=name
            if key in COMMUNITY_SOURCES:
                label+=' / '+datetime.fromtimestamp(date,ZoneInfo(CONFIG.location.timezone)).strftime('%b %d')
            items.append({'title':title,'link':link,'source':name,'display_source':label,'source_id':key,'published_at':date,'language':language or 'en'})
    return items


class BroadcastState(StrictModel):

    station: str = Field(default='STATION',min_length=1,max_length=40)

    camera: str = Field(default='cam1',pattern=r'^[a-z0-9][a-z0-9_-]{0,47}$')

    location: str = Field(default=CONFIG.location.name,max_length=70)

    kicker: str = Field(default='',max_length=40)

    headline: str = Field(default='',max_length=80)

    subline: str = Field(default='',max_length=140)

    scene: str = Field(default='standard',pattern=r'^(standard|breaking|clean|standby)$')

    show_lower: bool = True

    show_ticker: bool = True

    show_aircraft: bool = False

    ticker_speed: float = Field(default=150,ge=60,le=260)

    ticker_note: str = Field(default=BRAND.station_name,max_length=500)

    news_sources: list[str] = Field(default_factory=lambda:['vocm','ntv','cbc_nl','cbc_canada','bbc_world'],max_length=7)

    news_mix: Literal['standard','balanced','uplifting'] = 'standard'

def clean_legacy_copy(state):
    """Migrate only known stock copy; custom editorial fields remain untouched."""
    def normalize(value):return value.replace('\u2019',"'").strip()
    update={}
    if normalize(state.headline)=="THE SKY ABOVE ST. JOHN'S" and state.scene=='standard':
        update['headline']=''
        if state.kicker=='ACROSS THE CITY':update['kicker']=''
        if normalize(state.subline) in (
            "Live sky views from St. John's, Quidi Vidi Lake and Torbay",
            "Live views from St. John's, Quidi Vidi Lake and Torbay"):
            update['subline']=''
    if normalize(state.ticker_note)=="ST. JOHN'S SKYCAM • Views across the city • All times Newfoundland local":
        update['ticker_note']=BRAND.station_name
    return state.model_copy(update=update)


class Broadcast:

    def __init__(self,data: Path):

        self.path=data/'broadcast'/'state.json'

        self.news={}

        self.state=BroadcastState()

        if self.path.exists():

            self.state=BroadcastState.model_validate_json(self.path.read_text(encoding='utf-8'))
            cleaned=clean_legacy_copy(self.state)
            if cleaned!=self.state:
                archive=self.path.with_name('state-before-copy-cleanup.json')
                if not archive.exists():archive.write_text(self.state.model_dump_json(indent=2),encoding='utf-8')
                self.save(cleaned)
            if 'mun_gazette' in self.state.news_sources:self.save(self.state)

    def save(self,state):

        state=state.model_copy(update={'news_sources':list(dict.fromkeys('positive_news' if k=='mun_gazette' else k for k in state.news_sources))})

        if 'news_mix' not in state.model_fields_set:
            state=state.model_copy(update={'news_mix':self.state.news_mix})

        if any(s not in SOURCES for s in state.news_sources):

            raise ValueError('Unknown news source')

        self.path.parent.mkdir(parents=True,exist_ok=True)

        temporary=self.path.with_suffix('.tmp')

        temporary.write_text(state.model_dump_json(indent=2),encoding='utf-8')

        temporary.replace(self.path)

        self.state=state

    def public(self):

        now=time.time();groups={}
        for source in dict.fromkeys(self.state.news_sources):
            entry=self.news.get(source,{})
            if now-entry.get('fetched_at',0)>1800:continue
            groups[source]=sorted([p for p in entry.get('items',[]) if english(p.get('language')) and -300<=now-p['published_at']<=SOURCE_AGE.get(source,36*3600)],key=lambda p:p['published_at'],reverse=True)
        return {'state':self.state.model_dump(),'headlines':mix_headlines(groups,self.state.news_mix),

                'sources':{s:{'name':SOURCES[s][0],'url':SOURCES[s][1],**self.news.get(s,{})} for s in SOURCES},

                'server_time':now}

    async def refresh(self):

        async with httpx.AsyncClient(timeout=12,follow_redirects=True,trust_env=False,

                headers={'User-Agent':'SkyCam/1.0 RSS headline reader'}) as client:

            for key,(name,url) in SOURCES.items():

                try:

                    async with client.stream('GET',url) as response:

                        response.raise_for_status();parts=[];size=0

                        async for chunk in response.aiter_bytes():

                            size+=len(chunk)

                            if size>1_000_000:raise ValueError('Feed exceeds size limit')

                            parts.append(chunk)

                    items=parse_feed(b''.join(parts),key,time.time())

                    self.news[key]={'items':items,'fetched_at':time.time(),'error':None}

                except Exception as exc:

                    previous=self.news.get(key,{'items':[],'fetched_at':0})

                    self.news[key]={**previous,'error':f'{type(exc).__name__}: {public_error(exc)[:100]}'}

    async def poll(self):

        while True:

            await self.refresh()

            await asyncio.sleep(300)

