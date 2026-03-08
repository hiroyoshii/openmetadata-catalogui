# TODO — 整合性・テスタビリティ・拡張性

## 整合性 (Consistency)

### [ ] `nginx-autologin.conf` のファイル名を実態に合わせる
自動ログイン機能は存在せず、実態は「リバースプロキシ + Catalog UI ホスト」。  
ファイル名が誤解を招く。  
**対応案**: `nginx.conf` にリネームし、docker-compose の volume マウント先も更新。

### [ ] `catalog-ui` の dev proxy を nginx 経由から直接 OM に向ける
`vite.config.ts` の dev server proxy が `localhost:8686`（nginx）経由になっており、
開発時に nginx コンテナへの依存が生じている。  
**対応案**: proxy target を `http://localhost:8585` に変更し、
nginx への依存なしに `vite dev` で開発できるようにする。

### [ ] `catalog-ui` の router base path を nginx の location 設定と明示的に一致させる
`createWebHistory('/')` はルートマウント前提。nginx の `location /` と現在は一致しているが、
将来 `/catalog/` に移動する場合に両者の変更が必要。  
**対応案**: `VITE_BASE_PATH` 環境変数で制御し、`vite.config.ts`・router・nginx.conf を一元管理する。

### [ ] `catalog-ui` の API ベース URL を環境変数化する
`api/index.ts` の `const BASE = '/api/v1'` がハードコード。  
ホスト変更時や複数環境向けビルド時に問題になる。  
**対応案**: `import.meta.env.VITE_API_BASE` を使い、`.env` / `.env.production` で管理。

---

## テスタビリティ (Testability)

### [ ] `catalog-ui` にコンポーネントテストを追加する
Vue コンポーネント (`HomeView`, `TableView`, `DomainView`) に対するテストが存在しない。  
**対応案**: Vitest + `@vue/test-utils` を devDependencies に追加し、
各 View の主要な描画・API 呼び出しを検証するテストを作成する。

### [ ] `catalog-ui` の `api/index.ts` をモック可能な設計にする
`fetch` をグローバルに呼び出しているため、テスト時にモックへ差し替えにくい。  
**対応案**: `fetch` を引数注入可能にするか、`msw` (Mock Service Worker) でインターセプトする。

### [ ] CI パイプライン（GitHub Actions 等）を整備する
Python テスト (`tests/`) と catalog-ui のテストを自動実行する仕組みがない。  
**対応案**:  
- `.github/workflows/test.yml` を追加  
- Python: `docker compose up -d && python -m pytest tests/`  
- catalog-ui: `npm run test` (Vitest)

### [ ] テスト後のデータクリーンアップを実装する
`tests/` の各テストは OM API にエンティティを作成・更新するが、
実行後のクリーンアップが未実装（データが蓄積する）。  
**対応案**: `BaseTestCase.tearDownClass` に DELETE API 呼び出しを追加するか、
テスト専用のサービス名プレフィックス（例: `test_`）で隔離する。

### [ ] `test_config.py` の JWT_TOKEN 未設定スキップを解消する
`AIRFLOW__LINEAGE__JWT_TOKEN` が空のデフォルト値のため、
`test_04_jwt_token_set` が常にスキップされる。  
**対応案**: CI 実行時は `generate_om_token.py` でトークンを生成して環境変数に渡す手順を
README と CI ワークフローに明記する。

### [ ] `scripts/` にスモークテストを追加する
`register_catalog.py` / `register_lineage.py` / `register_sample_dq.py` の実行後に、
登録内容を OM API で検証する簡易チェックが存在しない。  
**対応案**: 各スクリプト末尾に GET 確認ロジックを追加、または専用の `test_smoke.py` を作成。

---

## 拡張性 (Extensibility)

### [ ] `catalog-ui` の型定義を OpenAPI スキーマから自動生成する
`src/types/index.ts` は手動メンテナンスで OpenMetadata API との乖離リスクがある。  
**対応案**: `openapi-typescript` を使い、OM サーバーの `/api/swagger.json` から
型を自動生成する `npm run gen:types` スクリプトを追加する。

### [ ] `scripts/` の共通設定を一元管理する
`register_catalog.py` / `register_lineage.py` 等に `OM_BASE_URL` 等の設定が分散している可能性。  
**対応案**: `scripts/config.py`（または `.env` + `python-dotenv`）に共通設定をまとめ、
各スクリプトから `import` する。

### [ ] `dags/` に DAG テンプレートとガイドラインを追加する
`sample_etl.py` のみで、新しい DAG を追加する際の規約が不明確。  
**対応案**: `dags/README.md` に `inlets`/`outlets` の書き方・命名規則・OM Lineage Backend との連携方法を記載する。

### [ ] `catalog-ui` の API レイヤーに認証ヘッダー挿入を準備する
現在は `NoopAuthorizer` で認証不要だが、JWT 認証に移行する際に
全 API 呼び出しへの `Authorization` ヘッダー追加が必要になる。  
**対応案**: `api/index.ts` の `get()` ヘルパーに `Authorization` ヘッダーのフック箇所を設け、
現在は空値のまま動作するようにしておく。

### [ ] `catalog-ui` にページネーションを実装する
`getTables()` が `limit=100` の固定クエリのため、テーブル数が増えると取得漏れが生じる。  
**対応案**: OM API の `paging.after` カーソルを使った無限スクロールまたはページング UI を実装する。

### [ ] MySQL の外部ポート公開を制限する
`docker-compose.yml` で MySQL の `3306:3306` がホストに公開されている。  
本番・ステージング環境ではセキュリティリスクになる。  
**対応案**: `ports` を `expose` に変更し、外部からの直接接続を防ぐ。ローカルデバッグが必要な場合は `.env` のオーバーライドで対応。

### [ ] `catalog-ui` にエラーバウンダリとローディング状態を統一する
各 View でのエラー/ローディング処理が個別実装になっていると拡張時に一貫性が失われる。  
**対応案**: 共通の `useAsyncData` コンポーザブルを `src/composables/` に作成し、
loading / error / data を統一した形で扱えるようにする。
