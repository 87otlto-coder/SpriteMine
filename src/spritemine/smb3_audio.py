"""Isolated SMB3 PRG1 music/SFX playback via an in-memory NSF adapter.

No game data is embedded here. Supply your own verified ROM and a separately
installed Game Music Emu shared library. This is not a native sequence decoder.
"""
from __future__ import annotations

import argparse
from array import array
import ctypes as ct
import ctypes.util
import hashlib
import json
from pathlib import Path
import statistics
import struct
import sys
import wave
import zipfile

ROM_SHA256 = '4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579'
RATE = 48000
PERIOD_US = 16639
BANKS = (28, 29, 31)
TRACKS = {'overworld': (0x04F5, 0x10), 'underground': (0x04F5, 0x20),
          'coin': (0x04F2, 0x01)}
SOURCE_REF = 'https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_rom(path: Path) -> bytes:
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as z:
            members = [x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith('.nes')]
            if len(members) != 1 or members[0].file_size != 393232:
                raise ValueError('Expected exactly one 393232-byte SMB3 PRG1 NES member')
            raw = z.read(members[0])
    else:
        raw = path.read_bytes()
    if len(raw) != 393232 or sha(raw) != ROM_SHA256:
        raise ValueError('Only the verified SMB3 USA PRG1 ROM is supported')
    return raw


def build_nsf(raw: bytes, track: str, *, diagnostic: bool = False) -> bytes:
    """Private in-memory adapter. ROM banks are copied verbatim; never saved to disk."""
    if sha(raw) != ROM_SHA256:
        raise ValueError('ROM fingerprint mismatch')
    return _make_adapter(raw[16:16 + 262144], track, diagnostic)


def _make_adapter(prg: bytes, track: str, diagnostic: bool = False) -> bytes:
    if len(prg) != 262144 or track not in TRACKS or (diagnostic and track == 'coin'):
        raise ValueError('Invalid PRG size or track')
    queue, value = TRACKS[track]
    # Init: reset channel enables, enable four channels, enqueue exactly one event.
    init = bytes([0xA9, 0, 0x8D, 0x15, 0x40, 0xA9, 0x0F, 0x8D, 0x15, 0x40,
                  0xA9, value, 0x8D, queue & 255, queue >> 8, 0x60])
    play = _diagnostic_play() if diagnostic else bytes([0x20, 0, 0xA0, 0x60])
    header = bytearray(128)
    header[:8] = b'NESM\x1a\x01\x01\x01'
    struct.pack_into('<HHH', header, 8, 0x8000, 0x8000, 0x8000 + len(init))
    struct.pack_into('<H', header, 110, PERIOD_US)
    struct.pack_into('<H', header, 120, 19997)
    return bytes(header) + (init + play).ljust(8192, b'\0') + b''.join(
        prg[b * 8192:(b + 1) * 8192] for b in BANKS)


def _diagnostic_play() -> bytes:
    """Signal entry to the ROM's loop segment using P1 in a *separate* NSF run.

    Compare index ($04DF) and square-2 offset ($04FE) before/after the native
    engine call. Loop index lives at $7AE2, and active index is one ahead.
    A same-index offset reset detects single-segment songs. Scratch $0600-$0601
    are unused by this isolated sound routine in the tested tracks.
    No diagnostic signal is emitted in the exported music.
    """
    code = bytearray(); labels = {}; fixes = []
    def emit(*v: int): code.extend(v)
    def label(name: str): labels[name] = len(code)
    def branch(op: int, name: str):
        emit(op, 0); fixes.append((len(code) - 1, name))
    emit(0xAD, 0xDF, 4, 0x8D, 0, 6, 0xAD, 0xFE, 4, 0x8D, 1, 6)
    emit(0x20, 0, 0xA0)
    emit(0xAD, 0xE2, 0x7A, 0x18, 0x69, 1, 0xCD, 0xDF, 4); branch(0xD0, 'off')
    emit(0xAD, 0xDF, 4, 0xCD, 0, 6); branch(0xD0, 'on')
    emit(0xAD, 0xFE, 4, 0xCD, 1, 6); branch(0x90, 'on')
    label('off'); emit(0xA9, 0x30); branch(0xD0, 'tone')
    label('on'); emit(0xA9, 0xBF)
    label('tone'); emit(0x8D, 0, 0x40, 0xA9, 0x80, 0x8D, 2, 0x40,
                         0xA9, 8, 0x8D, 3, 0x40, 0xA9, 0, 0x8D, 1, 0x40, 0x60)
    for i, name in fixes:
        offset = labels[name] - i - 1
        if not -128 <= offset <= 127: raise ValueError('Branch out of range')
        code[i] = offset & 255
    return bytes(code)


class GME:
    def __init__(self, library: str | None = None):
        self.path = library or ctypes.util.find_library('gme')
        if not self.path:
            raise RuntimeError('Supply --gme with a path to the Game Music Emu shared library')
        self.lib = ct.CDLL(self.path)
        g = self.lib
        g.gme_open_data.argtypes = [ct.c_void_p, ct.c_long, ct.POINTER(ct.c_void_p), ct.c_int]
        g.gme_open_data.restype = ct.c_char_p
        for name, args in [('gme_start_track', [ct.c_void_p, ct.c_int]),
                           ('gme_play', [ct.c_void_p, ct.c_int, ct.c_void_p])]:
            f = getattr(g, name); f.argtypes = args; f.restype = ct.c_char_p
        for name, args in [('gme_ignore_silence', [ct.c_void_p, ct.c_int]),
                           ('gme_mute_voices', [ct.c_void_p, ct.c_int]),
                           ('gme_delete', [ct.c_void_p])]:
            f = getattr(g, name); f.argtypes = args; f.restype = None

    @staticmethod
    def _check(err):
        if err: raise RuntimeError(err.decode('utf-8', 'replace'))

    def render(self, nsf: bytes, seconds: int, *, mute_mask: int = 0) -> array:
        if not 1 <= seconds <= 120: raise ValueError('Render duration must be 1–120 seconds')
        data = ct.create_string_buffer(nsf); emu = ct.c_void_p()
        self._check(self.lib.gme_open_data(data, len(nsf), ct.byref(emu), RATE))
        try:
            self.lib.gme_ignore_silence(emu, 1)
            self._check(self.lib.gme_start_track(emu, 0))
            if mute_mask: self.lib.gme_mute_voices(emu, mute_mask)
            samples = array('h', [0]) * (seconds * RATE * 2)
            self._check(self.lib.gme_play(emu, len(samples), samples.buffer_info()[0]))
            return samples
        finally:
            self.lib.gme_delete(emu)


def marker_positions(pcm: array, *, block: int = 96, threshold: int = 2400) -> list[int]:
    """Detect diagnostic pulse groups; positions are quantized to 2 ms at 48 kHz."""
    if len(pcm) % 2: raise ValueError('Expected interleaved stereo PCM')
    hot = []
    for i in range(0, len(pcm) // 2 - block + 1, block):
        power = sum(s * s for s in pcm[i * 2:(i + block) * 2:2])
        if power > block * threshold * threshold: hot.append(i // block)
    groups: list[list[int]] = []
    for i in hot:
        if not groups or i - groups[-1][-1] > 12: groups.append([])
        groups[-1].append(i)
    return [g[0] * block for g in groups if len(g) >= 3]


def select_loop(markers: list[int]) -> dict:
    """Require three recurring native-state events; no waveform-period guessing."""
    if len(markers) < 3: raise ValueError('Too few diagnostic loop-entry markers')
    periods = [b - a for a, b in zip(markers, markers[1:])]
    period = round(statistics.median(periods))
    if period <= 0 or any(abs(x - period) > 192 for x in periods):
        raise ValueError('Diagnostic markers do not form a stable recurring period')
    # Cut 8 ms before each marker (same musical phase, ahead of the NSF call).
    # Select a repeat after the intro; the marker detector is only 2 ms precise.
    start, end = markers[1] - 384, markers[2] - 384
    return {'markers_samples': markers, 'start_sample': start, 'end_sample': end,
            'duration_samples': end - start, 'seconds': (end - start) / RATE,
            'inferred_game_ticks': round(period / (RATE * PERIOD_US / 1_000_000)),
            'method': 'native loop-segment state marker, 2 ms resolution, 8 ms pre-roll; not exact APU state equality'}


def write_wav(path: Path, pcm: array) -> dict:
    if len(pcm) % 2: raise ValueError('Expected stereo PCM')
    clip = sum(x in (-32768, 32767) for x in pcm)
    if sys.byteorder != 'little': pcm = array('h', pcm); pcm.byteswap()
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(RATE); f.writeframes(pcm.tobytes())
    return {'file': path.name, 'samples_per_channel': len(pcm) // 2, 'seconds': len(pcm) / (2 * RATE),
            'sha256': sha(path.read_bytes()), 'full_scale_samples': clip}


def export(rom_path: Path, output: Path, library: str | None = None) -> dict:
    raw = read_rom(rom_path); gme = GME(library)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'schema': 1, 'kind': 'decoded/emulated audio', 'rom_sha256': sha(raw),
                'source': SOURCE_REF, 'nsf_banks_8k': list(BANKS), 'play_period_us': PERIOD_US,
                'sample_rate': RATE, 'gme_library': gme.path, 'tracks': {}}
    for name in ('overworld', 'underground'):
        normal = build_nsf(raw, name)
        diagnostic = build_nsf(raw, name, diagnostic=True)
        markers = marker_positions(gme.render(diagnostic, 90, mute_mask=0x1E))
        loop = select_loop(markers)
        # Require validated source-loop tick counts for these two tracks.
        if loop['inferred_game_ticks'] != {'overworld': 1536, 'underground': 1152}[name]:
            raise ValueError(f'Unexpected loop period for {name}: {loop}')
        music = gme.render(normal, 65)
        a, b = loop['start_sample'], loop['end_sample']
        if not 0 < a < b <= len(music) // 2: raise ValueError('Loop outside rendered audio')
        clip = music[a * 2:b * 2]
        files = [write_wav(output / f'{name}_loop.wav', clip)]
        if name == 'overworld':
            # Intro + first full loop up to next entry marker. Preserve start of original playback.
            files.append(write_wav(output / 'overworld_intro_and_first_loop.wav', music[:a * 2]))
        manifest['tracks'][name] = {'queue': list(TRACKS[name]), 'nsf_sha256': sha(normal),
                                     'diagnostic_nsf_sha256': sha(diagnostic), 'loop': loop, 'exports': files}
    n = build_nsf(raw, 'coin'); coin = gme.render(n, 2)
    # Keep the complete original effect plus a short tail; source-only queue, no music.
    start, end = 0, RATE
    manifest['tracks']['coin'] = {'queue': list(TRACKS['coin']), 'nsf_sha256': sha(n),
        'trim_samples': [start, end], 'exports': [write_wav(output / 'coin_isolated.wav', coin[:2 * end])]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('rom', type=Path)
    p.add_argument('output', type=Path); p.add_argument('--gme', help='Path to separately installed GME DLL/shared library')
    a = p.parse_args(); print(json.dumps(export(a.rom, a.output, a.gme), indent=2))

if __name__ == '__main__': main()
