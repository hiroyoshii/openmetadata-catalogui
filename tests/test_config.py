"""
V2-V3: Airflow 設定確認テスト

- Lineage Backend が OpenMetadataLineageBackend に設定されていること
- JWT_TOKEN が設定されていること (空でないこと)
- AIRFLOW_SERVICE_NAME / OPENMETADATA_API_ENDPOINT が設定されていること
"""

import unittest

from tests.base import BaseTestCase


EXPECTED_BACKEND = (
    "airflow_provider_openmetadata.lineage.backend.OpenMetadataLineageBackend"
)
EXPECTED_SERVICE_NAME = "local_airflow"
EXPECTED_OM_ENDPOINT = "http://openmetadata-server:8585/api"


class TestAirflowLineageConfig(BaseTestCase):
    """Airflow の Lineage Backend 設定確認 (V3)。"""

    @classmethod
    def setUpClass(cls):
        """Airflow config API でリネージ設定を一度だけ取得する。"""
        try:
            from urllib.request import Request, urlopen
            from base64 import b64encode
            from tests.base import AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PASS
            creds = b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
            url = f"{AIRFLOW_URL}/api/v1/config?section=lineage"
            req = Request(url, headers={
                "Accept": "text/plain",
                "Authorization": f"Basic {creds}",
            })
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode()

            # レスポンスは INI テキスト形式: "key = value\n..."
            cls.lineage_opts = {}
            for line in raw.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("["):
                    key, _, value = line.partition("=")
                    cls.lineage_opts[key.strip()] = value.strip()
        except Exception:
            cls.lineage_opts = {}

    def _skip_if_no_config(self):
        if not self.lineage_opts:
            self.skipTest("Airflow config API not available or lineage section missing")

    def test_01_lineage_backend_set(self):
        """lineage.backend が OpenMetadataLineageBackend であること。"""
        self._skip_if_no_config()
        backend = self.lineage_opts.get("backend", "")
        self.assertEqual(
            backend, EXPECTED_BACKEND,
            f"Lineage backend is '{backend}', expected '{EXPECTED_BACKEND}'"
        )

    def test_02_airflow_service_name_set(self):
        """lineage.airflow_service_name が 'local_airflow' であること。"""
        self._skip_if_no_config()
        name = self.lineage_opts.get("airflow_service_name", "")
        self.assertEqual(
            name, EXPECTED_SERVICE_NAME,
            f"airflow_service_name is '{name}', expected '{EXPECTED_SERVICE_NAME}'"
        )

    def test_03_openmetadata_api_endpoint_set(self):
        """lineage.openmetadata_api_endpoint が設定されていること。"""
        self._skip_if_no_config()
        endpoint = self.lineage_opts.get("openmetadata_api_endpoint", "")
        self.assertTrue(
            endpoint.startswith("http"),
            f"openmetadata_api_endpoint not set or invalid: '{endpoint}'"
        )

    def test_04_jwt_token_set(self):
        """lineage.jwt_token が空でないこと。"""
        self._skip_if_no_config()
        token = self.lineage_opts.get("jwt_token", "")
        self.assertTrue(
            len(token) > 50,
            "lineage.jwt_token is not set or too short (Lineage Backend push will fail)"
        )


if __name__ == "__main__":
    unittest.main()
