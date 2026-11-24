from array import array
import os
from pathlib import Path
import struct
import wave

import pytest
from spritemine import smb3_audio as a


@pytest.fixture
def prg():
    return b''.join(bytes([i]) * 8192 for i in range(32))


def test_nsf_mapping_and_queue(prg):
    n = a._make_adapter(prg, 'overworld')
    assert n[:8] == b'NESM\x1a\x01\x01\x01'
    assert struct.unpack_from('<HHH', n, 8) == (0x8000, 0x8000, 0x8010)
    assert struct.unpack_from('<H', n, 110) == (16639,)
    assert n[128+10:128+16] == bytes([0xA9, 0x10, 0x8D, 0xF5, 4, 0x60])
    assert n[128+16:128+20] == bytes([0x20, 0, 0xA0, 0x60])
    assert len(n) == 128 + 32768
    for i, bank in enumerate(a.BANKS, 1):
        assert n[128+i*8192:128+(i+1)*8192] == bytes([bank])*8192


@pytest.mark.parametrize('name,value,queue', [('underground', 0x20, 0xF5), ('coin', 1, 0xF2)])
def test_other_queues(prg, name, value, queue):
    n = a._make_adapter(prg, name)
    assert n[138:143] == bytes([0xA9, value, 0x8D, queue, 4])


def test_diagnostic_never_changes_prg_banks(prg):
    n = a._make_adapter(prg, 'overworld')
    d = a._make_adapter(prg, 'overworld', True)
    assert d[:144] == n[:144]
    assert d[128+8192:] == n[128+8192:]
    assert d != n


def test_bad_rom_rejected(tmp_path):
    p = tmp_path/'fake.nes'; p.write_bytes(b'\0'*393232)
    with pytest.raises(ValueError, match='verified'): a.read_rom(p)
    with pytest.raises(ValueError, match='fingerprint'): a.build_nsf(p.read_bytes(),'coin')


def test_unsupported_track(prg):
    with pytest.raises(ValueError): a._make_adapter(prg, 'unknown')
    with pytest.raises(ValueError): a._make_adapter(prg, 'coin', True)


def test_marker_groups():
    p = array('h', [0])*2*12000
    for start in (960, 4800, 8640):
        for i in range(start, start+768): p[2*i] = 5000
    assert a.marker_positions(p) == [960,4800,8640]
    assert a.select_loop([960,4800,8640])['start_sample'] == 4416


def test_real_marker_scale():
    x = a.select_loop([154176,1381248,2608224,3835296])
    assert x['inferred_game_ticks'] == 1536
    assert x['duration_samples'] == 1226976
    y = a.select_loop([768,921120,1841376,2761632,3681888])
    assert y['inferred_game_ticks'] == 1152
    assert y['seconds'] == 19.172


@pytest.mark.parametrize('markers', [[1,2], [1000,2000,9000], [300,200,100]])
def test_bad_marker_sequences(markers):
    with pytest.raises(ValueError): a.select_loop(markers)


def test_wav_roundtrip(tmp_path):
    p = array('h', [-32768,32767,0,-2,5,7]); f = tmp_path/'test.wav'
    x = a.write_wav(f,p)
    assert x['full_scale_samples'] == 2
    assert x['samples_per_channel'] == 3
    with wave.open(str(f)) as w:
        assert w.getparams()[:4] == (2,2,48000,3)
        assert w.readframes(3) == struct.pack('<6h', *p)
    assert x['sha256'] == a.sha(f.read_bytes())


@pytest.mark.skipif(not (os.getenv('SPRITEMINE_PRIVATE_ROM_ZIP') and os.getenv('SPRITEMINE_GME_LIBRARY')), reason='Private ROM and GME library not provided')
def test_private_rebuild(tmp_path):
    rom = Path(os.environ['SPRITEMINE_PRIVATE_ROM_ZIP']); lib = os.environ['SPRITEMINE_GME_LIBRARY']
    one, two = tmp_path/'one', tmp_path/'two'
    m1 = a.export(rom,one,lib); m2 = a.export(rom,two,lib)
    assert m1 == m2
    assert {x.name:a.sha(x.read_bytes()) for x in one.iterdir()} == {x.name:a.sha(x.read_bytes()) for x in two.iterdir()}
    for track in ('overworld','underground','coin'):
        for e in m1['tracks'][track]['exports']:
            with wave.open(str(one/e['file'])) as w:
                assert w.getnframes() == e['samples_per_channel']
                assert any(w.readframes(w.getnframes()))
