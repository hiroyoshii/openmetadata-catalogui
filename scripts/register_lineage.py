"""
Lineage グラフ手動登録スクリプト

登録するエッジ (Airflow Lineage Backend が使えない場合のフォールバック):
  customers       ──→ orders
  products        ──→ orders
  orders          ──→ monthly_revenue
  customers       ──→ customer_segments
  orders          ──→ customer_segments

前提: register_catalog.py が実行済みであること

使用方法:
    python scripts/register_lineage.py [--host http://localhost:8585] [--user admin] [--pass admin]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers.om_client import OMClient


# サービス名を固定 (register_catalog.py と合わせる)
SERVICE = "sample_db_service"
DATABASE = "sample_db"

# FQN テンプレート: service.database.schema.table
def fqn(schema: str, table: str) -> str:
    return f"{SERVICE}.{DATABASE}.{schema}.{table}"


# リネージエッジ定義: (上流FQN, 下流FQN)
LINEAGE_EDGES = [
    (fqn("public",    "customers"),        fqn("public",    "orders")),
    (fqn("public",    "products"),         fqn("public",    "orders")),
    (fqn("public",    "orders"),           fqn("analytics", "monthly_revenue")),
    (fqn("public",    "customers"),        fqn("analytics", "customer_segments")),
    (fqn("public",    "orders"),           fqn("analytics", "customer_segments")),
]


def _lineage_payload(from_id: str, from_fqn: str, to_id: str, to_fqn: str) -> dict:
    return {
        "edge": {
            "fromEntity": {"id": from_id, "type": "table", "fullyQualifiedName": from_fqn},
            "toEntity":   {"id": to_id,   "type": "table", "fullyQualifiedName": to_fqn},
        }
    }


def main():
    parser = argparse.ArgumentParser(description="OpenMetadata Lineage 手動登録")
    parser.add_argument("--host",     default="http://localhost:8585")
    parser.add_argument("--user",     default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    client = OMClient(args.host)
    client.login(args.user, args.password)

    print(f"Lineage エッジ {len(LINEAGE_EDGES)} 件を登録中...")

    for from_fqn, to_fqn in LINEAGE_EDGES:
        from_id = client.get_fqn("tables", from_fqn)
        to_id   = client.get_fqn("tables", to_fqn)
        payload = _lineage_payload(from_id, from_fqn, to_id, to_fqn)
        client.add_lineage(payload)
        # FQN の末尾 2 要素だけ表示
        src = ".".join(from_fqn.split(".")[-2:])
        dst = ".".join(to_fqn.split(".")[-2:])
        print(f"   ✓ {src}  ──→  {dst}")

    print("\n✅ Lineage 登録完了")
    print(f"   Lineage UI: {args.host}  → Explore → orders → Lineage タブ")


if __name__ == "__main__":
    main()
