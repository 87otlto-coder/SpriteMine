-- Synthetic MesenCE framebuffer and MMC3 mapping probe regression test.
-- No SMB3 bytes, assets or game code. All bank data is formula-generated.
local output = os.getenv("SPRITEMINE_CAPTURE_DIR")
assert(type(output) == "string" and output ~= "", "SPRITEMINE_CAPTURE_DIR must be configured")

local frame, clock, scanline, cycle = 500, 100, -1, 0
local registers = {8, 102, 83, 4, 34, 50, 0, 0}
local select = 0x40
local callbacks = {}

local function mapped_bank(slot)
    if slot == 0 then return registers[1] & 0xFE end
    if slot == 1 then return (registers[1] & 0xFE) + 1 end
    if slot == 2 then return registers[2] & 0xFE end
    if slot == 3 then return (registers[2] & 0xFE) + 1 end
    return registers[slot - 1]
end

emu = {
    memType = {nesSpriteRam = 1, nesPaletteRam = 2, nesPpuDebug = 3},
    eventType = {startFrame = 1, endFrame = 2},
    callbackType = {write = 3},
    getState = function()
        return {
            consoleType = "Nes", frameCount = frame, masterClock = clock,
            region = "Ntsc",
            ["ppu.scanline"] = scanline, ["ppu.cycle"] = cycle,
            ["ppu.control.largeSprites"] = true,
        }
    end,
    getRomInfo = function()
        return {fileSha1Hash = os.getenv("SPRITEMINE_TEST_ROM_SHA1") or string.rep("a", 40)}
    end,
    getMemorySize = function(kind)
        if kind == 1 then return 256 end
        if kind == 2 then return 32 end
        return 8192
    end,
    read = function(address, kind)
        if kind == 1 then
            if address == 40 or address == 44 then return 161 end
            if address == 41 then return 7 end
            if address == 45 then return 5 end
            if address == 43 then return 100 end
            if address == 47 then return 108 end
            if address % 4 == 0 then return 248 end
            return 0
        elseif kind == 2 then
            return address % 64
        elseif kind == 3 then
            local slot = address // 1024
            return (mapped_bank(slot) * 3 + (address % 1024)) % 256
        end
        error("Unexpected memory type")
    end,
    getScreenSize = function() return {width = 256, height = 240} end,
    getScreenBuffer = function()
        -- The displayed framebuffer was rendered using *pre-render* CHR banks.
        -- It stays populated even after the scanline-193 bank switch to blanks.
        local output = {}
        for i = 1, 256 * 240 do output[i] = 0x101010 end
        local colors = {0xA01010, 0x10A010, 0x1010A0}
        for _, entry in ipairs({{x=100, y=162, tile=7}, {x=108, y=162, tile=5}}) do
            local addr = 0x1000 + ((entry.tile & 0xFE) << 4)
            for row = 0, 15 do
                local tile_addr = addr + (row >= 8 and 16 or 0)
                local subrow = row % 8
                local low_offset = (tile_addr + subrow) % 1024
                local hi_offset = (tile_addr + subrow + 8) % 1024
                local low = (83 * 3 + low_offset) % 256
                local high = (83 * 3 + hi_offset) % 256
                for x = 0, 7 do
                    local bit = 7 - x
                    local idx = ((low >> bit) & 1) | (((high >> bit) & 1) << 1)
                    if idx ~= 0 then
                        output[(entry.y + row) * 256 + entry.x + x + 1] = colors[idx]
                    end
                end
            end
        end
        return output
    end,
    addEventCallback = function(callback, kind)
        callbacks[kind] = callback
        return kind
    end,
    addMemoryCallback = function(callback, mode, first, last)
        assert(mode == 3 and first == 0x8000 and last == 0x9FFF)
        callbacks.write = callback
        return 4
    end,
    log = function(message) print(message) end,
}

assert(arg[1], "Pass the rendered capture script file path")
dofile(arg[1])
assert(callbacks[1] and callbacks[2] and callbacks.write, "Expected all callbacks")

local function mapper_write(address, value)
    -- Debugger write callbacks are pre-write: update synthetic mapper afterwards.
    callbacks.write(address, value)
    if address == 0x8000 then
        select = value
    else
        registers[(select & 7) + 1] = value
    end
    clock = clock + 1
end

local function set_banks(values, first_clock, y)
    clock, scanline, cycle = first_clock, y, 70
    for r = 0, 5 do
        mapper_write(0x8000, 0x40 | r)
        mapper_write(0x8001, values[r + 1])
    end
end

local before = {8, 102, 83, 4, 34, 50}
local after = {92, 94, 126, 126, 126, 126}

-- First startFrame snapshot has unknown initial bank provenance in a real trace.
callbacks[1](0)
set_banks(after, 120, 193)
clock, scanline, cycle = 200, 240, 0
callbacks[2](0)

-- Writes between two frames are critical: these restore the known second start.
frame = 501
set_banks(before, 260, 246)
clock, scanline, cycle = 400, -1, 0
callbacks[1](0)
set_banks(after, 450, 193)
clock, scanline, cycle = 600, 240, 0
callbacks[2](0)

print("Synthetic rendered RGB + paired phase capture complete for frames 500 and 501")
