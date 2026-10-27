"""Station-owned radar reference pictures and their matching fitted models."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image


def load_calibration(folder,kind):
    if kind not in ('east','island'):raise ValueError('Unknown radar view')
    folder=Path(folder)
    model=folder/(kind+'.json');reference=folder/(kind+'-reference.jpg')
    for path in (model,reference):
        if path.is_symlink() or path.stat().st_size>8_000_000:raise ValueError('Invalid radar calibration asset')
    calibration=json.loads(model.read_text())
    parameters=calibration.get('parameters',[])
    if (calibration.get('kind')!=kind or calibration.get('model')!='spherical-camera'
        or calibration.get('width')!=960 or calibration.get('height')!=540
        or len(parameters)!=7 or any(type(p) not in (int,float) or not math.isfinite(p) for p in parameters)
        or not 0<parameters[6]<15):raise ValueError('Invalid radar calibration model')
    with Image.open(reference) as image:
        if image.size!=(960,540):raise ValueError('Radar reference dimensions do not match calibration')
        pixels=np.array(image.convert('RGB'))
    return calibration,pixels
