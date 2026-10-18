import json
from pathlib import Path

def test_dataset_size_and_groups():
    items=json.loads((Path(__file__).resolve().parents[1]/'data/test_scenarios.json').read_text(encoding='utf-8'))
    assert len(items)==36
    assert len({i['scenario'] for i in items})==12
    assert {'informacion','operaciones','seguridad','escalamiento'}=={i['group'] for i in items}
