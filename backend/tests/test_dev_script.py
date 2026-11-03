import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("dev", Path(__file__).resolve().parents[2] / "dev.py")
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def test_env_value_reads_values_and_treats_blank_or_missing_as_empty(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text("# GEMINI_API_KEY=commented\nA=1\nB=\nC=\"quoted\"\nD=x=y\n", encoding="utf-8")
    assert dev.env_value(env, "A") == "1"
    assert dev.env_value(env, "B") == ""
    assert dev.env_value(env, "C") == "quoted"
    assert dev.env_value(env, "D") == "x=y"
    assert dev.env_value(env, "GEMINI_API_KEY") == ""
    assert dev.env_value(tmp_path / "missing", "A") == ""


def test_set_env_value_replaces_or_appends_and_keeps_other_lines(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text("# comment\nKEY=\nOTHER=1\n", encoding="utf-8")
    dev.set_env_value(env, "KEY", "secret")
    dev.set_env_value(env, "NEW", "2")
    assert env.read_text(encoding="utf-8") == "# comment\nKEY=secret\nOTHER=1\nNEW=2\n"
