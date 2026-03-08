"""
V4: カタログ登録確認テスト

register_catalog.py で登録したエンティティが
OpenMetadata API から取得できることを確認する。
"""

import unittest

from tests.base import BaseTestCase, SERVICE_DB, SERVICE_PIPELINE, DATABASE, SCHEMAS, TABLES


class TestCatalogEntities(BaseTestCase):
    """OM カタログ登録の確認 (V4)。"""

    # ── サービス ──────────────────────────────────────────────────

    def test_01_database_service_exists(self):
        """DatabaseService 'sample_db_service' が登録されていること。"""
        entity = self.om_entity_by_fqn("services/databaseServices", SERVICE_DB)
        self.assertIsNotNone(entity, f"DatabaseService '{SERVICE_DB}' not found")
        self.assertEqual(entity.get("name"), SERVICE_DB)

    def test_02_pipeline_service_exists(self):
        """PipelineService 'local_airflow' が登録されていること。"""
        entity = self.om_entity_by_fqn("services/pipelineServices", SERVICE_PIPELINE)
        self.assertIsNotNone(entity, f"PipelineService '{SERVICE_PIPELINE}' not found")
        self.assertEqual(entity.get("name"), SERVICE_PIPELINE)

    def test_03_pipeline_service_type_is_airflow(self):
        """PipelineService の serviceType が 'Airflow' であること。"""
        entity = self.om_entity_by_fqn("services/pipelineServices", SERVICE_PIPELINE)
        self.assertIsNotNone(entity)
        self.assertEqual(entity.get("serviceType"), "Airflow")

    # ── データベース・スキーマ ─────────────────────────────────────

    def test_04_database_exists(self):
        """Database 'sample_db' が登録されていること。"""
        fqn = f"{SERVICE_DB}.{DATABASE}"
        entity = self.om_entity_by_fqn("databases", fqn)
        self.assertIsNotNone(entity, f"Database '{fqn}' not found")

    def test_05_schema_public_exists(self):
        """Schema 'public' が登録されていること。"""
        fqn = f"{SERVICE_DB}.{DATABASE}.public"
        entity = self.om_entity_by_fqn("databaseSchemas", fqn)
        self.assertIsNotNone(entity, f"Schema '{fqn}' not found")

    def test_06_schema_analytics_exists(self):
        """Schema 'analytics' が登録されていること。"""
        fqn = f"{SERVICE_DB}.{DATABASE}.analytics"
        entity = self.om_entity_by_fqn("databaseSchemas", fqn)
        self.assertIsNotNone(entity, f"Schema '{fqn}' not found")

    # ── テーブル ──────────────────────────────────────────────────

    def test_07_all_tables_exist(self):
        """全5テーブルが登録されていること。"""
        missing = []
        for fqn in TABLES:
            entity = self.om_entity_by_fqn("tables", fqn)
            if entity is None:
                missing.append(fqn)
        self.assertEqual(missing, [], f"Missing tables: {missing}")

    def test_08_customers_has_columns(self):
        """customers テーブルにカラムが定義されていること。"""
        fqn = f"{SERVICE_DB}.{DATABASE}.public.customers"
        entity = self.om_entity_by_fqn("tables", fqn, "columns")
        self.assertIsNotNone(entity)
        columns = entity.get("columns", [])
        self.assertGreater(len(columns), 0,
                           "customers table has no columns defined")
        col_names = [c["name"] for c in columns]
        self.assertIn("customer_id", col_names,
                      f"customer_id not in columns: {col_names}")

    def test_09_orders_has_columns(self):
        """orders テーブルに必須カラムが含まれること。"""
        fqn = f"{SERVICE_DB}.{DATABASE}.public.orders"
        entity = self.om_entity_by_fqn("tables", fqn, "columns")
        self.assertIsNotNone(entity)
        col_names = [c["name"] for c in entity.get("columns", [])]
        for required in ("order_id", "customer_id", "total_amount"):
            self.assertIn(required, col_names,
                          f"Required column '{required}' missing in orders: {col_names}")

    def test_10_table_count(self):
        """OM に登録されているテーブル数が5以上であること。"""
        resp = self.om_get(f"tables?limit=50&database={SERVICE_DB}.{DATABASE}")
        count = resp.get("paging", {}).get("total", 0)
        self.assertGreaterEqual(count, 5,
                                f"Expected at least 5 tables, got {count}")

    def om_entity_by_fqn(self, entity_type: str, fqn: str, fields: str = "") -> dict | None:
        """フィールド指定付きで FQN からエンティティを取得する。"""
        params = f"?fields={fields}" if fields else ""
        try:
            return self.om_get(f"{entity_type}/name/{fqn}{params}")
        except Exception as e:
            if "404" in str(e) or "HTTP Error 404" in str(e):
                return None
            raise


if __name__ == "__main__":
    unittest.main()
