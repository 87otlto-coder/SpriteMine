-- Passive SMB3 PRG1 observations. Insert before the render probe in a replay script.
do
    local first, last = 448385, 448408
    local output = assert(io.open(assert(os.getenv("SPRITEMINE_CAPTURE_DIR")) .. "/player.tsv", "wb"))
    local function stamp(event)
        local s = emu.getState()
        if s.frameCount >= first and s.frameCount <= last then
            output:write(string.format("%s\t%d\t%d\t%d\t%d\n", event, s.frameCount,
                s.masterClock, s["cpu.cycleCount"], emu.read(0xEE, emu.memType.nesDebug)))
        end
    end
    emu.addEventCallback(function() stamp("start") end, emu.eventType.startFrame)
    emu.addEventCallback(function() stamp("end") end, emu.eventType.endFrame)
    emu.addEventCallback(function() stamp("nmi") end, emu.eventType.nmi)
    emu.addEventCallback(function() stamp("irq") end, emu.eventType.irq)
    emu.addEventCallback(function() output:close() end, emu.eventType.scriptEnded)
end
