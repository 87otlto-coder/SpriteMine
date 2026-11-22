"""Launch a bounded passive NES capture, or inspect/reconstruct one offline. Stdlib only."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def snapshots(path):
    """Yield reconstructed samples. Fail on missing baselines/pages or invalid deltas."""
    memory, sizes, seq = {}, {}, 0
    for record in records(path):
        if record["type"] == "header":
            if sizes or record["schema"] != 1:
                raise ValueError("Duplicate header or unsupported schema")
            sizes = {k: v["size"] for k, v in record["regions"].items()}
            if not sizes or any(not 0 < n <= 262144 for n in sizes.values()) or sum(sizes.values()) > 274432:
                raise ValueError("Invalid memory sizes")
        elif record["type"] == "sample":
            if record["seq"] != seq + 1 or not sizes:
                raise ValueError("Missing header or non-contiguous sequence")
            seq += 1
            if record["full"]:
                memory = {k: bytearray(n) for k, n in sizes.items()}
            elif not memory:
                raise ValueError("Delta without baseline")
            if set(record["memory"]) != set(sizes):
                raise ValueError("Region mismatch")
            for name, pages in record["memory"].items():
                expected = set(range(0, sizes[name], 256))
                if record["full"] and {int(p) for p in pages} != expected:
                    raise ValueError("Incomplete checkpoint")
                for offset, data in pages.items():
                    offset, data = int(offset), bytes.fromhex(data)
                    if offset not in expected or len(data) != min(256, sizes[name] - offset):
                        raise ValueError("Invalid page")
                    memory[name][offset:offset + len(data)] = data
            yield record, {k: bytes(v) for k, v in memory.items()}


def summarize(path):
    count, peaks, ranges = 0, [], []
    for record, memory in snapshots(path):
        count += 1
        ranges.append(record["time"]["frame"])
        if count > 1:
            changes = record["changed_bytes"]
            peaks.append({"frame": ranges[-1], "tick": record["time"]["tick"],
                          "changed_bytes": changes, "total": sum(changes.values())})
    footer = None
    event_totals = {"write": 0, "exec": 0}
    retained = 0
    for record in records(path):
        if record["type"] == "end":
            footer = record
        if record["type"] == "burst":
            retained += len(record["events"])
            for kind, value in record["event_totals"].items():
                event_totals[kind] += value
    return {"samples": count, "frame_range": [min(ranges), max(ranges)] if ranges else [],
            "footer": footer, "retained_events": retained, "burst_event_totals": event_totals,
            "largest_changes": sorted(peaks, key=lambda p: p["total"], reverse=True)[:10],
            "interpretation": "Change candidates, not semantic area labels; snapshots alias transient changes."}


def find_writes(path, *, address, value=None, first=None, last=None):
    """Find retained writes. Omitted writes cannot be filtered by address or value."""
    if not 0 <= address <= 0xFFFF or value is not None and not 0 <= value <= 0xFF:
        raise ValueError("Expected a 16-bit address and optional 8-bit value")
    if first is not None and first < 0 or last is not None and last < 0:
        raise ValueError("Expected nonnegative frame numbers")
    if first is not None and last is not None and first > last:
        raise ValueError("First frame exceeds last frame")

    matches, omitted, footer = [], 0, None
    for record in records(path):
        if record["type"] == "end":
            footer = record
        if record["type"] != "burst":
            continue
        writes = [event for event in record["events"].values() if event["kind"] == "write"]
        frame = record["time"]["frame"]
        # A burst is flushed at end-of-frame. Its callbacks can also carry
        # the preceding frame number around the frame boundary.
        if (first is None or frame >= first) and (last is None or frame <= last + 1):
            omitted += record["event_totals"].get("write", 0) - len(writes)
        for event in writes:
            if (event["address"] == address and (value is None or event["value"] == value)
                    and (first is None or event["frame"] >= first)
                    and (last is None or event["frame"] <= last)):
                matches.append(event)
    matches.sort(key=lambda event: (event["frame"], event["cpu_cycle"]))
    return {"matches": matches, "omitted_writes_in_candidate_bursts": omitted, "footer": footer}


def package(folder):
    raw = folder / "capture.jsonl"
    target = folder / "capture.jsonl.gz"
    with raw.open("rb") as source, target.open("xb") as dest:
        with gzip.GzipFile(filename="", fileobj=dest, mode="wb", mtime=0) as zipped:
            shutil.copyfileobj(source, zipped)
    with gzip.open(target, "rb") as check:
        if hashlib.file_digest(check, "sha256").hexdigest() != digest(raw):
            raise ValueError("Compression verification failed")
    raw.unlink()  # Only this session's verified compressed spool.
    return target


def run_logged(command, *, cwd, env, log_path, timeout, headless):
    """Drain child output while retaining at most 1 MiB on disk."""
    with log_path.open("xb") as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if headless else 0)
        def drain():
            remaining = 1048576
            with process.stdout:
                while chunk := process.stdout.read(8192):
                    if remaining:
                        log.write(chunk[:remaining])
                        remaining = max(0, remaining - len(chunk))
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            return process.wait(timeout=timeout)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            reader.join()


def capture(args):
    script = Path(__file__).with_suffix(".lua").resolve()
    sources = {"rom": args.rom, "emulator": args.emulator, "recorder": script}
    for name in ("settings.json", "MesenCore.dll"):
        candidate = args.emulator.with_name(name)
        if candidate.exists():
            sources[name] = candidate
    hashes = {k: digest(v) for k, v in sources.items()}
    args.output.mkdir(parents=True, exist_ok=True)
    if any((p / ".git").exists() for p in (args.output, *args.output.parents)):
        raise ValueError("Private sessions must be outside Git checkouts")
    folder = args.output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
    folder.mkdir()
    env = dict(os.environ, SMFR_OUTPUT=str(folder), SMFR_INTERVAL=str(args.interval),
               SMFR_CHECKPOINT=str(args.checkpoint), SMFR_FRAMES=str(args.frames),
               SMFR_MAX_BYTES=str(args.max_mib * 1048576), SMFR_EVENTS=str(int(args.events)),
               SMFR_EVENT_CAP=str(args.event_cap),
               SMFR_TRIGGER_WRITE="" if args.trigger_write is None else str(args.trigger_write), SMFR_STOP=str(int(args.headless)))
    command = [str(args.emulator), "--doNotSaveSettings"]
    if args.headless:
        command += ["--testRunner", f"--timeout={args.timeout}"]
    command += [str(script), str(args.rom)]
    manifest = {"schema": 1, "evidence": "captured", "source_sha256": hashes,
                "sources": {k: str(v) for k, v in sources.items()}, "command": command,
                "config": {k: v for k, v in env.items() if k.startswith("SMFR_")},
                "status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    start = time.perf_counter()
    error = None
    try:
        code = run_logged(command, cwd=args.emulator.parent, env=env,
                          log_path=folder / "emulator.log", timeout=args.timeout + 15, headless=args.headless)
        if code:
            error = f"Emulator exit {code}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = str(exc)
    manifest["wall_seconds"] = time.perf_counter() - start
    manifest["sources_unchanged"] = all(digest(v) == hashes[k] for k, v in sources.items())
    if not manifest["sources_unchanged"]:
        error = "A source changed during capture"
    raw = folder / "capture.jsonl"
    if raw.exists():
        manifest["raw_bytes"] = raw.stat().st_size
        packed = package(folder)
        manifest["capture_sha256"] = digest(packed)
        manifest["compressed_bytes"] = packed.stat().st_size
        try:
            manifest["summary"] = summarize(packed)
            if not manifest["summary"]["footer"] or not manifest["summary"]["samples"]:
                error = error or "Capture incomplete (missing footer or baseline)"
        except (ValueError, KeyError) as exc:
            error = f"Incomplete/invalid capture: {exc}"
    else:
        error = error or "Recorder produced no capture"
    manifest["status"], manifest["error"] = ("failed" if error else "complete"), error
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(str(folder))
    if error:
        raise ValueError(error)


def bounded(low, high):
    def convert(value):
        n = int(value)
        if not low <= n <= high:
            raise argparse.ArgumentTypeError(f"Expected {low}..{high}")
        return n
    return convert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("capture")
    for name in ("emulator", "rom", "output"):
        run.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    for name, default, low, high in [("interval", 30, 1, 3600), ("checkpoint", 300, 1, 36000),
                                     ("frames", 3600, 1, 216000), ("max-mib", 64, 1, 1024),
                                     ("event-cap", 32, 1, 256), ("timeout", 120, 1, 7200)]:
        run.add_argument("--" + name, type=bounded(low, high), default=default)
    event_mode = run.add_mutually_exclusive_group()
    event_mode.add_argument("--events", action="store_true")
    event_mode.add_argument("--trigger-write", type=lambda value: int(value, 0))
    run.add_argument("--headless", action="store_true", help="Test runner; no controller automation")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("capture", type=Path)
    writes = sub.add_parser("writes", help="Find retained CPU writes in a recording")
    writes.add_argument("capture", type=Path)
    writes.add_argument("--address", type=lambda value: int(value, 0), required=True)
    writes.add_argument("--value", type=lambda value: int(value, 0))
    writes.add_argument("--first", type=int)
    writes.add_argument("--last", type=int)
    args = parser.parse_args()
    try:
        if args.action == "capture":
            if args.trigger_write is not None and not 0 <= args.trigger_write <= 65535:
                parser.error("--trigger-write must be a 16-bit CPU address")
            capture(args)
        elif args.action == "inspect":
            print(json.dumps(summarize(args.capture), indent=2))
        else:
            result = find_writes(args.capture, address=args.address, value=args.value,
                                 first=args.first, last=args.last)
            print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Flight recorder: {exc}\n")


if __name__ == "__main__":
    main()
