"""Headless Qt smoke tests, run with QT_QPA_PLATFORM=offscreen."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from spritemine.desktop import AtlasWidget, MainWindow
from spritemine.rom import parse_nes


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    instance = existing if existing is not None else QApplication(["spritemine-tests"])
    yield instance


def synthetic_rom(chr_banks=1):
    header = b"NES\x1a" + bytes((1, chr_banks, 0x40, 0)) + bytes(8)
    return parse_nes(header + bytes(16384) + bytes(chr_banks * 8192))


def test_atlas_tile_coordinates_and_zoom(app):
    widget = AtlasWidget()
    assert widget.tile_at(0, 0) is None
    rom = synthetic_rom()
    window = MainWindow()
    window.load_rom_object(rom, source_label="synthetic.nes")
    assert window.atlas.tile_at(0, 0) == 0
    assert window.atlas.tile_at(24, 0) == 1
    assert window.atlas.tile_at(0, 24) == 16
    assert window.atlas.tile_at(127 * 3, 255 * 3) == 511
    assert window.atlas.tile_at(-1, 0) is None
    assert window.atlas.tile_at(128 * 3, 0) is None
    window.zoom_spin.setValue(4)
    assert window.atlas.tile_at(31, 0) == 0
    assert window.atlas.tile_at(32, 0) == 1
    window.close()


def test_rom_provenance_selection_and_bank_switch(app):
    window = MainWindow()
    window.load_rom_object(synthetic_rom(chr_banks=2), source_label="test-fixture")
    assert "Unverified ROM" in window.identity_label.text()
    assert window.bank_spin.maximum() == 1
    assert window.selected_tile == 0
    assert "ROM offset: 0x04010" in window.tile_details.toPlainText()
    window.bank_spin.setValue(1)
    assert window.selected_tile == 512
    assert "ROM offset: 0x06010" in window.tile_details.toPlainText()
    window._on_tile_selected(17)
    assert window.selected_tile == 529
    assert "Tile within bank: 17" in window.tile_details.toPlainText()
    assert window.export_tile_action.isEnabled()
    window.palette_combo.setCurrentIndex(1)
    assert "synthetic" in window.tile_details.toPlainText()
    window.close()


def test_chr_ram_disables_exports(app):
    window = MainWindow()
    window.load_rom_object(synthetic_rom(chr_banks=0))
    assert not window.bank_spin.isEnabled()
    assert not window.export_tile_action.isEnabled()
    assert "runtime capture required" in window.statusBar().currentMessage()
    assert window.tile_preview.text() == "No static CHR-ROM graphics"
    window.close()
