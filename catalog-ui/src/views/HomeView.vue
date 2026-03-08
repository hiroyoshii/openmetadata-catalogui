<template>
  <div>
    <div v-if="loading" class="pg-loading"><div class="spin" /><span>読み込み中...</span></div>
    <div v-else-if="error" class="pg-error">{{ error }}</div>
    <template v-else>
      <div class="sec-hdr">
        <div class="sec-title">ドメイン一覧</div>
        <div class="sec-sub">ドメインを選択してテーブルを参照してください</div>
      </div>
      <div class="domain-grid">
        <!-- All tables card -->
        <RouterLink to="/domain" class="domain-card all-card">
          <div class="dc-icon all-icon">
            <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
          </div>
          <div class="dc-name">すべてのテーブル</div>
          <div class="dc-desc">全ドメインのテーブルを横断して参照できます。</div>
          <div class="dc-footer">
            <span class="dc-stat">
              <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
              {{ tables.length }} テーブル
            </span>
            <span class="dc-type">ALL</span>
          </div>
        </RouterLink>

        <!-- Domain cards -->
        <RouterLink
          v-for="(domain, i) in domains"
          :key="domain.id"
          :to="`/domain/${domain.id}`"
          class="domain-card"
          :style="`--dc-color: ${COLORS[i % COLORS.length]}`"
        >
          <div class="dc-icon domain-icon">
            <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          </div>
          <div class="dc-name">{{ domain.displayName || domain.name }}</div>
          <div class="dc-desc">{{ domain.description || '説明なし' }}</div>
          <div class="dc-footer">
            <span class="dc-stat">
              <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
              {{ tableCountByDomain(domain.id) }} テーブル
            </span>
            <span v-if="domainTypeLabel(domain.domainType)" class="dc-type">
              {{ domainTypeLabel(domain.domainType) }}
            </span>
          </div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api'
import type { Domain, Table } from '@/types'

const emit = defineEmits<{
  breadcrumbs: [crumbs: { label: string; to?: string }[]]
  hstat: [text: string]
}>()

const COLORS = ['#5c6bc0', '#26a69a', '#ef7c2b', '#8d6e63', '#42a5f5', '#ec407a']
const DOMAIN_TYPE_LABELS: Record<string, string> = {
  'Source-aligned': 'SOURCE',
  'Consumer-aligned': 'CONSUMER',
  'Aggregate': 'AGGREGATE',
  'Others': 'OTHER',
}

const loading = ref(true)
const error = ref('')
const domains = ref<Domain[]>([])
const tables = ref<Table[]>([])

function tableCountByDomain(domainId: string): number {
  return tables.value.filter((t) => t.domain?.id === domainId).length
}

function domainTypeLabel(type?: string): string {
  return type ? (DOMAIN_TYPE_LABELS[type] ?? type) : ''
}

onMounted(async () => {
  try {
    const [dr, tr] = await Promise.all([api.getDomains(), api.getTables()])
    domains.value = dr.data
    tables.value = tr.data
    emit('breadcrumbs', [])
    emit('hstat', `${domains.value.length} ドメイン / ${tables.value.length} テーブル`)
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.domain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.domain-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px 24px;
  cursor: pointer;
  transition: box-shadow .15s, transform .15s, border-color .15s;
  box-shadow: var(--sh);
  position: relative;
  overflow: hidden;
  display: block;
  color: var(--t1);
}
.domain-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: var(--dc-color, var(--accent));
}
.domain-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,.13);
  transform: translateY(-2px);
  border-color: var(--dc-color, var(--accent));
}
.all-card { --dc-color: var(--accent); }
.dc-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 14px;
}
.dc-icon svg { width: 22px; height: 22px; }
.all-icon { background: #f3e5f5; }
.all-icon svg { fill: #7b1fa2; }
.domain-icon {
  background: color-mix(in srgb, var(--dc-color, var(--accent)) 12%, white);
}
.domain-icon svg { fill: var(--dc-color, var(--accent)); }
.dc-name { font-size: 17px; font-weight: 700; margin-bottom: 6px; }
.dc-desc {
  font-size: 13px; color: var(--t2); line-height: 1.5;
  margin-bottom: 14px; min-height: 38px;
  overflow: hidden; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.dc-footer {
  display: flex; align-items: center; gap: 10px;
  padding-top: 12px; border-top: 1px solid var(--border);
}
.dc-stat {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; color: var(--t2);
}
.dc-stat svg { width: 13px; height: 13px; fill: var(--t3); }
.dc-type {
  margin-left: auto;
  padding: 2px 8px; border-radius: 8px;
  font-size: 10px; font-weight: 700;
  background: var(--bg); color: var(--t3); border: 1px solid var(--border);
}
</style>
