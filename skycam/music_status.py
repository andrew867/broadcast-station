"""Separate expected queue progress from faults, including older observations."""
PROGRESS_MESSAGES=frozenset({
    'Preparing generated music; existing audio continues',
    'New variation ready; changes at the next phrase boundary',
    'Level-matched playlist will follow the current track',
})

def split_status(value):
    return (None,value) if isinstance(value,str) and value in PROGRESS_MESSAGES else (value,None)
