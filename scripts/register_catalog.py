"""
カタログ登録スクリプト

設計方針 (design.md より):
  - 収集元システムごとに DatabaseService を分離 (crm / ec / oms)
  - 公開用テーブルは public_service にまとめる
  - Tag Classification.ingestion / Classification.public で可視性を分類
  - Lineage で収集元 → 公開テーブルを接続 (register_lineage.py)

使用方法:
    python scripts/register_catalog.py [--host http://localhost:8585]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers.om_client import OMClient


# ── タグ定義 ────────────────────────────────────────────────────

CLASSIFICATION = "Classification"
TAGS = [
    {"name": "ingestion", "description": "収集元システムのテーブル (内部用)"},
    {"name": "public",    "description": "外部公開テーブル"},
]

SLA_CLASSIFICATION = "SLA"
SLA_TAGS = [
    {"name": "hourly",  "description": "毎時更新 (PT1H)"},
    {"name": "daily",   "description": "毎日更新 (PT24H)"},
    {"name": "weekly",  "description": "毎週更新 (PT168H)"},
]

# ── ドメイン定義 ────────────────────────────────────────────────
# ビジネスドメイン (業務領域) で分類。公開/収集元の区分は Classification タグで管理。
DOMAINS = {
    "customer": {
        "displayName": "顧客",
        "description": "顧客に関するデータ (CRM・顧客セグメント)",
        "domainType": "Source-aligned",
    },
    "order": {
        "displayName": "注文",
        "description": "注文・売上に関するデータ (OMS・月次売上)",
        "domainType": "Source-aligned",
    },
    "product": {
        "displayName": "商品",
        "description": "商品に関するデータ (EC)",
        "domainType": "Source-aligned",
    },
}


def _col(name, data_type, description, nullable=True, tags=None):
    c = {
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


# ── サービス定義 ────────────────────────────────────────────────
#
# 各エントリ:
#   service_name → { description, db, schema, tag, tables: { table_name → def } }

SERVICES = {
    "crm_service": {
        "description": "CRM システム (顧客データ)",
        "db": "crm_db",
        "schema": "public",
        "tag": f"{CLASSIFICATION}.ingestion",
        "domain": "customer",
        "owner_team": {"name": "crm_team",      "displayName": "CRM チーム"},
        "owner_user": {"name": "crm_owner",      "displayName": "鈴木 一郎",   "email": "crm_owner@example.com"},
        "tables": {
            "customers": {
                "description": "顧客マスタ。CRM からの収集データ。",
                "sla": "daily",
                "columns": [
                    _col("customer_id", "INT",       "顧客ID",                           nullable=False),
                    _col("name",        "VARCHAR",   "顧客名",                            nullable=False, tags=["PII.Sensitive"]),
                    _col("email",       "VARCHAR",   "メールアドレス",                     nullable=False, tags=["PII.Sensitive"]),
                    _col("country",     "VARCHAR",   "国コード (ISO 3166-1 alpha-2)",     nullable=False),
                    _col("tier",        "VARCHAR",   "顧客ランク: standard/premium/enterprise", nullable=False),
                    _col("created_at",  "TIMESTAMP", "作成日時",                          nullable=False),
                    _col("updated_at",  "TIMESTAMP", "更新日時",                          nullable=False),
                ],
            },
        },
    },
    "ec_service": {
        "description": "EC システム (商品データ)",
        "db": "ec_db",
        "schema": "public",
        "tag": f"{CLASSIFICATION}.ingestion",
        "domain": "product",
        "owner_team": {"name": "ec_team",        "displayName": "EC チーム"},
        "owner_user": {"name": "ec_owner",        "displayName": "田中 花子",   "email": "ec_owner@example.com"},
        "tables": {
            "products": {
                "description": "商品マスタ。EC システムからの収集データ。",
                "sla": "weekly",
                "columns": [
                    _col("product_id", "INT",       "商品ID",                     nullable=False),
                    _col("sku",        "VARCHAR",   "商品コード (SKU)",             nullable=False),
                    _col("name",       "VARCHAR",   "商品名",                      nullable=False),
                    _col("category",   "VARCHAR",   "商品カテゴリ",                 nullable=False),
                    _col("price",      "NUMERIC",   "販売価格 (税抜・円)",           nullable=False),
                    _col("stock_qty",  "INT",       "在庫数量",                    nullable=False),
                    _col("is_active",  "BOOLEAN",   "販売中フラグ",                 nullable=False),
                    _col("created_at", "TIMESTAMP", "作成日時",                    nullable=False),
                ],
            },
        },
    },
    "oms_service": {
        "description": "OMS (注文管理システム)",
        "db": "oms_db",
        "schema": "public",
        "tag": f"{CLASSIFICATION}.ingestion",
        "domain": "order",
        "owner_team": {"name": "oms_team",       "displayName": "OMS チーム"},
        "owner_user": {"name": "oms_owner",       "displayName": "山本 次郎",   "email": "oms_owner@example.com"},
        "tables": {
            "orders": {
                "description": "注文履歴。OMS からの収集データ。",
                "sla": "hourly",
                "columns": [
                    _col("order_id",     "INT",       "注文ID",                     nullable=False),
                    _col("customer_id",  "INT",       "顧客ID (crm.customers 参照)", nullable=False),
                    _col("product_id",   "INT",       "商品ID (ec.products 参照)",   nullable=False),
                    _col("quantity",     "INT",       "注文数量",                    nullable=False),
                    _col("unit_price",   "NUMERIC",   "単価",                        nullable=False),
                    _col("total_amount", "NUMERIC",   "合計金額",                    nullable=True),
                    _col("status",       "VARCHAR",   "ステータス: pending/paid/shipped/delivered/cancelled", nullable=False),
                    _col("ordered_at",   "TIMESTAMP", "注文日時",                    nullable=False),
                    _col("shipped_at",   "TIMESTAMP", "出荷日時",                    nullable=True),
                ],
            },
        },
    },
    "public_service": {
        "description": "公開スキーマ (外部提供・集計済みテーブル群)",
        "db": "public_db",
        "schema": "analytics",
        "tag": f"{CLASSIFICATION}.public",
        "owner_team": {"name": "analytics_team", "displayName": "分析チーム"},
        "owner_user": {"name": "analytics_owner","displayName": "佐藤 太郎",   "email": "analytics_owner@example.com"},
        "tables": {
            "monthly_revenue": {
                "description": "月次売上サマリー。orders + products から集計。",
                "sla": "daily",
                "domain": "order",
                "columns": [
                    _col("year_month",       "CHAR",      "集計月 (YYYY-MM)",   nullable=False),
                    _col("category",         "VARCHAR",   "商品カテゴリ",        nullable=False),
                    _col("total_orders",     "INT",       "注文件数",            nullable=False),
                    _col("total_revenue",    "NUMERIC",   "売上合計 (円)",       nullable=False),
                    _col("avg_order_amount", "NUMERIC",   "平均注文金額",        nullable=False),
                    _col("refreshed_at",     "TIMESTAMP", "集計更新日時",        nullable=False),
                ],
            },
            "customer_segments": {
                "description": "顧客セグメンテーション結果。customers + orders から生成。",
                "sla": "daily",
                "domain": "customer",
                "columns": [
                    _col("customer_id",     "INT",       "顧客ID",              nullable=False),
                    _col("segment",         "VARCHAR",   "セグメント: high_value/at_risk/new/churned", nullable=False),
                    _col("lifetime_value",  "NUMERIC",   "顧客生涯価値 (LTV)",  nullable=False),
                    _col("total_orders",    "INT",       "累計注文件数",         nullable=False),
                    _col("last_order_date", "DATE",      "最終注文日",           nullable=True),
                    _col("segmented_at",    "TIMESTAMP", "セグメント更新日時",   nullable=False),
                ],
            },
        },
    },
}


# ── 登録処理 ────────────────────────────────────────────────────

def register_domains(client: OMClient) -> None:
    print("▶ Domain を登録中...")
    for name, d in DOMAINS.items():
        r = client.post_idempotent("domains", {"name": name, **d})
        if r.get("_already_exists"):
            print(f"   EXISTS {name}")
        else:
            print(f"   ✓ {name} ({d['domainType']})")


def _cleanup_obsolete_domains(client: OMClient) -> None:
    """旧ドメイン (source / analytics) を削除し、サービスのドメイン参照もクリアする。"""
    obsolete = ["source", "analytics"]
    for name in obsolete:
        # まずサービスのドメイン参照をクリア
        for svc_name, svc in SERVICES.items():
            if svc.get("domain") is None:
                # public_service のように domain を持たないサービスは PATCH で参照を除去
                svc_data = client.get_entity_by_fqn("services/databaseServices", svc_name)
                if svc_data and svc_data.get("domain", {}).get("name") == name:
                    client.patch("services/databaseServices", svc_data["id"], [
                        {"op": "remove", "path": "/domain"}
                    ])
                    print(f"   ✓ {svc_name} のドメイン参照を除去")
        # ドメインエンティティを削除
        domain_data = client.get_entity_by_fqn("domains", name)
        if domain_data:
            client.delete(f"domains/{domain_data['id']}", params={"hardDelete": "true"})
            print(f"   ✓ 旧ドメイン '{name}' を削除")


def register_tags(client: OMClient) -> None:
    print(f"▶ Classification '{CLASSIFICATION}' / '{SLA_CLASSIFICATION}' タグを登録中...")
    for clf, tags in [(CLASSIFICATION, TAGS), (SLA_CLASSIFICATION, SLA_TAGS)]:
        client.post_idempotent("classifications", {
            "name": clf,
            "description": "データの公開区分" if clf == CLASSIFICATION else "更新頻度の SLA 分類",
        })
        for tag in tags:
            client.post_idempotent("tags", {
                "classification": clf,
                "name": tag["name"],
                "description": tag["description"],
            })
    print(f"   ✓ Classification.ingestion / Classification.public")
    print(f"   ✓ SLA.hourly / SLA.daily / SLA.weekly")


def register_owners(client: OMClient) -> None:
    """各サービス・テーブルに担当チーム(Team)と担当者(User)を設定する。"""
    print("▶ Owner (Team/User) を登録中...")
    for svc_name, svc in SERVICES.items():
        # Team (担当部署) → DatabaseService の owner
        team = client.create_or_update("teams", {
            "name": svc["owner_team"]["name"],
            "displayName": svc["owner_team"]["displayName"],
            "teamType": "Group",  # Group のみエンティティの owner になれる
        })
        # User (担当者) → 各 Table の owner
        user = client.create_or_update("users", {
            "name": svc["owner_user"]["name"],
            "displayName": svc["owner_user"]["displayName"],
            "email": svc["owner_user"]["email"],
        })
        # Service に Team を PATCH
        svc_data = client.get_entity_by_fqn("services/databaseServices", svc_name)
        if svc_data:
            client.patch("services/databaseServices", svc_data["id"], [
                {"op": "add", "path": "/owners", "value": [{"id": team["id"], "type": "team"}]},
            ])
        # 各 Table に User を PATCH
        db, schema = svc["db"], svc["schema"]
        for table_name in svc["tables"]:
            tbl_fqn = f"{svc_name}.{db}.{schema}.{table_name}"
            tbl_data = client.get_entity_by_fqn("tables", tbl_fqn)
            if tbl_data:
                client.patch("tables", tbl_data["id"], [
                    {"op": "add", "path": "/owners", "value": [{"id": user["id"], "type": "user"}]},
                ])
        print(f"   ✓ {svc_name}: team={svc['owner_team']['displayName']}, user={svc['owner_user']['displayName']}")


def register_service(client: OMClient, svc_name: str, svc: dict) -> None:
    print(f"▶ DatabaseService '{svc_name}' を登録中...")
    result = client.create_or_update("services/databaseServices", {
        "name": svc_name,
        "serviceType": "CustomDatabase",
        "description": svc["description"],
        "domain": svc.get("domain"),
        "connection": {
            "config": {
                "type": "CustomDatabase",
                "sourcePythonClass": "metadata.ingestion.source.database.customdatabase.CustomDatabaseSource",
            }
        },
    })
    print(f"   ✓ id={result['id']}")

    db_fqn = f"{svc_name}.{svc['db']}"
    print(f"   ▶ Database '{svc['db']}'...")
    client.create_or_update("databases", {
        "name": svc["db"],
        "service": svc_name,
    })

    schema_fqn = f"{db_fqn}.{svc['schema']}"
    print(f"   ▶ Schema '{svc['schema']}'...")
    client.create_or_update("databaseSchemas", {
        "name": svc["schema"],
        "database": db_fqn,
    })

    for table_name, tdef in svc["tables"].items():
        print(f"   ▶ Table '{table_name}' (tag: {svc['tag']})...")
        tags_list = [{"tagFQN": svc["tag"]}]
        if "sla" in tdef:
            tags_list.append({"tagFQN": f"{SLA_CLASSIFICATION}.{tdef['sla']}"})
        # テーブル単位の domain > サービスレベルの domain の順で適用
        table_domain = tdef.get("domain") or svc.get("domain")
        table_fqn = f"{schema_fqn}.{table_name}"

        # 壊れたドメイン参照があれば hard delete して再作成
        existing = client.get_entity_by_fqn("tables", table_fqn, fields="domain")
        if existing and existing.get("domain"):
            try:
                client.get(f"domains/{existing['domain']['id']}")
            except RuntimeError:
                client.delete(f"tables/{existing['id']}", params={"hardDelete": "true"})
                print(f"      ⚠ broken domain ref, deleting for recreation")

        r = client.create_or_update("tables", {
            "name": table_name,
            "databaseSchema": schema_fqn,
            "description": tdef["description"],
            "tableType": "Regular",
            "columns": tdef["columns"],
            "tags": tags_list,
        })
        print(f"      ✓ id={r['id']}  columns={len(tdef['columns'])}")

        # PUT はドメインフィールドを更新しないため PATCH で明示的に設定
        if table_domain:
            domain_entity = client.get_entity_by_fqn("domains", table_domain)
            if domain_entity:
                client.patch("tables", r["id"], [
                    {"op": "add", "path": "/domain", "value": {
                        "id": domain_entity["id"],
                        "type": "domain",
                        "name": domain_entity["name"],
                        "fullyQualifiedName": domain_entity["fullyQualifiedName"],
                        "description": domain_entity.get("description", ""),
                        "displayName": domain_entity.get("displayName", domain_entity["name"]),
                    }}
                ])


def main(host: str = "http://localhost:8585") -> None:
    client = OMClient(host)
    client.login()

    register_domains(client)
    register_tags(client)
    for svc_name, svc in SERVICES.items():
        register_service(client, svc_name, svc)
    register_owners(client)
    _cleanup_obsolete_domains(client)

    print("\n✅ カタログ登録完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8585")
    args = parser.parse_args()
    main(args.host)
