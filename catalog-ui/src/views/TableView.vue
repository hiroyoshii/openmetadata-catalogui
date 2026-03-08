<template>
  <div>
    <div v-if="loading" class="pg-loading"><div class="spin" /><span>読み込み中...</span></div>
    <div v-else-if="error" class="pg-error">{{ error }}</div>
    <template v-else-if="table">
      <!-- Overview card -->
      <div class="card ov-card">
        <div class="ov">
          <h1 class="ov-name">{{ table.name }}</h1>
          <div class="ov-fqn">{{ table.fullyQualifiedName }}</div>
          <div class="ov-meta">
            <span v-if="domainName" class="meta-item domain-meta">
              <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
              {{ domainName }}
            </span>
            <RouterLink
              v-if="svc"
              :to="'/system/' + encodeURIComponent(table?.service?.name ?? '')"
              class="meta-item meta-svc-link"
              :class="tableRoleClass"
              @click.stop
            >
              <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 3.79 5 6v12c0 2.21 3.13 4 7 4s7-1.79 7-4V6c0-2.21-3.13-4-7-4zm0 2c3.31 0 5 1.34 5 2s-1.69 2-5 2-5-1.34-5-2 1.69-2 5-2z"/></svg>
              <span class="svc-label">{{ svc }}</span>
              <span class="role-badge">{{ tableRole }}</span>
              <svg class="ext-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
            </RouterLink>
            <span v-if="db" class="meta-item">
              <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 3.79 5 6v12c0 2.21 3.13 4 7 4s7-1.79 7-4V6c0-2.21-3.13-4-7-4zm0 2c3.31 0 5 1.34 5 2s-1.69 2-5 2-5-1.34-5-2 1.69-2 5-2z"/></svg>
              {{ db }}
            </span>
            <span v-if="schema" class="meta-item">
              <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
              {{ schema }}
            </span>
            <span class="meta-item">
              <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
              {{ columns.length }} カラム
            </span>
          </div>
          <div v-if="table.description" class="ov-desc">{{ table.description }}</div>

          <!-- タグ (Classification / PII 等) -->
          <div v-if="tags.length" class="tags">
            <span v-for="tag in tags" :key="tag.tagFQN ?? tag.name" class="tag" :class="tagClass(tag)">
              {{ tag.tagFQN ?? tag.name }}
            </span>
          </div>
        </div>
      </div>

      <!-- Detail tabs card -->
      <div class="card">
        <div class="tabs">
          <button
            v-for="tab in TABS" :key="tab.id"
            class="tb" :class="{ on: activeTab === tab.id }"
            @click="setTab(tab.id)"
          >
            {{ tab.label }}{{ tab.id === 'columns' ? ` (${columns.length})` : '' }}
          </button>
        </div>

        <!-- Columns tab -->
        <div v-if="activeTab === 'columns'" class="pane">
          <table class="ctbl">
            <thead>
              <tr><th>カラム名</th><th>型</th><th>説明</th><th>制約</th></tr>
            </thead>
            <tbody>
              <tr v-for="col in columns" :key="col.name">
                <td>{{ col.name }}</td>
                <td><span class="dt" :class="dtClass(col.dataType)">{{ dtDisplay(col) }}</span></td>
                <td>{{ col.description ?? '' }}</td>
                <td>
                  <span v-if="col.constraint === 'PRIMARY_KEY'" class="cn cn-pk">PK</span>
                  <span v-else-if="col.constraint === 'NOT_NULL'" class="cn cn-nn">NN</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Data Quality tab -->
        <div v-if="activeTab === 'dq'" class="pane">
          <div v-if="dqLoading" class="no-data"><div class="spin" /></div>
          <div v-else-if="dqError" class="no-data" style="color:var(--red)">{{ dqError }}</div>
          <div v-else-if="testCases.length === 0" class="no-data">このテーブルのテストケースはありません</div>
          <template v-else>

            <!-- 鮮度チェック -->
            <template v-if="freshnessTests.length > 0">
              <div class="dq-section-hdr">
                <svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm.5 5v6.25l4.5 2.67-.75 1.23L11 14V7h1.5z"/></svg>
                鮮度チェック
              </div>
              <div v-for="tc in freshnessTests" :key="tc.id" class="freshness-card" :class="tcIconClass(tc)">
                <div class="fr-status-icon">{{ tcIcon(tc) }}</div>
                <div class="fr-body">
                  <div class="fr-last-updated">
                    <span class="fr-lbl">最終更新</span>
                    <span v-if="getLastUpdatedAt(tc)" class="fr-ts">{{ fmtDatetime(getLastUpdatedAt(tc)!) }}</span>
                    <span v-else class="fr-ts-none">—</span>
                  </div>
                  <div class="fr-meta">
                    <span class="fr-name">{{ tc.name }}</span>
                    <span v-if="fmtCheckedAt(tc)" class="fr-checked">チェック日時: {{ fmtCheckedAt(tc) }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- 品質チェック -->
            <template v-if="qualityTests.length > 0">
              <div class="dq-section-hdr">
                <svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                品質チェック
              </div>
              <div class="dq-summary">
                <div class="dq-stat dq-total"><div class="num">{{ qualityTests.length }}</div><div class="lbl">Total</div></div>
                <div class="dq-stat dq-pass"><div class="num">{{ dqPass }}</div><div class="lbl">✓ Pass</div></div>
                <div v-if="dqFail" class="dq-stat dq-fail"><div class="num">{{ dqFail }}</div><div class="lbl">✗ Fail</div></div>
                <div v-if="dqNone" class="dq-stat dq-none"><div class="num">{{ dqNone }}</div><div class="lbl">— N/A</div></div>
              </div>
              <div v-for="tc in qualityTests" :key="tc.id" class="tc-item">
                <div class="tc-icon" :class="tcIconClass(tc)">{{ tcIcon(tc) }}</div>
                <div class="tc-body">
                  <div class="tc-name">{{ tc.name }}</div>
                  <div class="tc-defn">
                    {{ tc.testDefinition?.displayName ?? tc.testDefinition?.name ?? '' }}
                    <span v-if="tcParams(tc)" class="tc-params"> | {{ tcParams(tc) }}</span>
                  </div>
                  <div class="tc-result">{{ tc.testCaseResult?.result ?? 'No result yet' }}</div>
                </div>
              </div>
            </template>

          </template>
        </div>

        <!-- Sample Data tab -->
        <div v-if="activeTab === 'sample'" class="pane">
          <div v-if="sampleLoading" class="no-data"><div class="spin" /></div>
          <div v-else-if="sampleError" class="no-data" style="color:var(--red)">{{ sampleError }}</div>
          <div v-else-if="sampleCols.length === 0" class="no-data">サンプルデータなし</div>
          <template v-else>
            <div class="sample-wrap">
              <table class="stbl">
                <thead>
                  <tr><th v-for="col in sampleCols" :key="col">{{ col }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in sampleRows" :key="ri">
                    <td v-for="(val, ci) in row" :key="ci" :class="{ null: val === null || val === undefined }">
                      {{ val === null || val === undefined ? 'NULL' : truncate(String(val), 40) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="row-count">{{ sampleRows.length }} 行のサンプルデータ</div>
          </template>
        </div>

        <!-- Lineage tab -->
        <div v-if="activeTab === 'lineage'" class="pane">
          <LineageGraph v-if="lineage && table" :table="table" :lineage="lineage" @navigate="onLineageNavigate" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import type { Column, EntityLineage, Table, Tag, TestCase, TestResultValue } from '@/types'
import LineageGraph from '@/views/LineageGraph.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const emit = defineEmits<{
  breadcrumbs: [crumbs: { label: string; to?: string }[]]
  hstat: [text: string]
}>()

const route = useRoute()
const router = useRouter()
const tableId = computed(() => route.params.id as string)

const TABS = [
  { id: 'columns', label: 'カラム' },
  { id: 'dq', label: 'Data Quality' },
  { id: 'sample', label: 'サンプルデータ' },
  { id: 'lineage', label: 'Lineage' },
]

// Main data
const loading = ref(true)
const error = ref('')
const table = ref<Table | null>(null)
const lineage = ref<EntityLineage | null>(null)
const activeTab = ref('columns')

// DQ
const dqLoading = ref(false)
const dqError = ref('')
const testCases = ref<TestCase[]>([])
const dqLoaded = ref(false)

// Sample
const sampleLoading = ref(false)
const sampleError = ref('')
const sampleCols = ref<string[]>([])
const sampleRows = ref<(string | number | null)[][]>([])
const sampleLoaded = ref(false)

// Computed helpers
const columns = computed<Column[]>(() => table.value?.columns ?? [])
const tags = computed<Tag[]>(() => table.value?.tags ?? [])
const fqn = computed(() => table.value?.fullyQualifiedName ?? '')
const parts = computed(() => fqn.value.split('.'))
// design.md: service名がシステム境界を示す (crm_service / public_service 等)
const svc = computed(() => table.value?.service?.displayName ?? table.value?.service?.name ?? parts.value[0] ?? '')
const db = computed(() => parts.value[1] ?? '')
const schema = computed(() => parts.value[2] ?? '')
const domainName = computed(() =>
  table.value?.domain
    ? (table.value.domain.displayName ?? table.value.domain.name ?? '')
    : ''
)

/**
 * design.md: テーブルの役割を service 名から判定
 * - public_service 配下 → 公開スキーマ (public)
 * - それ以外          → 収集元 (ingestion)
 */
const tableRole = computed(() => {
  const s = (table.value?.service?.name ?? '').toLowerCase()
  return s === 'public_service' ? '公開' : '収集元'
})
const tableRoleClass = computed(() =>
  tableRole.value === '公開' ? 'meta-item-public' : 'meta-item-ingestion'
)

function tagClass(tag: Tag): string {
  const fqn = tag.tagFQN ?? ''
  if (fqn.startsWith('PII.')) return 'tag-pii'
  if (fqn.includes('public')) return 'tag-public'
  if (fqn.includes('ingestion')) return 'tag-ingestion'
  return ''
}

const dqPass = computed(() => qualityTests.value.filter((c) => tcStatus(c) === 'Success').length)
const dqFail = computed(() => qualityTests.value.filter((c) => ['Failed', 'Aborted'].includes(tcStatus(c))).length)
const dqNone = computed(() => qualityTests.value.filter((c) => !['Success', 'Failed', 'Aborted'].includes(tcStatus(c))).length)

/** 鮮度チェック: name が _freshness で終わるテストケース */
const freshnessTests = computed(() => testCases.value.filter((c) => (c.name ?? '').endsWith('_freshness')))
/** 品質チェック: 鮮度以外の通常テストケース */
const qualityTests = computed(() => testCases.value.filter((c) => !(c.name ?? '').endsWith('_freshness')))

/** testResultValue から lastUpdatedAt を取り出す */
function getLastUpdatedAt(tc: TestCase): string | null {
  const vals = (tc.testCaseResult?.testResultValue ?? []) as TestResultValue[]
  return vals.find((v) => v.name === 'lastUpdatedAt')?.value ?? null
}

/** lastUpdatedAt の ISO 文字列を "YYYY-MM-DD HH:mm" 形式に整形 */
function fmtDatetime(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16)
}

/** テスト実行日時 (testCaseResult.timestamp ms → "YYYY-MM-DD HH:mm") */
function fmtCheckedAt(tc: TestCase): string {
  const ts = tc.testCaseResult?.timestamp
  if (!ts) return ''
  return new Date(ts).toISOString().replace('T', ' ').slice(0, 16)
}

function tcStatus(tc: TestCase): string {
  return tc.testCaseResult?.testCaseStatus ?? tc.testCaseStatus ?? ''
}
function tcIcon(tc: TestCase): string {
  const s = tcStatus(tc)
  return s === 'Success' ? '✓' : s === 'Failed' ? '✗' : '—'
}
function tcIconClass(tc: TestCase): string {
  const s = tcStatus(tc)
  return s === 'Success' ? 'tc-pass' : s === 'Failed' ? 'tc-fail' : 'tc-none'
}
function tcParams(tc: TestCase): string {
  return (tc.parameterValues ?? []).map((p) => `${p.name ?? ''}=${p.value ?? ''}`).join(', ')
}

function dtClass(type?: string): string {
  const t = (type ?? '').toUpperCase()
  if (/INT|NUMERIC|DECIMAL|FLOAT|DOUBLE/.test(t)) return 'dt-num'
  if (/VARCHAR|CHAR|TEXT|STRING/.test(t)) return 'dt-str'
  if (/DATE|TIME|TIMESTAMP/.test(t)) return 'dt-date'
  return 'dt-other'
}
function dtDisplay(col: Column): string {
  return (col.dataType ?? '').toLowerCase() + (col.dataLength ? `(${col.dataLength})` : '')
}
function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

async function setTab(id: string) {
  activeTab.value = id
  if (id === 'dq' && !dqLoaded.value) await loadDQ()
  if (id === 'sample' && !sampleLoaded.value) await loadSample()
}

async function loadDQ() {
  dqLoading.value = true
  dqLoaded.value = true
  try {
    const res = await api.getTestCases(fqn.value)
    testCases.value = (res.data ?? []).filter((c) => (c.entityFQN ?? '').startsWith(fqn.value))
  } catch (e) {
    dqError.value = String(e)
  } finally {
    dqLoading.value = false
  }
}

async function loadSample() {
  sampleLoading.value = true
  sampleLoaded.value = true
  try {
    const res = await api.getSampleData(tableId.value)
    const sd = res.sampleData ?? res
    sampleCols.value = (Array.isArray(sd.columns) ? sd.columns : []).map((c) =>
      typeof c === 'object' && c !== null ? String((c as { name?: unknown }).name ?? '') : String(c)
    )
    sampleRows.value = Array.isArray(sd.rows) ? sd.rows.filter(Array.isArray) : []
  } catch (e) {
    sampleError.value = String(e)
  } finally {
    sampleLoading.value = false
  }
}

function onLineageNavigate(id: string) {
  router.push(`/table/${id}`)
}

async function load() {
  loading.value = true
  error.value = ''
  activeTab.value = 'columns'
  dqLoaded.value = false
  sampleLoaded.value = false
  testCases.value = []
  sampleCols.value = []
  sampleRows.value = []
  try {
    const [t, l] = await Promise.all([
      api.getTable(tableId.value),
      api.getLineage(tableId.value),
    ])
    table.value = t
    lineage.value = l
    const domId = t.domain?.id
    emit('breadcrumbs', [
      { label: 'ホーム', to: '/' },
      domId
        ? { label: t.domain?.displayName ?? t.domain?.name ?? '', to: `/domain/${domId}` }
        : { label: 'すべてのテーブル', to: '/domain' },
      { label: t.name },
    ])
    emit('hstat', `${columns.value.length} カラム`)
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

watch(tableId, load)
onMounted(load)
</script>

<style scoped>
.ov-card { margin-bottom: 16px; }
.ov { padding: 20px 24px; }
.ov-name { font-size: 22px; font-weight: 800; letter-spacing: -.3px; margin-bottom: 4px; }
.ov-fqn { font-family: monospace; font-size: 11px; color: var(--t3); }
.ov-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.meta-item {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; color: var(--t2);
  background: var(--bg); padding: 4px 10px;
  border-radius: 12px; border: 1px solid var(--border);
}
.meta-item svg { width: 13px; height: 13px; fill: var(--t3); }
.domain-meta { background: var(--accent-l); border-color: #c5cae9; color: var(--accent-d); }
.domain-meta svg { fill: var(--accent-d); }
.ov-desc {
  font-size: 13px; color: var(--t2); margin-top: 12px; line-height: 1.65;
  padding: 10px 14px; background: #fafafa;
  border-radius: 6px; border-left: 3px solid var(--accent);
}
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.tag { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; background: var(--accent-l); color: var(--accent-d); }
.tag-pii { background: var(--red-l); color: var(--red); }
.tag-public { background: var(--green-l); color: var(--green); }
.tag-ingestion { background: var(--yellow-l); color: var(--yellow); }

/* service name badge — design.md: service がシステム境界を示す */
.meta-item-ingestion { background: #fff3e0; border-color: #ffcc80; color: #e65100; }
.meta-item-ingestion svg { fill: #e65100; }
.meta-item-public { background: var(--green-l); border-color: #a5d6a7; color: var(--green); }
.meta-item-public svg { fill: var(--green); }
/* service link — 他のバッジと区別するため背景なし・ボーダーのみのリンクスタイル */
.meta-svc-link { background: transparent !important; border-style: dashed !important; cursor: pointer; text-decoration: none; }
.meta-svc-link .svc-label { text-decoration: underline; text-underline-offset: 2px; }
.meta-svc-link:hover { background: rgba(0,0,0,.04) !important; }
.ext-icon { width: 11px !important; height: 11px !important; opacity: .85; margin-left: 2px; flex-shrink: 0; }
.role-badge {
  display: inline-block; margin-left: 4px;
  padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 700;
  background: rgba(0,0,0,.08); letter-spacing: .3px;
}
</style>

<style scoped>
/* Tabs */
.tabs { display: flex; border-bottom: 1px solid var(--border); }
.tb { padding: 11px 18px; border: none; background: transparent; color: var(--t2); font-size: 13px; font-weight: 500; cursor: pointer; border-bottom: 2.5px solid transparent; margin-bottom: -1px; white-space: nowrap; }
.tb.on { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.tb:hover:not(.on) { color: var(--t1); }
.pane { padding: 18px 20px; }

/* Column table */
.ctbl { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.ctbl th { padding: 8px 10px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; color: var(--t3); border-bottom: 2px solid var(--border); background: var(--bg); }
.ctbl td { padding: 7px 10px; border-bottom: 1px solid var(--border); color: var(--t2); }
.ctbl td:first-child { color: var(--t1); font-weight: 500; font-family: monospace; font-size: 12px; }
.ctbl tr:last-child td { border-bottom: none; }
.ctbl tr:hover td { background: #fafafa; }
.dt { padding: 2px 7px; border-radius: 4px; font-size: 11px; font-family: monospace; font-weight: 600; }
.dt-num { background: var(--blue-l); color: var(--blue); }
.dt-str { background: #f3e5f5; color: #6a1b9a; }
.dt-date { background: var(--yellow-l); color: var(--yellow); }
.dt-other { background: var(--bg); color: var(--t2); }
.cn { font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: 700; }
.cn-nn { background: var(--green-l); color: var(--green); }
.cn-pk { background: var(--blue-l); color: var(--blue); }

/* DQ */
.dq-section-hdr {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px;
  color: var(--t3); margin-bottom: 10px; margin-top: 4px;
}
.dq-section-hdr + .dq-summary,
.dq-section-hdr + .freshness-card { margin-top: 0; }
.dq-section-hdr svg { width: 14px; height: 14px; fill: var(--t3); }
.dq-section-hdr ~ .dq-section-hdr { margin-top: 20px; }

/* 鮮度チェックカード */
.freshness-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; border-radius: 8px; border: 1px solid;
  margin-bottom: 8px;
}
.freshness-card.tc-pass { background: var(--green-l); border-color: #a5d6a7; }
.freshness-card.tc-fail { background: var(--red-l);   border-color: #ef9a9a; }
.freshness-card.tc-none { background: var(--bg);       border-color: var(--border); }
.fr-status-icon {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; font-size: 16px; font-weight: 700;
  background: rgba(255,255,255,.7);
}
.tc-pass .fr-status-icon { color: var(--green); }
.tc-fail .fr-status-icon { color: var(--red); }
.tc-none .fr-status-icon { color: var(--t3); }
.fr-body { flex: 1; min-width: 0; }
.fr-last-updated { display: flex; align-items: baseline; gap: 8px; }
.fr-lbl { font-size: 11px; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: .4px; }
.fr-ts { font-size: 18px; font-weight: 700; color: var(--t1); font-variant-numeric: tabular-nums; }
.fr-ts-none { font-size: 15px; color: var(--t3); }
.fr-meta { margin-top: 4px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.fr-name { font-size: 11px; color: var(--t3); font-family: monospace; }
.fr-checked { font-size: 11px; color: var(--t3); }

.dq-summary { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.dq-stat { padding: 10px 16px; border-radius: 8px; border: 1px solid; text-align: center; min-width: 80px; }
.dq-stat .num { font-size: 22px; font-weight: 700; }
.dq-stat .lbl { font-size: 11px; margin-top: 2px; font-weight: 500; }
.dq-pass { background: var(--green-l); border-color: #a5d6a7; color: var(--green); }
.dq-fail { background: var(--red-l); border-color: #ef9a9a; color: var(--red); }
.dq-none { background: var(--bg); border-color: var(--border); color: var(--t3); }
.dq-total { background: var(--accent-l); border-color: #c5cae9; color: var(--accent-d); }
.tc-item { padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 8px; display: flex; align-items: flex-start; gap: 10px; }
.tc-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 13px; font-weight: 700; }
.tc-pass { background: var(--green-l); color: var(--green); }
.tc-fail { background: var(--red-l); color: var(--red); }
.tc-none { background: var(--bg); color: var(--t3); }
.tc-body { flex: 1; min-width: 0; }
.tc-name { font-size: 12.5px; font-weight: 600; margin-bottom: 3px; }
.tc-defn { font-size: 11px; color: var(--t3); margin-bottom: 3px; }
.tc-result { font-size: 11px; color: var(--t2); }
.tc-params { font-family: monospace; color: var(--t3); }

/* Sample */
.sample-wrap { overflow-x: auto; }
.stbl { border-collapse: collapse; font-size: 12px; min-width: 100%; }
.stbl th { padding: 7px 12px; text-align: left; background: var(--bg); border-bottom: 2px solid var(--border); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .3px; color: var(--t3); white-space: nowrap; }
.stbl td { padding: 6px 12px; border-bottom: 1px solid var(--border); color: var(--t2); white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.stbl tr:last-child td { border-bottom: none; }
.stbl tr:nth-child(even) td { background: #fafafa; }
.stbl td.null { color: var(--t3); font-style: italic; }
.row-count { font-size: 11px; color: var(--t3); margin-top: 8px; }
</style>

