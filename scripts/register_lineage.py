"""
Lineage 登録スクリプト

収集元 DatabaseService のテーブル → public_service のテーブルへ Lineage を登録する。

前提: register_catalog.py が実行済みであること

使用方法:
    python scripts/register_lineage.py [--host http://localhost:8585]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers.om_client import OMClient


def fqn(service: str, db: str, schema: str, table: str) -> str:
    return f"{service}.{db}.{schema}.{table}"


# 収集元テーブル → 公開テーブルの Lineage エッジ定義
LINEAGE_EDGES = [
    (fqn("crm_service", "crm_db", "public",    "customers"),    fqn("public_service", "public_db", "analytics", "monthly_revenue")),
    (fqn("ec_service",  "ec_db",  "public",    "products"),     fqn("public_service", "public_db", "analytics", "monthly_revenue")),
    (fqn("oms_service", "oms_db", "public",    "orders"),       fqn("public_service", "public_db", "analytics", "monthly_revenue")),
    (fqn("crm_service", "crm_db", "public",    "customers"),    fqn("public_service", "public_db", "analytics", "customer_segments")),
    (fqn("oms_service", "oms_db", "public",    "orders"),       fqn("public_service", "public_db", "analytics", "customer_segments")),
]


def main(host: str = "http://localhost:8585") -> None:
    client = OMClient(host)
    client.login()

    print(f"Lineage エッジ {len(LINEAGE_EDGES)} 件を登録中...")
    for from_fqn, to_fqn in LINEAGE_EDGES:
        from_id = client.get_fqn("tables", from_fqn)
        to_id   = client.get_fqn("tables", to_fqn)
        client.add_lineage({
            "edge": {
                "fromEntity": {"id": from_id, "type": "table", "fullyQualifiedName": from_fqn},
                "toEntity":   {"id": to_id,   "type": "table", "fullyQualifiedName": to_fqn},
            }
        })
        src = ".".join(from_fqn.split(".")[-2:])
        dst = ".".join(to_fqn.split(".")[-2:])
        print(f"   ✓ {src}  ──→  {dst}")

    print("\n✅ Lineage 登録完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8585")
    args = parser.parse_args()
    main(args.host)
