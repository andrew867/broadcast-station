from copy import deepcopy
import pytest
from skycam.alerts import Alerts,HOSTS
from skycam.alert_graphics import page_rows,emergency_rows
from skycam.alert_presentation import AlertPresentation
from skycam.broadcast import parse_feed,Broadcast,BroadcastState
from skycam.language_policy import english
from tests.test_alerts import message,NOW


@pytest.mark.parametrize('tag',['fr','fr-CA','FR-ca','fr_CA','fra','fre','de','enough'])
def test_only_english_presentation(tag):
    assert not english(tag)


def test_cached_french_is_hidden_without_mutating_verification_or_cancel(tmp_path,monkeypatch):
    monkeypatch.setattr("skycam.alerts.time.time",lambda:NOW)
    alerts=Alerts(tmp_path,lambda _: {'verified':True})
    raw=message(immediate='yes')
    a=raw.index(b'<info>');b=raw.index(b'</info>')+7
    french=raw[a:b].replace(b'en-CA',b'FR-ca')
    alerts.ingest(raw.replace(b'</alert>',french+b'</alert>'),HOSTS[0],NOW)
    original=deepcopy(alerts.items)
    alerts.persist()
    restored=Alerts(tmp_path,lambda _: {'verified':True})
    for resources in (False,True):
        result=restored.public(NOW,include_resources=resources)
        assert len(result['immediate'])==1
        assert result['immediate'][0]['language']=='en-CA'
        assert result['language_excluded']==1
    assert alerts.items==original
    # A verified cancellation still retires the English alert, even when its
    # optional info block is French. Never filter protocol lifecycle messages.
    cancel=message('cancel',kind='Cancel',references='test-issuer,one,2026-10-17T15:00:00Z').replace(b'en-CA',b'fr-CA')
    restored.ingest(cancel,HOSTS[0],NOW)
    assert restored.public(NOW)['immediate']==[]


def test_french_never_becomes_page_or_speech_candidate(tmp_path):
    alerts=Alerts(tmp_path,lambda _: {'verified':True})
    alerts.ingest(message(immediate='yes'),HOSTS[0],NOW)
    row={**alerts.public(NOW)['immediate'][0],'language':'fr-CA'}
    assert page_rows([row])==emergency_rows([row])==[]
    class Audio:
        def prepare(self,*args):raise AssertionError('Excluded language reached audio')
        def public(self):return {}
    p=AlertPresentation(tmp_path,lambda:{'immediate':[row]},None,Audio())
    assert p.frame(NOW) is None


def test_news_language_inheritance_and_item_override(tmp_path,monkeypatch):
    item='<item {attr}><title>{title}</title><link>https://example.org/story</link><pubDate>Sun, 18 Oct 2026 12:00:00 GMT</pubDate>{extra}</item>'
    body=''.join(item.format(attr=attr,title=title,extra=extra) for attr,title,extra in [
        ('','Inherited French',''),('xml:lang="en-CA"','English override',''),
        ('','Explicit French','<dc:language>fr-CA</dc:language>')])
    xml='<rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><language>fr-CA</language>'+body+'</channel></rss>'
    result=parse_feed(xml.encode(),'positive_news',1792339200)
    assert [r['title'] for r in result]==['English override']
    b=Broadcast(tmp_path);b.state=BroadcastState(news_sources=['positive_news'])
    monkeypatch.setattr('skycam.broadcast.time.time',lambda:1792339200)
    b.news['positive_news']={'fetched_at':1792339200,'items':result+[{**result[0],'title':'Cached French','language':'fr'}]}
    assert [r['title'] for r in b.public()['headlines']]==['English override']
