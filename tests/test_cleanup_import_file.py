import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.workers.tasks_import import cleanup_import_file


def test_cleanup_import_file_handles_import_run_result(tmp_path):
    file_path = tmp_path / "import.ndjson"
    file_path.write_text("{}", encoding="utf-8")

    result = {"s3_key": str(file_path), "run_id": 1}

    returned = cleanup_import_file.run(result)

    assert returned == result
    assert not Path(result["s3_key"]).exists()
