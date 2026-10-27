"""One phrase per process. The controller bounds runtime and retains cached audio."""
import argparse
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path


def complete(path,frames):
    try:
        with wave.open(str(path),'rb') as wav:
            return ((wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes()) ==
                    (2,2,48000,frames) and len(wav.readframes(frames))==frames*4)
    except (OSError,EOFError,wave.Error):
        return False


def render(generator, seed, mood, index, timeout=90):
    name = generator.name(seed, mood, index)
    path = generator.folder / name
    if complete(path,generator.length(mood)):
        return name
    path.unlink(missing_ok=True)
    generator.folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    try:
        # No shell, inherited secrets are never included in diagnostics.
        result = subprocess.run([sys.executable, '-m', 'skycam.music_worker',
            str(generator.folder.resolve()), str(seed), mood, str(index),
            "--radio-options",json.dumps(generator.radio_options)],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=timeout, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode:
            raise RuntimeError('Music renderer exited unsuccessfully; cached audio retained')
        if not complete(path,generator.length(mood)):
            raise ValueError('Music renderer produced an incomplete phrase')
        generator.last_render_seconds = round(time.monotonic() - started, 3)
        return name
    except Exception:
        path.unlink(missing_ok=True)
        path.with_suffix('.tmp').unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('seed', type=int)
    parser.add_argument('mood', choices=['coastal', 'night', 'lofi', 'study', 'warm', 'strudel', 'radio'])
    parser.add_argument('index', type=int)
    parser.add_argument('--radio-options',default='{}')
    args = parser.parse_args()
    if not 0 <= args.seed <= 2147483647 or args.index < 0:
        parser.error('Invalid music sequence')
    if os.name != 'nt':
        try:os.nice(10)
        except OSError:pass
    from .generative_music import Generator
    Generator(args.folder,json.loads(args.radio_options)).ensure(args.seed, args.mood, args.index)


if __name__ == '__main__':
    main()
