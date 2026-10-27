"""Bounded, authenticated CAP audio resources. Never fetch arbitrary alert URLs."""
import base64
import hashlib
import hmac
import os
import re
import subprocess
import time
from urllib.parse import urlsplit

import httpx
import numpy as np

MAX_AUDIO_BYTES = 4 * 1024 * 1024
MAX_AUDIO_SECONDS = 120
DEFAULT_HOSTS = ('capcp1.naad-adna.pelmorex.com', 'capcp2.naad-adna.pelmorex.com',
                 'alerts.weather.gc.ca')


def resources(info, ns):
    """Only the explicitly designated audience audio, in its own language block."""
    rows = []
    for node in info.findall('c:resource', ns):
        text = lambda name: (node.findtext('c:' + name, '', ns) or '').strip()
        mime = text('mimeType').lower().split(';')[0]
        if text('resourceDesc') != 'Broadcast Audio' or mime not in (
                'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/wave'):
            continue
        size = text('size')
        if size and (not size.isdigit() or int(size) > MAX_AUDIO_BYTES):
            continue
        rows.append({'mime_type': mime, 'uri': text('uri'), 'inline': text('derefUri'),
                     'digest': text('digest'), 'size': int(size) if size else None})
    return sorted(rows, key=lambda r: r['mime_type'] not in ('audio/mpeg', 'audio/mp3'))[:2]


def allowed_url(uri, hosts):
    parsed = urlsplit(uri)
    if (parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username
            or parsed.password or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError('Audio URL is not on the approved HTTPS host list')
    return uri


def validate_bytes(data, row):
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise ValueError('Audio resource size outside limit')
    if row.get('size') is not None and len(data) != row['size']:
        raise ValueError('Audio resource size mismatch')
    # CAP 1.2 specifies SHA-1 for resource integrity. This is not issuer trust.
    digest = row.get('digest', '')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', digest):
        raise ValueError('Audio needs the CAP SHA-1 resource digest')
    if not hmac.compare_digest(hashlib.sha1(data).hexdigest(), digest.lower()):
        raise ValueError('Audio resource digest mismatch')
    return data


def fetch_resource(row, client, hosts, deadline):
    if row.get('uri'):
        try:
            allowed_url(row['uri'], hosts)
            data = bytearray()
            with client.stream('GET', row['uri']) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    if time.monotonic() > deadline:
                        raise ValueError('Audio download deadline exceeded')
                    data.extend(chunk)
                    if len(data) > MAX_AUDIO_BYTES:
                        raise ValueError('Audio resource exceeds size limit')
            return validate_bytes(bytes(data), row)
        except (httpx.HTTPError, ValueError):
            if not row.get('inline'):
                raise
    if row.get('inline'):
        if len(row['inline']) > MAX_AUDIO_BYTES * 4 // 3 + 4:
            raise ValueError('Inline audio exceeds size limit')
        return validate_bytes(base64.b64decode(row['inline'], validate=True), row)
    raise ValueError('Audio resource has no usable content')


def supplied_audio(alert, folder, key):
    """Return decoded mono 48 kHz samples, or a diagnostic for speech fallback."""
    if alert.get('utility') or not alert.get('audio_resources'):
        return None, None
    if alert.get('verification', {}).get('verified') is not True:
        return None, 'Supplied audio requires authenticated CAP'
    hosts = set(DEFAULT_HOSTS) | set(filter(None, os.environ.get('SKYCAM_CAP_AUDIO_HOSTS', '').split(',')))
    deadline = time.monotonic() + 25
    errors = []
    source = folder / (key + '.resource')
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=False) as client:
            for row in alert['audio_resources'][:2]:
                if time.monotonic() > deadline:
                    break
                try:
                    source.write_bytes(fetch_resource(row, client, hosts, deadline))
                    # Disable nested playlists and network protocols in the decoder.
                    result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error',
                        '-protocol_whitelist', 'file,pipe', '-f',
                        'mp3' if row['mime_type'] in ('audio/mpeg', 'audio/mp3') else 'wav',
                        '-i', str(source), '-vn',
                        '-t', str(MAX_AUDIO_SECONDS + 1), '-ac', '1', '-ar', '48000',
                        '-f', 'f32le', 'pipe:1'], capture_output=True, check=True, timeout=15)
                    samples = np.frombuffer(result.stdout, '<f4').copy()
                    if not 0 < len(samples) <= 48000 * MAX_AUDIO_SECONDS or not np.isfinite(samples).all():
                        raise ValueError('Supplied audio exceeds duration or format limits')
                    if float(np.max(np.abs(samples))) < .0001:
                        raise ValueError('Supplied audio is silent')
                    return samples, None
                except (ValueError, OSError, subprocess.SubprocessError, httpx.HTTPError) as exc:
                    errors.append(type(exc).__name__)
    finally:
        source.unlink(missing_ok=True)
    return None, 'Supplied audio unavailable or invalid; using local speech (' + ', '.join(errors) + ')'
