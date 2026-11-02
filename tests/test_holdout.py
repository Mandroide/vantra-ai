"""El conjunto de evaluación con frases nuevas está bien formado y su evaluación DEMO es reproducible."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_holdout_bien_formado():
    cases = json.loads((ROOT / "data/holdout_scenarios.json").read_text(encoding="utf-8"))
    assert len(cases) == 102
    assert {c["register"] for c in cases} == {"formal", "coloquial", "errores_stt"}
    assert len({c["id"] for c in cases}) == len(cases)
    assert all(c["rubric"] for c in cases)


def test_holdout_demo_es_determinista(tmp_path):
    env = {"VANTRA_DB_PATH": str(tmp_path / "t.sqlite3"), "PATH": ""}
    cmd = [sys.executable, "scripts/run_holdout_evaluation.py"]
    runs = []
    for _ in range(2):
        subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, env={**__import__("os").environ, **env})
        s = json.loads((ROOT / "results/holdout_demo_summary.json").read_text(encoding="utf-8"))
        runs.append((s["global"]["exactitud_pct"], s["failed_ids"]))
    assert runs[0] == runs[1]


def test_holdout_v2_congelado_no_cambio():
    from scripts.verify_frozen_holdout import verify_frozen_holdout

    status, actual, expected = verify_frozen_holdout()
    assert status in ("original", "crlf"), (
        "El held-out v2 congelado NO coincide con la evidencia: "
        f"SHA256={actual}, esperado={expected}. "
        "Solo se admite conversión LF/CRLF; restaure el JSON desde el ZIP original."
    )
