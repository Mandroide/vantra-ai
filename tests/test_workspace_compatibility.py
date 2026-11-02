"""Regresiones de desarrollo en Windows/PyCharm con un checkout previo."""

import hashlib
import subprocess

import scripts.check_secrets as scanner
from scripts.verify_frozen_holdout import integrity_status


def test_secret_scan_ignores_paths_deleted_from_old_git_index(monkeypatch, tmp_path):
    (tmp_path / "README.md").write_text("Documento seguro", encoding="utf-8")
    # Git puede listar rutas de versiones anteriores aunque no existan en disco.
    stdout = b"src/dashboard/__init__.py\0README.md\0"
    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    monkeypatch.setattr(
        scanner.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout, b""),
    )
    assert scanner.checked_paths() == [tmp_path / "README.md"]
    assert scanner.main() == 0


def test_secret_scan_still_detects_real_sensitive_tracked_files(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("TOKEN=secret", encoding="utf-8")
    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    monkeypatch.setattr(
        scanner.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, b".env\0", b""),
    )
    assert scanner.main() == 1


def test_holdout_integrity_only_tolerates_windows_line_endings():
    original = b'{"cases":[1,2]}\n'
    expected = hashlib.sha256(original).hexdigest()
    assert integrity_status(original, expected) == "original"
    assert integrity_status(original.replace(b"\n", b"\r\n"), expected) == "crlf"
    assert integrity_status(original.replace(b"2", b"3"), expected) == "modified"
    assert integrity_status(original + b" ", expected) == "modified"


def test_frozen_holdout_cannot_be_rebaselined_by_changing_both_files(monkeypatch, tmp_path):
    import scripts.verify_frozen_holdout as verifier
    data = tmp_path / "altered.json"
    manifest = tmp_path / "holdout_v2.sha256"
    data.write_bytes(b'{"dataset": "changed"}\n')
    modified_sha = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest.write_text(modified_sha + "  data/holdout_v2_scenarios.json\n", encoding="utf-8")
    monkeypatch.setattr(verifier, "DATA", data)
    monkeypatch.setattr(verifier, "CHECKSUM", manifest)
    status, _, expected = verifier.verify_frozen_holdout()
    assert status == "checksum-modified"
    assert expected == verifier.FROZEN_SHA256
