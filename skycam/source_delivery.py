# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serve the source archive assembled with this image, never runtime files."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get('/source')
def source_archive():
    path = Path(os.environ.get('STATION_SOURCE_ARCHIVE', '/app/source/station-source.tar.gz'))
    if not path.is_file():
        raise HTTPException(503, 'Source archive not packaged. See docs/SOURCE-AND-LICENCES.md for local development instructions.')
    return FileResponse(path, media_type='application/gzip', filename='station-source.tar.gz')
