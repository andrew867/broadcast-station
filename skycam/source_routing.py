"""One optional loopback fan-out, with an explicit direct-source rollback."""
import json
from pathlib import Path

from .station_config import CONFIG
DIRECT=CONFIG.inputs.camera_base
SHARED=CONFIG.inputs.camera_shared_base

def camera_base(data):
    try:
        config=json.loads((Path(data)/'broadcast'/'source-routing.json').read_text())
        return SHARED if config.get('shared_camera_inputs') is True else DIRECT
    except (OSError,ValueError,TypeError):return DIRECT
