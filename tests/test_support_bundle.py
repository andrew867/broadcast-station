import hashlib,json,zipfile
import pytest
from tools.support_bundle import build
from tools.stationctl import prepare


def test_support_report_omits_raw_text_secrets_and_logs(tmp_path):
    home=prepare(tmp_path/'station');secret='private-value-do-not-include'
    (home/'station.json').write_text(json.dumps({'schema_version':1,'location':{'name':secret},'secrets':{'finnhub':secret},'inputs':{'camera_base':secret},'output':{'profile':'1080p3000','publish_url':secret},'providers':{'weather':True,secret:True}}))
    (home/'data/broadcast/cameras.json').write_text(json.dumps({'cameras':[{'enabled':True,'name':secret,'source':secret}]}))
    (home/'runtime/watchdog.json').write_text(json.dumps({'checked_at':42,'frame':20,'error':secret,'note':secret}))
    (home/'logs/engine.log').write_text(secret)
    path=tmp_path/'support.zip';result=build(home,path)
    with zipfile.ZipFile(path) as z:
        assert sorted(z.namelist())==['manifest.json','report.json']
        assert secret.encode() not in z.read('report.json')
        report=json.loads(z.read('report.json'))
        assert report['camera_counts']=={'configured':1,'enabled':1}
        assert report['enabled_providers']==['weather'] and report['watchdog']['frame']==20
        assert hashlib.sha256(z.read('report.json')).hexdigest()==json.loads(z.read('manifest.json'))['report.json']
    assert result['files']==2
    with pytest.raises(FileExistsError):build(home,path)


def test_support_report_survives_bad_or_missing_diagnostics(tmp_path):
    home=prepare(tmp_path/'station');(home/'station.json').write_text('{broken')
    path=tmp_path/'support.zip';build(home,path)
    with zipfile.ZipFile(path) as z:
        assert json.loads(z.read('report.json'))['profile'] is None
