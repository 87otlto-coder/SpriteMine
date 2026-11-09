-- SpriteMine SMB3 mapper bank-register tracing (research only).
-- Records bounded MMC3 $8000-$9FFF CPU writes, frame/PPU positions and values.
-- MesenCE write callbacks run BEFORE the mapped write is applied.
-- Output: local metadata-only JSON in F:/Dev/ROMMAGE/FIXTURE/SMB3/MesenCE.

local VERSION = "spritemine-mmc3-register-trace-v1"
local FRAME_PAIRS = 2
local MAX_WRITES = 128
local OUTPUT_DIR = (type(os) == "table" and type(os.getenv) == "function"
    and os.getenv("SPRITEMINE_CAPTURE_DIR"))
    or "F:/Dev/ROMMAGE/FIXTURE/SMB3/MesenCE"

if emu.getState()["consoleType"] ~= "Nes" then
    emu.log("SpriteMine MMC3 trace: NES console required")
    return
end
if type(io) ~= "table" or type(io.open) ~= "function" then
    emu.log("SpriteMine MMC3 trace: enable script I/O and OS functions")
    return
end

local function encode_string(value)
    local s = tostring(value)
    s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
    return '"' .. s .. '"'
end

local function encode_number(n)
    return type(n) == "number" and string.format("%.0f", n) or "null"
end

local writes, boundaries = {}, {}
local dropped_writes = 0
local started = false
local finished = false
local frame_pairs_seen = 0
local start_frame_no = nil

local function record_boundary(event)
    local state = emu.getState()
    boundaries[#boundaries + 1] = {
        event = event,
        frame = state["frameCount"],
        clock = state["masterClock"],
        scanline = state["ppu.scanline"],
        cycle = state["ppu.cycle"],
    }
end

local function on_start_frame(_cpu)
    if finished then return end
    if not started then
        started = true
        start_frame_no = emu.getState()["frameCount"]
    end
    record_boundary("startFrame")
end

local function on_mapper_write(address, value)
    if not started or finished then return end
    if #writes >= MAX_WRITES then
        dropped_writes = dropped_writes + 1
        return
    end
    -- Callback is called before the CPU write; do not read the new bank mapping here.
    local state = emu.getState()
    writes[#writes + 1] = {
        address = address, value = value,
        register = (address & 1) == 0 and "bankSelect" or "bankData",
        frame = state["frameCount"],
        clock = state["masterClock"],
        scanline = state["ppu.scanline"],
        cycle = state["ppu.cycle"],
    }
end

local function format_point(point)
    local bits = {
        '{"frame":', encode_number(point.frame),
        ',"master_clock":', encode_number(point.clock),
        ',"ppu_scanline":', encode_number(point.scanline),
        ',"ppu_cycle":', encode_number(point.cycle),
    }
    if point.event then
        bits[#bits + 1] = ',"event":'
        bits[#bits + 1] = encode_string(point.event)
    else
        bits[#bits + 1] = ',"address":'
        bits[#bits + 1] = encode_number(point.address)
        bits[#bits + 1] = ',"value":'
        bits[#bits + 1] = encode_number(point.value)
        bits[#bits + 1] = ',"register":'
        bits[#bits + 1] = encode_string(point.register)
    end
    bits[#bits + 1] = "}"
    return table.concat(bits)
end

local function finish()
    local info = emu.getRomInfo()
    local pieces = {
        '{"schema_version":1,"tool":', encode_string(VERSION),
        ',"source":"MesenCE Lua CPU write callback; pre-write metadata only"',
        ',"rom_sha1":', encode_string(info["fileSha1Hash"] or "unknown"),
        ',"started_frame":', encode_number(start_frame_no),
        ',"completed_frame_pairs":', encode_number(frame_pairs_seen),
        ',"max_writes":', encode_number(MAX_WRITES),
        ',"dropped_writes":', encode_number(dropped_writes),
        ',"boundaries":[',
    }
    for i, point in ipairs(boundaries) do
        if i > 1 then pieces[#pieces + 1] = "," end
        pieces[#pieces + 1] = format_point(point)
    end
    pieces[#pieces + 1] = '],"writes":['
    for i, point in ipairs(writes) do
        if i > 1 then pieces[#pieces + 1] = "," end
        pieces[#pieces + 1] = format_point(point)
    end
    pieces[#pieces + 1] = "]}\n"

    local name = string.format("mmc3_trace_%010d_%d.json",
        start_frame_no or 0, os.time())
    local path = OUTPUT_DIR .. "/" .. name
    local output, err = io.open(path, "wb")
    if not output then
        emu.log("SpriteMine MMC3 trace FAILED opening report: " .. tostring(err))
        return
    end
    local ok, write_err = output:write(table.concat(pieces))
    if not ok then
        output:close()
        emu.log("SpriteMine MMC3 trace FAILED writing report: " .. tostring(write_err))
        return
    end
    output:close()
    emu.log("SpriteMine MMC3 trace COMPLETE: " .. path)
    emu.log(string.format("SpriteMine: %d register writes, %d omitted (limit %d)",
        #writes, dropped_writes, MAX_WRITES))
end

local function on_end_frame(_cpu)
    if not started or finished then return end
    record_boundary("endFrame")
    frame_pairs_seen = frame_pairs_seen + 1
    if frame_pairs_seen >= FRAME_PAIRS then
        finished = true
        local ok, msg = pcall(finish)
        if not ok then emu.log("SpriteMine MMC3 trace FAILED: " .. tostring(msg)) end
    end
end

emu.addEventCallback(on_start_frame, emu.eventType.startFrame)
emu.addEventCallback(on_end_frame, emu.eventType.endFrame)
emu.addMemoryCallback(on_mapper_write, emu.callbackType.write, 0x8000, 0x9FFF)
emu.log("SpriteMine: tracing up to " .. MAX_WRITES
    .. " MMC3 bank register writes across " .. FRAME_PAIRS .. " frames.")
