# Design: Hub and Sopke パターン × OpenMetadata マッピング設計

複数の収集元システムのスキーマを一元管理し、公開用スキーマとの対応関係を  
OpenMetadata のエンティティ構造にどうマッピングするかの設計方針を記述する。

---

## 概念モデル

Hub and Sopke パターンには3つの役割がある。

| 役割 | 概念 | OpenMetadata エンティティ |
|---|---|---|
| 収集元システム | 各業務システム (CRM / EC / OMS …) | `DatabaseService` (システムごとに1つ) |
| 公開スキーマ | 外部提供・集計済みテーブル群 | `DatabaseService` (public_service として1つ) |
| データフロー | 収集元 → 公開スキーマへの依存関係 | `EntityLineage` |

---

## DatabaseService によるシステム分離

収集元システムを **DatabaseService 単位で分離**することで、  
システム境界・担当者・SLA をサービスごとに独立して管理できる。

```
crm_service   (CRM System)
ec_service    (EC System)
oms_service   (Order Management System)
      ↓ Lineage
public_service (公開用スキーマ)
```

実 DB への接続は持たず、スキーマ定義のみを push する (`serviceType: CustomDatabase`)。

---

## エンティティ階層とマッピング

```mermaid
erDiagram
    Domain {
        string name PK "customer / order / product"
        string displayName "顧客 / 注文 / 商品"
        string domainType "Source-aligned"
        string description
    }
    DatabaseService {
        string name PK "crm_service / public_service 等"
        string serviceType "CustomDatabase"
        ref owner "担当者 (User) または担当部署 (Team)"
        ref domain FK "ビジネスドメイン"
        string description
    }
    Database {
        string fullyQualifiedName PK
        ref service FK
    }
    DatabaseSchema {
        string fullyQualifiedName PK
        ref database FK
    }
    Table {
        string fullyQualifiedName PK
        ref schema FK
        tagLabel[] tags "Classification.ingestion / Classification.public / SLA.daily 等"
        ref owner
        ref domain FK "ビジネスドメイン (テーブル単位で上書き可)"
    }
    Column {
        string name PK
        string dataType
        string constraint "PRIMARY_KEY / NOT_NULL"
        tagLabel[] tags
    }
    EntityLineage {
        ref fromEntity FK "収集元テーブル (ingestion)"
        ref toEntity FK "公開テーブル (public)"
    }
    DataContract {
        ref entity FK "Table FQN"
        string status "Active / Draft"
    }
    SLA {
        string refreshFrequency "期待する更新頻度 ISO8601"
        float availability "稼働率 %"
        string latency "最大遅延許容"
    }
    TestCase {
        ref entity FK "Table FQN"
        string testDefinition "freshnessTest / rowCountTest 等"
    }
    TestCaseResult {
        string testCaseStatus "Success / Failed"
        timestamp timestamp
    }
    Team {
        string name PK
        string teamType "Department / Group"
    }
    User {
        string name PK
        ref[] teams
    }

    Domain ||--o{ DatabaseService : "owns"
    Domain ||--o{ Table : "owns"
    DatabaseService ||--o{ Database : ""
    Database ||--o{ DatabaseSchema : ""
    DatabaseSchema ||--o{ Table : ""
    Table ||--o{ Column : ""
    Table }o--o{ EntityLineage : "upstream / downstream"
    Table ||--o| DataContract : "governed by"
    DataContract ||--o| SLA : ""
    Table ||--o{ TestCase : ""
    TestCase ||--o{ TestCaseResult : ""
    DatabaseService }o--o| User : "owner"
    DatabaseService }o--o| Team : "owner"
```

---

## メタデータ項目マッピング

| 管理したい情報 | エンティティ | フィールド | 備考 |
|---|---|---|---|
| 出所システム名・識別 | `DatabaseService` | `name` | システムごとに1サービス |
| 業務ドメイン分類 | `Domain` | `name` | `customer` / `order` / `product` |
| 担当者 | `DatabaseService` | `owner` (User) | |
| 担当部署 | `DatabaseService` | `owner` (Team) | User と Team は排他。Team 推奨 |
| 公開区分 | `Table` | `tags` | `Classification.public` / `Classification.ingestion` |
| 更新頻度 SLA | `Table` | `tags` | `SLA.hourly` / `SLA.daily` / `SLA.weekly` |
| 機密性 | `Table` / `Column` | `tags` | `PII.Sensitive` 等 |
| データフロー | `EntityLineage` | `fromEntity` → `toEntity` | 収集元テーブル → 公開テーブル |
| 鮮度チェック (実測) | `TestCase` + `TestCaseResult` | `freshnessTest` | 実績の pass/fail 時系列 |
| データ品質チェック | `TestCase` + `TestCaseResult` | 各 testDefinition | 行数・NULL・一意性 等 |
| サンプルデータ | `SampleData` | `rows` / `columns` | テーブルプレビュー用 |

> **Domain はビジネス領域** (顧客/注文/商品) で分類する。  
> 公開/収集元の区分はビジネス領域とは直交する概念のため `Classification` タグで管理する。  
> public_service のテーブルはサービス横断的なため、テーブル単位でドメインを設定する。

