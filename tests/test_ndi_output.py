import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('ndi_output', Path(__file__).parents[1]/'deploy/ndi-output.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_optional_ndi_preserves_other_outputs_and_channels(tmp_path):
    paths = [tmp_path/'source.xml', tmp_path/'runtime.xml']
    xml = '<configuration><channels><channel><video-mode>2160p6000</video-mode><consumers><screen><device>2</device></screen><system-audio/></consumers></channel><channel><video-mode>720p3000</video-mode><consumers/></channel></channels></configuration>'
    for p in paths:
        p.write_text(xml)
    for enabled in (True, True, False, False):
        module.configure(paths, enabled)
        for p in paths:
            tree = ET.parse(p)
            consumers = tree.getroot().find('channels/channel/consumers')
            assert len(consumers.findall('ndi')) == int(enabled)
            assert consumers.find('screen/device').text == '2'
            assert consumers.find('system-audio') is not None
            assert [n.text for n in tree.findall('.//video-mode')] == ['2160p6000', '720p3000']
            if enabled:
                assert consumers.find('ndi/width').text == '1280'
                assert consumers.find('ndi/height').text == '720'


def test_invalid_second_config_does_not_modify_first(tmp_path):
    a, b = tmp_path/'a.xml', tmp_path/'b.xml'
    text = '<configuration><channels><channel><consumers/></channel></channels></configuration>'
    a.write_text(text)
    b.write_text('<broken>')
    with pytest.raises(ET.ParseError):
        module.configure([a, b], True)
    assert a.read_text() == text
