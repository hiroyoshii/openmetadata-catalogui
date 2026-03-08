"""
V6: Airflow Lineage Backend エンドツーエンド push テスト

sample_etl DAG をトリガーし、完了後に OpenMetadata のリネージが
更新されていることを確認する。

注意: このテストは実際に Airflow DAG を実行するため時間がかかる (最大 120 秒)。
     統合テストとして分類し、通常の単体テストとは別に実行することを推奨。
"""

import time
import unittest
from urllib.parse import quote

from tests.base import BaseTestCase, SERVICE_DB, DATABASE, SAMPLE_DAG_ID, wait_dag_run


class TestAirflowLineagePush(BaseTestCase):
    """Airflow DAG 実行 → OM Lineage push の End-to-End 確認 (V6)。"""

    RUN_TIMEOUT = 120  # DAG 完了待ちタイムアウト [秒]

    @classmethod
    def setUpClass(cls):
        """DAG をトリガーして完了を待つ。"""
        cls.dag_state = "not_triggered"
        cls.run_id = None

        try:
            # DAG が存在するか事前確認
            dag_info = cls.airflow_get(f"dags/{SAMPLE_DAG_ID}")
            if dag_info.get("is_paused", True):
                # paused なら unpause する (Airflow REST API PATCH)
                import json
                from urllib.request import Request, urlopen
                from base64 import b64encode
                from tests.base import AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PASS
                creds = b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
                url = f"{AIRFLOW_URL}/api/v1/dags/{SAMPLE_DAG_ID}"
                data = json.dumps({"is_paused": False}).encode()
                req = Request(url, data=data, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {creds}",
                }, method="PATCH")
                with urlopen(req) as resp:
                    resp.read()

            # DAG トリガー
            resp = cls.airflow_post(
                f"dags/{SAMPLE_DAG_ID}/dagRuns",
                {"conf": {}}
            )
            cls.run_id = resp["dag_run_id"]
            cls.dag_state = wait_dag_run(
                SAMPLE_DAG_ID, cls.run_id, timeout=cls.RUN_TIMEOUT
            )

        except Exception as e:
            cls._setup_error = str(e)

    def _skip_if_not_triggered(self):
        if self.run_id is None:
            self.skipTest(f"DAG trigger failed: {getattr(self, '_setup_error', 'unknown')}")

    def test_01_dag_exists_in_airflow(self):
        """sample_etl DAG が Airflow に存在すること。"""
        dag_info = self.airflow_get(f"dags/{SAMPLE_DAG_ID}")
        self.assertEqual(dag_info.get("dag_id"), SAMPLE_DAG_ID)

    def test_02_dag_run_succeeded(self):
        """sample_etl DAG の実行が success で完了すること。"""
        self._skip_if_not_triggered()
        self.assertEqual(
            self.dag_state, "success",
            f"DAG run state is '{self.dag_state}' (run_id={self.run_id}). "
            f"Check Airflow logs at http://localhost:8080"
        )

    def test_03_all_tasks_succeeded(self):
        """全タスク (build_orders, build_monthly_revenue, build_customer_segments) が成功すること。"""
        self._skip_if_not_triggered()
        encoded = quote(self.run_id, safe="")
        resp = self.airflow_get(
            f"dags/{SAMPLE_DAG_ID}/dagRuns/{encoded}/taskInstances"
        )
        task_states = {
            t["task_id"]: t["state"]
            for t in resp.get("task_instances", [])
        }
        for task_id in ("build_orders", "build_monthly_revenue", "build_customer_segments"):
            self.assertEqual(
                task_states.get(task_id), "success",
                f"Task '{task_id}' state is '{task_states.get(task_id)}'"
            )

    def test_04_lineage_backend_log_present(self):
        """タスクログに 'Executing OpenMetadata Lineage Backend...' が含まれること。"""
        self._skip_if_not_triggered()
        if self.dag_state != "success":
            self.skipTest("DAG did not succeed, skipping log check")
        from urllib.request import Request, urlopen
        from base64 import b64encode
        from tests.base import AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PASS
        creds = b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
        encoded = quote(self.run_id, safe="")
        url = (
            f"{AIRFLOW_URL}/api/v1/dags/{SAMPLE_DAG_ID}/dagRuns/{encoded}"
            f"/taskInstances/build_orders/logs/1"
        )
        req = Request(url, headers={
            "Accept": "text/plain",
            "Authorization": f"Basic {creds}",
        })
        with urlopen(req, timeout=15) as resp:
            log_text = resp.read().decode()
        self.assertIn(
            "Executing OpenMetadata Lineage Backend",
            log_text,
            "Lineage Backend was not executed for build_orders task"
        )

    def test_05_lineage_pushed_to_om_after_dag(self):
        """DAG 実行後に OM のリネージグラフが存在すること。"""
        self._skip_if_not_triggered()
        if self.dag_state != "success":
            self.skipTest("DAG did not succeed, skipping OM lineage check")

        orders_fqn = f"{SERVICE_DB}.{DATABASE}.public.orders"
        entity = self.om_get(f"tables/name/{orders_fqn}")
        lineage = self.om_get(
            f"lineage/table/{entity['id']}?upstreamDepth=2&downstreamDepth=2"
        )
        nodes = lineage.get("nodes", [])
        self.assertGreater(
            len(nodes), 0,
            "No lineage nodes found for orders after DAG execution"
        )

    def test_06_pipeline_entity_created_in_om(self):
        """Airflow Lineage Backend が PipelineService と Pipeline エンティティを作成すること。"""
        self._skip_if_not_triggered()
        if self.dag_state != "success":
            self.skipTest("DAG did not succeed")
        # PipelineService が存在するか確認
        from tests.base import SERVICE_PIPELINE
        entity = self.om_entity_by_fqn("services/pipelineServices", SERVICE_PIPELINE)
        self.assertIsNotNone(
            entity,
            f"PipelineService '{SERVICE_PIPELINE}' not found after DAG run"
        )


if __name__ == "__main__":
    unittest.main()
