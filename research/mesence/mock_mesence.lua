-- Synthetic MesenCE API stand-in for CI only.
-- Does not emulate an NES and must not be mistaken for real runtime validation.
local output = os.getenv("SPRITEMINE_TEST_OUTPUT")
assert(type(output) == "string" and output ~= "", "SPRITEMINE_TEST_OUTPUT is required")

local frame = 100
local end_frame_callback = nil

emu = {
    memType = { nesSpriteRam = 1, nesPaletteRam = 2, nesPpuDebug = 3 },
    eventType = { endFrame = 4 },
    getState = function()
        return {
            consoleType = "Nes",
            frameCount = frame,
            masterClock = frame * 10000,
            region = "Ntsc",
            ["ppu.control.largeSprites"] = true,
            ["ppu.scanline"] = 241,
            ["ppu.cycle"] = 0,
        }
    end,
    getRomInfo = function()
        return { fileSha1Hash = string.rep("a", 40) }
    end,
    getScriptDataFolder = function()
        return output
    end,
    getMemorySize = function(memory_type)
        if memory_type == 1 then return 256 end
        if memory_type == 2 then return 32 end
        return 0
    end,
    read = function(address, memory_type)
        if memory_type == 1 then return address % 256 end
        if memory_type == 2 then return (address * 7) % 64 end
        if memory_type == 3 then return (address * 3) % 256 end
        error("Unsupported synthetic memory type " .. tostring(memory_type))
    end,
    getScreenSize = function()
        return { width = 4, height = 3 }
    end,
    getScreenBuffer = function()
        local pixels = {}
        for index = 1, 12 do
            pixels[index] = 0x102030 + (index - 1)
        end
        return pixels
    end,
    addEventCallback = function(callback, event_type)
        assert(event_type == 4, "Expected endFrame event")
        end_frame_callback = callback
        return 42
    end,
    log = function(message)
        print(message)
    end,
    displayMessage = function(title, message)
        print(title .. ": " .. message)
    end,
}

assert(arg[1], "Path to frame probe Lua script is required")
dofile(arg[1])
assert(type(end_frame_callback) == "function", "Probe did not register endFrame")
for index = 1, 3 do
    end_frame_callback(0)
    frame = frame + 1
end
print("Synthetic two-frame Lua probe execution finished")
