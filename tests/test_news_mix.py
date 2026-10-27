import time
from skycam.broadcast import Broadcast,BroadcastState,mix_headlines,parse_feed


def rows(prefix,n):
    return [{'title':f'{prefix} {i}','source':prefix} for i in range(n)]


def test_balanced_and_uplifting_keep_general_news_without_repeats():
    groups={'good_news':rows('Good',12),'positive_news':rows('Community',8),'vocm':rows('Local',16)}
    balanced=mix_headlines(groups,'balanced')
    assert [r['source'] for r in balanced[:4]]==['Good','Local','Community','Local']
    assert len(balanced)==16 and sum(r['source']=='Local' for r in balanced)==8
    upbeat=mix_headlines(groups,'uplifting')
    assert [r['source'] for r in upbeat[:3]]==['Good','Community','Local']
    assert sum(r['source']=='Local' for r in upbeat)==5
    groups['good_news']=rows('Local',3)
    assert len({r['title'] for r in mix_headlines(groups,'balanced')})==16
    assert mix_headlines({'vocm':rows('Local',3)},'uplifting')==rows('Local',3)
    assert mix_headlines({},'balanced')==[]


def test_community_dates_expire_and_stale_feed_never_looks_fresh(tmp_path):
    b=Broadcast(tmp_path);now=time.time()
    b.save(BroadcastState(news_sources=['positive_news','vocm'],news_mix='balanced'))
    b.news['positive_news']={'fetched_at':now,'items':[{'title':'Community','published_at':now-4*86400},{'title':'Old','published_at':now-8*86400}]}
    b.news['vocm']={'fetched_at':now,'items':[{'title':'Old general','published_at':now-2*86400}]}
    assert [r['title'] for r in b.public()['headlines']]==['Community']
    b.news['positive_news']['fetched_at']=now-1801
    assert b.public()['headlines']==[]
    b.save(BroadcastState(ticker_speed=175))
    assert b.state.news_mix=='balanced'


def test_feed_dates_labels_and_excludes_history_without_headline_rewrites():
    xml=b'<rss><channel><item><title>A kind act &amp; a community</title><link>https://example.org/story</link><pubDate>Sun, 18 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Historical item</title><link>https://example.org/history</link><pubDate>Sun, 18 Oct 2026 12:00:00 GMT</pubDate><category>This Day In History</category></item></channel></rss>'
    result=parse_feed(xml,'good_news',1792339200)
    assert len(result)==1 and result[0]['title']=='A kind act & a community'
    assert result[0]['display_source']=='Good News Network / Oct 18'
    assert result[0]['source']=='Good News Network'


def test_gazette_selection_migrates_without_other_operator_changes(tmp_path):
    b=Broadcast(tmp_path)
    b.save(BroadcastState(news_sources=['vocm','mun_gazette'],news_mix='balanced',ticker_speed=180))
    assert b.state.news_sources==['vocm','positive_news']
    # Simulate a persisted pre-upgrade selection as well as an old browser.
    raw=b.state.model_dump();raw['news_sources']=['good_news','mun_gazette']
    import json
    b.path.write_text(json.dumps(raw))
    restored=Broadcast(tmp_path)
    assert restored.state.news_sources==['good_news','positive_news']
    assert restored.state.ticker_speed==180 and restored.state.news_mix=='balanced'
    assert 'mun_gazette' not in restored.path.read_text()
