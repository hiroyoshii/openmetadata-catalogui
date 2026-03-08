/**
 * OpenMetadata API types — design.md のマッピング思想に基づく型定義
 *
 * 自動生成: `npm run gen:types` (OM サーバーの swagger.json から生成)
 * 手動定義は UI 独自の補助型のみ。
 *
 * ## design.md マッピング概要
 *
 * | 概念              | OpenMetadata エンティティ         |
 * |-------------------|-----------------------------------|
 * | 収集元システム    | DatabaseService (システムごとに1つ) |
 * | 公開スキーマ      | DatabaseService (public_service)   |
 * | データフロー      | EntityLineage (ingestion → public) |
 * | 公開区分・機密性  | TagLabel (Classification / PII)    |
 * | 品質チェック      | TestCase + TestCaseResult          |
 * | サンプルデータ    | TableData (sampleData)             |
 */

import type { components } from './openmetadata'

// ── OpenMetadata スキーマ型エイリアス ──────────────────────────────────────

/** 収集元システム / 公開サービスの単位 (design.md: DatabaseService 1システム1サービス) */
export type DatabaseService = components['schemas']['DatabaseService']

/** ドメイン (EC / Analytics 等の業務領域) */
export type Domain     = components['schemas']['Domain']

/** テーブル — `service` フィールドがどの DatabaseService 配下かを示す */
export type Table      = components['schemas']['Table']

export type Column     = components['schemas']['Column']

/** TagLabel — Classification (public/ingestion) や PII タグとして利用 */
export type Tag        = components['schemas']['TagLabel']

export type EntityRef  = components['schemas']['EntityReference']

// TestCase / DQ (design.md: TestCase + TestCaseResult で品質チェック)
export type TestCase       = components['schemas']['TestCase']
export type TestCaseResult = components['schemas']['TestCaseResult']
export type TestResultValue = components['schemas']['TestResultValue']
export type TestDefinition = components['schemas']['TestDefinition']

// SampleData (design.md: TableData としてサンプルプレビュー)
export type SampleData = components['schemas']['TableData']

// Lineage — design.md: 収集元テーブル(ingestion) → 公開テーブル(public) のデータフロー
export type EntityLineage  = components['schemas']['EntityLineage']
export type LineageEdge    = components['schemas']['Edge']
export type LineageDetails = components['schemas']['LineageDetails']

// ── UI 独自型 ────────────────────────────────────────────────────────────────

export interface PagedResponse<T> {
  data: T[]
  paging: { total: number; after?: string; before?: string }
}
