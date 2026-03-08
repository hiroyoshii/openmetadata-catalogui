"""
サンプルデータ + DQ テストケース登録スクリプト

v1.6.2 での TestSuite:
  - POST /dataQuality/testSuites/executable + basicEntityReference フィールドで basic suite 作成
  - TestCase の testSuite には "<tableFQN>.testSuite" を指定する

使用方法:
    python scripts/register_sample_dq.py [--host http://localhost:8585]
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent))


def _request(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    req = Request(url, data=data, headers=h, method=method)
    try:
        with urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        err = e.read().decode()
        print(f"  WARN {method} {url} => {e.code}: {err[:120]}")
        return {"_error": e.code}


def tbl(service, db, schema, table):
    return f"{service}.{db}.{schema}.{table}"

def el(service, db, schema, table, col=None):
    base = f"<#E::table::{tbl(service, db, schema, table)}"
    return (base + f"::columns::{col}>") if col else (base + ">")


# basic TestSuite を作成するテーブル
SUITE_TABLES = [
    tbl("crm_service", "crm_db", "public",    "customers"),
    tbl("oms_service", "oms_db", "public",    "orders"),
    tbl("ec_service",  "ec_db",  "public",    "products"),
]

SAMPLE = {
    tbl("crm_service", "crm_db", "public", "customers"): {
        "columns": ["customer_id", "name", "email", "country", "tier", "created_at", "updated_at"],
        "rows": [
            [1, "山田 太郎",   "yamada@example.com",  "JP", "premium",    "2024-01-15 09:00:00", "2024-11-01 12:00:00"],
            [2, "Aiko Suzuki", "suzuki@example.com",  "JP", "standard",   "2024-02-20 10:30:00", "2024-10-15 08:00:00"],
            [3, "John Smith",  "jsmith@example.com",  "US", "enterprise", "2023-11-05 14:00:00", "2024-12-01 16:00:00"],
        ],
    },
    tbl("ec_service", "ec_db", "public", "products"): {
        "columns": ["product_id", "sku", "name", "category", "price", "stock_qty", "is_active", "created_at"],
        "rows": [
            [201, "SKU-201", "ワイヤレスイヤホン Pro", "Electronics", 29800,  150, True,  "2023-06-01 00:00:00"],
            [202, "SKU-202", "4K モニター 27インチ",   "Electronics", 198000,  42, True,  "2023-07-15 00:00:00"],
            [203, "SKU-203", "メカニカルキーボード",    "Accessories",  4500,  320, True,  "2023-08-01 00:00:00"],
        ],
    },
    tbl("oms_service", "oms_db", "public", "orders"): {
        "columns": ["order_id", "customer_id", "product_id", "quantity", "unit_price", "total_amount", "status", "ordered_at", "shipped_at"],
        "rows": [
            [1001, 1, 201, 2, 29800,  59600,  "shipped",   "2024-11-01 10:00:00", "2024-11-03 14:00:00"],
            [1002, 3, 202, 1, 198000, 198000, "delivered", "2024-11-05 09:30:00", "2024-11-08 11:00:00"],
            [1003, 2, 203, 3, 4500,   13500,  "pending",   "2024-11-10 15:00:00", None],
        ],
    },
    tbl("public_service", "public_db", "analytics", "monthly_revenue"): {
        "columns": ["year_month", "category", "total_orders", "total_revenue", "avg_order_amount", "refreshed_at"],
        "rows": [
            ["2024-10", "Electronics", 198,  9800000, 49494, "2024-11-01 03:00:00"],
            ["2024-10", "Accessories", 630,  4100000,  6508, "2024-11-01 03:00:00"],
            ["2024-11", "Electronics", 271, 14200000, 52399, "2024-12-01 03:00:00"],
        ],
    },
    tbl("public_service", "public_db", "analytics", "customer_segments"): {
        "columns": ["customer_id", "segment", "lifetime_value", "total_orders", "last_order_date", "segmented_at"],
        "rows": [
            [1, "high_value", 198400, 12, "2024-11-12", "2024-12-01 02:00:00"],
            [2, "at_risk",     13500,  3, "2024-09-20", "2024-12-01 02:00:00"],
            [3, "high_value", 256800,  8, "2024-11-08", "2024-12-01 02:00:00"],
        ],
    },
}

TESTS = [
    # crm_service: customers  (testSuite = "<tableFQN>.testSuite")
    {"name": "customers_id_not_null",   "entityLink": el("crm_service","crm_db","public","customers","customer_id"), "testDefinition": "columnValuesToBeNotNull",  "parameterValues": [], "testSuite": tbl("crm_service","crm_db","public","customers")+".testSuite"},
    {"name": "customers_email_unique",  "entityLink": el("crm_service","crm_db","public","customers","email"),       "testDefinition": "columnValuesToBeUnique",   "parameterValues": [], "testSuite": tbl("crm_service","crm_db","public","customers")+".testSuite"},
    {"name": "customers_tier_in_set",   "entityLink": el("crm_service","crm_db","public","customers","tier"),        "testDefinition": "columnValuesToBeInSet",    "parameterValues": [{"name":"allowedValues","value":"[\"standard\",\"premium\",\"enterprise\"]"}], "testSuite": tbl("crm_service","crm_db","public","customers")+".testSuite"},
    {"name": "customers_row_count",     "entityLink": el("crm_service","crm_db","public","customers"),               "testDefinition": "tableRowCountToBeBetween", "parameterValues": [{"name":"minValue","value":"1"},{"name":"maxValue","value":"100000"}], "testSuite": tbl("crm_service","crm_db","public","customers")+".testSuite"},
    # oms_service: orders
    {"name": "orders_id_not_null",      "entityLink": el("oms_service","oms_db","public","orders","order_id"),       "testDefinition": "columnValuesToBeNotNull",  "parameterValues": [], "testSuite": tbl("oms_service","oms_db","public","orders")+".testSuite"},
    {"name": "orders_status_in_set",    "entityLink": el("oms_service","oms_db","public","orders","status"),         "testDefinition": "columnValuesToBeInSet",    "parameterValues": [{"name":"allowedValues","value":"[\"pending\",\"paid\",\"shipped\",\"delivered\",\"cancelled\"]"}], "testSuite": tbl("oms_service","oms_db","public","orders")+".testSuite"},
    # ec_service: products
    {"name": "products_price_positive", "entityLink": el("ec_service","ec_db","public","products","price"),          "testDefinition": "columnValuesToBeBetween",  "parameterValues": [{"name":"minValue","value":"1"}], "testSuite": tbl("ec_service","ec_db","public","products")+".testSuite"},
    {"name": "products_column_count",   "entityLink": el("ec_service","ec_db","public","products"),                  "testDefinition": "tableColumnCountToEqual",  "parameterValues": [{"name":"columnCount","value":"8"}], "testSuite": tbl("ec_service","ec_db","public","products")+".testSuite"},
]

DQ_RESULTS = {
    "customers_id_not_null":   ("Success", 3, 3, 0),
    "customers_email_unique":  ("Success", 3, 3, 0),
    "customers_tier_in_set":   ("Success", 3, 3, 0),
    "customers_row_count":     ("Success", 3, 3, 0),
    "orders_id_not_null":      ("Success", 3, 3, 0),
    "orders_status_in_set":    ("Success", 3, 3, 0),
    "products_price_positive": ("Success", 3, 3, 0),
    "products_column_count":   ("Success", 8, 8, 0),
}


def main(host: str = "http://localhost:8585") -> None:
    base = host.rstrip("/") + "/api/v1"
    put  = lambda p, b: _request("PUT",  f"{base}{p}", b)
    post = lambda p, b: _request("POST", f"{base}{p}", b)
    get  = lambda p:    _request("GET",  f"{base}{p}")

    print("=== TestSuite 登録 ===")
    for table_fqn in SUITE_TABLES:
        r = post("/dataQuality/testSuites/executable", {
            "name": f"{table_fqn}.testSuite",
            "basicEntityReference": table_fqn,   # v1.6.2 の正しいフィールド名
        })
        label = table_fqn.split(".")[-1]
        if "_error" in r:
            print(f"  EXISTS {label}.testSuite")
        else:
            print(f"  OK {label}.testSuite (basic={r.get('basic')})")

    print("\n=== サンプルデータ登録 ===")
    tables = get("/tables?limit=50&fields=name,fullyQualifiedName").get("data", [])
    tmap = {t["fullyQualifiedName"]: t for t in tables}
    for fqn_key, sd in SAMPLE.items():
        t = tmap.get(fqn_key)
        if not t:
            print(f"  SKIP {fqn_key.split('.')[-1]} (not found)")
            continue
        r = put(f"/tables/{t['id']}/sampleData", {"columns": sd["columns"], "rows": sd["rows"]})
        print(f"  {'WARN' if '_error' in r else 'OK'} {fqn_key.split('.')[-1]}")

    print("\n=== DQ テストケース登録 ===")
    for tc in TESTS:
        r = post("/dataQuality/testCases", tc)
        if "_error" in r:
            print(f"  EXISTS {tc['name']}")
        else:
            print(f"  OK {tc['name']}")

    # 既存/新規問わず全テストケースを取得して結果を登録
    all_tcs = get("/dataQuality/testCases?limit=50").get("data", [])
    tc_map  = {t["name"]: t for t in all_tcs}

    print("\n=== DQ テスト結果登録 ===")
    ts = int(time.time() * 1000)
    for name, res in DQ_RESULTS.items():
        tc = tc_map.get(name)
        if not tc:
            print(f"  SKIP {name} (not found)")
            continue
        status, total, passed, failed = res
        # FQN はドット区切りのためパスコンポーネントとして %2E でエンコードが必要
        fqn_enc = tc.get("fullyQualifiedName", "").replace(".", "%2E")
        r = put(f"/dataQuality/testCases/{fqn_enc}/testCaseResult", {
            "timestamp": ts,
            "testCaseStatus": status,
            "result": f"checked: {total}, passed: {passed}, failed: {failed}",
            "testResultValue": [{"name": "rowCount", "value": str(total)}],
        })
        print(f"  {'✓' if '_error' not in r else '✗'} {name}")

    print("\n✅ サンプル/DQ 登録完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8585")
    args = parser.parse_args()
    main(args.host)
