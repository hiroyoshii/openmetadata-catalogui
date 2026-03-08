"""
System Catalog + Data Catalog 初期登録スクリプト

登録内容:
  [System Catalog]
    - DatabaseService : sample_db_service
    - PipelineService : local_airflow

  [Data Catalog]
    - Database        : sample_db
    - Schema          : public, analytics
    - Tables          : customers, products, orders, monthly_revenue, customer_segments
      (カラム定義・説明・タグ付け含む)

使用方法:
    python scripts/register_catalog.py [--host http://localhost:8585] [--user admin] [--pass admin]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers.om_client import OMClient


# ── テーブル定義 ───────────────────────────────────────────────

def _col(name: str, data_type: str, description: str,
         nullable: bool = True, tags: list | None = None) -> dict:
    c: dict = {
        "name": name,
        "dataType": data_type,
        "description": description,
        "constraint": "NULL" if nullable else "NOT_NULL",
    }
    if data_type.upper() in ("VARCHAR", "CHAR", "BINARY", "VARBINARY"):
        c["dataLength"] = 255
    if tags:
        c["tags"] = [{"tagFQN": t} for t in tags]
    return c


TABLE_DEFS = {
    "public.customers": {
        "description": "顧客マスタ。CRMシステムから日次同期。",
        "tableType": "Regular",
        "columns": [
            _col("customer_id", "INT",       "顧客ID (自動採番)",                          nullable=False),
            _col("name",        "VARCHAR",   "顧客名 (個人情報)",                          nullable=False, tags=["PII.Sensitive"]),
            _col("email",       "VARCHAR",   "メールアドレス (個人情報・ユニーク制約あり)",  nullable=False, tags=["PII.Sensitive"]),
            _col("country",     "VARCHAR",   "国コード (ISO 3166-1 alpha-2)",              nullable=False),
            _col("tier",        "VARCHAR",   "顧客ランク: standard / premium / enterprise", nullable=False),
            _col("created_at",  "TIMESTAMP", "レコード作成日時",                           nullable=False),
            _col("updated_at",  "TIMESTAMP", "レコード更新日時",                           nullable=False),
        ],
    },
    "public.products": {
        "description": "商品マスタ。ECシステムと同期。",
        "tableType": "Regular",
        "columns": [
            _col("product_id",  "INT",       "商品ID (自動採番)",              nullable=False),
            _col("sku",         "VARCHAR",   "商品コード (Stock Keeping Unit)", nullable=False),
            _col("name",        "VARCHAR",   "商品名",                          nullable=False),
            _col("category",    "VARCHAR",   "商品カテゴリ",                    nullable=False),
            _col("price",       "NUMERIC",   "販売価格 (税抜・円)",              nullable=False),
            _col("stock_qty",   "INT",       "在庫数量",                        nullable=False),
            _col("is_active",   "BOOLEAN",   "販売中フラグ",                    nullable=False),
            _col("created_at",  "TIMESTAMP", "レコード作成日時",                nullable=False),
        ],
    },
    "public.orders": {
        "description": "注文履歴。customers / products を親テーブルとする (Lineage確認用)。",
        "tableType": "Regular",
        "columns": [
            _col("order_id",     "INT",       "注文ID (自動採番)",                             nullable=False),
            _col("customer_id",  "INT",       "顧客ID (public.customers への外部キー)",         nullable=False),
            _col("product_id",   "INT",       "商品ID (public.products への外部キー)",          nullable=False),
            _col("quantity",     "INT",       "注文数量",                                       nullable=False),
            _col("unit_price",   "NUMERIC",   "単価",                                           nullable=False),
            _col("total_amount", "NUMERIC",   "合計金額 (quantity × unit_price の計算列)",      nullable=True),
            _col("status",       "VARCHAR",   "注文ステータス: pending/paid/shipped/delivered/cancelled", nullable=False),
            _col("ordered_at",   "TIMESTAMP", "注文日時",                                       nullable=False),
            _col("shipped_at",   "TIMESTAMP", "出荷日時",                                       nullable=True),
        ],
    },
    "analytics.monthly_revenue": {
        "description": "月次売上サマリー。orders + products から集計 (ETLパイプラインで更新)。",
        "tableType": "Regular",
        "columns": [
            _col("year_month",       "CHAR",    "集計月 (YYYY-MM 形式)",   nullable=False),
            _col("category",         "VARCHAR", "商品カテゴリ",             nullable=False),
            _col("total_orders",     "INT",     "注文件数",                 nullable=False),
            _col("total_revenue",    "NUMERIC", "売上合計 (円)",            nullable=False),
            _col("avg_order_amount", "NUMERIC", "平均注文金額",             nullable=False),
            _col("refreshed_at",     "TIMESTAMP", "集計更新日時",           nullable=False),
        ],
    },
    "analytics.customer_segments": {
        "description": "顧客セグメンテーション結果。customers + orders から生成 (MLパイプライン)。",
        "tableType": "Regular",
        "columns": [
            _col("customer_id",     "INT",     "顧客ID",                                            nullable=False),
            _col("segment",         "VARCHAR", "セグメントラベル: high_value / at_risk / new / churned", nullable=False),
            _col("lifetime_value",  "NUMERIC", "顧客生涯価値 (LTV)",                                nullable=False),
            _col("total_orders",    "INT",     "累計注文件数",                                      nullable=False),
            _col("last_order_date", "DATE",    "最終注文日",                                        nullable=True),
            _col("segmented_at",    "TIMESTAMP", "セグメント更新日時",                              nullable=False),
        ],
    },
}

SCHEMA_OF = {
    "public.customers":         "public",
    "public.products":          "public",
    "public.orders":            "public",
    "analytics.monthly_revenue":    "analytics",
    "analytics.customer_segments":  "analytics",
}

TABLE_NAME_OF = {k: k.split(".", 1)[1] for k in TABLE_DEFS}


# ── 登録処理 ──────────────────────────────────────────────────

def register_database_service(client: OMClient) -> str:
    print("▶ DatabaseService 'sample_db_service' を登録中...")
    result = client.create_or_update("services/databaseServices", {
        "name": "sample_db_service",
        "serviceType": "CustomDatabase",
        "description": "API push 型デモ用 DatabaseService (実DB接続なし)",
        "connection": {
            "config": {
                "type": "CustomDatabase",
                "sourcePythonClass": "metadata.ingestion.source.database.customdatabase.CustomDatabaseSource",
            }
        },
    })
    print(f"   ✓ id={result['id']}")
    return result["id"]


def register_pipeline_service(client: OMClient) -> str:
    print("▶ PipelineService 'local_airflow' を登録中...")
    result = client.create_or_update("services/pipelineServices", {
        "name": "local_airflow",
        "serviceType": "Airflow",
        "description": "push 型構成での自律 Airflow インスタンス",
        "connection": {
            "config": {
                "type": "Airflow",
                "hostPort": "http://ingestion:8080",
                "connection": {"type": "Backend"},
            }
        },
    })
    print(f"   ✓ id={result['id']}")
    return result["id"]


def register_database(client: OMClient, service_fqn: str) -> str:
    print("▶ Database 'sample_db' を登録中...")
    result = client.create_or_update("databases", {
        "name": "sample_db",
        "service": service_fqn,
        "description": "API push 型デモ用データベース",
    })
    print(f"   ✓ id={result['id']}")
    return f"{service_fqn}.sample_db"


def register_schemas(client: OMClient, db_fqn: str) -> dict[str, str]:
    schema_fqns: dict[str, str] = {}
    for schema_name in ("public", "analytics"):
        print(f"▶ DatabaseSchema '{schema_name}' を登録中...")
        result = client.create_or_update("databaseSchemas", {
            "name": schema_name,
            "database": db_fqn,
            "description": f"スキーマ: {schema_name}",
        })
        fqn = f"{db_fqn}.{schema_name}"
        schema_fqns[schema_name] = fqn
        print(f"   ✓ id={result['id']}")
    return schema_fqns


def register_tables(client: OMClient, schema_fqns: dict[str, str]) -> dict[str, str]:
    table_ids: dict[str, str] = {}
    for key, definition in TABLE_DEFS.items():
        schema_name = SCHEMA_OF[key]
        table_name  = TABLE_NAME_OF[key]
        schema_fqn  = schema_fqns[schema_name]
        print(f"▶ Table '{key}' を登録中...")
        result = client.create_or_update("tables", {
            "name": table_name,
            "databaseSchema": schema_fqn,
            "description": definition["description"],
            "tableType": definition["tableType"],
            "columns": definition["columns"],
        })
        table_ids[key] = result["id"]
        print(f"   ✓ id={result['id']}  columns={len(definition['columns'])}")
    return table_ids


# ── メイン ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OpenMetadata カタログ初期登録")
    parser.add_argument("--host", default="http://localhost:8585")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    client = OMClient(args.host)
    client.login(args.user, args.password)

    # System Catalog
    register_database_service(client)
    register_pipeline_service(client)

    # Data Catalog
    db_fqn      = register_database(client, "sample_db_service")
    schema_fqns = register_schemas(client, db_fqn)
    register_tables(client, schema_fqns)

    print("\n✅ カタログ登録完了")
    print(f"   OpenMetadata UI: {args.host}")


if __name__ == "__main__":
    main()
