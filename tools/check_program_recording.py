# SPDX-License-Identifier: Apache-2.0
"""Check a local acceptance recording without opening any station or network feed."""
import argparse,json,math,subprocess
from pathlib import Path


def cadence(packets,kind,expected_fps=30):
    rows=[p for p in packets if p.get('codec_type')==kind]
    points=[]
    for row in rows:
        try:
            timestamp=float(row.get('pts_time',row.get('dts_time')))
            duration=float(row.get('duration_time',0))
            if math.isfinite(timestamp) and math.isfinite(duration):points.append((timestamp,max(0,duration)))
        except (ValueError,TypeError):continue
    if len(points)<2:return {'samples':len(points),'passed':False,'reason':'Insufficient timestamp evidence'}
    # Keep delivery order for audio; sort video PTS because B frames can be reordered.
    if kind=='video':points.sort()
    intervals=[b[0]-a[0] for a,b in zip(points,points[1:])]
    overlaps=sum(delta<=0 for delta in intervals)
    if kind=='video':
        limit=2.5/expected_fps
        gaps=[delta for delta in intervals if delta>limit]
    else:
        gaps=[b[0]-(a[0]+a[1]) for a,b in zip(points,points[1:]) if b[0]-(a[0]+a[1])>.1]
    span=points[-1][0]-points[0][0]
    rate=(len(points)-1)/span if span>0 else None
    matched=kind!='video' or (rate is not None and .98*expected_fps<=rate<=1.02*expected_fps)
    return {'samples':len(points),'first_timestamp':round(points[0][0],6),'last_timestamp':round(points[-1][0],6),'span_seconds':round(span,3),'measured_packets_per_second':round(rate,3) if rate is not None else None,
            'largest_interval_seconds':round(max(intervals),6),'large_gaps':len(gaps),'largest_gap_seconds':round(max(gaps,default=0),6),
            'nonadvancing_timestamps':overlaps,'expected_rate_met':matched,'passed':not gaps and not overlaps and matched}


def coverage(video,audio):
    if not all('first_timestamp' in row and 'last_timestamp' in row for row in (video,audio)):
        return {'passed':False,'reason':'Missing stream coverage'}
    start=audio['first_timestamp']-video['first_timestamp']
    end=audio['last_timestamp']-video['last_timestamp']
    # Allow joining within one two-second video GOP, but catch missing audio
    # at the start/end that a per-stream cadence check alone cannot detect.
    return {'passed':-2.1<=start<=1 and abs(end)<=1,
            'audio_minus_video_start_seconds':round(start,6),
            'audio_minus_video_end_seconds':round(end,6),
            'scope':'Stream coverage only, not perceptual lip-sync measurement'}


def inspect(path,expected_fps=30):
    path=Path(path).resolve(strict=True)
    if not path.is_file():raise ValueError('A local recording file is required')
    command=['ffprobe','-v','error','-show_streams','-show_packets','-show_entries','stream=codec_type,codec_name,width,height,sample_rate,avg_frame_rate,field_order:packet=codec_type,pts_time,dts_time,duration_time','-of','json',str(path)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=180,check=True)
    payload=json.loads(result.stdout)
    # A verification pass must not claim every CPU core on a host that is
    # simultaneously playing out. Bound decoder and filter parallelism.
    decode=subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-filter_threads','1','-i',str(path),'-f','null','-'],capture_output=True,text=True,timeout=180)
    video=cadence(payload['packets'],'video',expected_fps);audio=cadence(payload['packets'],'audio',expected_fps)
    streams=payload['streams'];rate=next((s.get('sample_rate') for s in streams if s['codec_type']=='audio'),None)
    alignment=coverage(video,audio)
    return {'passed':video['passed'] and audio['passed'] and alignment['passed'] and decode.returncode==0 and rate=='48000',
            'scope':'Packet cadence and decode integrity; not proof of picture quality or audible continuity',
            'streams':streams,'video':video,'audio':audio,'stream_coverage':alignment,'decode_clean':decode.returncode==0,'audio_rate_48000':rate=='48000'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recording',type=Path);parser.add_argument('--fps',type=float,default=30);parser.add_argument('--report',type=Path);args=parser.parse_args()
    if not math.isfinite(args.fps) or not 0<args.fps<=240:parser.error('Expected frame rate must be between 0 and 240')
    report=inspect(args.recording,args.fps);text=json.dumps(report,indent=2)
    if args.report:
        with args.report.open('x',encoding='utf-8') as f:f.write(text+'\n')
    print(text)
    raise SystemExit(0 if report['passed'] else 1)
