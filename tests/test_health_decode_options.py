import importlib.util
from pathlib import Path
import pytest
import shutil
import subprocess

spec=importlib.util.spec_from_file_location('health_decode_options',Path(__file__).parents[1]/'deploy/source-health.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_intel_without_vpp_keeps_hardware_decode_and_downloads_before_scaling():
    args,filters=module.decoder_options('/dev/dri/renderD128','software')
    assert args[:2]==['-hwaccel','vaapi']
    assert filters.split(',')==['hwdownload','format=nv12','scale=640:360','format=nv12']
    assert 'scale_vaapi' not in filters

def test_existing_hardware_and_cpu_paths_remain_distinct():
    assert module.decoder_options('/dev/dri/renderD128')[1].startswith('scale_vaapi=')
    assert module.decoder_options('','software')==(['-threads','1'],'scale=640:360,format=nv12')
    with pytest.raises(ValueError):module.decoder_options('/dev/dri/renderD128','unknown')


def test_sampling_precedes_download_without_manufacturing_duplicate_frames():
    for device in ('','/dev/dri/renderD128'):
        args,filters=module.decoder_options(device,'software',3)
        assert filters.startswith("select='not(mod(n,3))',")
        assert 'fps=' not in filters
        assert '-skip_frame' not in args
    for invalid in (0,7,True,2.5,'3'):
        with pytest.raises(ValueError):module.decoder_options('','software',invalid)


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg is required for the actual frame-selection check')
def test_real_sampler_emits_ten_actual_frames_from_thirty():
    args,filters=module.decoder_options('','software',3)
    data=subprocess.check_output(['ffmpeg','-v','error',*args,'-f','lavfi','-i',
        'testsrc2=size=64x64:rate=30:duration=1','-filter_threads','1',
        '-vf',filters,'-fps_mode','passthrough','-f','rawvideo','pipe:1'],timeout=15)
    assert len(data)==10*640*360*3//2
