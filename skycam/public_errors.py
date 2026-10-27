"""Operator-facing errors must not include transport credentials or command lines."""
import re
import subprocess


def public_error(error):
    if isinstance(error,subprocess.TimeoutExpired):return 'Media operation timed out'
    if isinstance(error,subprocess.SubprocessError):return 'Media operation failed'
    if isinstance(error,OSError):return 'Local service or file operation failed'
    text=str(error)
    text=re.sub(r'(?i)\b(?:https?|wss?|rtsp|rtmp|srt|file)://[^\s<>]+','[endpoint]',text)
    text=re.sub(r'(?i)\b(?:api[_-]?key|token|password|authorization|secret)\s*[=:]\s*[^\s,;]+','[credential]',text)
    text=re.sub(r'(?i)\bbearer\s+[^\s,;]+','[credential]',text)
    text=re.sub(r'(?:[A-Za-z]:[\\/]|/(?:home|root|tmp|run|etc|workspace|station|app)/)[^\s<>]+','[local path]',text)
    return text[:300] or type(error).__name__
