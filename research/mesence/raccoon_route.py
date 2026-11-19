"""Rebuild the documented 2590-poll *controller-only* replay byte sequence.

This reads the recorded RLE input recipe from the committed research report.
It does not contain or write ROM, graphics, savestate or audio data.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import re

EXPECTED_POLLS = 2590
EXPECTED_SHA256 = "f780c7ba7e5002f9a62161486ad29e978106588571f6bf8eb268bd909681d082"
REPORT = Path(__file__).resolve().parents[2] / "docs/research/SMB3_NATIVE_RACCOON_PIPE.md"


def recorded_controller_bytes(report_text: str) -> bytes:
    found = re.search(r"## Replay inputs\b[\s\S]*?\x60{3}text\s*(.*?)\s*\x60{3}", report_text, re.S)
    if not found:
        raise ValueError("No controller RLE sequence in the native replay report")
    tokens = found.group(1).split()
    values = bytearray()
    for token in tokens:
        item = re.fullmatch(r"([1-9][0-9]*)\*([0-9A-Fa-f]{2})", token)
        if item is None:
            raise ValueError(f"Invalid controller input token {token!r}")
        count, mask = int(item.group(1)), int(item.group(2), 16)
        if len(values) + count > EXPECTED_POLLS:
            raise ValueError("Controller input exceeds the documented replay limit")
        values.extend([mask] * count)
    data = bytes(values)
    if len(data) != EXPECTED_POLLS or sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Controller replay length or SHA-256 differs from accepted native evidence")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Private controller file under the SpriteMine FIXTURE tree")
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        if any((parent / ".git").exists() for parent in (output.parent, *output.parents)):
            raise ValueError("Refusing to save controller evidence inside a Git checkout")
        if not output.parent.is_dir():
            raise ValueError(f"Output directory must already exist: {output.parent}")
        data = recorded_controller_bytes(REPORT.read_text(encoding="utf-8"))
        if output.exists() and output.read_bytes() != data:
            raise ValueError("Refusing to overwrite a different existing controller file")
        output.write_bytes(data)
        print(f"Recorded {len(data)} polls to {output} (SHA-256 {sha256(data).hexdigest()})")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot generate controller replay: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
