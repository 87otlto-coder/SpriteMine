-- Passive, bounded PRG1 Plains scroll-producer captures.
-- Appended to pipe_replay.lua as ONE Lua chunk; uses its local read helpers,
-- verified save-state restoration, poll counter and private output path.
-- The write callbacks are pre-write. A subsequent execute callback observes
-- completed RAM state. Never return a value from a write observer.
do
    if detailed and os.getenv("SPRITEMINE_BG_STAGING") == "1" then
        local out = assert(io.open(output .. "/background-staging.tsv", "wb"))
        out:write("sequence\tkind\tframe\tcpu_cycle\tscanline\tppu_cycle\tpoll\tdirection\tcolumn\thalf\tlast_ppu_column\tlast_attribute\tjunction_flag\ttileset\n")
        local pending, attribute_armed, count = nil, false, 0
        local function completed_producer()
            if not pending then return end
            local kind = pending
            pending = nil
            if not restored then return end
            local s = emu.getState()
            if not in_window(s) or cpu(0x070A) ~= 1 then return end -- Plains only
            local direction = cpu(0x5B) -- Scroll_LastDir: 0 right, 1 left
            assert(direction == 0 or direction == 1, "Invalid scroll direction")
            count = count + 1
            assert(count <= 256, "Background staging capture exceeded 256 producer events")
            local column = cpu(0x23 + direction) -- Scroll_ColumnR/L
            local basename = string.format("bg-%04d", count)
            save(basename .. "-pattern.bin",
                 read_region(0x0382, 54, emu.memType.nesDebug))
            save(basename .. "-attribute.bin",
                 read_region(0x03BA, 14, emu.memType.nesDebug))
            save(basename .. "-colors.bin",
                 read_region(0x0025, 54, emu.memType.nesDebug))
            save(basename .. "-tiles.bin",
                 read_region(0x6000, 864, emu.memType.nesDebug))
            out:write(table.concat({count, kind, s.frameCount, clock(s),
                s["ppu.scanline"], s["ppu.cycle"], poll, direction, column,
                cpu(0xF4), cpu(0x0381), cpu(0x03B9), cpu(0x03DF),
                cpu(0x070A)}, "\t"), "\n")
            out:flush()
        end

        -- Preserve the base replay's existing CPU-execute observer. This extra
        -- callback performs no work unless a producer-completion write armed it.
        emu.addMemoryCallback(completed_producer, emu.callbackType.exec, 0, 0xffff)

        -- Scroll_DoColumn sets Scroll_ToVRAMHi=$20 AFTER all 54 pattern bytes.
        emu.addMemoryCallback(function(_, value)
            if restored and value == 0x20 then pending = "pattern" end
        end, emu.callbackType.write, 0x0380, 0x0380)

        -- Scroll_Do_AttrColumn sets the attribute VRAM flag, computes the
        -- final address, THEN clears Scroll_UpdAttrFlag. Record after the latter.
        emu.addMemoryCallback(function(_, value)
            if restored and value == 0x23 then attribute_armed = true end
        end, emu.callbackType.write, 0x03B8, 0x03B8)
        emu.addMemoryCallback(function(_, value)
            if restored and attribute_armed and value == 0 then
                pending = "attribute"
                attribute_armed = false
            end
        end, emu.callbackType.write, 0x0707, 0x0707)

        emu.addEventCallback(function() out:close() end, emu.eventType.scriptEnded)
    end
end
