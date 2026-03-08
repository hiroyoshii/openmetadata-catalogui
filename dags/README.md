# このディレクトリは push 型構成でのカスタム Airflow DAG 置き場です。
#
# docker-compose.yml で以下のようにマウントされています:
#   ./dags:/opt/airflow/dags/custom
#
# ファイル構成:
#   sample_etl.py  - inlets/outlets で Lineage を自動 push するサンプル DAG
#
# 新しい DAG を追加する場合:
#   1. このディレクトリに {dag_name}.py を追加
#   2. @task に inlets=[...] / outlets=[...] を定義
#   3. Airflow UI (http://localhost:8080) で DAG を有効化
#
# Lineage が OM に push される仕組み:
#   AIRFLOW__LINEAGE__BACKEND=airflow_provider_openmetadata.lineage.backend.OpenMetadataLineageBackend
#   → DAG 実行後に OpenMetadata API (/api/v1/lineage) へ自動登録
