"""
テスト共通基盤

環境変数で接続先を変更可能:
  OM_URL      (default: http://localhost:8585)
  AIRFLOW_URL (default: http://localhost:8080)
  AIRFLOW_USER / AIRFLOW_PASS (default: admin / admin)
"""

import json
import os
import time
import unittest
from base64 import b64encode
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 接続先設定 (env で上書き可能)
OM_URL      = os.environ.get("OM_URL",      "http://localhost:8585")
AIRFLOW_URL = os.environ.get("AIRFLOW_URL", "http://localhost:8080")
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.environ.get("AIRFLOW_PASS", "admin")

# テスト対象エンティティ定数
SERVICE_DB       = "sample_db_service"
SERVICE_PIPELINE = "local_airflow"
DATABASE         = "sample_db"
SCHEMAS          = ["public", "analytics"]
TABLES = [
    f"{SERVICE_DB}.{DATABASE}.public.customers",
    f"{SERVICE_DB}.{DATABASE}.public.products",
    f"{SERVICE_DB}.{DATABASE}.public.orders",
    f"{SERVICE_DB}.{DATABASE}.analytics.monthly_revenue",
    f"{SERVICE_DB}.{DATABASE}.analytics.customer_segments",
]
SAMPLE_DAG_ID = "sample_etl"


# ── HTTP ヘルパー ────────────────────────────────────────────────

def _om_get(path: str, timeout: int = 10) -> dict:
    """OM API への GET リクエスト。"""
    url = f"{OM_URL}/api/v1/{path.lstrip('/')}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _airflow_get(path: str, timeout: int = 10) -> dict:
    """Airflow REST API への認証付き GET リクエスト。"""
    url = f"{AIRFLOW_URL}/api/v1/{path.lstrip('/')}"
    creds = b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
    req = Request(url, headers={
        "Accept": "application/json",
        "Authorization": f"Basic {creds}",
    })
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _airflow_post(path: str, body: dict, timeout: int = 10) -> dict:
    """Airflow REST API への認証付き POST リクエスト。"""
    url = f"{AIRFLOW_URL}/api/v1/{path.lstrip('/')}"
    creds = b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Basic {creds}",
    }, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def wait_dag_run(dag_id: str, run_id: str, timeout: int = 90, interval: int = 5) -> str:
    """DAG ランが完了するまでポーリング。最終 state を返す。"""
    from urllib.parse import quote
    encoded_run_id = quote(run_id, safe="")
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = _airflow_get(f"dags/{dag_id}/dagRuns/{encoded_run_id}")
        state = run.get("state", "")
        if state in ("success", "failed"):
            return state
        time.sleep(interval)
    return "timeout"


class BaseTestCase(unittest.TestCase):
    """全テストクラスの基底クラス。"""

    @classmethod
    def om_get(cls, path: str) -> dict:
        return _om_get(path)

    @classmethod
    def om_entity_by_fqn(cls, entity_type: str, fqn: str) -> dict | None:
        try:
            return _om_get(f"{entity_type}/name/{fqn}")
        except HTTPError as e:
            if e.code == 404:
                return None
            raise

    @classmethod
    def airflow_get(cls, path: str) -> dict:
        return _airflow_get(path)

    @classmethod
    def airflow_post(cls, path: str, body: dict) -> dict:
        return _airflow_post(path, body)
