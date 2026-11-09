"""Read-only iNES/ZIP loading and immutable ROM metadata.

Only legacy iNES is implemented. NES 2.0 and CHR-RAM extraction are intentionally
not silently interpreted as legacy CHR-ROM images.
"""

from __future__ import annotations

import hashlib
import zlib
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_ROM_BYTES = 64 * 1024 * 1024
INES_HEADER_BYTES = 16
TRAINER_BYTES = 512
PRG_BANK_BYTES = 16 * 1024
CHR_BANK_BYTES = 8 * 1024


class RomFormatError(ValueError):
    """An input file is invalid or unsupported by the current reader."""


@dataclass(frozen=True, slots=True)
class RomMetadata:
    format: str
    mapper: int
    prg_banks_16k: int
    chr_banks_8k: int
    prg_bytes: int
    chr_bytes: int
    trainer_present: bool
    battery_backed: bool
    mirroring: str
    header_bytes: int
    prg_rom_offset: int
    chr_rom_offset: int
    trailing_bytes: int
    rom_sha256: str
    prg_sha256: str
    chr_sha256: str
    prg_crc32: str
    chr_crc32: str
    prg_chr_crc32: str

    def to_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Rom:
    """Immutable in-memory copy; source files are never opened for writing."""

    image: bytes
    prg: bytes
    chr: bytes
    metadata: RomMetadata


def _crc32(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08X}"


def parse_nes(data: bytes) -> Rom:
    if len(data) > MAX_ROM_BYTES:
        raise RomFormatError(f"ROM exceeds {MAX_ROM_BYTES} byte safety limit")
    if len(data) < INES_HEADER_BYTES or data[:4] != b"NES\x1a":
        raise RomFormatError("Invalid or missing iNES header")
    flags6, flags7 = data[6], data[7]
    if flags7 & 0x0C == 0x08:
        raise RomFormatError("NES 2.0 headers are not yet supported")
    if flags7 & 0x0C:
        raise RomFormatError("Unsupported reserved iNES header variant")
    prg_banks, chr_banks = data[4], data[5]
    if not prg_banks:
        raise RomFormatError("iNES ROM must declare at least one PRG bank")
    trainer = bool(flags6 & 0x04)
    prg_offset = INES_HEADER_BYTES + (TRAINER_BYTES if trainer else 0)
    prg_size = prg_banks * PRG_BANK_BYTES
    chr_size = chr_banks * CHR_BANK_BYTES
    chr_offset = prg_offset + prg_size
    expected_size = chr_offset + chr_size
    if len(data) < expected_size:
        raise RomFormatError(f"Truncated ROM: expected >= {expected_size}, got {len(data)}")
    prg, chr_rom = data[prg_offset:chr_offset], data[chr_offset:expected_size]
    mirroring = "four_screen" if flags6 & 0x08 else ("vertical" if flags6 & 1 else "horizontal")
    meta = RomMetadata(
        format="iNES 1.0",
        mapper=(flags6 >> 4) | (flags7 & 0xF0),
        prg_banks_16k=prg_banks,
        chr_banks_8k=chr_banks,
        prg_bytes=prg_size,
        chr_bytes=chr_size,
        trainer_present=trainer,
        battery_backed=bool(flags6 & 0x02),
        mirroring=mirroring,
        header_bytes=INES_HEADER_BYTES,
        prg_rom_offset=prg_offset,
        chr_rom_offset=chr_offset,
        trailing_bytes=len(data) - expected_size,
        rom_sha256=hashlib.sha256(data).hexdigest(),
        prg_sha256=hashlib.sha256(prg).hexdigest(),
        chr_sha256=hashlib.sha256(chr_rom).hexdigest(),
        prg_crc32=_crc32(prg),
        chr_crc32=_crc32(chr_rom),
        prg_chr_crc32=_crc32(prg + chr_rom),
    )
    return Rom(image=data, prg=prg, chr=chr_rom, metadata=meta)


def load_rom(path: str | Path) -> Rom:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".nes":
        if source.stat().st_size > MAX_ROM_BYTES:
            raise RomFormatError("ROM exceeds size safety limit")
        return parse_nes(source.read_bytes())
    if suffix != ".zip":
        raise RomFormatError("Expected a .nes or .zip file")
    try:
        with zipfile.ZipFile(source) as archive:
            candidates = [
                entry for entry in archive.infolist()
                if not entry.is_dir() and entry.filename.lower().endswith(".nes")
            ]
            if len(candidates) != 1:
                raise RomFormatError("ZIP must contain exactly one .nes file")
            entry = candidates[0]
            if entry.flag_bits & 1:
                raise RomFormatError("Encrypted ZIP entries are not supported")
            if entry.file_size > MAX_ROM_BYTES:
                raise RomFormatError("ZIP ROM exceeds size safety limit")
            # Never unpack ZIP members to the filesystem.
            with archive.open(entry) as stream:
                data = stream.read(MAX_ROM_BYTES + 1)
            return parse_nes(data)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise RomFormatError(f"Invalid ZIP archive: {exc}") from exc
