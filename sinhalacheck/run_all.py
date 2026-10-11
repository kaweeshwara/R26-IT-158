"""Start all three SinhalaCheck services and keep them running.

    python run_all.py

Module 1 loads a ~1.9GB transformer, so the first start takes a minute or two — longer
still on the very first run, when the weights are downloaded from the Hugging Face Hub.
The script waits for each service to answer before opening the UI.

Ctrl-C shuts everything down.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("SINHALACHECK_HOST", "127.0.0.1")

SERVICES = [
    ("module2", ROOT / "services" / "module2", 8002),   # fast: sklearn model
    ("module1", ROOT / "services" / "module1", 8001),   # slow: transformer
]
ENABLE_MODULE3 = os.environ.get("ENABLE_MODULE3", "").strip().lower() in {
    "1", "true", "yes", "on"
}
MODULE3_DIR = ROOT / "services" / "module3"
configured_module3_model = os.environ.get("MODULE3_MODEL_PATH", "").strip()
MODULE3_MODEL_PATH = (
    Path(configured_module3_model).expanduser()
    if configured_module3_model
    else MODULE3_DIR / "model"
)
if not MODULE3_MODEL_PATH.is_absolute():
    MODULE3_MODEL_PATH = MODULE3_DIR / MODULE3_MODEL_PATH
MODULE3_MODEL_AVAILABLE = (
    MODULE3_MODEL_PATH.is_dir() and (MODULE3_MODEL_PATH / "config.json").is_file()
)
if ENABLE_MODULE3 and MODULE3_MODEL_AVAILABLE:
    SERVICES.append(("module3", MODULE3_DIR, 8003))
SERVICES.append(("fusion", ROOT / "services" / "fusion", 8000))

procs: list[tuple[str, subprocess.Popen]] = []


def wait_for(port: int, name: str, timeout: int = 300) -> bool:
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        for pname, p in procs:
            if pname == name and p.poll() is not None:
                print(f"\n  !! {name} exited with code {p.returncode}")
                return False
        try:
            with urllib.request.urlopen(url, timeout=2):
                print(f"\r  {name}: ready on :{port}          ")
                return True
        except Exception:
            dots = (dots + 1) % 4
            print(f"\r  {name}: starting{'.' * dots}   ", end="", flush=True)
            time.sleep(1)
    print(f"\n  !! {name} did not become ready within {timeout}s")
    return False


def shutdown(*_):
    print("\nStopping services ...")
    for name, p in reversed(procs):
        if p.poll() is None:
            p.terminate()
    for name, p in procs:
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()
    print("Stopped.")
    sys.exit(0)


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("SinhalaCheck — starting services\n")
    if ENABLE_MODULE3 and not MODULE3_MODEL_AVAILABLE:
        print(
            f"  !! optional module3 not started: local model not found at "
            f"{MODULE3_MODEL_PATH}; the existing system will continue without it."
        )

    for name, cwd, port in SERVICES:
        if not (cwd / "main.py").is_file():
            print(f"  !! {name}: main.py not found in {cwd}")
            return 1
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", HOST, "--port", str(port)],
            cwd=str(cwd), env=env,
        )
        procs.append((name, p))
        if not wait_for(port, name):
            if name == "module3":
                print("  !! optional module3 failed; continuing without XLM-R.")
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait()
                procs.remove((name, p))
                continue
            print(f"\n{name} failed to start. Its error output is above.")
            shutdown()
            return 1

    url = "http://127.0.0.1:8000"
    print(f"\nAll services up. Opening {url}")
    print("  module 1 (content)          http://127.0.0.1:8001/docs")
    print("  module 2 (source/temporal)  http://127.0.0.1:8002/docs")
    if HOST != "127.0.0.1":
        print(f"  listening on                {HOST} (only expose on a trusted private network)")
    if any(name == "module3" for name, _ in procs):
        print("  module 3 (XLM-R + LIME)     http://127.0.0.1:8003/docs")
        print("  XLM-R fusion proxy          http://127.0.0.1:8000/docs")
    elif not ENABLE_MODULE3:
        print("  optional Module 3: set ENABLE_MODULE3=1 to start XLM-R + LIME")
    else:
        print("  optional Module 3 unavailable; existing services are running without it")
    print("  fusion + UI                 http://127.0.0.1:8000")
    print("\nCtrl-C to stop.\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    while True:
        time.sleep(2)
        for name, p in procs:
            if p.poll() is not None:
                print(f"!! {name} stopped unexpectedly (code {p.returncode})")
                shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
