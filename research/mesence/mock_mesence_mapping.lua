-- Synthetic, phase-sensitive MesenCE API mock; never loads copyrighted data.
local output = os.getenv("SPRITEMINE_TEST_OUTPUT")
assert(type(output) == "string" and output ~= "", "SPRITEMINE_TEST_OUTPUT missing")

local frame = 300
local phase = "start"
local callbacks = {}

emu = {
    memType = { nesSpriteRam = 1, nesPpuDebug = 2 },
    eventType = { startFrame = 3, endFrame = 4 },
    getState = function()
        return {
            consoleType = "Nes", frameCount = frame,
            masterClock = frame * 29780, region = "Ntsc",
            ["ppu.control.largeSprites"] = true,
            ["ppu.scanline"] = phase == "start" and 0 or 240,
            ["ppu.cycle"] = 0,
        }
    end,
    getRomInfo = function() return { fileSha1Hash = string.rep("a", 40) } end,
    read = function(addr, memory_type)
        if memory_type == 1 then
            if addr == 40 or addr == 44 then return 161 end
            if addr == 41 then return 7 end
            if addr == 45 then return 5 end
            if addr % 4 == 0 then return 0xF8 end
            return 0
        elseif memory_type == 2 then
            if addr < 4096 then return addr % 13 == 0 and 0 or 1 end
            return phase == "start" and 1 or 0
        end
        error("Unknown synthetic memory type")
    end,
    addEventCallback = function(callback, kind)
        callbacks[kind] = callback
        return kind
    end,
    log = function(message) print(message) end,
}

assert(arg[1], "Mapping probe script path missing")
dofile(arg[1])
assert(type(callbacks[3]) == "function" and type(callbacks[4]) == "function",
    "Both frame callbacks are required")
for i = 1, 2 do
    phase = "start"
    callbacks[3](0)
    phase = "end"
    callbacks[4](0)
    frame = frame + 1
end
print("Synthetic mapping probe produced two frame phase pairs")
