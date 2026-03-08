#!/usr/bin/env python3
"""register_sample_dq.py: register sample data and DQ test cases/results."""
import requests, json, sys

BASE = "http://localhost:8585/api/v1"
H = {"Content-Type": "application/json"}

def put(path, body):
    r = requests.put(f"{BASE}{path}", json=body, headers=H)
    if r.status_code not in (200, 201, 204):
        print(f"  WARN PUT {path} => {r.status_code}: {r.text[:120]}")
    return r

def post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, headers=H)
    if r.status_code not in (200, 201, 204):
        print(f"  WARN POST {path} => {r.status_code}: {r.text[:120]}")
    return r

def get(path):
    r = requests.get(f"{BASE}{path}", headers=H)
    r.raise_for_status()
    return r.json()

# ── サンプルデータ ──────────────────────────────────────────────────
SAMPLE = {
    "customers": {
        "columns": ["customer_id","name","email","country","tier","created_at","updated_at"],
        "rows": [
            [1,"山田 太郎","yamada@example.com","JP","premium","2024-01-15 09:00:00","2024-11-01 12:00:00"],
            [2,"Aiko Suzuki","suzuki@example.com","JP","standard","2024-02-20 10:30:00","2024-10-15 08:00:00"],
            [3,"John Smith","jsmith@example.com","US","enterprise","2023-11-05 14:00:00","2024-12-01 16:00:00"],
            [4,"Marie Dupont","mdupont@example.com","FR","standard","2024-05-10 11:00:00","2024-09-20 09:30:00"],
            [5,"张伟","zhang@example.com","CN","premium","2024-03-01 08:00:00","2024-11-30 10:00:00"],
        ]
    },
    "orders": {
        "columns": ["order_id","customer_id","product_id","quantity","unit_price","total_amount","status","ordered_at","shipped_at"],
        "rows": [
            [1001,1,201,2,29800,59600,"shipped","2024-11-01 10:00:00","2024-11-03 14:00:00"],
            [1002,3,202,1,198000,198000,"delivered","2024-11-05 09:30:00","2024-11-08 11:00:00"],
            [1003,2,203,3,4500,13500,"processing","2024-11-10 15:00:00",None],
            [1004,5,201,1,29800,29800,"shipped","2024-11-12 08:00:00","2024-11-14 16:00:00"],
            [1005,4,204,2,8900,17800,"cancelled","2024-11-15 11:30:00",None],
        ]
    },
    "products": {
        "columns": ["product_id","sku","name","category","price","stock_qty","is_active","created_at"],
        "rows": [
            [201,"SKU-201","ワイヤレスイヤホン Pro","Electronics",29800,150,True,"2023-06-01 00:00:00"],
            [202,"SKU-202","4K モニター 27インチ","Electronics",198000,42,True,"2023-07-15 00:00:00"],
            [203,"SKU-203","メカニカルキーボード","Accessories",4500,320,True,"2023-08-01 00:00:00"],
            [204,"SKU-204","ノートPC スタンド","Accessories",8900,85,True,"2023-09-10 00:00:00"],
            [205,"SKU-205","旧型マウス","Accessories",2500,0,False,"2022-01-01 00:00:00"],
        ]
    },
    "monthly_revenue": {
        "columns": ["year_month","category","total_orders","total_revenue","avg_order_amount","refreshed_at"],
        "rows": [
            ["2024-09","Electronics",234,12800000,54701,"2024-10-01 03:00:00"],
            ["2024-09","Accessories",512,3200000,6250,"2024-10-01 03:00:00"],
            ["2024-10","Electronics",198,9800000,49494,"2024-11-01 03:00:00"],
            ["2024-10","Accessories",630,4100000,6508,"2024-11-01 03:00:00"],
            ["2024-11","Electronics",271,14200000,52399,"2024-12-01 03:00:00"],
        ]
    },
    "customer_segments": {
        "columns": ["customer_id","segment","lifetime_value","total_orders","last_order_date","segmented_at"],
        "rows": [
            [1,"high_value",198400,12,"2024-11-12","2024-12-01 02:00:00"],
            [2,"at_risk",13500,3,"2024-09-20","2024-12-01 02:00:00"],
            [3,"high_value",256800,8,"2024-11-08","2024-12-01 02:00:00"],
            [4,"churned",17800,2,"2024-08-15","2024-12-01 02:00:00"],
            [5,"new",29800,1,"2024-11-14","2024-12-01 02:00:00"],
        ]
    }
}

print("=== サンプルデータ登録 ===")
tables = get("/tables?limit=20&fields=name,fullyQualifiedName")["data"]
tmap = {t["name"]: t for t in tables}

for name, sd in SAMPLE.items():
    t = tmap.get(name)
    if not t:
        print(f"  SKIP {name} (not found)")
        continue
    r = put(f"/tables/{t['id']}/sampleData", {"columns": sd["columns"], "rows": sd["rows"]})
    print(f"  {name}: {r.status_code}")

# ── DQ テストケース ──────────────────────────────────────────────────
print("\n=== DQ テストケース登録 ===")

TESTS = [
    # customers
    {
        "name": "customers_customer_id_not_null",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.customers::columns::customer_id>",
        "testDefinition": "columnValuesToBeNotNull",
        "parameterValues": []
    },
    {
        "name": "customers_email_unique",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.customers::columns::email>",
        "testDefinition": "columnValuesToBeUnique",
        "parameterValues": []
    },
    {
        "name": "customers_tier_in_set",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.customers::columns::tier>",
        "testDefinition": "columnValuesToBeInSet",
        "parameterValues": [{"name": "allowedValues", "value": "[\"standard\",\"premium\",\"enterprise\"]"}]
    },
    {
        "name": "customers_row_count",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.customers>",
        "testDefinition": "tableRowCountToBeBetween",
        "parameterValues": [{"name": "minValue", "value": "1"}, {"name": "maxValue", "value": "100000"}]
    },
    # orders
    {
        "name": "orders_order_id_not_null",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.orders::columns::order_id>",
        "testDefinition": "columnValuesToBeNotNull",
        "parameterValues": []
    },
    {
        "name": "orders_status_in_set",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.orders::columns::status>",
        "testDefinition": "columnValuesToBeInSet",
        "parameterValues": [{"name": "allowedValues", "value": "[\"processing\",\"shipped\",\"delivered\",\"cancelled\"]"}]
    },
    {
        "name": "orders_total_amount_positive",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.orders::columns::total_amount>",
        "testDefinition": "columnValuesToBeBetween",
        "parameterValues": [{"name": "minValue", "value": "0"}]
    },
    # products
    {
        "name": "products_price_positive",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.products::columns::price>",
        "testDefinition": "columnValuesToBeBetween",
        "parameterValues": [{"name": "minValue", "value": "1"}]
    },
    {
        "name": "products_column_count",
        "entityLink": "<#E::table::sample_db_service.sample_db.public.products>",
        "testDefinition": "tableColumnCountToEqual",
        "parameterValues": [{"name": "columnCount", "value": "8"}]
    },
]

created = []
for tc in TESTS:
    r = post("/dataQuality/testCases", tc)
    if r.status_code in (200, 201):
        created.append(r.json())
        print(f"  OK {tc['name']}")
    else:
        # maybe already exists - try to get
        name_enc = tc["name"].replace("/", "%2F")
        fqn = tc["entityLink"].replace("<#E::table::", "").replace(">", "").replace("::", ".")
        print(f"  EXISTS? {tc['name']}")

# ── DQ テスト結果 (合成) ──────────────────────────────────────────────
print("\n=== DQ テスト結果登録 ===")
import time
ts = int(time.time() * 1000)

RESULTS = {
    "customers_customer_id_not_null": ("success", 5, 5, 0),
    "customers_email_unique":         ("success", 5, 5, 0),
    "customers_tier_in_set":          ("success", 5, 5, 0),
    "customers_row_count":            ("success", 5, 5, 0),
    "orders_order_id_not_null":       ("success", 5, 5, 0),
    "orders_status_in_set":           ("success", 5, 5, 0),
    "orders_total_amount_positive":   ("failed", 5, 4, 1),  # 1件 cancelled=0
    "products_price_positive":        ("success", 5, 5, 0),
    "products_column_count":          ("success", 8, 8, 0),
}

for tc in created:
    name = tc.get("name", "")
    res = RESULTS.get(name)
    if not res:
        continue
    status, total, passed, failed = res
    fqn = tc.get("fullyQualifiedName", "")
    body = {
        "timestamp": ts,
        "testCaseStatus": status,
        "result": f"Rows checked: {total}, passed: {passed}, failed: {failed}",
        "testResultValue": [{"name": "rowCount", "value": str(total)}]
    }
    fqn_enc = fqn.replace("/", "%2F")
    r = post(f"/dataQuality/testCases/{fqn_enc}/testCaseResult", body)
    icon = "✓" if status == "success" else "✗"
    print(f"  {icon} {name}: {r.status_code}")

print("\nDone.")
