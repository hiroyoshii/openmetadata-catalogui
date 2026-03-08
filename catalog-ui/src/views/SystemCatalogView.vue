<template>
  <div>
    <div v-if="loading" class="pg-loading"><div class="spin" /><span>読み込み中...</span></div>
    <div v-else-if="error" class="pg-error">{{ error }}</div>
    <template v-else>
      <div class="sec-hdr">
        <div class="sec-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="var(--accent)">
            <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
          </svg>
          システムカタログ
          <span class="badge">{{ services.length }}</span>
        </div>
        <div class="sec-sub">収集元・公開サービスの担当チーム・オーナー情報</div>
      </div>

      <div class="svc-grid">
        <RouterLink
          v-for="svc in services"
          :key="svc.id"
          :to="`/system/${encodeURIComponent(svc.name)}`"
          class="svc-card card"
        >
          <div class="svc-top">
            <div class="svc-name">{{ svc.name }}</div>
            <span v-if="svc.domain" class="svc-domain-badge" :class="domainClass(svc.domain.name)">
              {{ svc.domain.displayName || svc.domain.name }}
            </span>
          </div>
          <div v-if="svc.description" class="svc-desc">{{ svc.description }}</div>
          <div class="svc-meta">
            <span v-if="teamOwner(svc)" class="svc-badge svc-team">
              <svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
              {{ teamOwner(svc) }}
            </span>
            <span class="svc-badge svc-table-cnt">
              <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
              テーブル一覧 →
            </span>
          </div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import type { DatabaseService } from '@/types'
import { onMounted, ref } from 'vue'

const emit = defineEmits<{
  breadcrumbs: [crumbs: { label: string; to?: string }[]]
  hstat: [text: string]
}>()

const loading = ref(true)
const error = ref('')
const services = ref<DatabaseService[]>([])

function teamOwner(svc: DatabaseService): string {
  return svc.owners?.find((o) => o.type === 'team')?.displayName ?? ''
}

function domainClass(name?: string): string {
  if (!name) return ''
  return name === 'source' ? 'domain-source' : 'domain-analytics'
}

onMounted(async () => {
  try {
    const res = await api.getDatabaseServices()
    services.value = res.data
    emit('breadcrumbs', [{ label: 'ホーム', to: '/' }, { label: 'システムカタログ' }])
    emit('hstat', `${res.data.length} サービス`)
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.svc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.svc-card {
  display: block; padding: 18px 20px;
  border-radius: 8px; cursor: pointer; color: var(--t1);
  transition: box-shadow .15s, border-color .15s;
}
.svc-card:hover { box-shadow: 0 4px 16px rgba(92,107,192,.18); border-color: var(--accent); }
.svc-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
.svc-name { font-size: 15px; font-weight: 700; font-family: monospace; }
.svc-domain-badge { padding: 2px 9px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.domain-source { background: #fff3e0; color: #e65100; }
.domain-analytics { background: var(--green-l); color: var(--green); }
.svc-desc { font-size: 12.5px; color: var(--t2); margin-bottom: 12px; line-height: 1.5; }
.svc-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.svc-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 12px; font-size: 11px; font-weight: 500;
}
.svc-badge svg { width: 12px; height: 12px; }
.svc-team { background: #e8f5e9; color: #2e7d32; }
.svc-team svg { fill: #2e7d32; }
.svc-table-cnt { background: var(--accent-l); color: var(--accent-d); }
.svc-table-cnt svg { fill: var(--accent-d); }
</style>
