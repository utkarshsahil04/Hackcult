"""Set up whatever is missing, then run the API and web app together: python dev.py"""

import argparse
import getpass
import hashlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API, BACKEND, FRONTEND = ROOT / "api", ROOT / "backend", ROOT / "frontend"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
ENV_FILE = ROOT / ".env"
API_PORT, WEB_PORT = 8000, 3000
TORCH_INDEX = "https://download.pytorch.org/whl/"


def run(*cmd: object, cwd: Path = ROOT, check: bool = True) -> None:
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=check)


def env_value(path: Path, key: str) -> str:
    """The value of key in a .env file, or "" if the file or the value is missing."""
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return value.strip().strip("'\"")
    return ""


def set_env_value(path: Path, key: str, value: str) -> None:
    """Set key in a .env file and leave every other line as it is."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    entry = f"{key}={value}"
    for i, line in enumerate(lines):
        if line.partition("=")[0].strip() == key:
            lines[i] = entry
            break
    else:
        lines.append(entry)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_env() -> None:
    if not ENV_FILE.exists():
        shutil.copyfile(ROOT / ".env.example", ENV_FILE)
    key = "GEMINI_API_KEY"
    if os.environ.get(key) or env_value(ENV_FILE, key) or env_value(API / ".env", key):
        return
    if not sys.stdin.isatty():
        sys.exit(f"Set {key} in {ENV_FILE}, then run this again.")
    value = getpass.getpass(f"Paste your {key} (input is hidden): ").strip()
    if not value:
        sys.exit(f"{key} is required. Set it in {ENV_FILE}, then run this again.")
    set_env_value(ENV_FILE, key, value)


def fingerprint(*files: Path) -> str:
    return hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()


def install_python() -> None:
    if not VENV_PY.exists():
        if sys.version_info[:2] != (3, 12):
            sys.exit("Python 3.12 is required. Install it, then run: py -3.12 dev.py")
        run(sys.executable, "-m", "venv", ROOT / ".venv")
    stamp = ROOT / ".venv" / ".dev-setup"
    wanted = fingerprint(API / "requirements.txt", ROOT / "ml" / "pyproject.toml")
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == wanted:
        return
    has_pip = subprocess.run([str(VENV_PY), "-m", "pip", "--version"], capture_output=True, check=False)
    if has_pip.returncode != 0:  # environments created with uv have no pip
        run(VENV_PY, "-m", "ensurepip", "--upgrade")
    run(VENV_PY, "-m", "pip", "install", "-r", API / "requirements.txt", "-e", ROOT / "ml")
    stamp.write_text(wanted, encoding="utf-8")


def install_recognition() -> None:
    index = TORCH_INDEX + ("cu124" if shutil.which("nvidia-smi") else "cpu")
    run(VENV_PY, "-m", "pip", "install", "--index-url", index, "torch==2.5.1")
    run(VENV_PY, "-m", "pip", "install", "-e", f"{ROOT / 'ml'}[gpu]")


def install_frontend(pnpm: str) -> None:
    stamp = FRONTEND / "node_modules" / ".dev-setup"
    wanted = fingerprint(FRONTEND / "pnpm-lock.yaml")
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == wanted:
        return
    run(pnpm, "install", "--frozen-lockfile", cwd=FRONTEND)
    stamp.write_text(wanted, encoding="utf-8")


def check_ports_free() -> None:
    for port in (API_PORT, WEB_PORT):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"Port {port} is already in use. Stop what's running there and try again.")


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":  # both servers spawn children, so stop the whole tree
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        os.killpg(process.pid, signal.SIGTERM)


def serve(pnpm: str) -> int:
    env = dict(os.environ)
    if not shutil.which("nvidia-smi"):
        env.setdefault("RAAHEIN_ML_DEVICE", "cpu")
        env.setdefault("RAAHEIN_ML_ALLOW_CPU", "true")
    new_group = os.name != "nt"
    servers = [
        subprocess.Popen(
            [str(VENV_PY), "-m", "uvicorn", "app.main:app", "--reload", "--port", str(API_PORT)],
            cwd=API, env=env, start_new_session=new_group,
        ),
        subprocess.Popen(
            [pnpm, "dev", "--port", str(WEB_PORT)], cwd=FRONTEND, start_new_session=new_group,
            env={**env, "NEXT_PUBLIC_API_URL": f"http://localhost:{API_PORT}"},
        ),
    ]
    print(f"\n  App  http://localhost:{WEB_PORT}\n  API  http://localhost:{API_PORT}/docs\n"
          "  Press Ctrl+C to stop.\n", flush=True)
    try:  # if either server exits, the app is broken, so stop the other too
        while all(p.poll() is None for p in servers):
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        for p in servers:
            stop(p)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recognition", action="store_true", help="install photo recognition (large download)")
    parser.add_argument("--stories", action="store_true", help="generate stories with Gemini (at least 8 minutes)")
    args = parser.parse_args()

    pnpm = shutil.which("pnpm")
    if not pnpm:
        sys.exit("pnpm is required. Install Node 22, then run: npm install -g pnpm")
    check_ports_free()
    ensure_env()
    install_python()
    if args.recognition:
        install_recognition()
    install_frontend(pnpm)
    run(VENV_PY, "-m", "app.db.seed", cwd=BACKEND)
    if args.stories:  # one failed story should not stop the app from starting
        run(VENV_PY, "-m", "scripts.generate_stories", cwd=API, check=False)
    return serve(pnpm)


if __name__ == "__main__":
    sys.exit(main())
