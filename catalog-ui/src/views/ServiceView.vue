<template>
  <div>
    <div v-if="loading" class="pg-loading"><div class="spin" /><span>読み込み中...</span></div>
    <div v-else-if="error" class="pg-error">{{ error }}</div>
    <template v-else-if="svc">
      <!-- Overview card -->
      <div class="card ov-card">
        <div class="ov">
          <div class="ov-top">
            <div>
              <h1 class="ov-name">{{ svc.name }}</h1>
              <div class="ov-fqn">DatabaseService</div>
            </div>
            <span v-if="svc.domain" class="domain-badge" :class="domainClass(svc.domain.name)">
              {{ svc.domain.displayName || svc.domain.name }}
            </span>
          </div>
          <div v-if="svc.description" class="ov-desc">{{ svc.description }}</div>

          <!-- 担当チーム・担当者・更新頻度 -->
          <div class="owners-grid">
            <div class="ow-item">
              <div class="ow-label">
                <svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                担当部署
              </div>
              <div class="ow-val">{{ teamOwner || '—' }}</div>
            </div>
            <div class="ow-item">
              <div class="ow-label">
                <svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                担当者 (テーブル別)
              </div>
              <div class="ow-val ow-users">
                <template v-if="tableUsers.length">
                  <span v-for="u in tableUsers" :key="u" class="user-chip">{{ u }}</span>
                </template>
                <span v-else>—</span>
              </div>
            </div>
            <div class="ow-item">
              <div class="ow-label">
                <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm4.24 16L12 15.45 7.77 18l1.12-4.81-3.73-3.23 4.92-.42L12 5l1.92 4.53 4.92.42-3.73 3.23L16.23 18z"/></svg>
                更新頻度 (テーブル別)
              </div>
              <div class="ow-val ow-slas">
                <template v-if="tableSlas.length">
                  <span v-for="(s, i) in tableSlas" :key="i" class="sla-chip">{{ s }}</span>
                </template>
                <span v-else>—</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tables card -->
      <div class="card">
        <div class="tbl-hdr">
          <span class="tbl-hdr-title">テーブル一覧</span>
          <span class="badge">{{ tables.length }}</span>
        </div>
        <table class="svctbl">
          <thead>
            <tr>
              <th>テーブル名</th>
              <th>担当者</th>
              <th>更新頻度</th>
              <th>タグ</th>
              <th>説明</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="t in tables"
              :key="t.id"
              class="tbl-row"
              @click="goToTable(t.id)"
            >
              <td class="td-name">{{ t.name }}</td>
              <td>
                <span v-if="userOwner(t)" class="user-chip">{{ userOwner(t) }}</span>
                <span v-else class="nd">—</span>
              </td>
              <td>
                <span v-if="slaLabel(t)" class="sla-chip">{{ slaLabel(t) }}</span>
                <span v-else class="nd">—</span>
              </td>
              <td>
                <div class="tag-list">
                  <span v-for="tag in classificationTags(t)" :key="tag" class="tag" :class="tagClass(tag)">{{ tag }}</span>
                </div>
              </td>
              <td class="td-desc">{{ t.description || '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import type { DatabaseService, Table } from '@/types'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const emit = defineEmits<{
  breadcrumbs: [crumbs: { label: string; to?: string }[]]
  hstat: [text: string]
}>()

const route = useRoute()
const router = useRouter()
const svcName = computed(() => decodeURIComponent(route.params.name as string))

const loading = ref(true)
const error = ref('')
const svc = ref<DatabaseService | null>(null)
const tables = ref<Table[]>([])

const SLA_MAP: Record<string, string> = { hourly: '毎時', daily: '毎日', weekly: '毎週', monthly: '毎月' }

const teamOwner = computed(() =>
  svc.value?.owners?.find((o) => o.type === 'team')?.displayName ?? ''
)

/** テーブルごとの担当者 (重複除去) */
const tableUsers = computed(() => {
  const users = tables.value
    .map((t) => t.owners?.find((o) => o.type === 'user')?.displayName ?? '')
    .filter(Boolean)
  return [...new Set(users)]
})

/** テーブルごとのSLA (重複除去) */
const tableSlas = computed(() => {
  const slas = tables.value.map((t) => slaLabel(t)).filter(Boolean)
  return [...new Set(slas)]
})

function userOwner(t: Table): string {
  return t.owners?.find((o) => o.type === 'user')?.displayName ?? ''
}

function slaLabel(t: Table): string {
  const tag = (t.tags ?? []).find((tg) => (tg.tagFQN ?? '').startsWith('SLA.'))
  if (!tag) return ''
  const key = (tag.tagFQN ?? '').split('.')[1] ?? ''
  return SLA_MAP[key] ?? key
}

function classificationTags(t: Table): string[] {
  return (t.tags ?? [])
    .map((tg) => tg.tagFQN ?? '')
    .filter((f) => f.startsWith('Classification.'))
}

function tagClass(fqn: string): string {
  if (fqn.includes('public')) return 'tag-public'
  if (fqn.includes('ingestion')) return 'tag-ingestion'
  return ''
}

function domainClass(name?: string): string {
  if (name === 'customer') return 'domain-customer'
  if (name === 'order') return 'domain-order'
  if (name === 'product') return 'domain-product'
  return 'domain-other'
}

function goToTable(id: string) {
  router.push(`/table/${id}`)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, tr] = await Promise.all([
      api.getDatabaseService(svcName.value),
      api.getTablesByServiceName(svcName.value),
    ])
    svc.value = s
    tables.value = tr.data
    emit('breadcrumbs', [
      { label: 'ホーム', to: '/' },
      { label: 'システムカタログ', to: '/systems' },
      { label: s.name },
    ])
    emit('hstat', `${tr.data.length} テーブル`)
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

watch(svcName, load)
onMounted(load)
</script>

<style scoped>
.ov-card { margin-bottom: 16px; }
.ov { padding: 20px 24px; }
.ov-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.ov-name { font-size: 22px; font-weight: 800; font-family: monospace; margin-bottom: 2px; }
.ov-fqn { font-size: 11px; color: var(--t3); }
.domain-badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.domain-customer { background: #e3f2fd; color: #1565c0; }
.domain-order    { background: #fff3e0; color: #e65100; }
.domain-product  { background: #e8f5e9; color: #2e7d32; }
.domain-other    { background: var(--accent-l); color: var(--accent-d); }
.ov-desc {
  font-size: 13px; color: var(--t2); margin: 10px 0 14px; line-height: 1.65;
  padding: 10px 14px; background: #fafafa;
  border-radius: 6px; border-left: 3px solid var(--accent);
}

/* オーナー情報グリッド */
.owners-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px; margin-top: 8px;
}
.ow-item {
  background: var(--bg); border-radius: 8px; padding: 12px 14px;
  border: 1px solid var(--border);
}
.ow-label {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; color: var(--t3);
  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 6px;
}
.ow-label svg { width: 13px; height: 13px; fill: var(--t3); }
.ow-val { font-size: 13px; color: var(--t1); font-weight: 500; }
.ow-users, .ow-slas { display: flex; flex-wrap: wrap; gap: 4px; }

.user-chip { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; background: #e3f2fd; color: #1565c0; }
.sla-chip { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; background: #fff8e1; color: #f57f17; }

/* Tables */
.tbl-hdr { display: flex; align-items: center; gap: 8px; padding: 14px 20px 0; font-size: 14px; font-weight: 700; }
.tbl-hdr-title { font-size: 14px; font-weight: 700; }
.svctbl { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
.svctbl th { padding: 8px 14px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; color: var(--t3); border-bottom: 2px solid var(--border); background: var(--bg); }
.svctbl td { padding: 9px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.tbl-row { cursor: pointer; }
.tbl-row:hover td { background: #f5f7ff; }
.tbl-row:last-child td { border-bottom: none; }
.td-name { font-weight: 600; font-family: monospace; color: var(--accent-d); }
.td-desc { color: var(--t2); font-size: 12px; max-width: 280px; }
.nd { color: var(--t3); }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.tag { padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; }
.tag-public { background: var(--green-l); color: var(--green); }
.tag-ingestion { background: #fff3e0; color: #e65100; }
</style>
