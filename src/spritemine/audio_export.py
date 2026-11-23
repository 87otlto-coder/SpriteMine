"""M2 headless capture-to-WAV editor, preserving source provenance.

This module never accesses a ROM or fabricates game sounds. It processes a
captured soundtrack; isolating APU channels requires different source evidence.
"""

from __future__ import annotations

import argparse
from array import array
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

RECIPE_VERSION = 1
OUTPUT_VERSION = "m2-audio-export-1"
NAME_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z")


@dataclass(frozen=True)
class PCM:
    rate: int
    channels: int
    samples: array

    @property
    def frames(self) -> int:
        return len(self.samples) // self.channels


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def read_pcm_wav(path: Path) -> PCM:
    with wave.open(str(path), "rb") as w:
        if w.getcomptype() != "NONE" or w.getsampwidth() != 2:
            raise ValueError("Only uncompressed signed 16-bit PCM WAV is supported; convert the capture to PCM16 first")
        if w.getnchannels() not in (1, 2):
            raise ValueError("Expected mono or stereo audio")
        channels, rate, count = w.getnchannels(), w.getframerate(), w.getnframes()
        if not (8000 <= rate <= 192000):
            raise ValueError("Unsupported sample rate")
        raw = w.readframes(count)
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) != count * channels:
        raise ValueError("Corrupt or truncated WAV audio")
    return PCM(rate, channels, samples)


def _decode_to_pcm(source: Path, decoded: Path) -> dict:
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
           "-y", "-i", str(source), "-map", "0:a:0", "-vn",
           "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(decoded)]
    try:
        run = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as ex:
        raise RuntimeError("ffmpeg is required to decode media other than PCM16 WAV") from ex
    if run.returncode != 0:
        raise ValueError("Audio decode failed: " + (run.stderr or "unknown ffmpeg error")[-1500:])
    version = subprocess.run(["ffmpeg", "-version"], check=False,
                             capture_output=True, text=True)
    first_line = (version.stdout or "").splitlines()
    return {"method": "ffmpeg-decode-pcm16", "sample_rate": 48000, "channels": 2,
            "decoder_version": first_line[0] if first_line else "unknown",
            "warning": "Compressed original audio remains lossy after decoding"}


def _frame(value: object, sample_rate: int, label: str) -> int:
    try:
        d = Decimal(str(value))
    except Exception as ex:
        raise ValueError(f"Invalid {label}") from ex
    if not d.is_finite() or d < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return int((d * sample_rate).to_integral_value(rounding=ROUND_HALF_UP))


def _quantize(sample: float) -> int:
    return max(-32768, min(32767, round(sample)))


def _pcm_select(pcm: PCM, start: int, end: int) -> array:
    if start < 0 or end <= start or end > pcm.frames:
        raise ValueError("Trim interval is empty or outside source duration")
    return array("h", pcm.samples[start * pcm.channels:end * pcm.channels])


def _seam_crossfade(samples: array, channels: int, length: int) -> array:
    """Wrap overlap: result tail and head follow adjacent original samples.

    Put last L frames over first L, and remove the repeated tail L. At the
    boundary output[-1] and output[0] are originally adjacent sample frames.
    This guarantees no *new* splice discontinuity, but not a musical phrase match.
    """
    frames = len(samples) // channels
    if not 2 <= length <= frames // 4:
        raise ValueError("Loop crossfade needs >=2 samples and <= one quarter of clip")
    result = array("h", samples[:(frames - length) * channels])
    for i in range(length):
        weight = i / (length - 1)
        a = i * channels
        b = (frames - length + i) * channels
        for c in range(channels):
            result[a + c] = _quantize(weight * samples[a + c] + (1 - weight) * samples[b + c])
    return result


def _fade(samples: array, channels: int, head: int, tail: int) -> array:
    frames = len(samples) // channels
    if head < 0 or tail < 0 or head + tail > frames:
        raise ValueError("Fades must be nonnegative and fit inside clip")
    for i in range(head):
        scale = i / max(1, head - 1)
        for c in range(channels):
            idx = i * channels + c
            samples[idx] = _quantize(samples[idx] * scale)
    for i in range(tail):
        scale = 1.0 - i / max(1, tail - 1)
        for c in range(channels):
            idx = (frames - tail + i) * channels + c
            samples[idx] = _quantize(samples[idx] * scale)
    return samples


def write_wav(dest: Path, pcm: PCM) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = array("h", pcm.samples)
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(pcm.channels)
        w.setsampwidth(2)
        w.setframerate(pcm.rate)
        w.writeframes(data.tobytes())


def _report_samples(data: array, channels: int) -> dict:
    size = len(data)
    if not size:
        raise ValueError("Empty output")
    peak = max(abs(i) for i in data)
    rms = math.sqrt(sum(i * i for i in data) / size)
    return {"peak_dbfs": round(20 * math.log10(max(1, peak) / 32768), 2),
            "rms_dbfs": round(20 * math.log10(max(1, rms) / 32768), 2),
            "last_to_first_jump_max": max(abs(data[c] - data[-channels + c]) for c in range(channels))}


def export(source: Path, recipe_path: Path, output_dir: Path) -> dict:
    source, recipe_path = Path(source), Path(recipe_path)
    if not source.is_file() or not recipe_path.is_file():
        raise FileNotFoundError("Source capture and recipe JSON must exist")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe.get("version") != RECIPE_VERSION:
        raise ValueError("Unsupported audio recipe version")
    items = recipe.get("exports")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("Expected between 1 and 100 exports")
    names = [x.get("name", "") for x in items if isinstance(x, dict)]
    if len(names) != len(items) or len(set(names)) != len(items) or any(not NAME_PATTERN.fullmatch(n) for n in names):
        raise ValueError("Each export needs a distinct safe name")
    capture_kind = recipe.get("source_kind", "captured")
    if capture_kind not in ("captured", "decoded"):
        raise ValueError("Source provenance must be captured or decoded")
    output_dir = Path(output_dir)
    if source.resolve() == output_dir.resolve() or recipe_path.resolve() == output_dir.resolve():
        raise ValueError("Output folder must not overwrite the source or recipe")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source)
    with TemporaryDirectory(prefix="spritemine-audio-") as temp:
        if source.suffix.lower() == ".wav":
            pcm = read_pcm_wav(source)
            decoder = {"method": "pcm16-wav-direct", "warning": None}
        else:
            converted = Path(temp) / "audio.wav"
            decoder = _decode_to_pcm(source, converted)
            pcm = read_pcm_wav(converted)
        outputs = []
        for clip in items:
            name, kind = clip["name"], clip.get("kind")
            if kind not in ("music", "sfx", "other"):
                raise ValueError(f"Unsupported clip kind for {name}")
            start = _frame(clip.get("start_s"), pcm.rate, "start_s")
            end = _frame(clip.get("end_s"), pcm.rate, "end_s")
            data = _pcm_select(pcm, start, end)
            looping = bool(clip.get("loop", False))
            overlap = _frame(Decimal(str(clip.get("crossfade_ms", 0))) / 1000, pcm.rate, "crossfade_ms")
            if looping:
                if overlap:
                    data = _seam_crossfade(data, pcm.channels, overlap)
            else:
                if overlap:
                    raise ValueError("Crossfade is only for looped audio")
                fadein = _frame(Decimal(str(clip.get("fade_in_ms", 0))) / 1000, pcm.rate, "fade_in_ms")
                fadeout = _frame(Decimal(str(clip.get("fade_out_ms", 0))) / 1000, pcm.rate, "fade_out_ms")
                if fadein or fadeout:
                    data = _fade(data, pcm.channels, fadein, fadeout)
            dest = output_dir / f"{name}.wav"
            write_wav(dest, PCM(pcm.rate, pcm.channels, data))
            audio = read_pcm_wav(dest)
            if audio.samples != data:
                raise AssertionError(f"PCM round-trip failed: {name}")
            outputs.append({"name": name, "kind": kind, "classification": "composed/edited", "file": dest.name, "sha256": digest(dest),
                            "source_start_s": start / pcm.rate, "source_end_s": end / pcm.rate,
                            "loop": looping, "crossfade_samples": overlap,
                            "duration_s": audio.frames / audio.rate, "frames": audio.frames,
                            "note": clip.get("note", ""), "stats": _report_samples(data, pcm.channels)})
        manifest = {"schema": OUTPUT_VERSION, "source": {"filename": source.name,
                    "sha256": source_hash, "kind": capture_kind,
                    "context": recipe.get("source_context", ""),
                    "disclaimer": recipe.get("source_disclaimer", "")},
                    "decode": decoder, "audio": {"sample_rate": pcm.rate,
                    "channels": pcm.channels, "source_duration_s": pcm.frames / pcm.rate,
                    "sample_format": "signed PCM16"},
                    "recipe_sha256": digest(recipe_path), "exports": outputs}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SpriteMine M2: trim/loop captured audio and export provenanced PCM16 WAV")
    parser.add_argument("source", type=Path, help="PCM16 WAV capture, or MP4/other media with ffmpeg installed")
    parser.add_argument("recipe", type=Path, help="JSON clip selection and edit recipe")
    parser.add_argument("output", type=Path, help="Private output directory")
    args = parser.parse_args(argv)
    try:
        result = export(args.source, args.recipe, args.output)
    except (ValueError, FileNotFoundError, RuntimeError, wave.Error) as exc:
        parser.exit(2, f"SpriteMine audio export error: {exc}\n")
    print(json.dumps({"source_sha256": result["source"]["sha256"],
                      "exports": [{"file": x["file"], "sha256": x["sha256"], "duration_s": x["duration_s"]}
                                  for x in result["exports"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
