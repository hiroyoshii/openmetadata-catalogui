# OpenMetadata サンプル構成 (push 型 API-only)

OpenMetadata を使って **Data Catalog・System Catalog・Lineage** を管理するサンプル Docker Compose 環境です。

**push 型構成**: データソースへの直接接続なしに、API スクリプトと Airflow Lineage Backend のみでメタデータを登録します。

## アーキテクチャ

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  OpenMetadata Server  :8585  (受け取るだけ)               │    │
│  │    PIPELINE_SERVICE_CLIENT_ENABLED=false                  │    │
│  └────────┬──────────────────────────┬────────────────────── ┘   │
│           │ API push (カタログ登録)   │ API push (Lineage)        │
│  ┌────────▼──────────┐   ┌───────────▼──────────────────────┐    │
│  │  register scripts │   │  Ingestion (Airflow)  :8080      │    │
│  │  register_catalog │   │  LINEAGE__BACKEND=OpenMetadata   │    │
│  │  register_lineage │   │  DAG: inlets/outlets で自動 push  │    │
│  └───────────────────┘   └──────────────────────────────────┘    │
│                                                                  │
│  ┌──────────┐  ┌─────────────────────┐                          │
│  │  MySQL   │  │   Elasticsearch     │                          │
│  │  :3306   │  │       :9200         │                          │
│  └──────────┘  └─────────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
```

### 各サービスの役割

| サービス | 役割 |
|---|---|
| `openmetadata-server` | メインUI・API。Data Catalog / System Catalog / Lineage を統合管理 |
| `mysql` | OpenMetadata のメタデータ永続ストレージ (lineage グラフ含む) |
| `elasticsearch` | カタログの全文検索インデックス (テーブル・タグ・説明文の横断検索) |
| `ingestion` | 自律 Airflow。Lineage Backend 経由で OM API へリネージを自動 push |

### 旧構成 (pull 型) との違い

| 観点 | push 型 (本構成) | pull 型 (旧構成) |
|---|---|---|
| データソース直接接続 | **不要** | 必要 (sample-postgres) |
| OM→Airflow 制御 | **なし** (PIPELINE_SERVICE_CLIENT_ENABLED=false) | あり |
| Lineage 登録方法 | Airflow DAG inlets/outlets + スクリプト | OM-managed ingestion DAG |
| メモリ目安 | **~5GB** | ~8GB |
| 起動時間 | **3〜5分** | 5〜10分 |

## 起動方法

### 前提条件

- Docker >= 20.10
- Docker Compose >= v2.2
- メモリ: **5GB 以上推奨**
- Python >= 3.11 (登録スクリプト実行用・標準ライブラリのみ使用)

### 起動

```bash
# 初回起動 (DBマイグレーション含む)
docker compose up -d

# 起動状況確認
docker compose ps

# ログ確認
docker compose logs -f openmetadata-server
```

### アクセス先

| サービス | URL | 認証情報 |
|---|---|---|
| **OpenMetadata UI** | http://localhost:8585 | `admin` / `admin` |
| **Airflow UI** | http://localhost:8080 | `admin` / `admin` |

> ⚠️ **初回起動には 3〜5 分かかります。** MySQL・Elasticsearch の起動後にマイグレーションが走ります。

## セットアップ手順

### Step 1: サービス起動確認

```bash
# 全サービスが healthy になるまで待つ
docker compose ps

# OM API 疎通確認
curl -s http://localhost:8585/api/v1/system/config/auth
```

### Step 2: System Catalog + Data Catalog を登録

```bash
python scripts/register_catalog.py
# --host http://localhost:8585 (デフォルト)
# --user admin --password admin (デフォルト)
```

登録内容:
- **System Catalog**: `sample_db_service` (DatabaseService) / `local_airflow` (PipelineService)
- **Data Catalog**: `sample_db` > `public` / `analytics` スキーマ > 5テーブル (カラム定義込み)

### Step 3: Lineage を登録 (方法 A: スクリプト)

```bash
python scripts/register_lineage.py
```

登録されるリネージ:
```
customers ──┐
             ├──→ orders ──→ monthly_revenue
products  ──┘         └──→ customer_segments
customers ──────────────→ customer_segments
```

### Step 4: Lineage を登録 (方法 B: Airflow DAG 実行)

Airflow Lineage Backend が有効なため、DAG 実行時に自動で Lineage が push されます。

```bash
# Airflow UI から手動実行 → http://localhost:8080
# または CLI から実行
docker exec openmetadata_ingestion airflow dags trigger sample_etl
```

`dags/sample_etl.py` の `inlets`/`outlets` 定義が OM Lineage API へ自動 push されます。

### Step 5: UI で確認

1. `http://localhost:8585` → `Explore` → `Tables` でテーブル一覧を確認
2. `orders` テーブルを開く → `Lineage` タブでグラフを確認
3. `Settings` → `Services` → `Database` / `Pipeline` でサービス一覧を確認

## カスタム DAG の追加

`dags/` ディレクトリに Python ファイルを追加するだけで、Airflow に自動認識されます。

```python
# dags/my_etl.py
from airflow.lineage.entities import Table
from airflow.decorators import dag, task

def om_table(schema, name):
    return Table(cluster="sample_db_service", database="sample_db", name=f"{schema}.{name}")

@dag(dag_id="my_etl", ...)
def my_etl():
    @task(
        inlets=[om_table("public", "source_table")],
        outlets=[om_table("analytics", "dest_table")],
    )
    def transform(**ctx):
        pass  # 実処理

    transform()

my_etl()
```

DAG を実行すると、Airflow Lineage Backend が自動で OM の `/api/v1/lineage` に push します。

## 停止・クリーンアップ

```bash
# 停止 (データ保持)
docker compose down

# 停止 + ボリューム削除 (完全リセット)
docker compose down -v
```

## 検証コマンド

```bash
# Pipeline Client 無効化確認 (Airflow 接続エラーが出ていないこと)
docker compose logs openmetadata-server | grep -i "pipeline\|airflow" | grep -i "error\|fail"

# Airflow Lineage Backend 設定確認
docker exec openmetadata_ingestion env | grep AIRFLOW__LINEAGE

# テーブル登録確認
curl -s "http://localhost:8585/api/v1/tables?limit=20" | python3 -m json.tool | grep '"name"'

# Lineage 確認 (orders テーブル)
TABLE_ID=$(curl -s "http://localhost:8585/api/v1/tables/name/sample_db_service.sample_db.public.orders" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s "http://localhost:8585/api/v1/lineage/table/${TABLE_ID}?upstreamDepth=2&downstreamDepth=2" \
  | python3 -m json.tool
```

詳細な検証手順は [`plan.md`](.copilot/session-state/*/plan.md) の「検証方法」セクションを参照してください。

## トラブルシューティング

### OpenMetadata が起動しない

```bash
docker compose logs execute-migrate-all
docker compose logs openmetadata-server
```

### Elasticsearch が起動しない (vm.max_map_count エラー)

```bash
sudo sysctl -w vm.max_map_count=262144
# 永続化: /etc/sysctl.conf に vm.max_map_count=262144 を追記
```

### Airflow Lineage push が OM に反映されない

1. `docker exec openmetadata_ingestion env | grep AIRFLOW__LINEAGE` で環境変数確認
2. `docker exec openmetadata_ingestion airflow config get-value lineage backend` でバックエンド確認
3. Airflow タスクログで "lineage" 関連エラーを確認

### スクリプト実行時に 404 エラーが出る

OM サーバーが完全に起動するまで待ってから再実行してください:
```bash
curl -s http://localhost:8585/api/v1/system/config/auth  # 応答が返ればOK
```

## 参考リンク

- [OpenMetadata 公式ドキュメント](https://docs.open-metadata.org/)
- [OpenMetadata REST API Swagger](http://localhost:8585/docs)
- [OpenMetadata Airflow Lineage Backend](https://docs.open-metadata.org/connectors/pipeline/airflow/lineage-backend)
- [Airflow Lineage inlets/outlets](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/lineage.html)
