"""Synthetic-only checks for SpriteMine's private-capture audio workbench."""

from array import array
import json
import math
from pathlib import Path
import wave

import pytest

from spritemine.audio_export import (
    PCM, _frame, _seam_crossfade, digest, export, read_pcm_wav, write_wav,
)


def _tone(path: Path, rate: int = 8000, duration_frames: int = 8000, channels: int = 2) -> PCM:
    wave_data = array("h")
    for frame in range(duration_frames):
        signal = round(9000 * math.sin(2 * math.pi * 330 * frame / rate))
        for ch in range(channels):
            wave_data.append(signal if ch == 0 else -signal // 2)
    result = PCM(rate, channels, wave_data)
    write_wav(path, result)
    return result


def _recipe(path: Path, **edits):
    items = [
        {"name": "music_clip", "kind": "music", "start_s": "0.1", "end_s": "0.8", "loop": True, "crossfade_ms": 20},
        {"name": "effect_clip", "kind": "sfx", "start_s": "0.55", "end_s": "0.95", "fade_in_ms": 3, "fade_out_ms": 7},
    ]
    info = {"version": 1, "source_kind": "captured", "source_context": "synthetic fixture", "exports": items}
    info.update(edits)
    path.write_text(json.dumps(info), encoding="utf-8")
    return path


def test_pcm16_roundtrip(tmp_path):
    source = _tone(tmp_path / "source.wav", rate=8000, channels=2)
    actual = read_pcm_wav(tmp_path / "source.wav")
    assert source == actual
    assert actual.frames == 8000
    assert actual.channels == 2


def test_two_exports_exact_durations_and_determinism(tmp_path):
    source = tmp_path / "source.wav"
    _tone(source)
    recipe = _recipe(tmp_path / "recipe.json")
    result_a = export(source, recipe, tmp_path / "out_a")
    result_b = export(source, recipe, tmp_path / "out_b")
    assert result_a == result_b
    assert len(result_a["exports"]) == 2
    assert result_a["source"]["sha256"] == digest(source)
    assert result_a["audio"]["sample_rate"] == 8000
    assert result_a["exports"][0]["frames"] == round(0.7 * 8000) - round(0.02 * 8000)
    assert result_a["exports"][1]["frames"] == round(0.4 * 8000)
    for clip in result_a["exports"]:
        p = tmp_path / "out_a" / clip["file"]
        assert p.read_bytes() == (tmp_path / "out_b" / clip["file"]).read_bytes()
        assert clip["sha256"] == digest(p)
    assert (tmp_path / "out_a" / "manifest.json").read_bytes() == (
        tmp_path / "out_b" / "manifest.json").read_bytes()


def test_loop_wrap_preserves_source_contiguous_boundary():
    samples = array("h", list(range(100)))
    actual = _seam_crossfade(samples, channels=1, length=10)
    assert len(actual) == 90
    assert actual[0] == samples[90]
    assert actual[-1] == samples[89]
    assert actual[9] == samples[9]
    assert abs(actual[0] - actual[-1]) == 1


def test_effect_fades_to_zero_and_keeps_stereo(tmp_path):
    source = tmp_path / "source.wav"
    _tone(source)
    recipe = _recipe(tmp_path / "recipe.json")
    export(source, recipe, tmp_path / "out")
    result = read_pcm_wav(tmp_path / "out" / "effect_clip.wav")
    assert result.channels == 2
    assert list(result.samples[:2]) == [0, 0]
    assert list(result.samples[-2:]) == [0, 0]
    assert any(value != 0 for value in result.samples)


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(version=999),
    lambda c: c.update(source_kind="raw-probably-game-data"),
    lambda c: c.update(exports=[]),
    lambda c: c["exports"][0].update(name="../path-escape"),
    lambda c: c["exports"][0].update(name="effect_clip"),
    lambda c: c["exports"][0].update(start_s="1", end_s="2"),
    lambda c: c["exports"][0].update(crossfade_ms="1000"),
    lambda c: c["exports"][0].update(start_s="nan"),
    lambda c: c["exports"][1].update(crossfade_ms=10),
    lambda c: c["exports"][1].update(fade_out_ms=5000),
])
def test_rejects_invalid_recipes(tmp_path, mutate):
    src = tmp_path / "source.wav"
    _tone(src)
    path = _recipe(tmp_path / "recipe.json")
    c = json.loads(path.read_text(encoding="utf-8"))
    mutate(c)
    path.write_text(json.dumps(c), encoding="utf-8")
    with pytest.raises(ValueError):
        export(src, path, tmp_path / "out")


def test_wav_must_be_pcm16(tmp_path):
    p = tmp_path / "8bit.wav"
    with wave.open(str(p), "wb") as w:
        w.setframerate(8000)
        w.setsampwidth(1)
        w.setnchannels(1)
        w.writeframes(b"\x80" * 800)
    with pytest.raises(ValueError, match="16-bit"):
        read_pcm_wav(p)


def test_frame_half_up_and_bounded(tmp_path):
    assert _frame("0.0005", 1000, "start_s") == 1
    assert _frame("0.00049", 1000, "start_s") == 0
    with pytest.raises(ValueError):
        _frame("-1", 48000, "start_s")
    with pytest.raises(ValueError):
        _frame("NaN", 48000, "start_s")
