-- SpriteMine mapper timing probe for MesenCE, research-only.
-- Records derived counts, not graphics bytes, at startFrame and endFrame.
-- Tests whether PPU pattern tables are different at these two moments.
-- Does NOT establish the mapping used on visible sprite scanlines.

local VERSION = "spritemine-mapping-phase-v1"
local LIMIT = 2
local DIR = (type(os) == "table" and os.getenv("SPRITEMINE_CAPTURE_DIR"))
    or "F:/Dev/ROMMAGE/FIXTURE/SMB3/MesenCE"

if emu.getState()["consoleType"] ~= "Nes" then
    emu.log("SpriteMine mapping probe: NES console required")
    return
end
if type(io) ~= "table" or type(io.open) ~= "function" then
    emu.log("SpriteMine mapping probe: enable I/O and OS access in Script Window settings")
    return
end

local function esc(value)
    local s = tostring(value)
    s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
    return '"' .. s .. '"'
end

local function jsnumber(n)
    return type(n) == "number" and string.format("%.0f", n) or "null"
end

local function pattern_count(base, size)
    local nonzero = 0
    for addr = base, base + size - 1 do
        if emu.read(addr, emu.memType.nesPpuDebug) ~= 0 then
            nonzero = nonzero + 1
        end
    end
    return nonzero
end

local function snapshot(event_name)
    local s = emu.getState()
    local height = s["ppu.control.largeSprites"] and 16 or 8
    local visible_entries, odd_entries, blank_odd_entries = 0, 0, 0
    for index = 0, 63 do
        local off = index * 4
        local y = emu.read(off, emu.memType.nesSpriteRam)
        if y + 1 < 240 then
            visible_entries = visible_entries + 1
            if height == 16 then
                local tile = emu.read(off + 1, emu.memType.nesSpriteRam)
                if (tile & 1) == 1 then
                    odd_entries = odd_entries + 1
                    local start = 0x1000 + ((tile & 0xFE) << 4)
                    if pattern_count(start, 32) == 0 then
                        blank_odd_entries = blank_odd_entries + 1
                    end
                end
            end
        end
    end
    return {
        event = event_name,
        frame = s["frameCount"],
        clock = s["masterClock"],
        scanline = s["ppu.scanline"],
        cycle = s["ppu.cycle"],
        sprite_height = height,
        lower_nonzero = pattern_count(0, 4096),
        upper_nonzero = pattern_count(0x1000, 4096),
        visible_oam_entries = visible_entries,
        odd_tile_oam_entries = odd_entries,
        odd_tile_blank_pattern_entries = blank_odd_entries,
    }
end

local function format_snapshot(s)
    return table.concat({
        '{"event":', esc(s.event),
        ',"frame":', jsnumber(s.frame),
        ',"master_clock":', jsnumber(s.clock),
        ',"ppu_scanline":', jsnumber(s.scanline),
        ',"ppu_cycle":', jsnumber(s.cycle),
        ',"sprite_height":', jsnumber(s.sprite_height),
        ',"ppu_lower_nonzero":', jsnumber(s.lower_nonzero),
        ',"ppu_upper_nonzero":', jsnumber(s.upper_nonzero),
        ',"possible_on_screen_oam":', jsnumber(s.visible_oam_entries),
        ',"odd_tile_oam":', jsnumber(s.odd_tile_oam_entries),
        ',"odd_tile_blank_patterns":', jsnumber(s.odd_tile_blank_pattern_entries),
        '}',
    })
end

local first = nil
local pairs = {}
local done = false

local function on_start_frame(_cpu_type)
    if done then return end
    local ok, result = pcall(snapshot, "startFrame")
    if not ok then
        done = true
        emu.log("SpriteMine mapping probe FAILED at startFrame: " .. tostring(result))
        return
    end
    first = result
end

local function on_end_frame(_cpu_type)
    if done or first == nil then return end
    local ok, result = pcall(snapshot, "endFrame")
    if not ok then
        done = true
        emu.log("SpriteMine mapping probe FAILED at endFrame: " .. tostring(result))
        return
    end
    pairs[#pairs + 1] = { start = first, finish = result }
    emu.log(string.format(
        "SpriteMine PPU phase %d: start upper=%d; end upper=%d; OAM odd-tile blanks=%d/%d",
        #pairs, first.upper_nonzero, result.upper_nonzero,
        result.odd_tile_blank_pattern_entries, result.odd_tile_oam_entries
    ))
    first = nil
    if #pairs < LIMIT then return end
    done = true
    local rom = emu.getRomInfo()
    local parts = {
        '{"schema_version":1',
        ',"tool":', esc(VERSION),
        ',"rom_sha1":', esc(rom["fileSha1Hash"] or "unknown"),
        ',"pairs":[',
    }
    for index, pair in ipairs(pairs) do
        if index > 1 then parts[#parts + 1] = "," end
        parts[#parts + 1] = '{"start":'
        parts[#parts + 1] = format_snapshot(pair.start)
        parts[#parts + 1] = ',"end":'
        parts[#parts + 1] = format_snapshot(pair.finish)
        parts[#parts + 1] = "}"
    end
    parts[#parts + 1] = "]}\n"
    local path = DIR .. "/" .. string.format(
        "mapping_probe_%010d_%d.json", pairs[1].start.frame or 0, os.time())
    local f, err = io.open(path, "wb")
    if not f then
        emu.log("SpriteMine mapping probe FAILED to open output: " .. tostring(err))
        return
    end
    local written, message = f:write(table.concat(parts))
    if not written then
        f:close()
        emu.log("SpriteMine mapping probe FAILED writing output: " .. tostring(message))
        return
    end
    f:close()
    emu.log("SpriteMine mapping probe complete: " .. path)
end

emu.addEventCallback(on_start_frame, emu.eventType.startFrame)
emu.addEventCallback(on_end_frame, emu.eventType.endFrame)
emu.log("SpriteMine: comparing PPU pattern mappings at startFrame and endFrame for "
    .. LIMIT .. " frame pairs")
