"""Original, deterministic instrumental songs for the low-cost study music bus.

Compose sparse note events once per song; mix cached original instruments only
where their tails overlap a requested block. No commercial samples or models.
"""
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from .lofi_music import keyboard, kit

RATE = 24000
BPM = 74
BEAT = 60 / BPM
PHRASE_FRAMES = round(64 * BEAT * 48000)
SONG_FRAMES = PHRASE_FRAMES * 4
SONG_SAMPLES = SONG_FRAMES // 2
MAX_TAIL = 8
SECTIONS = ('Opening', 'First theme', 'Answer', 'Bridge', 'Theme returns',
            'Second theme', 'Soft interlude', 'Closing')
SCALE = (0, 2, 4, 5, 7, 9, 11)
# Diatonic ninth chords, with distinct harmonic journeys and a contrasting bridge.
PROGRESSIONS = ((5, 3, 0, 4), (1, 4, 0, 5), (0, 5, 1, 4),
                (3, 2, 5, 1), (5, 1, 3, 4), (3, 0, 1, 4))
KEYS = (0, 5, 2, 7, 3, 8, 10)
KEY_NAMES = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B')
PLACES = ('Harbour', 'Window', 'Notebook', 'Rain', 'Lamplight', 'Boardwalk',
          'Side Street', 'Quiet Room', 'Bookshop', 'Late Bus', 'Coast', 'Rooftop')
TIMES = ('After Hours', 'in Soft Focus', 'at Dusk', 'Reflections', 'Daydream',
         'Postcards', 'in October', 'Drifting', 'Memories', 'at Midnight',
         'Sketches', 'on Sunday')


@dataclass(frozen=True)
class Note:
    start: int
    kind: str
    pitch: int
    gain: float
    pan: float
    duration: float


@dataclass(frozen=True)
class Song:
    title: str
    key: int
    progression: tuple
    events: tuple
    starts: tuple
    kit_id: int


def scale_note(degree, key):
    return 60 + key + SCALE[degree % 7] + 12 * (degree // 7)


@lru_cache(maxsize=4)
def compose(seed, number, warm=False):
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), int(number), 301]))
    # Adjacent songs must change tonal centre and harmonic sequence, even when
    # a random draw would otherwise repeat the previous one.
    key = KEYS[(seed + number * 3) % len(KEYS)]
    progression = PROGRESSIONS[(seed // 7 + number) % len(PROGRESSIONS)]
    bridge = PROGRESSIONS[(seed // 7 + number + 3) % len(PROGRESSIONS)]
    title_index = (seed + number * 37) % (len(PLACES) * len(TIMES))
    title = f'{PLACES[title_index % len(PLACES)]} {TIMES[title_index // len(PLACES)]}'
    swing = float(rng.uniform(.57, .62))
    kit_id = int(rng.integers(0, 64))
    lead = (('reed', 'velvet', 'softlead') if warm else ('felt', 'round', 'keys'))[int(rng.integers(0, 3))]
    motif = [int(rng.integers(0, 4))]
    for _ in range(15):
        motif.append(int(np.clip(motif[-1] + rng.choice((-2, -1, 1, 2)), -1, 8)))
    rhythm = ((.18, 1 + swing, 2.20, 3 + swing),
              (.18, swing, 2.20, 3.15),
              (.18, 1.18, 2 + swing, 3.15))[int(rng.integers(0, 3))]
    events = []

    def add(beat, kind, pitch, gain, pan=0, duration=2.5):
        if warm:
            kind={'keys':'velvet','bass':'fingerbass','bed':'warmbed'}.get(kind,kind)
        events.append(Note(round(beat * BEAT * RATE), kind, int(pitch),
                           float(gain), float(pan), float(duration)))

    def degree_at(bar):
        p = bridge if bar // 8 in (3, 5) else progression
        return p[(bar // 2) % 4]

    previous = None
    for bar in range(64):
        section = bar // 8
        degree = degree_at(bar)
        # Fold each chord into a comfortable register, choose the inversion
        # with the smallest distance from the preceding voicing.
        tones = [scale_note(degree + d, key) for d in (0, 2, 4, 6, 8)]
        voicings = []
        for inversion in range(5):
            v = sorted(tones[inversion:] + [n + 12 for n in tones[:inversion]])
            while np.mean(v) > (66 if warm else 71): v = [n - 12 for n in v]
            voicings.append(v)
        chord = min(voicings, key=lambda v: sum(abs(a-b) for a, b in zip(v, previous or [60, 64, 67, 71, 74])))
        previous = chord
        soft = section in (0, 6, 7)
        chord_gain = .034 if soft else .041
        for hit in (.08, 2 + swing if bar % 2 else 2.12):
            for j, note in enumerate(chord):
                add(bar * 4 + hit + j * .009, 'keys', note,
                    chord_gain * rng.uniform(.82, 1.03), (j - 2) * .13, 3)
        # Long quiet chord tails retain warmth under melodic rests.
        if bar % 2 == 0:
            for j in (0, 2, 3):
                add(bar * 4, 'bed', chord[j], .011, (j - 1) * .17, MAX_TAIL)

        root = scale_note(degree, key) - 24
        while root > 45: root -= 12
        bass_hits = ((.03, 0, 1.2), (1 + swing, 7, .65), (2.08, 0, .9), (3 + swing, 12, .35))
        if (bar + number) % 3 == 0:
            bass_hits = ((.03, 0, 1.6), (2 + swing, 7, .7), (3.20, 0, .55))
        for pos, interval, length in bass_hits:
            if soft and interval == 12: continue
            add(bar * 4 + pos, 'bass', root + interval, .13 if not soft else .105, 0, length * BEAT)

        # Related four-bar phrases, with an answering contour and occasional
        # rests. The bridge and second theme use a different register/contour.
        melodic_bar = (section not in (0, 6) and bar % 4 != 3) or (section == 0 and bar >= 4 and bar % 2 == 0)
        if melodic_bar:
            for j, pos in enumerate(rhythm):
                if (bar + j) % 5 == 0: continue
                step = motif[((bar % 4) * 4 + j) % len(motif)]
                if section in (2, 5): step = 7 - step
                if j == 0: step = degree + (0, 2, 4)[bar % 3]
                if section in (3, 5): step += 2 if warm else 7
                note = scale_note(step, key)
                while note < 60: note += 12
                while note > (76 if warm else 84): note -= 12
                gain = ((.036 if section in (1, 4) else .030) if warm else (.044 if section in (1, 4) else .038)) * rng.uniform(.8, 1.05)
                add(bar * 4 + pos + .025, lead, note, gain, -.12, 2.5)
                add(bar * 4 + pos + .775, lead, note, gain * .24, .30, 2.5)

        # Swung drums: stable backbeat, changing kicks, quiet ghost notes and
        # brief fills. No noisy vinyl loop or bright perpetual lead line.
        kick_positions = ((0, 1 + swing, 2.5), (0, 2, 3 + swing), (0, .75, 2 + swing))[(bar // 2 + number) % 3]
        for pos in kick_positions:
            add(bar * 4 + pos, 'drum', 0, .205 if not soft else .15, 0, 1)
        for pos in (1.035, 3.035):
            add(bar * 4 + pos, 'drum', 1, .115 if not soft else .075, .05, 1)
            if section in (2, 4, 5): add(bar * 4 + pos + .012, 'drum', 2, .021, -.08, 1)
        for eighth in range(8):
            if soft and eighth % 2: continue
            pos = eighth // 2 + (swing if eighth % 2 else 0)
            add(bar * 4 + pos + float(rng.uniform(0, .009)), 'drum', 3,
                (.019 if eighth % 2 else .027) * rng.uniform(.8, 1.08), -.18, 1)
        if bar % 4 == 2: add(bar * 4 + 3 + swing, 'drum', 4, .022, .18, 1)
        if bar % 8 == 7:
            for pos in (2 + swing, 3.78): add(bar * 4 + pos, 'drum', 5, .022, .22, 1)
    events.sort(key=lambda n: n.start)
    return Song(title, key, progression, tuple(events), tuple(n.start for n in events), kit_id)


@lru_cache(maxsize=192)
def instrument(kind, note, duration):
    if kind == 'keys': return keyboard(note, RATE)
    t = np.arange(round(duration * RATE), dtype=np.float64) / RATE
    f = 440 * 2 ** ((note - 69) / 12)
    end = np.clip((duration - t) / .12, 0, 1)
    if kind in ('velvet','reed','softlead','warmbed','fingerbass'):
        return warm_instrument(kind,note,duration)
    if kind == 'bass':
        sound = (np.sin(2*np.pi*f*t) + .15*np.sin(4*np.pi*f*t))
        env = (1-np.exp(-t*90)) * np.exp(-t*.8) * end
    elif kind == 'bed':
        sound = np.sin(2*np.pi*f*t + .025*np.sin(t*2)) + .12*np.sin(2*np.pi*f*.999*t)
        env = (1-np.exp(-t*4)) * np.exp(-t*.08) * np.clip((duration-t)/2, 0, 1)
    else:
        colour = .15 if kind == 'felt' else .5 if kind == 'round' else .3
        sound = np.sin(2*np.pi*f*t + colour*np.exp(-t*4)*np.sin(2*np.pi*f*2*t))
        sound += .08*np.sin(2*np.pi*f*.997*t)
        env = (1-np.exp(-t*85)) * np.exp(-t*(2.2 if kind == 'felt' else 1.5)) * end
    return (np.tanh(sound*1.1)*env).astype(np.float32)


def _render(start, count, seed, warm=False, composer=None, voice_factory=None):
    audio = np.zeros((count, 2), dtype=np.float32)
    # Include the previous song's decaying notes for a natural overlapping join.
    first = max(0, (start - MAX_TAIL*RATE) // SONG_SAMPLES)
    last = (start + count - 1) // SONG_SAMPLES
    for number in range(first, last + 1):
        song = (composer or compose)(seed, number, warm)
        origin = number * SONG_SAMPLES
        lo = bisect_left(song.starts, start-origin-MAX_TAIL*RATE)
        hi = bisect_left(song.starts, start+count-origin)
        for event in song.events[lo:hi]:
            sound = kit(song.kit_id, RATE)[event.pitch] if event.kind == 'drum' else (voice_factory or instrument)(event.kind, event.pitch, event.duration)
            onset = origin + event.start
            a = max(start, onset); b = min(start+count, onset+len(sound))
            if a >= b: continue
            voice = sound[a-onset:b-onset] * event.gain
            audio[a-start:b-start, 0] += voice * (1-event.pan)
            audio[a-start:b-start, 1] += voice * (1+event.pan)
    return (np.tanh(audio*1.2)*.68).astype(np.float32)


def samples(start, count, seed, warm=False):
    if count == 0: return np.empty((0, 2), dtype=np.float32)
    base = start // 2
    last = (start+count-1)//2 + 1
    low = _render(base, last-base+1, seed, warm)
    positions = np.arange(count) + start % 2
    i = positions // 2; blend = (positions % 2).astype(np.float32)*.5
    return low[i]*(1-blend[:, None]) + low[i+1]*blend[:, None]


def song_info(seed, phrase, warm=False):
    number = phrase // 4
    song = compose(seed, number, warm)
    return {'number': number+1, 'title': song.title, 'key': KEY_NAMES[song.key]+' major / relative minor',
            'duration_seconds': SONG_FRAMES/48000,
            'section': ' / '.join(SECTIONS[(phrase % 4)*2:(phrase % 4)*2+2]), 'phrase_in_song': phrase % 4+1,
            'next_title': compose(seed, number+1, warm).title}


@lru_cache(maxsize=128)
def warm_instrument(kind, note, duration):
    """Original rounded harmonics with a slow hammer/reed attack, no FM bell transient.

    Render once into a bounded one-shot cache. Delay taps are part of the voice,
    so independent WAV blocks retain precisely the same tails.
    """
    duration=min(MAX_TAIL,float(duration)+1.2)
    t=np.arange(round(duration*RATE),dtype=np.float64)/RATE
    f=440*2**((note-69)/12);phase=2*np.pi*f*t
    if kind=='fingerbass':
        sound=np.sin(phase)+.22*np.sin(2*phase)*np.exp(-t*2)+.06*np.sin(3*phase)*np.exp(-t*5)
        env=(1-np.exp(-t*48))*np.exp(-t*1.1)
    elif kind=='warmbed':
        sound=np.sin(phase)+.22*np.sin(2*phase+.3)+.10*np.sin(phase*.999)
        env=(1-np.exp(-t*2.2))*np.exp(-t*.23)
    else:
        # Harmonic (rather than inharmonic tine) colour, with less energy in
        # the upper register and gentler note onsets than the original keys.
        partials=(1,.35,.14,.05) if kind=='reed' else (1,.22,.09,.025)
        sound=sum(g*np.sin(phase*(i+1)+.05*i)*np.exp(-t*i*.7) for i,g in enumerate(partials))
        sound+=.12*np.sin(phase*.9985+.2)*np.exp(-t*.6)
        env=(1-np.exp(-t*(24 if kind=='softlead' else 38)))*np.exp(-t*(1.05 if kind=='velvet' else .8))
        env*=.94+.06*np.sin(2*np.pi*3.1*t)
    env*=np.clip((duration-t)/.25,0,1)
    dry=np.tanh(sound*.85)*env
    if kind not in ('fingerbass','warmbed'):
        wet=dry.copy()
        for seconds,gain in ((.079,.11),(.143,.065),(.281,.035)):
            offset=round(seconds*RATE);wet[offset:]+=dry[:-offset]*gain
        dry=wet
    return (dry*.88).astype(np.float32)

