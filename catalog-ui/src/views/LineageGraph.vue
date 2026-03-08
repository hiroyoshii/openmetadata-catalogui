<template>
  <div>
    <div v-if="hasLineage" class="lg-wrap">
      <svg :viewBox="`0 0 ${W} ${H}`" :height="H" class="lg-svg">
        <defs>
          <marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#bbb" />
          </marker>
          <marker id="arr-focus" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#5c6bc0" />
          </marker>
        </defs>
        <rect :width="W" :height="H" fill="#f9f9f9" />

        <!-- Edges -->
        <g v-for="(edge, i) in renderedEdges" :key="i">
          <path
            fill="none"
            :stroke="edge.focused ? '#5c6bc0' : '#bbb'"
            :stroke-width="edge.focused ? 2 : 1.5"
            :marker-end="edge.focused ? 'url(#arr-focus)' : 'url(#arr)'"
            :d="edge.d"
          />
          <!-- パイプライン名ラベル -->
          <text
            v-if="edge.pipeline"
            :x="edge.labelX" :y="edge.labelY - 4"
            text-anchor="middle" font-size="9"
            font-family="system-ui" fill="#888"
          >
            <tspan>⚡ {{ edge.pipeline }}</tspan>
          </text>
        </g>

        <!-- Nodes -->
        <g
          v-for="node in renderedNodes"
          :key="node.id"
          :style="node.focus ? '' : 'cursor:pointer'"
          @click="!node.focus && emit('navigate', node.id)"
        >
          <rect
            :x="node.x" :y="node.y"
            :width="NW" :height="NH"
            :fill="node.focus ? '#3949ab' : '#fff'"
            :stroke="node.focus ? '#3949ab' : '#bbb'"
            :stroke-width="node.focus ? 2.5 : 1"
            rx="8"
          />
          <text
            :x="node.x + NW / 2" :y="node.y + 18"
            text-anchor="middle" font-size="12"
            :font-weight="node.focus ? 700 : 600"
            font-family="system-ui"
            :fill="node.focus ? '#fff' : '#333'"
          >{{ node.label }}</text>
          <text
            :x="node.x + NW / 2" :y="node.y + 32"
            text-anchor="middle" font-size="9"
            font-family="system-ui"
            :fill="node.focus ? 'rgba(255,255,255,.65)' : '#999'"
          >{{ node.sublabel }}</text>
        </g>
      </svg>
    </div>

    <div v-if="hasLineage" class="lg-meta">
      <span>← upstream: {{ upCount }} テーブル</span>
      <span class="lg-focus">◉ {{ props.table.name }}</span>
      <span>downstream: {{ downCount }} テーブル →</span>
      <span v-if="pipelines.length" class="lg-pipelines">
        ⚡ {{ pipelines.join(' / ') }}
      </span>
    </div>
    <p v-if="hasLineage" class="lg-hint">他のノードをクリックするとそのテーブルに移動します</p>
    <div v-else class="no-data">Lineage データなし</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Table, EntityLineage } from '@/types'

const props = defineProps<{ table: Table; lineage: EntityLineage }>()
const emit = defineEmits<{ navigate: [id: string] }>()

const W = 700, H = 280, NW = 148, NH = 48, G = 14

interface NodePos { id: string; name: string; fqn: string; focus: boolean; x: number; y: number }

const hasLineage = computed(() => {
  const nodes = props.lineage.nodes ?? []
  const edges = [...(props.lineage.upstreamEdges ?? []), ...(props.lineage.downstreamEdges ?? [])]
  return nodes.length > 0 || edges.length > 0
})

const nodeMap = computed<Record<string, NodePos>>(() => {
  const upEdges = props.lineage.upstreamEdges ?? []
  const downEdges = props.lineage.downstreamEdges ?? []
  const nodes = props.lineage.nodes ?? []

  const nm: Record<string, NodePos> = {}
  nm[props.table.id] = { id: props.table.id, name: props.table.name, fqn: props.table.fullyQualifiedName ?? '', focus: true, x: 0, y: 0 }
  nodes.forEach((n) => {
    nm[n.id] = { id: n.id, name: n.name ?? '', fqn: n.fullyQualifiedName ?? '', focus: false, x: 0, y: 0 }
  })

  const upIds = [...new Set(upEdges.map((e) => e.fromEntity).filter((id) => id !== props.table.id && nm[id]))]
  const downIds = [...new Set(downEdges.map((e) => e.toEntity).filter((id) => id !== props.table.id && nm[id]))]

  const uth = upIds.length * (NH + G) - G
  upIds.forEach((id, i) => { nm[id].x = 16; nm[id].y = H / 2 - uth / 2 + i * (NH + G) })
  nm[props.table.id].x = W / 2 - NW / 2
  nm[props.table.id].y = H / 2 - NH / 2
  const dth = downIds.length * (NH + G) - G
  downIds.forEach((id, i) => { nm[id].x = W - NW - 16; nm[id].y = H / 2 - dth / 2 + i * (NH + G) })

  return nm
})

const upCount = computed(() =>
  (props.lineage.upstreamEdges ?? []).filter((e) => e.fromEntity !== props.table.id && nodeMap.value[e.fromEntity]).length
)
const downCount = computed(() =>
  (props.lineage.downstreamEdges ?? []).filter((e) => e.toEntity !== props.table.id && nodeMap.value[e.toEntity]).length
)

/** 関連するパイプライン名の重複なしリスト */
const pipelines = computed(() => {
  const all = [...(props.lineage.upstreamEdges ?? []), ...(props.lineage.downstreamEdges ?? [])]
  const names = all
    .map((e) => e.lineageDetails?.pipeline?.displayName ?? e.lineageDetails?.pipeline?.name)
    .filter((n): n is string => !!n)
  return [...new Set(names)]
})

const renderedNodes = computed(() =>
  Object.values(nodeMap.value).map((n) => {
    const name = n.name || '(unknown)'
    const label = name.length > 18 ? name.slice(0, 17) + '…' : name
    const sch = n.fqn.split('.').slice(-3, -1).join('.')
    const sublabel = sch.length > 21 ? sch.slice(0, 20) + '…' : sch
    return { ...n, label, sublabel }
  })
)

const renderedEdges = computed(() => {
  const allEdges = [...(props.lineage.upstreamEdges ?? []), ...(props.lineage.downstreamEdges ?? [])]
  const nm = nodeMap.value
  // fromEntity=toEntity (self-loop) など不正エッジを除外し重複排除
  const seen = new Set<string>()
  return allEdges.flatMap((e) => {
    if (e.fromEntity === e.toEntity) return []
    const key = `${e.fromEntity}→${e.toEntity}`
    if (seen.has(key)) return []
    seen.add(key)
    const f = nm[e.fromEntity], t = nm[e.toEntity]
    if (!f || !t) return []
    const x1 = f.x + NW, y1 = f.y + NH / 2
    const x2 = t.x,      y2 = t.y + NH / 2
    const mx = (x1 + x2) / 2
    const focused = e.fromEntity === props.table.id || e.toEntity === props.table.id
    const pipeline = e.lineageDetails?.pipeline?.displayName ?? e.lineageDetails?.pipeline?.name ?? null
    return [{ d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, focused, pipeline, labelX: mx, labelY: (y1 + y2) / 2 }]
  })
})
</script>

<style scoped>
.lg-wrap { background: #f9f9f9; border-radius: 6px; overflow: hidden; }
.lg-svg { display: block; width: 100%; }
.lg-meta { display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--t3); flex-wrap: wrap; }
.lg-focus { color: var(--accent); font-weight: 600; }
.lg-pipelines { color: var(--t2); }
.lg-hint { font-size: 11px; color: var(--t3); margin-top: 4px; }
</style>

