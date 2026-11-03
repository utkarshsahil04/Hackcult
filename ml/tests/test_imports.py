import subprocess
import sys


def test_live_recognition_path_does_not_load_faiss() -> None:
    # A fresh process, since other tests may already have imported faiss.
    code = (
        "import sys; import raahein_ml.dataset_pipeline; "
        "sys.exit('faiss' in sys.modules)"
    )
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
