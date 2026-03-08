"""
サンプル ETL DAG: inlets/outlets による Lineage 自動 push

概要:
  - Airflow OpenMetadata Lineage Backend が有効な場合、
    @task に inlets/outlets を定義するだけで DAG 実行時に
    自動で OpenMetadata API へリネージが push される。
  - このファイルは ./dags/ に配置し、ingestion コンテナの
    /opt/airflow/dags/custom/ にマウントされる。

リネージ構造:
  customers + products ──→ orders ──→ monthly_revenue
  customers + orders   ──→ customer_segments

inlets/outlets フォーマット (OpenMetadata Lineage Backend 用):
  OM Lineage Backend は airflow.lineage.entities.Table を非サポート。
  代わりに {"tables": ["<FQN>"]} 形式の dict を使用する。
  FQN 形式: service.database.schema.table

アクセス:
  Airflow UI : http://localhost:8080  (admin / admin)
  OM Lineage : http://localhost:8585 → Explore → orders → Lineage タブ
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task


# ── OpenMetadata FQN 定義 ──────────────────────────────────────────
# FQN 形式: service.database.schema.table
# register_catalog.py で登録した名前と一致させる

def _tables(*fqns: str) -> list[dict]:
    """OM Lineage Backend が期待する {"tables": [...]} 形式を返す。"""
    return [{"tables": list(fqns)}]


SERVICE = "sample_db_service"
DATABASE = "sample_db"

CUSTOMERS         = f"{SERVICE}.{DATABASE}.public.customers"
PRODUCTS          = f"{SERVICE}.{DATABASE}.public.products"
ORDERS            = f"{SERVICE}.{DATABASE}.public.orders"
MONTHLY_REVENUE   = f"{SERVICE}.{DATABASE}.analytics.monthly_revenue"
CUSTOMER_SEGMENTS = f"{SERVICE}.{DATABASE}.analytics.customer_segments"


# ── DAG 定義 ────────────────────────────────────────────────────

default_args = {
    "owner": "data-team",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="sample_etl",
    description="サンプル ETL: inlets/outlets で OM Lineage を自動 push",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["sample", "lineage-demo"],
)
def sample_etl():

    @task(
        task_id="build_orders",
        inlets=_tables(CUSTOMERS, PRODUCTS),
        outlets=_tables(ORDERS),
    )
    def build_orders(**context):
        """
        customers + products を結合して orders を生成するダミータスク。
        inlets: customers, products → outlets: orders
        """
        print("[build_orders] customers + products → orders (demo)")

    @task(
        task_id="build_monthly_revenue",
        inlets=_tables(ORDERS),
        outlets=_tables(MONTHLY_REVENUE),
    )
    def build_monthly_revenue(**context):
        """
        orders を月次集計して monthly_revenue を更新するダミータスク。
        inlets: orders → outlets: monthly_revenue
        """
        print("[build_monthly_revenue] orders → monthly_revenue (demo)")

    @task(
        task_id="build_customer_segments",
        inlets=_tables(CUSTOMERS, ORDERS),
        outlets=_tables(CUSTOMER_SEGMENTS),
    )
    def build_customer_segments(**context):
        """
        customers + orders から顧客セグメントを生成するダミータスク。
        inlets: customers, orders → outlets: customer_segments
        """
        print("[build_customer_segments] customers + orders → customer_segments (demo)")

    # タスク依存関係
    t_orders   = build_orders()
    t_revenue  = build_monthly_revenue()
    t_segments = build_customer_segments()

    t_orders >> [t_revenue, t_segments]


sample_etl()
