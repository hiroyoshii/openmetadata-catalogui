<template>
  <div>
    <div v-if="loading" class="pg-loading"><div class="spin" /><span>読み込み中...</span></div>
    <div v-else-if="error" class="pg-error">{{ error }}</div>
    <template v-else>
      <div class="sec-hdr">
        <div class="sec-title">
          {{ domainName }}
          <span class="badge">{{ filteredTables.length }}</span>
        </div>
        <div v-if="domain?.description" class="sec-sub">{{ domain.description }}</div>
      </div>

      <!-- Search bar (also available in header sidebar search) -->
      <div class="tbl-controls">
        <div class="search-wrap">
          <svg class="si" viewBox="0 0 24 24">
            <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
          </svg>
          <input v-model="searchQ" type="text" placeholder="テーブルを絞り込み..." />
        </div>
      </div>

      <div v-if="filteredTables.length === 0" class="no-data">テーブルが見つかりません</div>
      <div v-else class="tbl-grid">
        <RouterLink
          v-for="table in filteredTables"
          :key="table.id"
          :to="`/table/${table.id}`"
          class="tbl-card"
        >
          <div class="tc-top">
            <div class="tc-name">{{ table.name }}</div>
            <div class="tc-dq tc-dq-none">—</div>
          </div>
          <div class="tc-schema">{{ schemaPath(table.fullyQualifiedName) }}</div>
          <div class="tc-desc">{{ table.description || '説明なし' }}</div>
          <div class="tc-footer">
            <span class="tc-meta">
              <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
              {{ (table.columns ?? []).length }} カラム
            </span>
            <!-- 担当者 (Table の User owner) -->
            <span v-if="tableOwner(table)" class="tc-owner-badge">
              {{ tableOwner(table) }}
            </span>
            <span v-if="!domainId && table.domain" class="tc-domain-badge">
              {{ table.domain.displayName || table.domain.name }}
            </span>
          </div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api'
import type { Domain, Table } from '@/types'

const emit = defineEmits<{
  breadcrumbs: [crumbs: { label: string; to?: string }[]]
  hstat: [text: string]
}>()

const route = useRoute()
const domainId = computed(() => route.params.id as string | undefined)

const loading = ref(true)
const error = ref('')
const domain = ref<Domain | null>(null)
const allTables = ref<Table[]>([])
const searchQ = ref('')

const domainName = computed(() =>
  domain.value ? (domain.value.displayName ?? domain.value.name) : 'すべてのテーブル'
)

const domainTables = computed(() =>
  domainId.value
    ? allTables.value.filter((t) => t.domain?.id === domainId.value)
    : allTables.value
)

const filteredTables = computed(() => {
  const q = searchQ.value.toLowerCase()
  if (!q) return domainTables.value
  return domainTables.value.filter(
    (t) =>
      (t.name ?? '').toLowerCase().includes(q) ||
      (t.description ?? '').toLowerCase().includes(q) ||
      (t.fullyQualifiedName ?? '').toLowerCase().includes(q)
  )
})

function schemaPath(fqn?: string): string {
  return (fqn ?? '').split('.').slice(0, -1).join('.')
}

function tableOwner(table: Table): string {
  return table.owners?.find((o) => o.type === 'user')?.displayName ?? ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [dr, tr] = await Promise.all([api.getDomains(), api.getTables()])
    allTables.value = tr.data
    if (domainId.value) {
      domain.value = dr.data.find((d) => d.id === domainId.value) ?? null
    }
    updateMeta()
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

function updateMeta() {
  emit('breadcrumbs', [
    { label: 'ホーム', to: '/' },
    { label: domainName.value },
  ])
  emit('hstat', `${domainTables.value.length} テーブル`)
}

watch(domainId, load)
onMounted(load)
</script>

<style scoped>
.tbl-controls {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 18px;
}
.search-wrap { position: relative; width: 280px; }
.search-wrap input {
  width: 100%; padding: 7px 12px 7px 32px;
  border: 1px solid var(--border); border-radius: 20px;
  background: var(--card); color: var(--t1); font-size: 13px;
  outline: none; transition: border-color .2s;
}
.search-wrap input:focus { border-color: var(--accent); }
.search-wrap input::placeholder { color: var(--t3); }
.si {
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  width: 15px; height: 15px; fill: var(--t3); pointer-events: none;
}

.tbl-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.tbl-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 18px;
  cursor: pointer; display: block; color: var(--t1);
  transition: box-shadow .15s, border-color .15s;
}
.tbl-card:hover {
  box-shadow: 0 3px 12px rgba(0,0,0,.11);
  border-color: var(--accent);
}
.tc-top {
  display: flex; align-items: flex-start;
  justify-content: space-between; gap: 8px; margin-bottom: 6px;
}
.tc-name { font-size: 14px; font-weight: 700; }
.tc-dq {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.tc-dq-pass { background: var(--green-l); color: var(--green); }
.tc-dq-fail { background: var(--red-l); color: var(--red); }
.tc-dq-none { background: var(--bg); color: var(--t3); border: 1px solid var(--border); }
.tc-schema { font-size: 11px; color: var(--t3); font-family: monospace; margin-bottom: 7px; }
.tc-desc {
  font-size: 12px; color: var(--t2); line-height: 1.45; min-height: 32px;
  overflow: hidden; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.tc-footer {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border);
}
.tc-meta {
  font-size: 11px; color: var(--t3);
  display: flex; align-items: center; gap: 3px;
}
.tc-meta svg { width: 11px; height: 11px; fill: var(--t3); }
.tc-domain-badge {
  margin-left: auto; padding: 2px 8px; border-radius: 8px;
  font-size: 10px; font-weight: 600;
  background: var(--accent-l); color: var(--accent-d);
}
.tc-owner-badge {
  padding: 2px 8px; border-radius: 8px;
  font-size: 10px; font-weight: 600;
  background: #e3f2fd; color: #1565c0;
}
</style>
