"""Inspect uploaded MP4 in time-bounded processes with no network protocols."""
import io,json,math,os,subprocess,tempfile,time
from fractions import Fraction
from PIL import Image

def bounded_process(command,output_limit,timeout=12):
    """Spool codec output outside Python memory and stop noisy/hung decoders."""
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=output,stderr=errors)
        deadline=time.monotonic()+timeout
        try:
            while process.poll() is None:
                if time.monotonic()>deadline:raise subprocess.TimeoutExpired(command,timeout)
                if os.fstat(output.fileno()).st_size>output_limit or os.fstat(errors.fileno()).st_size>262144:
                    raise ValueError('Decoder output exceeds limit')
                time.sleep(.05)
            if process.returncode:raise subprocess.CalledProcessError(process.returncode,command)
            if os.fstat(output.fileno()).st_size>output_limit or os.fstat(errors.fileno()).st_size>262144:
                raise ValueError('Decoder output exceeds limit')
            output.seek(0)
            return output.read(output_limit+1)
        finally:
            if process.poll() is None:process.kill()
            process.wait(timeout=5)


def video_poster(path):
    try:
        result=bounded_process(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-select_streams','v:0',
            '-show_entries','stream=codec_name,width,height,avg_frame_rate:format=duration','-of','json',str(path)],
            output_limit=100_000)
        data=json.loads(result);stream=data['streams'][0]
        w=int(stream['width']);h=int(stream['height']);fps=float(Fraction(stream['avg_frame_rate']));duration=float(data['format']['duration'])
        if not(0<w<=1920 and 0<h<=1080 and math.isfinite(fps) and 1<=fps<=60 and math.isfinite(duration) and 1<=duration<=180) or stream['codec_name']!='h264':
            raise ValueError('Use H.264 MP4, up to 1080p60 and 180 seconds')
        poster=None
        for position in (0,duration/2,max(0,duration-.2)):
            frame=bounded_process(['ffmpeg','-v','error','-nostdin','-threads','1','-filter_threads','1',
                '-protocol_whitelist','file,pipe','-ss',str(position),'-i',str(path),'-an','-frames:v','1',
                '-vf','scale=1920:1080:force_original_aspect_ratio=decrease','-f','image2pipe','-c:v','png','pipe:1'],
                output_limit=10*1024*1024)
            if not frame:raise ValueError('Video preview is absent')
            with Image.open(io.BytesIO(frame),formats=('PNG',)) as image:
                image.load()
                if poster is None:poster=image.convert('RGB').copy()
        return w,h,fps,duration,poster
    except (OSError,subprocess.SubprocessError,KeyError,IndexError,ZeroDivisionError,json.JSONDecodeError) as exc:
        # Do not disclose decoder stderr, filesystem paths or embedded media URLs.
        raise ValueError('Video could not be safely decoded within the time limit') from None
