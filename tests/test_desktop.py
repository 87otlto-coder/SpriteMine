import json
from types import SimpleNamespace

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


def test_gui_export_routes_to_provenance_extractor(app, tmp_path, monkeypatch):
    from spritemine import desktop

    window = MainWindow()
    window.load_rom_object(synthetic_rom(chr_banks=2))
    monkeypatch.setattr(
        desktop, "QFileDialog",
        SimpleNamespace(getExistingDirectory=lambda *_args: str(tmp_path)),
    )
    messages = []
    monkeypatch.setattr(
        desktop, "QMessageBox",
        SimpleNamespace(
            information=lambda *_args: messages.append("information"),
            warning=lambda *_args: messages.append("warning"),
        ),
    )
    window._on_tile_selected(17)
    window.palette_combo.setCurrentIndex(1)
    window.export_tile_action.trigger()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["provenance_type"] == "raw"
    assert manifest["palette"] == "synthetic_grayscale_not_authentic_nes_palette"
    assert len(manifest["entries"]) == 1
    assert manifest["entries"][0]["tile_index"] == 17
    assert (tmp_path / "chr_tile_0017.png").exists()

    window.export_all_action.trigger()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert len(manifest["entries"]) == 2
    assert (tmp_path / "chr_bank_00.png").exists()
    assert (tmp_path / "chr_bank_01.png").exists()
    assert messages == ["information", "information"]
    window.close()


def test_last_bank_preview_palette_switch_and_bank_export(app, tmp_path, monkeypatch):
    """Boundary bank 15 and live synthetic color must agree with raw export."""
    from spritemine import desktop

    window = MainWindow()
    window.load_rom_object(synthetic_rom(chr_banks=16), source_label="synthetic-16.nes")
    assert window.bank_spin.maximum() == 15
    window.bank_spin.setValue(15)
    assert window.selected_tile == 7680
    assert "8 KiB bank: 15" in window.tile_details.toPlainText()
    assert "ROM offset: 0x22010" in window.tile_details.toPlainText()
    first_color = window.atlas.image.pixelColor(0, 0).name()
    assert first_color == "#000000"
    window.palette_combo.setCurrentIndex(1)
    second_color = window.atlas.image.pixelColor(0, 0).name()
    assert second_color == "#0b2015"
    assert first_color != second_color
    assert "Evidence: raw 2bpp; palette is synthetic" in window.tile_details.toPlainText()

    monkeypatch.setattr(
        desktop, "QFileDialog",
        SimpleNamespace(getExistingDirectory=lambda *_args: str(tmp_path)),
    )
    feedback = []
    monkeypatch.setattr(
        desktop, "QMessageBox",
        SimpleNamespace(
            information=lambda *_args: feedback.append("exported"),
            warning=lambda *_args: feedback.append("warning"),
        ),
    )
    window.export_bank_action.trigger()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert len(manifest["entries"]) == 1
    assert manifest["entries"][0]["bank_index"] == 15
    assert (tmp_path / "chr_bank_15.png").is_file()
    assert feedback == ["exported"]
    window.close()


def test_bad_rom_import_preserves_disabled_controls(app, tmp_path, monkeypatch):
    from spritemine import desktop

    corrupted = tmp_path / "invalid.nes"
    corrupted.write_bytes(b"not a valid NES header")
    window = MainWindow()
    warnings = []
    monkeypatch.setattr(
        desktop, "QFileDialog",
        SimpleNamespace(getOpenFileName=lambda *_args: (str(corrupted), "")),
    )
    monkeypatch.setattr(
        desktop, "QMessageBox",
        SimpleNamespace(warning=lambda *_args: warnings.append("rejected")),
    )
    window._choose_rom()
    assert warnings == ["rejected"]
    assert window.rom is None
    assert not window.export_tile_action.isEnabled()
    assert not window.export_bank_action.isEnabled()
    assert not window.export_all_action.isEnabled()
    assert window.statusBar().currentMessage() == "ROM import failed"
    window.close()
