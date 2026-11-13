"""Offline, file:// animation inspector for validated private SMB3 timelines.

Playback intervals are user-chosen PREVIEW settings, not proven NES timing.
No web server, PySide6 dependency, or emulator session is required.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from .animation_archive import read_verified_timeline


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpriteMine — private animation preview</title>
<style>
:root { color-scheme: dark; font: 15px system-ui, sans-serif; background: #171b23; color: #eef1f5; }
body { max-width: 900px; margin: 0 auto; padding: 24px; }
p { color: #b8c0cd; line-height: 1.55; }
h1 { font-size: 1.5rem; }
.panel { background: #232a35; border: 1px solid #3c4452; border-radius: 10px; padding: 16px; margin: 16px 0; }
.stage { min-height: 280px; display: grid; place-items: center; overflow: auto;
 background-color: #b8bec5; background-image: linear-gradient(45deg,#9099a5 25%, transparent 25%),linear-gradient(-45deg,#9099a5 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#9099a5 75%),linear-gradient(-45deg,transparent 75%,#9099a5 75%);
 background-size: 24px 24px; background-position: 0 0,0 12px,12px -12px,-12px 0; }
#sprite { width: 160px; height: 160px; image-rendering: pixelated; object-fit: contain; }
.controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
button, input { accent-color: #f5be63; }
button { background: #3b4657; color: #fff; border: 1px solid #667283; border-radius: 5px; padding: 8px 12px; cursor: pointer; }
button:focus-visible, input:focus-visible { outline: 2px solid #f5be63; }
#seek { flex: 1; min-width: 180px; }
#metadata { white-space: pre-wrap; font: 12px/1.5 ui-monospace, monospace; overflow-wrap: anywhere; }
small { color: #b8c0cd; }
</style>
</head>
<body>
<h1>SpriteMine — Mario frame evidence</h1>
<p>This is a private, offline visual inspector, not a proof of a complete walking cycle. Original video-frame events and master clocks remain authoritative in <a href="timeline.json">timeline.json</a>. Playback speed is illustrative only.</p>
<div class="panel">
  <div class="stage"><img id="sprite" src="__FIRST_IMAGE__" width="160" height="160" alt="Captured 16-by-16 RGBA Mario frame"></div>
  <div class="controls" style="margin-top:16px">
    <button id="previous" type="button">Previous</button>
    <button id="next" type="button">Next</button>
    <button id="play" type="button">Play preview</button>
    <label for="seek">Frame</label><input id="seek" type="range" min="0" max="0" value="0">
    <label for="zoom">Zoom</label><select id="zoom"><option value="4">4×</option><option value="10" selected>10×</option><option value="16">16×</option><option value="20">20×</option></select>
    <label for="speed">Preview ms/frame</label><input id="speed" type="number" min="50" max="1000" step="10" value="150" style="width:70px">
  </div>
  <p id="counter"></p>
</div>
<div class="panel"><h2>Frame provenance</h2><div id="metadata"></div></div>
<script type="application/json" id="timeline-data">__DATA__</script>
<script>
"use strict";
const report = JSON.parse(document.getElementById("timeline-data").textContent);
const frames = report.frames;
const sprite = document.getElementById("sprite");
const seek = document.getElementById("seek");
const speed = document.getElementById("speed");
const play = document.getElementById("play");
let current = 0, timer = null;
seek.max = String(frames.length - 1);
function show(index) {
  current = (index + frames.length) % frames.length;
  const f = frames[current];
  sprite.src = f.png_file;
  seek.value = String(current);
  document.getElementById("counter").textContent =
    "Event " + (current + 1) + " / " + frames.length + " | Emulator frame " + f.frame_count +
    " | " + report.unique_visual_frame_count + " unique RGBA appearances";
  document.getElementById("metadata").textContent =
    "Source: captured A/B/A, reconstructed from ROM-mapped OAM entries\n" +
    "Frame: " + f.frame_count + ", warmup: " + f.warmup +
    ", master clock: " + f.start_master_clock + "\n" +
    "OAM group: " + JSON.stringify(f.oam_group) + ", tiles: " + JSON.stringify(f.tile_ids) + "\n" +
    "Position: (" + f.position_x + ", " + f.position_y + ")\n" +
    "Opaque: " + f.opaque_pixels + ", transparent: " + f.transparent_pixels + "\n" +
    "RGBA SHA-256: " + f.rgba_sha256 + "\n" +
    "ROM SHA-256: " + report.source_rom_sha256 + "\n" +
    "Prior frame same RGBA: " + Boolean(f.identical_to_previous_frame) + "\n" +
    "Timing: NES emulator-frame events; loop and milliseconds unverified";
}
document.getElementById("previous").onclick = () => show(current - 1);
document.getElementById("next").onclick = () => show(current + 1);
seek.oninput = () => show(Number(seek.value));
document.getElementById("zoom").onchange = e => {
  sprite.style.width = (16 * Number(e.target.value)) + "px";
  sprite.style.height = (16 * Number(e.target.value)) + "px";
};
function stop() {
  if (timer !== null) clearInterval(timer);
  timer = null;
  play.textContent = "Play preview";
}
function start() {
  const interval = Number(speed.value);
  if (!Number.isFinite(interval) || interval < 50 || interval > 1000) {
    alert("Choose an illustrative preview interval between 50 and 1000 ms."); return;
  }
  stop();
  timer = setInterval(() => show(current + 1), interval);
  play.textContent = "Pause";
}
play.onclick = () => timer === null ? start() : stop();
speed.onchange = () => { if (timer !== null) start(); };
window.onkeydown = e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.key === "ArrowLeft") show(current - 1);
  if (e.key === "ArrowRight") show(current + 1);
};
show(0);
</script>
</body>
</html>
"""


def write_preview(timeline_file: Path, output: Path | None = None) -> Path:
    """Write only a new HTML page alongside its validated private frame PNGs."""
    timeline = Path(timeline_file).resolve(strict=True)
    report = read_verified_timeline(timeline)
    target = (Path(output) if output is not None else timeline.with_name("preview.html")).resolve()
    if target.parent != timeline.parent or target.suffix.lower() != ".html":
        raise ValueError("Preview must be a new .html file beside the timeline")
    payload = {
        "frames": report["frames"],
        "source_rom_sha256": report["source_rom_sha256"],
        "unique_visual_frame_count": report["unique_visual_frame_count"],
    }
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    serialized = serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page = (_PAGE.replace("__DATA__", serialized)
                 .replace("__FIRST_IMAGE__", html.escape(report["frames"][0]["png_file"], quote=True)))
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate offline private SMB3 animation HTML preview")
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None, help="New .html file in the timeline directory")
    args = parser.parse_args(argv)
    try:
        target = write_preview(args.timeline, args.output)
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        print(f"SpriteMine animation preview unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"preview_html": str(target), "status": "private_preview_not_loop_proof"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
