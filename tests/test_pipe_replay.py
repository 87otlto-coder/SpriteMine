from hashlib import sha256

from research.mesence.pipe_replay import common_signature


def test_neutrality_signature_includes_controller_and_rendered_evidence(tmp_path):
    common = ("trace.tsv", "controller.tsv", "1-start-tiles.bin", "1-end-rgb.bin")
    detailed = ("events.tsv", "1-start-oam.bin", "checkpoint.mss")
    for name in common + detailed:
        (tmp_path / name).write_bytes(name.encode())
    assert common_signature(tmp_path) == {name: sha256(name.encode()).hexdigest() for name in common}
    (tmp_path / "controller.tsv").write_bytes(b"changed")
    assert common_signature(tmp_path)["controller.tsv"] == sha256(b"changed").hexdigest()
