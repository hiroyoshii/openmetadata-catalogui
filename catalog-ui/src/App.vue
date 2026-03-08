<template>
  <div id="root">
    <!-- ── Header ── -->
    <header class="app-header">
      <RouterLink to="/" class="logo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
        </svg>
        Data Catalog
      </RouterLink>

      <nav class="breadcrumb" aria-label="breadcrumb">
        <template v-for="(crumb, i) in breadcrumbs" :key="i">
          <span v-if="i > 0" class="bc-sep">›</span>
          <RouterLink v-if="crumb.to" :to="crumb.to" class="bc-link">{{ crumb.label }}</RouterLink>
          <span v-else class="bc-cur">{{ crumb.label }}</span>
        </template>
      </nav>

      <div class="spacer" />

      <!-- Header search (sidebar mode) -->
      <div v-if="showSidebar" class="header-search">
        <svg class="si" viewBox="0 0 24 24">
          <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>
        <input v-model="sidebarSearch" type="text" placeholder="テーブルを検索..." />
      </div>

      <span class="hstat">{{ hstat }}</span>
    </header>

    <!-- ── Body: sidebar + main ── -->
    <div class="app-body">
      <!-- Sidebar (shown on domain/table pages) -->
      <aside v-if="showSidebar" class="sidebar">
        <!-- Domain filter pills -->
        <div class="sb-domains">
          <button
            class="dn-btn" :class="{ on: activeDomainFilter === null }"
            @click="setDomainFilter(null)"
          >すべて<span class="dn-cnt">{{ allTables.length }}</span></button>
          <button
            v-for="d in allDomains" :key="d.id"
            class="dn-btn" :class="{ on: activeDomainFilter === d.id }"
            @click="setDomainFilter(d.id)"
          >{{ d.displayName || d.name }}<span class="dn-cnt">{{ domainCount(d.id) }}</span></button>
        </div>

        <!-- Table list -->
        <div class="sb-list">
          <div v-if="sidebarLoading" class="sb-msg"><div class="spin-sm" />読み込み中...</div>
          <div v-else-if="filteredSidebarTables.length === 0" class="sb-msg">該当なし</div>
          <RouterLink
            v-for="t in filteredSidebarTables"
            :key="t.id"
            :to="`/table/${t.id}`"
            class="sb-item"
            :class="{ on: currentTableId === t.id }"
          >
            <div class="sb-name">{{ t.name }}</div>
            <div class="sb-path">{{ schemaPath(t.fullyQualifiedName) }}</div>
            <div v-if="t.description" class="sb-desc">{{ t.description }}</div>
            <span v-if="activeDomainFilter === null && t.domain" class="sb-domain-badge">
              {{ t.domain.displayName || t.domain.name }}
            </span>
          </RouterLink>
        </div>
      </aside>

      <!-- Page content -->
      <main class="app-main" :class="{ 'with-sidebar': showSidebar }">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component
              :is="Component"
              @breadcrumbs="setBreadcrumbs"
              @hstat="setHstat"
            />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api'
import type { Domain, Table } from '@/types'

interface Crumb { label: string; to?: string }

const route = useRoute()

const breadcrumbs = ref<Crumb[]>([])
const hstat = ref('')
const allDomains = ref<Domain[]>([])
const allTables = ref<Table[]>([])
const sidebarLoading = ref(true)
const sidebarSearch = ref('')
const activeDomainFilter = ref<string | null>(null)

const showSidebar = computed(() => route.name === 'domain' || route.name === 'domain-all' || route.name === 'table')
const currentTableId = computed(() => route.name === 'table' ? String(route.params.id) : '')

const filteredSidebarTables = computed(() => {
  let tables = allTables.value
  if (activeDomainFilter.value) {
    tables = tables.filter((t) => t.domain?.id === activeDomainFilter.value)
  }
  const q = sidebarSearch.value.toLowerCase()
  if (q) {
    tables = tables.filter(
      (t) =>
        (t.name ?? '').toLowerCase().includes(q) ||
        (t.description ?? '').toLowerCase().includes(q)
    )
  }
  return tables
})

function domainCount(id: string) {
  return allTables.value.filter((t) => t.domain?.id === id).length
}

function setDomainFilter(id: string | null) {
  activeDomainFilter.value = id
}

function schemaPath(fqn?: string): string {
  return (fqn ?? '').split('.').slice(0, -1).join('.')
}

function setBreadcrumbs(crumbs: Crumb[]) { breadcrumbs.value = crumbs }
function setHstat(text: string) { hstat.value = text }

// Sync domain filter to current route domain
watch(
  () => route.params.id,
  (id) => {
    if (route.name === 'domain' && id) {
      activeDomainFilter.value = String(id)
    } else if (route.name === 'domain-all') {
      activeDomainFilter.value = null
    }
    // table route: keep existing filter
  },
  { immediate: true }
)

onMounted(async () => {
  try {
    const [dr, tr] = await Promise.all([api.getDomains(), api.getTables()])
    allDomains.value = dr.data
    allTables.value = tr.data
  } finally {
    sidebarLoading.value = false
  }
})
</script>

<style>
/* ── Reset & Variables ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --accent: #5c6bc0; --accent-d: #3949ab; --accent-l: #e8eaf6;
  --bg: #f0f2f5; --card: #fff; --border: #e0e0e0;
  --t1: #212121; --t2: #555; --t3: #999;
  --green: #2e7d32; --green-l: #e8f5e9;
  --red: #c62828; --red-l: #ffebee;
  --yellow: #f57c00; --yellow-l: #fff8e1;
  --blue: #1565c0; --blue-l: #e3f2fd;
  --r: 8px; --sh: 0 1px 4px rgba(0,0,0,.09);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --sb-width: 272px;
}
html, body { height: 100%; }
body { font-family: var(--font); background: var(--bg); color: var(--t1); }
a { text-decoration: none; color: inherit; }

/* ── Header ── */
.app-header {
  background: var(--accent); color: #fff; height: 52px; padding: 0 18px;
  display: flex; align-items: center; gap: 12px;
  position: sticky; top: 0; z-index: 200;
  box-shadow: 0 2px 8px rgba(0,0,0,.22);
}
.logo { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 7px; white-space: nowrap; color: #fff; }
.logo svg { opacity: .9; flex-shrink: 0; }
.breadcrumb { display: flex; align-items: center; gap: 4px; font-size: 13px; flex-shrink: 0; }
.bc-sep { opacity: .4; font-size: 11px; }
.bc-link { color: rgba(255,255,255,.75); padding: 2px 4px; border-radius: 4px; transition: .15s; }
.bc-link:hover { color: #fff; background: rgba(255,255,255,.15); }
.bc-cur { color: #fff; font-weight: 600; }
.spacer { flex: 1; min-width: 0; }
.hstat { color: rgba(255,255,255,.75); font-size: 12px; white-space: nowrap; flex-shrink: 0; }

.header-search { position: relative; width: 240px; flex-shrink: 0; }
.header-search input {
  width: 100%; padding: 6px 12px 6px 30px;
  border: none; border-radius: 16px;
  background: rgba(255,255,255,.18); color: #fff; font-size: 13px; outline: none;
}
.header-search input::placeholder { color: rgba(255,255,255,.55); }
.header-search input:focus { background: rgba(255,255,255,.28); }
.header-search .si { position: absolute; left: 9px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; fill: rgba(255,255,255,.7); pointer-events: none; }

/* ── Body layout ── */
.app-body { display: flex; height: calc(100vh - 52px); overflow: hidden; }

/* ── Sidebar ── */
.sidebar {
  width: var(--sb-width); flex-shrink: 0;
  background: var(--card); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; overflow: hidden;
}
.sb-domains {
  padding: 8px 10px; border-bottom: 1px solid var(--border);
  display: flex; flex-wrap: wrap; gap: 4px;
}
.dn-btn {
  padding: 3px 10px; border-radius: 14px;
  border: 1.5px solid var(--border);
  background: #fff; color: var(--t2); font-size: 11px; font-weight: 500;
  cursor: pointer; transition: all .15s; white-space: nowrap;
}
.dn-btn:hover { border-color: var(--accent); color: var(--accent); }
.dn-btn.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.dn-cnt { font-size: 10px; opacity: .75; margin-left: 3px; }

.sb-list { flex: 1; overflow-y: auto; padding: 6px; }
.sb-msg { padding: 20px; text-align: center; color: var(--t3); font-size: 13px; display: flex; align-items: center; justify-content: center; gap: 8px; }
.spin-sm { width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: sp .7s linear infinite; flex-shrink: 0; }
@keyframes sp { to { transform: rotate(360deg); } }

.sb-item {
  display: block; padding: 8px 10px; border-radius: 6px; margin-bottom: 2px;
  border: 1.5px solid transparent; cursor: pointer; color: var(--t1);
  transition: background .12s;
}
.sb-item:hover { background: var(--accent-l); }
.sb-item.on { background: var(--accent-l); border-color: var(--accent); }
.sb-name { font-size: 13px; font-weight: 600; margin-bottom: 1px; }
.sb-path { font-size: 10px; color: var(--t3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sb-desc { font-size: 11px; color: var(--t2); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sb-domain-badge { display: inline-block; margin-top: 4px; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 600; background: var(--accent-l); color: var(--accent-d); }

/* ── Main content ── */
.app-main { flex: 1; overflow-y: auto; padding: 24px; }
.app-main:not(.with-sidebar) { max-width: 1200px; width: 100%; margin: 0 auto; }

/* ── Transitions ── */
.fade-enter-active, .fade-leave-active { transition: opacity .15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Common utilities ── */
.spin { width: 28px; height: 28px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: sp .7s linear infinite; margin: 0 auto; }
.pg-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px; color: var(--t3); gap: 12px; }
.pg-error { padding: 40px; text-align: center; color: var(--red); }
.no-data { padding: 36px; text-align: center; color: var(--t3); font-size: 13px; }
.sec-hdr { margin-bottom: 20px; }
.sec-title { font-size: 19px; font-weight: 700; letter-spacing: -.2px; display: flex; align-items: center; gap: 8px; }
.sec-sub { font-size: 13px; color: var(--t3); margin-top: 4px; }
.badge { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: var(--accent-l); color: var(--accent-d); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--r); overflow: hidden; box-shadow: var(--sh); }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
