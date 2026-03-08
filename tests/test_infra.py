"""
V1: インフラ疎通テスト

各サービスの API エンドポイントが到達可能かを確認する。
"""

import unittest
from urllib.error import URLError

from tests.base import BaseTestCase, OM_URL, AIRFLOW_URL


class TestInfrastructure(BaseTestCase):
    """サービス起動・API 到達性の確認 (V1)。"""

    def test_01_om_server_reachable(self):
        """OM サーバー /api/v1/system/status の全チェックが passed: True であること。"""
        resp = self.om_get("system/status")
        # レスポンス形式: {key: {passed: bool, message: str}, ...}
        self.assertIsInstance(resp, dict, f"Unexpected response type: {type(resp)}")
        failed = {k: v for k, v in resp.items() if not v.get("passed", False)}
        self.assertEqual(
            failed, {},
            f"OM health check failed for: {failed}"
        )

    def test_02_om_server_version(self):
        """OM サーバーのバージョンが取得できること。"""
        resp = self.om_get("system/version")
        self.assertIn("version", resp,
                      f"version field missing in response: {resp}")
        version = resp["version"]
        self.assertTrue(version.startswith("1."),
                        f"Unexpected version format: {version}")

    def test_03_airflow_api_reachable(self):
        """Airflow REST API /api/v1/version が 200 を返すこと。"""
        resp = self.airflow_get("version")
        self.assertIn("version", resp, f"Unexpected response: {resp}")

    def test_04_airflow_health(self):
        """Airflow scheduler が healthy であること。"""
        resp = self.airflow_get("health")
        scheduler_status = resp.get("scheduler", {}).get("status")
        self.assertEqual(scheduler_status, "healthy",
                         f"Airflow scheduler not healthy: {resp}")

    def test_05_om_config_no_pipeline_client(self):
        """
        PIPELINE_SERVICE_CLIENT_ENABLED が false であること (V2)。
        OM は Airflow を管理しない (push 型) 設定。

        確認方法: Airflow に OM-managed インジェスション DAG が存在しないこと。
        (PIPELINE_SERVICE_CLIENT_ENABLED=false の場合 OM は新規 DAG を作成しない)
        """
        resp = self.airflow_get("dags?tags=openmetadata&limit=50")
        dag_ids = [d["dag_id"] for d in resp.get("dags", [])]
        # OM が自動生成するインジェスション DAG の命名パターン
        om_managed = [
            dag_id for dag_id in dag_ids
            if dag_id.startswith("openmetadata_metadata_")
            or dag_id.startswith("openmetadata_lineage_")
            or dag_id.startswith("openmetadata_usage_")
        ]
        self.assertEqual(
            om_managed, [],
            f"OM-managed ingestion DAGs exist (PIPELINE_SERVICE_CLIENT_ENABLED may be true): {om_managed}"
        )


if __name__ == "__main__":
    unittest.main()
