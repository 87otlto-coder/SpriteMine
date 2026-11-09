-- SpriteMine MesenCE source-level feasibility probe (not a validated emulator adapter).
-- Requires MesenCE's script file I/O permission. Captures two endFrame samples.
-- Run while the verified SMB3 US PRG1 ROM is actively playing.
-- Output is LOCAL: MesenCE's LuaScriptData/spritemine_frame_probe folder.
-- This original script depends on MesenCE Lua API semantics and must be tested on Windows.

local PROBE_VERSION = "spritemine-mesence-endframe-v1"
local FRAMES_TO_CAPTURE = 2
local CAPTURED = 0

local state = emu.getState()
if state["consoleType"] ~= "Nes" then
    emu.log("SpriteMine: NES console required; no data captured.")
    return
end

-- MesenCE's ScriptingContext omits the io and os libraries unless explicitly enabled.
if type(io) ~= "table" or type(io.open) ~= "function" then
    emu.log("SpriteMine: script I/O is disabled. Enable Lua file I/O in MesenCE debugger settings.")
    return
end

local OUTPUT_DIR = emu.getScriptDataFolder()
if type(OUTPUT_DIR) ~= "string" or OUTPUT_DIR == "" then
    emu.log("SpriteMine: MesenCE did not provide an accessible script data folder.")
    return
end

local function quote_json(value)
    local s = tostring(value)
    s = s:gsub("\\", "\\\\")
    s = s:gsub('"', '\\"')
    s = s:gsub("\r", "\\r")
    s = s:gsub("\n", "\\n")
    return '"' .. s .. '"'
end

local function number_or_null(value)
    return type(value) == "number" and string.format("%d", value) or "null"
end

local function write_binary(path, data)
    local f, err = io.open(path, "wb")
    assert(f ~= nil, "Unable to open " .. path .. ": " .. tostring(err))
    local success, message = f:write(data)
    if not success then
        f:close()
        error("Unable to write " .. path .. ": " .. tostring(message))
    end
    assert(f:close(), "Unable to close " .. path)
end

local function read_bytes(memory_type, count)
    local chunks = {}
    for i = 0, count - 1 do
        chunks[#chunks + 1] = string.char(emu.read(i, memory_type))
    end
    return table.concat(chunks)
end

local function read_screen_rgb()
    local size = emu.getScreenSize()
    local width, height = size.width, size.height
    assert(type(width) == "number" and type(height) == "number", "Invalid screen dimensions")
    assert(width > 0 and height > 0 and width * height <= 512 * 512, "Screen dimensions out of scope")
    local pixel_values = emu.getScreenBuffer()
    assert(#pixel_values == width * height, "Screen pixel count does not match dimensions")

    -- API implementation returns 0xRRGGBB; record RGB24 bytes in row-major order.
    local chunks = {}
    for i = 1, #pixel_values do
        local pixel = pixel_values[i]
        chunks[i] = string.char((pixel >> 16) & 0xFF, (pixel >> 8) & 0xFF, pixel & 0xFF)
    end
    return table.concat(chunks), width, height
end

local function capture_one()
    local s = emu.getState()
    local info = emu.getRomInfo()
    local frame = s["frameCount"]
    assert(type(frame) == "number", "No frameCount in emu.getState()")

    assert(emu.getMemorySize(emu.memType.nesSpriteRam) == 256, "Unexpected OAM size")
    assert(emu.getMemorySize(emu.memType.nesPaletteRam) >= 32, "Unexpected palette RAM size")

    local basename = string.format("frame_%010d", frame)
    local oam_name = basename .. "_oam.bin"
    local palette_name = basename .. "_palette.bin"
    local pattern_name = basename .. "_ppu_pattern.bin"
    local screen_name = basename .. "_screen_rgb.bin"
    local meta_name = basename .. ".json"

    -- Effective PPU pattern-space reads are NOT mapped to physical CHR-ROM offsets here.
    -- endFrame callback coherence and screenshot phase alignment require runtime validation.
    local oam = read_bytes(emu.memType.nesSpriteRam, 256)
    local palette = read_bytes(emu.memType.nesPaletteRam, 32)
    local pattern = read_bytes(emu.memType.nesPpuDebug, 8192)
    local screen, width, height = read_screen_rgb()

    write_binary(OUTPUT_DIR .. "/" .. oam_name, oam)
    write_binary(OUTPUT_DIR .. "/" .. palette_name, palette)
    write_binary(OUTPUT_DIR .. "/" .. pattern_name, pattern)
    write_binary(OUTPUT_DIR .. "/" .. screen_name, screen)

    local sprite_height = s["ppu.control.largeSprites"] and 16 or 8
    local json = table.concat({
        "{\n",
        '  "schema_version": 1,\n',
        '  "evidence": "captured",\n',
        '  "capture_tool": ', quote_json(PROBE_VERSION), ",\n",
        '  "event": "endFrame",\n',
        '  "pixel_source": "emu.getScreenBuffer (video-filtered RGB; phase unverified)",\n',
        '  "mapping_source": "nesPpuDebug effective address space; physical CHR bank mapping unresolved",\n',
        '  "console_type": ', quote_json(s["consoleType"]), ",\n",
        '  "region": ', quote_json(s["region"] or "unknown"), ",\n",
        '  "rom_sha1_reported_by_mesen": ', quote_json(info["fileSha1Hash"] or "unknown"), ",\n",
        '  "frame_count": ', number_or_null(frame), ",\n",
        '  "master_clock": ', number_or_null(s["masterClock"]), ",\n",
        '  "ppu_scanline": ', number_or_null(s["ppu.scanline"]), ",\n",
        '  "ppu_cycle": ', number_or_null(s["ppu.cycle"]), ",\n",
        '  "sprite_height": ', number_or_null(sprite_height), ",\n",
        '  "screen_width": ', number_or_null(width), ",\n",
        '  "screen_height": ', number_or_null(height), ",\n",
        '  "files": {\n',
        '    "oam": ', quote_json(oam_name), ",\n",
        '    "palette": ', quote_json(palette_name), ",\n",
        '    "ppu_pattern": ', quote_json(pattern_name), ",\n",
        '    "screen_rgb": ', quote_json(screen_name), "\n",
        "  }\n",
        "}\n",
    })

    -- Write metadata last; incomplete captures without a manifest are not accepted.
    write_binary(OUTPUT_DIR .. "/" .. meta_name, json)
    emu.log("SpriteMine: captured frame " .. tostring(frame) .. " in " .. OUTPUT_DIR)
    CAPTURED = CAPTURED + 1
    if CAPTURED >= FRAMES_TO_CAPTURE then
        emu.displayMessage("SpriteMine", "Captured " .. FRAMES_TO_CAPTURE .. " endFrame snapshots.")
    end
end

local function on_end_frame(_cpu_type)
    if CAPTURED >= FRAMES_TO_CAPTURE then
        return
    end
    local ok, message = pcall(capture_one)
    if not ok then
        emu.log("SpriteMine capture FAILED: " .. tostring(message))
        -- Stop trying after a write error; do not flood disk or log.
        CAPTURED = FRAMES_TO_CAPTURE
    end
end

emu.addEventCallback(on_end_frame, emu.eventType.endFrame)
emu.log("SpriteMine probe: capturing the next " .. FRAMES_TO_CAPTURE
    .. " endFrame events; output folder: " .. OUTPUT_DIR)
