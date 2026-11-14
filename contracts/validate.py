"""Validate a JSON file against a contract schema.

    python contracts/validate.py run_result fixtures/run_result.drone.json
"""
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

HERE = Path(__file__).parent

def validate(schema_name: str, data) -> list[str]:
    schema = json.loads((HERE / f"{schema_name}.schema.json").read_text())
    v = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in v.iter_errors(data)]

if __name__ == "__main__":
    name, path = sys.argv[1], sys.argv[2]
    errs = validate(name, json.loads(Path(path).read_text()))
    print("OK" if not errs else "\n".join(errs))
    sys.exit(1 if errs else 0)
