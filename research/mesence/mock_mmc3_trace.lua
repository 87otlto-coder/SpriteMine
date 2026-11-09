-- Mock only: exercises SpriteMine's bounded MMC3 register trace.
local folder = os.getenv("SPRITEMINE_CAPTURE_DIR")
assert(type(folder) == "string" and folder ~= "", "Set SPRITEMINE_CAPTURE_DIR")
local callbacks = {}
local frame, scanline, cycle = 450, -1, 0

emu = {
    callbackType = { write = 1 },
    eventType = { startFrame = 2, endFrame = 3 },
    getState = function()
        return {
            consoleType = "Nes",
            frameCount = frame,
            masterClock = frame * 30000 + (scanline + 1) * 341 + cycle,
            ["ppu.scanline"] = scanline,
            ["ppu.cycle"] = cycle,
        }
    end,
    getRomInfo = function() return {fileSha1Hash = string.rep("a", 40)} end,
    addEventCallback = function(callback, event)
        callbacks[event] = callback
        return event
    end,
    addMemoryCallback = function(callback, callbackType, startAddr, endAddr)
        assert(callbackType == 1)
        assert(startAddr == 0x8000 and endAddr == 0x9FFF)
        callbacks.mapper = callback
        return 4
    end,
    log = function(message) print(message) end,
}

assert(arg[1], "Pass a Lua script path")
dofile(arg[1])
assert(callbacks[2] and callbacks[3] and callbacks.mapper)
for _ = 1, 2 do
    scanline, cycle = -1, 0
    callbacks[2](0)
    scanline, cycle = 66, 43
    callbacks.mapper(0x8000, 0x82)
    scanline, cycle = 67, 55
    callbacks.mapper(0x8001, 0x0A)
    scanline, cycle = 240, 0
    callbacks[3](0)
    frame = frame + 1
end
print("Synthetic MMC3 register trace complete")
