import json

from spritemine.cli import main


def test_inspect_cli(tmp_path, capsys):
    path = tmp_path / "small.nes"
    path.write_bytes(b"NES\x1a" + bytes((1, 1, 0x40, 0)) + bytes(8) + bytes(16384 + 8192))
    assert main(["inspect", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["mapper"] == 4


def test_cli_error(tmp_path, capsys):
    assert main(["inspect", str(tmp_path / "missing.nes")]) == 2
    assert "SpriteMine:" in capsys.readouterr().err
