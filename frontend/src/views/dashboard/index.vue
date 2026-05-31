<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'

import {
  getDashboardStats,
  type DashboardStats,
  type RecentInvoiceItem,
} from '@/api/dashboard'
import {
  cancelWorkflow,
  getWorkflowStatus,
  startWorkflow,
  type WorkflowStatus,
} from '@/api/workflow'

use([
  CanvasRenderer,
  PieChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
])

const router = useRouter()

// ─── Stats ────────────────────────────────────────────────────
const stats = ref<DashboardStats | null>(null)
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await getDashboardStats()
  } catch (e) {
    console.error(e)
  } finally {
    statsLoading.value = false
  }
}

// ─── Workflow ─────────────────────────────────────────────────
interface FlowOption {
  key: 'email_fetch' | 'recognize' | 'classify' | 'organize'
  label: string
  hint: string
  serial: string
  enabled: boolean
}

const flowOptions = reactive<FlowOption[]>([
  { key: 'email_fetch', label: '邮箱发票拉取', hint: 'IMAP · 自动归档', serial: 'I', enabled: true },
  { key: 'recognize', label: 'AI识别发票内容', hint: 'qwen-vl · OCR', serial: 'II', enabled: true },
  { key: 'classify', label: '自动分类', hint: '关键词匹配', serial: 'III', enabled: true },
  { key: 'organize', label: '文件归档整理', hint: '按开票日期', serial: 'IV', enabled: true },
])

const workflow = ref<WorkflowStatus | null>(null)
const workflowStarting = ref(false)
const isRunning = computed(() => workflow.value?.status === 'processing')
const POLL_MS = 2000
let pollTimer: number | undefined

function clearPoll() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = undefined
  }
}

async function pollStatus(taskId: number) {
  try {
    const data = await getWorkflowStatus(taskId)
    workflow.value = data
    if (data.status !== 'processing') {
      clearPoll()
      // 完成后刷新统计
      loadStats()
      if (data.status === 'completed') {
        ElMessage.success('整理流程已完成')
      } else if (data.status === 'failed') {
        ElMessage.error('整理流程执行失败')
      } else if (data.status === 'cancelled') {
        ElMessage.warning('整理流程已取消')
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function handleStart() {
  if (!flowOptions.some((o) => o.enabled)) {
    ElMessage.warning('请至少勾选一个步骤')
    return
  }
  workflowStarting.value = true
  try {
    const payload = flowOptions.reduce(
      (acc, opt) => {
        acc[opt.key] = opt.enabled
        return acc
      },
      {} as Record<string, boolean>,
    )
    const res = await startWorkflow(payload)
    ElMessage.success(`流程已启动 (#${res.task_id})`)
    clearPoll()
    await pollStatus(res.task_id)
    pollTimer = window.setInterval(() => pollStatus(res.task_id), POLL_MS)
  } catch (e) {
    console.error(e)
  } finally {
    workflowStarting.value = false
  }
}

async function handleCancel() {
  if (!workflow.value) return
  try {
    await ElMessageBox.confirm(`确认取消正在执行的整理流程 #${workflow.value.task_id}？`, '取消流程', {
      type: 'warning',
      confirmButtonText: '确认取消',
      cancelButtonText: '继续运行',
    })
    await cancelWorkflow(workflow.value.task_id)
    ElMessage.info('已发送取消请求')
  } catch {
    /* user cancelled or no perm */
  }
}

// ─── Charts options ───────────────────────────────────────────
const VERMILION = '#B8410E'
const INK = '#0E0E0E'
const MUTE = '#6B6157'
const PAPER = '#F5F1E8'
const PAL = ['#0E0E0E', '#B8410E', '#C99A4B', '#6B6157', '#978B7C', '#3A4A3A', '#8E2F08', '#BDC3C7']

const pieOption = computed(() => {
  const list = (stats.value?.category_distribution || []).filter((c) => c.amount > 0 || c.count > 0)
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: PAPER,
      borderColor: INK,
      borderWidth: 1,
      textStyle: { color: INK, fontFamily: 'Geist, Helvetica Neue, sans-serif', fontSize: 12 },
      extraCssText: 'border-radius: 0; box-shadow: 0 8px 24px rgba(14,14,14,0.08);',
      formatter: (p: any) =>
        `<div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.14em; color:${MUTE}; text-transform:uppercase;">${p.name}</div>` +
        `<div style="font-family: 'Fraunces', serif; font-style: italic; font-size: 18px; margin-top: 4px;">¥${(p.value as number).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>` +
        `<div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color:${MUTE}; margin-top:2px;">${p.percent}%</div>`,
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 'middle',
      icon: 'rect',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 12,
      textStyle: {
        color: INK,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 11,
        rich: { v: { color: MUTE } },
      },
      formatter: (name: string) => name,
    },
    series: [
      {
        name: '分类金额',
        type: 'pie',
        radius: ['52%', '74%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          position: 'center',
          formatter: () => {
            const total = list.reduce((s, c) => s + c.amount, 0)
            return `{a|TOTAL}\n{b|¥${total.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}}\n{c|${list.length} categories}`
          },
          rich: {
            a: {
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              letterSpacing: 2,
              color: MUTE,
              padding: [0, 0, 6, 0],
            },
            b: {
              fontFamily: 'Fraunces, serif',
              fontStyle: 'italic',
              fontSize: 24,
              color: INK,
              padding: [0, 0, 4, 0],
            },
            c: {
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: MUTE,
              letterSpacing: 1,
            },
          },
        },
        labelLine: { show: false },
        itemStyle: {
          borderColor: PAPER,
          borderWidth: 2,
        },
        emphasis: {
          scale: true,
          scaleSize: 6,
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(184, 65, 14, 0.32)',
          },
        },
        data: list.map((c, i) => ({
          name: c.name,
          value: Number(c.amount.toFixed(2)),
          itemStyle: { color: PAL[i % PAL.length] },
        })),
      },
    ],
  }
})

const lineOption = computed(() => {
  const trend = stats.value?.monthly_trend || []
  return {
    backgroundColor: 'transparent',
    grid: { left: 50, right: 56, top: 36, bottom: 36, containLabel: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: PAPER,
      borderColor: INK,
      borderWidth: 1,
      textStyle: { color: INK, fontFamily: 'Geist, Helvetica Neue, sans-serif', fontSize: 12 },
      extraCssText: 'border-radius: 0; box-shadow: 0 8px 24px rgba(14,14,14,0.08);',
      axisPointer: {
        type: 'line',
        lineStyle: { color: INK, width: 1, type: 'dashed' },
      },
    },
    legend: {
      data: ['张数', '金额'],
      right: 0,
      top: 0,
      icon: 'rect',
      itemWidth: 10,
      itemHeight: 2,
      textStyle: { color: INK, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
    },
    xAxis: {
      type: 'category',
      data: trend.map((t) => t.month),
      axisLine: { lineStyle: { color: INK } },
      axisTick: { show: false },
      axisLabel: {
        color: MUTE,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 10,
        formatter: (v: string) => v.slice(2),
      },
    },
    yAxis: [
      {
        type: 'value',
        name: '张',
        nameTextStyle: { color: MUTE, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: 'rgba(14,14,14,0.07)', type: 'dashed' } },
        axisLabel: { color: MUTE, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
      },
      {
        type: 'value',
        name: '元',
        nameTextStyle: { color: MUTE, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          color: MUTE,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10,
          formatter: (v: number) =>
            v >= 10000 ? `${(v / 10000).toFixed(1)}w` : v.toString(),
        },
      },
    ],
    series: [
      {
        name: '张数',
        type: 'line',
        yAxisIndex: 0,
        smooth: false,
        symbol: 'rect',
        symbolSize: 6,
        lineStyle: { color: INK, width: 1.4 },
        itemStyle: { color: INK, borderColor: PAPER, borderWidth: 1 },
        data: trend.map((t) => t.count),
      },
      {
        name: '金额',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { color: VERMILION, width: 1.6 },
        itemStyle: { color: VERMILION, borderColor: PAPER, borderWidth: 1 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(184, 65, 14, 0.18)' },
              { offset: 1, color: 'rgba(184, 65, 14, 0.0)' },
            ],
          },
        },
        data: trend.map((t) => t.amount),
      },
    ],
  }
})

// ─── helpers ──────────────────────────────────────────────────
function formatMoney(n: number | null | undefined) {
  if (n == null) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function formatInt(n: number | null | undefined) {
  if (n == null) return '0'
  return n.toLocaleString('zh-CN')
}
function statusLabel(s?: string) {
  switch (s) {
    case 'pending': return '待识别'
    case 'recognized': return '已识别'
    case 'verified': return '已核验'
    case 'error': return '识别失败'
    default: return s || '—'
  }
}
function statusKind(s?: string) {
  switch (s) {
    case 'recognized':
    case 'verified': return 'ok'
    case 'pending': return 'pending'
    case 'error': return 'error'
    default: return 'default'
  }
}
function stepKind(s?: string) {
  switch (s) {
    case 'completed': return 'ok'
    case 'processing': return 'run'
    case 'failed': return 'error'
    case 'skipped': return 'skip'
    default: return 'pending'
  }
}
function stepBadge(s?: string) {
  switch (s) {
    case 'completed': return 'OK'
    case 'processing': return '运行'
    case 'failed': return '失败'
    case 'skipped': return '跳过'
    default: return '待运行'
  }
}
function todayStamp() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
}
function gotoInvoice(item?: RecentInvoiceItem) {
  if (item) router.push(`/invoice`)
  else router.push('/invoice')
}

const monthLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()} · ${String(d.getMonth() + 1).padStart(2, '0')}`
})

const totalRecords = computed(() => stats.value?.recent_invoices?.length ?? 0)

onMounted(() => {
  loadStats()
})
onBeforeUnmount(() => {
  clearPoll()
})
</script>

<template>
  <article class="dash">
    <!-- ── HEAD ── -->
    <header class="dash__head">
      <div class="dash__head-left">
        <span class="serial">§ 01 · DASHBOARD · {{ todayStamp() }}</span>
        <h1 class="dash__title">
          <span>仪表盘</span>
          <em>tableau de bord</em>
        </h1>
        <p class="dash__caption">
          本月发票 · 分类与趋势 · 月度整理流程 — 一切始于此页。
        </p>
      </div>
      <div class="dash__head-right">
        <div class="period">
          <div class="eyebrow">PERIOD</div>
          <div class="period__value">{{ monthLabel }}</div>
        </div>
        <div class="stamp dash__stamp">整</div>
      </div>
    </header>

    <div class="rule" />

    <!-- ── STATS GRID ── -->
    <section class="stats">
      <article class="stat" v-loading="statsLoading">
        <div class="stat__head">
          <span class="serial">A · 本月票据</span>
          <span class="stat__unit">张</span>
        </div>
        <div class="stat__num">{{ formatInt(stats?.total_invoices) }}</div>
        <div class="stat__foot">
          <span class="dot" />
          <span>this month</span>
        </div>
      </article>

      <article class="stat stat--accent" v-loading="statsLoading">
        <div class="stat__head">
          <span class="serial">B · 价税合计</span>
          <span class="stat__unit">CNY</span>
        </div>
        <div class="stat__num stat__num--money">
          <span class="cur">¥</span>{{ formatMoney(stats?.total_amount) }}
        </div>
        <div class="stat__foot">
          <span class="dot dot--ink" />
          <span>monthly total</span>
        </div>
      </article>

      <article class="stat" v-loading="statsLoading">
        <div class="stat__head">
          <span class="serial">C · 待识别</span>
          <span class="stat__unit">PEND</span>
        </div>
        <div class="stat__num">
          {{ formatInt(stats?.pending_count) }}
        </div>
        <div class="stat__foot">
          <span class="dot dot--mute" />
          <span>queue</span>
        </div>
      </article>

      <article class="stat" v-loading="statsLoading">
        <div class="stat__head">
          <span class="serial">D · 已识别</span>
          <span class="stat__unit">OK</span>
        </div>
        <div class="stat__num">{{ formatInt(stats?.recognized_count) }}</div>
        <div class="stat__foot">
          <span class="dot dot--ink" />
          <span>recognized</span>
        </div>
      </article>
    </section>

    <!-- ── CHARTS ── -->
    <section class="charts">
      <article class="card chart-card">
        <header class="card__head">
          <div>
            <span class="serial">§ 02 · CATEGORY BREAKDOWN</span>
            <h3 class="card__title">分类占比 <em>by amount</em></h3>
          </div>
          <span class="card__count">{{ stats?.category_distribution?.length ?? 0 }} cat.</span>
        </header>
        <div class="chart-wrap">
          <VChart
            v-if="stats && stats.category_distribution?.length"
            :option="pieOption"
            autoresize
            class="echart"
          />
          <div v-else class="empty">暂无数据 · NO DATA</div>
        </div>
      </article>

      <article class="card chart-card">
        <header class="card__head">
          <div>
            <span class="serial">§ 03 · 6-MONTH TREND</span>
            <h3 class="card__title">月度趋势 <em>last six</em></h3>
          </div>
          <span class="card__count">{{ stats?.monthly_trend?.length ?? 0 }} mo.</span>
        </header>
        <div class="chart-wrap">
          <VChart
            v-if="stats && stats.monthly_trend?.length"
            :option="lineOption"
            autoresize
            class="echart"
          />
          <div v-else class="empty">暂无数据 · NO DATA</div>
        </div>
      </article>
    </section>

    <!-- ── WORKFLOW ── -->
    <section class="card workflow">
      <header class="card__head workflow__head">
        <div>
          <span class="serial">§ 04 · MONTHLY ROUTINE</span>
          <h3 class="card__title">一键月度整理 <em>routine</em></h3>
          <p class="card__caption">
            邮箱拉取 → AI识别 → 自动分类 → 文件归档 — 四步串联，可勾选执行。
          </p>
        </div>
        <div class="workflow__cta">
          <button
            v-if="!isRunning"
            class="btn btn--primary"
            :disabled="workflowStarting"
            @click="handleStart"
          >
            <span class="btn__num">↳</span>
            <span>{{ workflowStarting ? '启动中...' : '启动整理' }}</span>
          </button>
          <button v-else class="btn btn--ghost" @click="handleCancel">
            <span class="btn__num">⨯</span>
            <span>取消运行</span>
          </button>
        </div>
      </header>

      <!-- options -->
      <div class="workflow__opts">
        <label
          v-for="opt in flowOptions"
          :key="opt.key"
          class="opt"
          :class="{ 'opt--off': !opt.enabled, 'opt--locked': isRunning }"
        >
          <input
            v-model="opt.enabled"
            type="checkbox"
            class="opt__cb"
            :disabled="isRunning"
          />
          <span class="opt__index">{{ opt.serial }}</span>
          <div class="opt__body">
            <div class="opt__label">{{ opt.label }}</div>
            <div class="opt__hint">{{ opt.hint }}</div>
          </div>
          <span class="opt__check" aria-hidden="true">{{ opt.enabled ? '✓' : '·' }}</span>
        </label>
      </div>

      <!-- progress / steps -->
      <div v-if="workflow" class="workflow__exec">
        <div class="exec__bar">
          <div class="exec__bar-meta">
            <span class="serial">TASK · #{{ workflow.task_id }}</span>
            <span class="exec__status" :class="`exec__status--${workflow.status}`">
              {{ workflow.status.toUpperCase() }}
            </span>
            <span class="exec__current">{{ workflow.current_step || '—' }}</span>
          </div>
          <div class="exec__progress">
            <div class="exec__progress-bar" :style="{ width: workflow.progress + '%' }" />
            <span class="exec__progress-num">{{ workflow.progress }}%</span>
          </div>
        </div>

        <ol class="steps">
          <li
            v-for="(step, idx) in workflow.steps_detail"
            :key="step.key"
            class="step"
            :class="`step--${stepKind(step.status)}`"
          >
            <div class="step__index">{{ String(idx + 1).padStart(2, '0') }}</div>
            <div class="step__body">
              <div class="step__head">
                <span class="step__name">{{ step.step }}</span>
                <span class="step__badge">{{ stepBadge(step.status) }}</span>
              </div>
              <div v-if="step.result" class="step__result">{{ step.result }}</div>
              <div v-if="step.error" class="step__error">⚠ {{ step.error }}</div>
            </div>
            <div class="step__rail">
              <span v-if="step.status === 'processing'" class="step__pulse" />
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- ── RECENT INVOICES ── -->
    <section class="card recent">
      <header class="card__head">
        <div>
          <span class="serial">§ 05 · LATEST ENTRIES</span>
          <h3 class="card__title">最近处理记录 <em>recent</em></h3>
        </div>
        <a class="link" @click.prevent="gotoInvoice()">
          查看全部 →
        </a>
      </header>

      <div class="ledger-table" v-loading="statsLoading">
        <div class="ledger-table__head">
          <div class="col col--no">№</div>
          <div class="col col--inv">发票号码</div>
          <div class="col col--date">日期</div>
          <div class="col col--seller">销售方</div>
          <div class="col col--amount">金额</div>
          <div class="col col--cat">分类</div>
          <div class="col col--status">状态</div>
        </div>
        <div
          v-for="(item, idx) in (stats?.recent_invoices || [])"
          :key="item.id"
          class="ledger-table__row"
          @click="gotoInvoice(item)"
        >
          <div class="col col--no mono">{{ String(idx + 1).padStart(3, '0') }}</div>
          <div class="col col--inv mono">{{ item.invoice_no || '—' }}</div>
          <div class="col col--date mono">{{ item.invoice_date || '—' }}</div>
          <div class="col col--seller">{{ item.seller_name || '—' }}</div>
          <div class="col col--amount mono">
            <span v-if="item.total != null" class="amount">
              <span class="cur">¥</span>{{ formatMoney(item.total) }}
            </span>
            <span v-else class="muted">—</span>
          </div>
          <div class="col col--cat">
            <span v-if="item.category" class="tag">{{ item.category }}</span>
            <span v-else class="muted">未分类</span>
          </div>
          <div class="col col--status">
            <span class="badge" :class="`badge--${statusKind(item.status)}`">
              {{ statusLabel(item.status) }}
            </span>
          </div>
        </div>
        <div v-if="totalRecords === 0 && !statsLoading" class="empty empty--row">
          暂无发票记录 · NO RECORDS
        </div>
      </div>
    </section>
  </article>
</template>

<style scoped>
/* ─── Page frame ─── */
.dash {
  padding: 12px 0 60px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  animation: rise 0.5s ease both;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.rule { height: 1px; background: var(--rule); }

/* ─── Header ─── */
.dash__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 22px;
}
.dash__head-left { max-width: 720px; }
.serial {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--mute);
  text-transform: uppercase;
  display: inline-block;
  margin-bottom: 12px;
}
.dash__title {
  font-family: var(--serif);
  font-weight: 300;
  font-size: clamp(34px, 4vw, 54px);
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0 0 14px;
  color: var(--ink);
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}
.dash__title em {
  font-style: italic;
  color: var(--stamp);
  font-size: 0.5em;
}
.dash__caption {
  font-size: 15px;
  color: var(--mute);
  line-height: 1.6;
  margin: 0;
}
.dash__head-right {
  display: flex;
  align-items: center;
  gap: 24px;
}
.period {
  text-align: right;
  border-right: 1px solid var(--rule-soft);
  padding-right: 24px;
}
.eyebrow {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--mute);
  margin-bottom: 6px;
}
.period__value {
  font-family: var(--serif);
  font-style: italic;
  font-size: 28px;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.dash__stamp {
  width: 56px;
  height: 56px;
  font-size: 24px;
}

/* ─── Stats grid ─── */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--rule);
  background: var(--paper);
}
.stat {
  position: relative;
  padding: 22px 24px 20px;
  border-right: 1px solid var(--rule-soft);
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--paper);
  transition: background 0.18s ease;
}
.stat:last-child { border-right: 0; }
.stat:hover { background: var(--paper-2); }
.stat--accent {
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(184, 65, 14, 0.05), transparent 60%),
    var(--paper);
}
.stat__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.stat__head .serial { margin: 0; }
.stat__unit {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--mute-2);
  text-transform: uppercase;
  border: 1px solid var(--rule-soft);
  padding: 1px 6px;
}
.stat__num {
  font-family: var(--serif);
  font-style: italic;
  font-weight: 400;
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1;
  color: var(--ink);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.stat__num--money {
  color: var(--ink);
  display: flex;
  align-items: baseline;
}
.stat__num--money .cur {
  font-family: var(--serif);
  font-size: 0.6em;
  margin-right: 4px;
  color: var(--stamp);
}
.stat--accent .stat__num { color: var(--ink); }
.stat__foot {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--mute);
}
.dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--stamp);
  box-shadow: 0 0 0 3px var(--stamp-soft);
  animation: pulse 1.6s ease-in-out infinite;
}
.dot--ink { background: var(--ink); box-shadow: 0 0 0 3px rgba(14,14,14,0.06); }
.dot--mute { background: var(--mute-2); box-shadow: none; animation: none; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

/* ─── Card primitives ─── */
.card {
  background: var(--paper);
  border: 1px solid var(--rule);
  padding: 22px 24px;
}
.card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--rule-soft);
  margin-bottom: 18px;
}
.card__head .serial { margin: 0 0 6px; }
.card__title {
  font-family: var(--serif);
  font-weight: 400;
  font-size: 24px;
  margin: 0;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.card__title em {
  font-style: italic;
  color: var(--stamp);
  font-size: 0.55em;
  margin-left: 8px;
  letter-spacing: 0.02em;
}
.card__caption {
  margin: 6px 0 0;
  color: var(--mute);
  font-size: 13px;
  line-height: 1.6;
}
.card__count {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--mute);
  text-transform: uppercase;
  border: 1px solid var(--rule-soft);
  padding: 4px 8px;
}
.link {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink);
  cursor: pointer;
  border-bottom: 1px solid var(--ink);
  padding-bottom: 2px;
  transition: color 0.18s ease, border-color 0.18s ease;
}
.link:hover { color: var(--stamp); border-color: var(--stamp); }

/* ─── Charts ─── */
.charts {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 20px;
}
.chart-card { padding: 22px 24px 24px; }
.chart-wrap {
  height: 320px;
  position: relative;
}
.echart {
  width: 100%;
  height: 100%;
}
.empty {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--mute);
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* ─── Workflow ─── */
.workflow { padding: 24px 26px 28px; }
.workflow__head { align-items: center; }
.workflow__cta { display: flex; gap: 10px; align-self: stretch; align-items: flex-start; }

.btn {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 14px 22px;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: var(--paper);
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn__num {
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  letter-spacing: 0;
  color: var(--paper);
}
.btn:hover { background: var(--stamp); border-color: var(--stamp); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn--ghost {
  background: transparent;
  color: var(--ink);
}
.btn--ghost .btn__num { color: var(--stamp); }
.btn--ghost:hover { background: var(--stamp); border-color: var(--stamp); color: var(--paper); }
.btn--ghost:hover .btn__num { color: var(--paper); }

.workflow__opts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 4px;
}
.opt {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid var(--rule-soft);
  background: var(--paper);
  cursor: pointer;
  transition: all 0.18s ease;
}
.opt:hover { border-color: var(--ink); }
.opt--off { opacity: 0.5; }
.opt--locked { cursor: not-allowed; opacity: 0.6; }
.opt__cb {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.opt__index {
  font-family: var(--serif);
  font-style: italic;
  font-size: 22px;
  color: var(--mute);
  width: 30px;
  text-align: center;
  letter-spacing: -0.02em;
}
.opt__body { flex: 1; min-width: 0; }
.opt__label {
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}
.opt__hint {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--mute);
  margin-top: 4px;
}
.opt__check {
  width: 26px; height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--rule-soft);
  font-family: var(--mono);
  font-size: 14px;
  color: var(--mute);
  transition: all 0.2s ease;
}
.opt:has(.opt__cb:checked) .opt__check {
  border-color: var(--stamp);
  background: var(--stamp);
  color: var(--paper);
}
.opt:has(.opt__cb:checked) .opt__index { color: var(--stamp); }
.opt:has(.opt__cb:checked) {
  border-color: var(--ink);
}

/* ─── Workflow Execution ─── */
.workflow__exec {
  margin-top: 22px;
  padding-top: 22px;
  border-top: 1px solid var(--rule-soft);
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.exec__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.exec__bar-meta { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.exec__bar-meta .serial { margin: 0; }
.exec__status {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  padding: 3px 8px;
  border: 1px solid var(--rule);
  color: var(--ink);
}
.exec__status--processing { background: var(--ink); color: var(--paper); border-color: var(--ink); animation: pulse 1.6s ease-in-out infinite; }
.exec__status--completed { background: var(--paper); border-color: var(--ink); }
.exec__status--failed,
.exec__status--cancelled { background: var(--stamp); color: var(--paper); border-color: var(--stamp); }
.exec__current {
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: var(--ink);
}
.exec__progress {
  flex: 1;
  min-width: 240px;
  position: relative;
  height: 22px;
  border: 1px solid var(--rule);
  background: var(--paper-2);
  display: flex;
  align-items: center;
}
.exec__progress-bar {
  height: 100%;
  background:
    repeating-linear-gradient(
      135deg,
      var(--ink) 0 6px,
      var(--ink-2) 6px 12px
    );
  transition: width 0.5s ease;
}
.exec__progress-num {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--ink);
  mix-blend-mode: difference;
  filter: invert(1);
}

/* steps */
.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0;
  border: 1px solid var(--rule-soft);
}
.step {
  display: grid;
  grid-template-columns: 56px 1fr 6px;
  align-items: stretch;
  padding: 14px 0 14px 0;
  border-right: 1px solid var(--rule-soft);
  border-bottom: 1px solid var(--rule-soft);
  background: var(--paper);
  position: relative;
}
.step:nth-child(2n) { border-right: 0; }
.step:nth-last-child(-n+2) { border-bottom: 0; }
.step__index {
  font-family: var(--serif);
  font-style: italic;
  font-size: 22px;
  color: var(--mute);
  text-align: center;
  align-self: center;
  font-variant-numeric: tabular-nums;
}
.step__body { padding-right: 14px; min-width: 0; }
.step__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.step__name {
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
}
.step__badge {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  padding: 2px 6px;
  border: 1px solid var(--rule-soft);
  color: var(--mute);
  text-transform: uppercase;
}
.step__result {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--mute);
  line-height: 1.5;
}
.step__error {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--stamp);
  margin-top: 4px;
  line-height: 1.5;
}
.step__rail {
  position: relative;
  background: transparent;
}
.step--ok .step__index { color: var(--ink); }
.step--ok .step__badge { color: var(--paper); background: var(--ink); border-color: var(--ink); }
.step--ok .step__rail { background: var(--ink); }
.step--run .step__index { color: var(--stamp); }
.step--run .step__badge { color: var(--paper); background: var(--stamp); border-color: var(--stamp); }
.step--run .step__rail { background: var(--stamp); }
.step--error .step__badge { color: var(--paper); background: var(--stamp-2); border-color: var(--stamp-2); }
.step--error .step__rail { background: var(--stamp-2); }
.step--skip { opacity: 0.45; }
.step--skip .step__rail { background: transparent; }

.step__pulse {
  position: absolute;
  inset: 0;
  background: var(--stamp);
  animation: rail-pulse 1.4s ease-in-out infinite;
}
@keyframes rail-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}

/* ─── Recent table (custom ledger) ─── */
.recent { padding: 22px 0 0; }
.recent .card__head { padding: 0 24px 14px; margin-bottom: 0; }

.ledger-table {
  width: 100%;
  font-variant-numeric: tabular-nums;
}
.ledger-table__head {
  display: grid;
  grid-template-columns: 60px 1.2fr 0.9fr 1.5fr 1.1fr 0.9fr 0.9fr;
  gap: 12px;
  padding: 12px 24px;
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  background: var(--paper-2);
}
.ledger-table__head .col {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--mute);
}
.ledger-table__row {
  display: grid;
  grid-template-columns: 60px 1.2fr 0.9fr 1.5fr 1.1fr 0.9fr 0.9fr;
  gap: 12px;
  padding: 14px 24px;
  border-bottom: 1px solid var(--rule-faint);
  cursor: pointer;
  transition: background 0.16s ease;
  align-items: center;
}
.ledger-table__row:hover { background: var(--paper-2); }
.ledger-table__row:last-child { border-bottom: 0; }
.col {
  font-size: 13px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.col--no { color: var(--mute-2); }
.col--seller { white-space: nowrap; }
.col--amount { font-weight: 500; }
.col--amount .cur { color: var(--stamp); margin-right: 2px; font-family: var(--serif); font-style: italic; }
.col--amount .amount { display: inline-flex; align-items: baseline; }
.mono {
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.02em;
}
.muted { color: var(--mute-2); font-family: var(--mono); font-size: 11px; }

.tag {
  display: inline-block;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  border: 1px solid var(--rule-soft);
  padding: 3px 8px;
  color: var(--ink);
}
.badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 3px 8px;
  border: 1px solid var(--rule);
  color: var(--ink);
}
.badge--ok { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.badge--pending { background: var(--paper); color: var(--mute); border-color: var(--rule-soft); }
.badge--error { background: var(--stamp); color: var(--paper); border-color: var(--stamp); }

.empty--row {
  height: 120px;
  border-bottom: 0;
  font-size: 11px;
}

/* ─── Responsive ─── */
@media (max-width: 1100px) {
  .charts { grid-template-columns: 1fr; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .stat:nth-child(2n) { border-right: 0; }
  .stat:nth-child(-n+2) { border-bottom: 1px solid var(--rule-soft); }
  .workflow__opts { grid-template-columns: 1fr; }
  .steps { grid-template-columns: 1fr; }
  .step { border-right: 0 !important; }
  .step:not(:last-child) { border-bottom: 1px solid var(--rule-soft); }
  .ledger-table__head,
  .ledger-table__row {
    grid-template-columns: 40px 1fr 0.8fr 1fr 1fr 0.8fr;
  }
  .col--seller { display: none; }
}
@media (max-width: 720px) {
  .dash__head { flex-direction: column; align-items: flex-start; }
  .dash__head-right { align-self: flex-end; }
  .stats { grid-template-columns: 1fr; }
  .stat { border-right: 0 !important; border-bottom: 1px solid var(--rule-soft); }
  .stat:last-child { border-bottom: 0; }
  .ledger-table__head { display: none; }
  .ledger-table__row {
    grid-template-columns: 1fr 1fr;
    gap: 4px 12px;
    padding: 14px 24px;
  }
  .col--cat,
  .col--no { display: none; }
}
</style>
