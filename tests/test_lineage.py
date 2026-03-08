"""
V5: リネージ登録確認テスト

register_lineage.py または Airflow Lineage Backend によって登録された
リネージエッジが OpenMetadata API から取得できることを確認する。
"""

import unittest

from tests.base import BaseTestCase, SERVICE_DB, DATABASE


# 期待するエッジ (upstream -> downstream)
EXPECTED_EDGES = [
    (f"{SERVICE_DB}.{DATABASE}.public.customers",
     f"{SERVICE_DB}.{DATABASE}.public.orders"),
    (f"{SERVICE_DB}.{DATABASE}.public.products",
     f"{SERVICE_DB}.{DATABASE}.public.orders"),
    (f"{SERVICE_DB}.{DATABASE}.public.orders",
     f"{SERVICE_DB}.{DATABASE}.analytics.monthly_revenue"),
    (f"{SERVICE_DB}.{DATABASE}.public.customers",
     f"{SERVICE_DB}.{DATABASE}.analytics.customer_segments"),
    (f"{SERVICE_DB}.{DATABASE}.public.orders",
     f"{SERVICE_DB}.{DATABASE}.analytics.customer_segments"),
]


class TestLineageEdges(BaseTestCase):
    """OM リネージエッジ登録の確認 (V5)。"""

    @classmethod
    def setUpClass(cls):
        """orders テーブルのリネージを一度だけ取得してキャッシュする。"""
        orders_fqn = f"{SERVICE_DB}.{DATABASE}.public.orders"
        try:
            entity = cls._get_table(orders_fqn)
            cls.orders_id = entity["id"]
            lineage = cls._get_lineage("table", cls.orders_id)
            cls.lineage_data = lineage
            # ノードマップ (id -> fqn) を構築
            cls.id2fqn: dict[str, str] = {}
            for node in lineage.get("nodes", []):
                cls.id2fqn[node["id"]] = node.get(
                    "fullyQualifiedName", node.get("name", "")
                )
            entity_node = lineage.get("entity", {})
            if entity_node:
                cls.id2fqn[entity_node["id"]] = entity_node.get(
                    "fullyQualifiedName", entity_node.get("name", "")
                )
        except Exception as e:
            cls.orders_id = None
            cls.lineage_data = {}
            cls.id2fqn = {}
            cls._setup_error = str(e)

    @classmethod
    def _get_table(cls, fqn: str) -> dict:
        return cls.om_get(f"tables/name/{fqn}")

    @classmethod
    def _get_lineage(cls, entity_type: str, entity_id: str,
                     upstream_depth: int = 3, downstream_depth: int = 3) -> dict:
        return cls.om_get(
            f"lineage/{entity_type}/{entity_id}"
            f"?upstreamDepth={upstream_depth}&downstreamDepth={downstream_depth}"
        )

    def _all_edges(self) -> list[tuple[str, str]]:
        """upstream + downstream エッジを (from_fqn, to_fqn) のリストで返す。"""
        edges = []
        for e in self.lineage_data.get("upstreamEdges", []):
            f = self.id2fqn.get(e.get("fromEntity", ""), "")
            t = self.id2fqn.get(e.get("toEntity", ""), "")
            if f and t:
                edges.append((f, t))
        for e in self.lineage_data.get("downstreamEdges", []):
            f = self.id2fqn.get(e.get("fromEntity", ""), "")
            t = self.id2fqn.get(e.get("toEntity", ""), "")
            if f and t:
                edges.append((f, t))
        return edges

    def test_01_orders_lineage_node_reachable(self):
        """orders テーブルのリネージ API が取得できること。"""
        if self.orders_id is None:
            self.fail(f"orders table not found: {getattr(self, '_setup_error', '')}")
        self.assertIsNotNone(self.lineage_data)

    def test_02_lineage_has_nodes(self):
        """リネージグラフに複数のノードが存在すること。"""
        nodes = self.lineage_data.get("nodes", [])
        self.assertGreater(len(nodes), 0, "No lineage nodes found for orders table")

    def test_03_customers_to_orders_edge_exists(self):
        """customers → orders のエッジが存在すること。"""
        edges = self._all_edges()
        expected = (
            f"{SERVICE_DB}.{DATABASE}.public.customers",
            f"{SERVICE_DB}.{DATABASE}.public.orders",
        )
        self.assertIn(expected, edges,
                      f"Edge {expected[0]} -> {expected[1]} not found in: {edges}")

    def test_04_products_to_orders_edge_exists(self):
        """products → orders のエッジが存在すること。"""
        edges = self._all_edges()
        expected = (
            f"{SERVICE_DB}.{DATABASE}.public.products",
            f"{SERVICE_DB}.{DATABASE}.public.orders",
        )
        self.assertIn(expected, edges,
                      f"Edge {expected[0]} -> {expected[1]} not found in: {edges}")

    def test_05_orders_to_monthly_revenue_edge_exists(self):
        """orders → monthly_revenue のエッジが存在すること。"""
        edges = self._all_edges()
        expected = (
            f"{SERVICE_DB}.{DATABASE}.public.orders",
            f"{SERVICE_DB}.{DATABASE}.analytics.monthly_revenue",
        )
        self.assertIn(expected, edges,
                      f"Edge {expected[0]} -> {expected[1]} not found in: {edges}")

    def test_06_orders_to_customer_segments_edge_exists(self):
        """orders → customer_segments のエッジが存在すること。"""
        edges = self._all_edges()
        expected = (
            f"{SERVICE_DB}.{DATABASE}.public.orders",
            f"{SERVICE_DB}.{DATABASE}.analytics.customer_segments",
        )
        self.assertIn(expected, edges,
                      f"Edge {expected[0]} -> {expected[1]} not found in: {edges}")

    def test_07_customers_lineage_reachable(self):
        """customers テーブルからもリネージが取得できること。"""
        customers_fqn = f"{SERVICE_DB}.{DATABASE}.public.customers"
        entity = self.om_get(f"tables/name/{customers_fqn}")
        lineage = self._get_lineage("table", entity["id"])
        self.assertIn("entity", lineage)

    def test_08_all_5_nodes_in_lineage_graph(self):
        """リネージグラフに全5テーブルノードが含まれること。"""
        fqn_set = set(self.id2fqn.values())
        expected_fqns = {
            f"{SERVICE_DB}.{DATABASE}.public.customers",
            f"{SERVICE_DB}.{DATABASE}.public.products",
            f"{SERVICE_DB}.{DATABASE}.public.orders",
            f"{SERVICE_DB}.{DATABASE}.analytics.monthly_revenue",
            f"{SERVICE_DB}.{DATABASE}.analytics.customer_segments",
        }
        missing = expected_fqns - fqn_set
        self.assertEqual(missing, set(),
                         f"Missing nodes in lineage graph: {missing}")


if __name__ == "__main__":
    unittest.main()
