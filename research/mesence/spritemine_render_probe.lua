-- SpriteMine: same-session PPU/OAM + endFrame rendered RGB research probe.
-- Research only. Samples startFrame and endFrame for two frame pairs and
-- includes pre-write MMC3 bank register callbacks for independent reconciliation.
-- Binary data stays in F:/Dev/ROMMAGE/FIXTURE/SMB3/MesenCE (never in GitHub).
--
-- The samples are observations at frame BOUNDARIES, not proof of sprite
-- patterns fetched on every visible scanline or final rendered pixel timing.

local VERSION = "spritemine-mesence-render-capture-v1"
local CAPTURE_PAIRS = 2
local MAX_WRITES = 256
local OUTPUT_DIR = (type(os) == "table" and type(os.getenv) == "function"
    and os.getenv("SPRITEMINE_CAPTURE_DIR"))
    or "F:/Dev/ROMMAGE/FIXTURE/SMB3/MesenCE"

if emu.getState()["consoleType"] ~= "Nes" then
    emu.log("SpriteMine: NES console required")
    return
end
if type(io) ~= "table" or type(io.open) ~= "function" then
    emu.log("SpriteMine: enable script I/O and OS access; leave network disabled")
    return
end

local function json_string(value)
    local s = tostring(value)
    s = s:gsub("\\", "\\\\"):gsub('"', '\\"')
    s = s:gsub("\r", "\\r"):gsub("\n", "\\n")
    return '"' .. s .. '"'
end

local function json_number(value)
    return type(value) == "number" and string.format("%.0f", value) or "null"
end

local function read_bytes(memory_type, count)
    local items = {}
    for i = 0, count - 1 do
        local value = emu.read(i, memory_type)
        assert(type(value) == "number" and value >= 0 and value <= 255,
            "Out-of-range debugger memory byte at " .. tostring(i))
        items[#items + 1] = string.char(value)
    end
    return table.concat(items)
end

-- MesenCE LuaApi.GetRenderedFrame processes the current emulator PPU output
-- through the active video filter. This script records its 24-bit RGB pixels
-- inside endFrame, before SendFrame dispatches to the video frontend.
-- The precise phase alignment must be established against an independent
-- same-frame verification experiment; startFrame PPU/OAM are not atomic with it.
local function read_screen()
    local size = emu.getScreenSize()
    local width, height = size.width, size.height
    assert(type(width) == "number" and type(height) == "number"
        and width > 0 and height > 0 and width * height <= 512 * 512,
        "Invalid or unsupported screen output dimensions")
    local pixels = emu.getScreenBuffer()
    assert(#pixels == width * height, "Rendered screen pixel count mismatch")
    local bytes = {}
    for i = 1, #pixels do
        local value = pixels[i]
        assert(type(value) == "number" and value >= 0 and value <= 0xFFFFFF,
            "Unexpected screen RGB pixel")
        bytes[i] = string.char(
            (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
        )
    end
    return table.concat(bytes), width, height
end

local samples = {}
local writes = {}
local dropped_writes = 0
local started = false
local finished = false
local pending = false
local pairs_done = 0
local initial_frame = nil

local function sample(event)
    local s = emu.getState()
    assert(type(s["frameCount"]) == "number", "Missing frameCount")
    assert(emu.getMemorySize(emu.memType.nesSpriteRam) == 256, "Unexpected OAM size")
    assert(emu.getMemorySize(emu.memType.nesPaletteRam) >= 32, "Unexpected palette RAM size")
    local screen, screen_width, screen_height = nil, nil, nil
    if event == "endFrame" then
        screen, screen_width, screen_height = read_screen()
    end
    return {
        screen = screen, screen_width = screen_width, screen_height = screen_height,
        event = event,
        frame = s["frameCount"],
        clock = s["masterClock"],
        scanline = s["ppu.scanline"],
        cycle = s["ppu.cycle"],
        sprite_height = s["ppu.control.largeSprites"] and 16 or 8,
        oam = read_bytes(emu.memType.nesSpriteRam, 256),
        palette = read_bytes(emu.memType.nesPaletteRam, 32),
        ppu = read_bytes(emu.memType.nesPpuDebug, 8192),
    }
end

local function encode_sample(s, files)
    return table.concat({
        '{"event":', json_string(s.event),
        ',"frame_count":', json_number(s.frame),
        ',"master_clock":', json_number(s.clock),
        ',"ppu_scanline":', json_number(s.scanline),
        ',"ppu_cycle":', json_number(s.cycle),
        ',"sprite_height":', json_number(s.sprite_height),
        ',"screen_width":', json_number(s.screen_width),
        ',"screen_height":', json_number(s.screen_height),
        ',"screen_pixel_source":"emu.getScreenBuffer() video-filtered RGB24 at endFrame; phase correspondence unverified"',
        ',"files":{"oam":', json_string(files.oam),
        ',"palette":', json_string(files.palette),
        ',"ppu_pattern":', json_string(files.ppu),
        ',"screen_rgb":', files.screen_rgb and json_string(files.screen_rgb) or "null",
        '}}',
    })
end

local function encode_write(w)
    return table.concat({
        '{"frame_count":', json_number(w.frame),
        ',"master_clock":', json_number(w.clock),
        ',"ppu_scanline":', json_number(w.scanline),
        ',"ppu_cycle":', json_number(w.cycle),
        ',"address":', json_number(w.address),
        ',"value":', json_number(w.value),
        '}',
    })
end

local function write_new_file(path, bytes)
    -- Never silently overwrite previous experiment evidence.
    local old = io.open(path, "rb")
    if old then
        old:close()
        error("Capture path already exists: " .. path)
    end
    local out, err = io.open(path, "wb")
    assert(out ~= nil, "Failed to open capture: " .. tostring(err))
    local ok, message = out:write(bytes)
    if not ok then
        out:close()
        error("Failed writing capture: " .. tostring(message))
    end
    assert(out:close(), "Failed closing capture: " .. path)
end

local function finish()
    local session = string.format("render_%010d_%d", initial_frame, os.time())
    local saved = {}
    local encoded = {}
    for index, s in ipairs(samples) do
        local prefix = string.format("%s_%d_%s", session, index, s.event)
        local names = {
            oam = prefix .. "_oam.bin",
            palette = prefix .. "_palette.bin",
            ppu = prefix .. "_ppu_pattern.bin",
        }
        for _, part in ipairs({"oam", "palette", "ppu"}) do
            saved[#saved + 1] = {name = names[part], data = s[part]}
        end
        if s.screen ~= nil then
            names.screen_rgb = prefix .. "_screen_rgb.bin"
            saved[#saved + 1] = {name = names.screen_rgb, data = s.screen}
        end
        encoded[#encoded + 1] = encode_sample(s, names)
    end

    local encoded_writes = {}
    for _, w in ipairs(writes) do
        encoded_writes[#encoded_writes + 1] = encode_write(w)
    end

    local rom = emu.getRomInfo()
    local json = table.concat({
        '{"schema_version":1',
        ',"capture_tool":', json_string(VERSION),
        ',"evidence":"captured"',
        ',"source":"MesenCE Lua frame callbacks and pre-write CPU-memory callback"',
        ',"rom_sha1_reported_by_mesen":', json_string(rom["fileSha1Hash"] or "unknown"),
        ',"session_id":', json_string(session),
        ',"completed_frame_pairs":', json_number(pairs_done),
        ',"write_limit":', json_number(MAX_WRITES),
        ',"dropped_writes":', json_number(dropped_writes),
        ',"phase_captures":[', table.concat(encoded, ","), ']',
        ',"writes":[', table.concat(encoded_writes, ","), ']',
        '}\n',
    })

    local manifest = OUTPUT_DIR .. "/" .. session .. ".json"
    local existing = io.open(manifest, "rb")
    if existing then
        existing:close()
        error("Capture session already exists: " .. manifest)
    end
    for _, entry in ipairs(saved) do
        local handle = io.open(OUTPUT_DIR .. "/" .. entry.name, "rb")
        if handle then
            handle:close()
            error("Existing capture part would be overwritten: " .. entry.name)
        end
    end

    for _, entry in ipairs(saved) do
        write_new_file(OUTPUT_DIR .. "/" .. entry.name, entry.data)
    end
    -- Commit metadata only after all component files have been written.
    write_new_file(manifest, json)
    emu.log("SpriteMine RENDER CAPTURE COMPLETE: " .. manifest)
    emu.log("SpriteMine: " .. #samples .. " snapshots, " .. #writes
        .. " timed MMC3 register writes; dropped " .. dropped_writes)
end

local function on_write(address, value)
    if not started or finished then return end
    if #writes >= MAX_WRITES then
        dropped_writes = dropped_writes + 1
        return
    end
    local s = emu.getState()
    writes[#writes + 1] = {
        address = address, value = value,
        frame = s["frameCount"], clock = s["masterClock"],
        scanline = s["ppu.scanline"], cycle = s["ppu.cycle"],
    }
end

local function stop_error(message)
    finished = true
    emu.log("SpriteMine RENDER CAPTURE FAILED: " .. tostring(message))
end

local function on_start(_cpu)
    if finished then return end
    if pending then
        stop_error("startFrame called twice without endFrame")
        return
    end
    if not started then
        started = true
        initial_frame = emu.getState()["frameCount"]
    end
    local ok, result = pcall(sample, "startFrame")
    if not ok then return stop_error(result) end
    samples[#samples + 1] = result
    pending = true
end

local function on_end(_cpu)
    if finished or not pending then return end
    local ok, result = pcall(sample, "endFrame")
    if not ok then return stop_error(result) end
    samples[#samples + 1] = result
    pending = false
    pairs_done = pairs_done + 1
    if pairs_done >= CAPTURE_PAIRS then
        finished = true
        local done, err = pcall(finish)
        if not done then stop_error(err) end
    end
end

emu.addEventCallback(on_start, emu.eventType.startFrame)
emu.addEventCallback(on_end, emu.eventType.endFrame)
emu.addMemoryCallback(on_write, emu.callbackType.write, 0x8000, 0x9FFF)
emu.log("SpriteMine: recording " .. CAPTURE_PAIRS
    .. " start/end frame pairs with raw PPU/OAM/palette, endFrame RGB24 and MMC3 writes")
emu.log("SpriteMine: local FIXTURE output: " .. OUTPUT_DIR)
