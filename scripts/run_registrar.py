#!/usr/bin/env python3
"""
registrar エントリポイント

OM サーバーが起動するまで待ち、全登録スクリプトを順に実行する。
REGISTRAR_INTERVAL 秒ごとに繰り返す (0 なら1回だけ実行して終了)。
"""
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

HOST     = os.environ.get("OM_HOST", "http://openmetadata-server:8585")
INTERVAL = int(os.environ.get("REGISTRAR_INTERVAL", "60"))
HEALTH   = f"{HOST}/api/v1/system/config/auth"


def wait_for_om(timeout: int = 300, interval: int = 10) -> None:
    print(f"Waiting for OpenMetadata at {HOST} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(HEALTH, timeout=5):
                print("OpenMetadata is ready.", flush=True)
                return
        except (URLError, HTTPError):
            time.sleep(interval)
    print("ERROR: OpenMetadata did not become ready in time.", flush=True)
    sys.exit(1)


def run_once() -> None:
    import register_catalog
    import register_lineage
    import register_sample_dq
    import importlib

    print("\n" + "=" * 50, flush=True)
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] Starting registration", flush=True)

    for mod, label in [
        (register_catalog,   "catalog"),
        (register_lineage,   "lineage"),
        (register_sample_dq, "sample_dq"),
    ]:
        print(f"\n--- {label} ---", flush=True)
        try:
            importlib.reload(mod)
            mod.main(HOST)
        except Exception as e:
            print(f"  ERROR in {label}: {e}", flush=True)

    print(f"\n[{time.strftime('%Y-%m-%dT%H:%M:%S')}] Registration complete", flush=True)


if __name__ == "__main__":
    wait_for_om()
    run_once()
    if INTERVAL > 0:
        while True:
            time.sleep(INTERVAL)
            run_once()
