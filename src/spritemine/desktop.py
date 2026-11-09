"""Windows-first PySide6 static CHR explorer.

No emulator data, original SMB3 palettes or semantic sprite classification are
claimed by this interface. Optional GUI dependency: pip install -e '.[gui]'.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QAction, QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QScrollArea, QSpinBox,
    QSplitter, QToolBar, QVBoxLayout, QWidget,
)

from .chr import ATLAS_COLUMNS, TILE_BYTES, TILES_PER_BANK, export_chr
from .preview import PALETTES, preview_bank, preview_tile
from .rom import Rom, RomFormatError, load_rom

SMB3_PRG1_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"


def as_qimage(image: Image.Image) -> QImage:
    """Copy PIL RGB bytes into Qt-managed memory, avoiding dangling buffers."""
    rgb = image.convert("RGB")
    buffer = rgb.tobytes()
    return QImage(buffer, rgb.width, rgb.height, rgb.width * 3, QImage.Format_RGB888).copy()


class AtlasWidget(QWidget):
    """Pixel-perfect atlas with clickable 8x8 tile coordinates."""

    tile_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image: QImage | None = None
        self.zoom = 3
        self.selected_local: int | None = None
        self.setFixedSize(128 * self.zoom, 256 * self.zoom)

    def set_image(self, image: QImage | None) -> None:
        self.image = image
        if image is not None:
            self.setFixedSize(image.width() * self.zoom, image.height() * self.zoom)
        self.update()

    def set_zoom(self, zoom: int) -> None:
        self.zoom = zoom
        if self.image is not None:
            self.setFixedSize(self.image.width() * zoom, self.image.height() * zoom)
        self.update()

    def set_selected(self, local_index: int | None) -> None:
        self.selected_local = local_index
        self.update()

    def tile_at(self, x: int, y: int) -> int | None:
        if self.image is None or x < 0 or y < 0:
            return None
        if x >= self.image.width() * self.zoom or y >= self.image.height() * self.zoom:
            return None
        col = x // (8 * self.zoom)
        row = y // (8 * self.zoom)
        return row * ATLAS_COLUMNS + col

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            position = event.position()
            selected = self.tile_at(int(position.x()), int(position.y()))
            if selected is not None:
                self.tile_selected.emit(selected)
                event.accept()
                return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20232a"))
        if self.image is not None:
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            painter.drawImage(
                QRect(0, 0, self.image.width() * self.zoom, self.image.height() * self.zoom),
                self.image,
            )
            if self.selected_local is not None:
                cell = 8 * self.zoom
                col, row = self.selected_local % ATLAS_COLUMNS, self.selected_local // ATLAS_COLUMNS
                painter.setPen(QPen(QColor("#ffdb58"), 2))
                painter.drawRect(QRect(col * cell, row * cell, cell - 1, cell - 1))
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.rom: Rom | None = None
        self.source_label = ""
        self.selected_tile: int | None = None
        self.setWindowTitle("SpriteMine — SMB3 Static CHR Explorer")
        self.resize(1100, 900)

        toolbar = QToolBar("ROM and export", self)
        self.addToolBar(toolbar)
        open_action = QAction("Open ROM / ZIP", self)
        open_action.triggered.connect(self._choose_rom)
        toolbar.addAction(open_action)

        self.export_tile_action = QAction("Export tile (grayscale)", self)
        self.export_bank_action = QAction("Export bank (grayscale)", self)
        self.export_all_action = QAction("Export all banks (grayscale)", self)
        for action in (self.export_tile_action, self.export_bank_action, self.export_all_action):
            action.setEnabled(False)
            toolbar.addAction(action)
        self.export_tile_action.triggered.connect(lambda: self._export("tile"))
        self.export_bank_action.triggered.connect(lambda: self._export("bank"))
        self.export_all_action.triggered.connect(lambda: self._export("all"))

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.identity_label = QLabel("Open a legally obtained SMB3 PRG1 ROM or ZIP to begin.")
        self.identity_label.setWordWrap(True)
        layout.addWidget(self.identity_label)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("8 KiB CHR bank:"))
        self.bank_spin = QSpinBox()
        self.bank_spin.setRange(0, 0)
        self.bank_spin.setEnabled(False)
        controls.addWidget(self.bank_spin)
        controls.addWidget(QLabel("Zoom:"))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(1, 8)
        self.zoom_spin.setValue(3)
        controls.addWidget(self.zoom_spin)
        controls.addWidget(QLabel("Preview palette:"))
        self.palette_combo = QComboBox()
        for key, (label, _) in PALETTES.items():
            self.palette_combo.addItem(label, key)
        controls.addWidget(self.palette_combo)
        controls.addStretch()
        layout.addLayout(controls)
        palette_warning = QLabel(
            "Preview palettes are synthetic. Raw CHR data contains no authentic game palette. "
            "PNG exports use grayscale only."
        )
        palette_warning.setWordWrap(True)
        layout.addWidget(palette_warning)

        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, stretch=1)

        atlas_group = QGroupBox("CHR bank — select a tile")
        atlas_layout = QVBoxLayout(atlas_group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        self.atlas = AtlasWidget()
        scroll.setWidget(self.atlas)
        atlas_layout.addWidget(scroll)
        split.addWidget(atlas_group)

        inspector = QWidget()
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.addWidget(QLabel("Selected tile (pixel-perfect 20×):"))
        self.tile_preview = QLabel("No tile selected")
        self.tile_preview.setAlignment(Qt.AlignCenter)
        self.tile_preview.setMinimumHeight(170)
        inspector_layout.addWidget(self.tile_preview)

        inspector_layout.addWidget(QLabel("Tile provenance:"))
        self.tile_details = QPlainTextEdit()
        self.tile_details.setReadOnly(True)
        self.tile_details.setMaximumHeight(140)
        inspector_layout.addWidget(self.tile_details)

        inspector_layout.addWidget(QLabel("ROM metadata:"))
        self.rom_details = QPlainTextEdit()
        self.rom_details.setReadOnly(True)
        inspector_layout.addWidget(self.rom_details, stretch=1)
        split.addWidget(inspector)
        split.setSizes([650, 450])

        self.bank_spin.valueChanged.connect(self._on_bank_changed)
        self.zoom_spin.valueChanged.connect(self.atlas.set_zoom)
        self.palette_combo.currentIndexChanged.connect(self._refresh_previews)
        self.atlas.tile_selected.connect(self._on_tile_selected)
        self.statusBar().showMessage("Ready — no ROM loaded")

    def _choose_rom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open NES ROM or ZIP", "", "NES ROMs (*.nes *.NES *.zip *.ZIP)"
        )
        if path:
            try:
                self.load_rom_path(path)
            except (OSError, RomFormatError, ValueError) as exc:
                QMessageBox.warning(self, "Unable to open ROM", str(exc))
                self.statusBar().showMessage("ROM import failed")

    def load_rom_path(self, path: str | Path) -> None:
        rom = load_rom(path)
        self.load_rom_object(rom, source_label=Path(path).name)

    def load_rom_object(self, rom: Rom, *, source_label: str = "ROM") -> None:
        """Enable synthetic fixtures in tests without requiring copyrighted bytes."""
        self.rom = rom
        self.source_label = source_label
        meta = rom.metadata
        verified = meta.rom_sha256 == SMB3_PRG1_SHA256
        identity = "Verified SMB3 US PRG1 / Revision A" if verified else "Unverified ROM — SMB3 game-specific support not established"
        self.identity_label.setText(f"{source_label} — {identity}")
        self.rom_details.setPlainText(json.dumps(meta.to_dict(), indent=2, sort_keys=True))
        self.bank_spin.blockSignals(True)
        self.bank_spin.setRange(0, max(meta.chr_banks_8k - 1, 0))
        self.bank_spin.setValue(0)
        self.bank_spin.setEnabled(bool(rom.chr))
        self.bank_spin.blockSignals(False)
        has_chr = bool(rom.chr)
        self.selected_tile = 0 if has_chr else None
        for action in (self.export_tile_action, self.export_bank_action, self.export_all_action):
            action.setEnabled(has_chr)
        self._refresh_previews()
        if has_chr:
            self.statusBar().showMessage(
                f"{meta.chr_banks_8k} CHR-ROM banks, {meta.chr_bytes // TILE_BYTES} raw tiles — {identity}"
            )
        else:
            self.statusBar().showMessage("CHR-RAM / no static CHR-ROM tiles: runtime capture required")

    def _on_bank_changed(self, bank: int) -> None:
        self.selected_tile = bank * TILES_PER_BANK
        self._refresh_previews()

    def _on_tile_selected(self, local: int) -> None:
        self.selected_tile = self.bank_spin.value() * TILES_PER_BANK + local
        self._refresh_tile()

    def _refresh_previews(self, *_args: object) -> None:
        if self.rom is None or not self.rom.chr:
            self.atlas.set_image(None)
            self.atlas.set_selected(None)
            self.tile_preview.setText("No static CHR-ROM graphics")
            self.tile_preview.setPixmap(QPixmap())
            self.tile_details.clear()
            return
        image = preview_bank(self.rom, self.bank_spin.value(), str(self.palette_combo.currentData()))
        self.atlas.set_image(as_qimage(image))
        self._refresh_tile()

    def _refresh_tile(self) -> None:
        if self.rom is None or self.selected_tile is None:
            return
        index = self.selected_tile
        palette = str(self.palette_combo.currentData())
        tile = as_qimage(preview_tile(self.rom, index, palette))
        large = tile.scaled(160, 160, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.tile_preview.setPixmap(QPixmap.fromImage(large))
        bank, local = divmod(index, TILES_PER_BANK)
        self.atlas.set_selected(local)
        chr_offset = index * TILE_BYTES
        rom_offset = self.rom.metadata.chr_rom_offset + chr_offset
        self.tile_details.setPlainText(
            f"Global tile index: {index}\n"
            f"8 KiB bank: {bank}\n"
            f"Tile within bank: {local}\n"
            f"Bank coordinates: ({local % ATLAS_COLUMNS}, {local // ATLAS_COLUMNS})\n"
            f"CHR offset: 0x{chr_offset:05X}\n"
            f"ROM offset: 0x{rom_offset:05X}\n"
            f"Source length: {TILE_BYTES} bytes\n"
            f"Evidence: raw 2bpp; palette is synthetic"
        )

    def _export(self, what: str) -> None:
        if self.rom is None or not self.rom.chr:
            return
        folder = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not folder:
            return
        try:
            options: dict[str, int] = {}
            if what == "tile":
                if self.selected_tile is None:
                    return
                options["tile"] = self.selected_tile
            elif what == "bank":
                options["bank"] = self.bank_spin.value()
            manifest = export_chr(self.rom, folder, **options)
        except (OSError, RomFormatError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Grayscale export complete: {manifest}")
        QMessageBox.information(
            self, "Export complete",
            f"PNG export and manifest saved to:\n{manifest}\n\n"
            "Existing manifest.json in that folder has been replaced. "
            "These are raw grayscale CHR previews, not authentic SMB3 sprite colors.",
        )


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
