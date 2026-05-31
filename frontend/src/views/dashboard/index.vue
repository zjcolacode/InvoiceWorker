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
  enabled: boolean
}

const flowOptions = reactive<FlowOption[]>([
  { key: 'email_fetch', label: '邮箱发票拉取', hint: 'IMAP 自动归档', enabled: true },
  { key: 'recognize', label: 'AI 识别发票内容', hint: 'qwen-vl OCR', enabled: true },
  { key: 'classify', label: '自动分类', hint: '关键词匹配', enabled: true },
  { key: 'organize', label: '文件归档整理', hint: '按开票日期', enabled: true },
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
    await ElMessageBox.confirm(
      `确认取消正在执行的整理流程 #${workflow.value.task_id}？`,
      '取消流程',
      {
        type: 'warning',
        confirmButtonText: '确认取消',
        cancelButtonText: '继续运行',
      },
    )
    await cancelWorkflow(workflow.value.task_id)
    ElMessage.info('已发送取消请求')
  } catch {
    /* user cancelled */
  }
}

// ─── Charts options ───────────────────────────────────────────
const PALETTE = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#9B59B6', '#3498DB', '#1ABC9C']

const pieOption = computed(() => {
  const list = (stats.value?.category_distribution || []).filter(
    (c) => c.amount > 0 || c.count > 0,
  )
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (p: any) =>
        `${p.name}<br/>¥${(p.value as number).toLocaleString('zh-CN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })} (${p.percent}%)`,
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 'middle',
      itemGap: 12,
      textStyle: { fontSize: 12, color: '#606266' },
    },
    series: [
      {
        name: '分类金额',
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        data: list.map((c, i) => ({
          name: c.name,
          value: Number(c.amount.toFixed(2)),
          itemStyle: { color: PALETTE[i % PALETTE.length] },
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
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['张数', '金额'],
      right: 0,
      top: 0,
      textStyle: { color: '#606266', fontSize: 12 },
    },
    xAxis: {
      type: 'category',
      data: trend.map((t) => t.month),
      axisLabel: { color: '#909399', fontSize: 12 },
    },
    yAxis: [
      {
        type: 'value',
        name: '张',
        nameTextStyle: { color: '#909399' },
        axisLabel: { color: '#909399' },
        splitLine: { lineStyle: { color: '#ebeef5' } },
      },
      {
        type: 'value',
        name: '元',
        nameTextStyle: { color: '#909399' },
        splitLine: { show: false },
        axisLabel: {
          color: '#909399',
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
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#67C23A', width: 2 },
        itemStyle: { color: '#67C23A' },
        data: trend.map((t) => t.count),
      },
      {
        name: '金额',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#409EFF', width: 2 },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.25)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0)' },
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
  return n.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatInt(n: number | null | undefined) {
  if (n == null) return '0'
  return n.toLocaleString('zh-CN')
}

function statusLabel(s?: string) {
  switch (s) {
    case 'pending':
      return '待识别'
    case 'recognized':
      return '已识别'
    case 'verified':
      return '已核验'
    case 'error':
      return '识别失败'
    default:
      return s || '—'
  }
}

function statusTagType(s?: string): 'success' | 'info' | 'warning' | 'danger' {
  switch (s) {
    case 'recognized':
    case 'verified':
      return 'success'
    case 'pending':
      return 'warning'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
}

function stepBadge(s?: string) {
  switch (s) {
    case 'completed':
      return '已完成'
    case 'processing':
      return '运行中'
    case 'failed':
      return '失败'
    case 'skipped':
      return '已跳过'
    default:
      return '待运行'
  }
}

function stepTagType(s?: string): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  switch (s) {
    case 'completed':
      return 'success'
    case 'processing':
      return 'primary'
    case 'failed':
      return 'danger'
    case 'skipped':
      return 'info'
    default:
      return 'info'
  }
}

function gotoInvoice(item?: RecentInvoiceItem) {
  if (item) router.push(`/invoice`)
  else router.push('/invoice')
}

const totalRecords = computed(() => stats.value?.recent_invoices?.length ?? 0)

onMounted(() => {
  loadStats()
})
onBeforeUnmount(() => {
  clearPoll()
})
</script>

<template>
  <div class="dashboard">
    <!-- Stats -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-card__label">本月票据 (张)</div>
          <div class="stat-card__value" v-loading="statsLoading">
            {{ formatInt(stats?.total_invoices) }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-card__label">价税合计 (元)</div>
          <div class="stat-card__value stat-card__value--primary" v-loading="statsLoading">
            ¥ {{ formatMoney(stats?.total_amount) }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-card__label">待识别</div>
          <div class="stat-card__value" v-loading="statsLoading">
            {{ formatInt(stats?.pending_count) }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-card__label">已识别</div>
          <div class="stat-card__value" v-loading="statsLoading">
            {{ formatInt(stats?.recognized_count) }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts -->
    <el-row :gutter="16" class="charts-row">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-header__title">分类占比（按金额）</span>
              <span class="card-header__sub">
                {{ stats?.category_distribution?.length ?? 0 }} 个分类
              </span>
            </div>
          </template>
          <div class="chart-wrap">
            <VChart
              v-if="stats && stats.category_distribution?.length"
              :option="pieOption"
              autoresize
              class="echart"
            />
            <el-empty v-else description="暂无数据" :image-size="80" />
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-header__title">月度趋势（近 6 个月）</span>
              <span class="card-header__sub">
                {{ stats?.monthly_trend?.length ?? 0 }} 个月
              </span>
            </div>
          </template>
          <div class="chart-wrap">
            <VChart
              v-if="stats && stats.monthly_trend?.length"
              :option="lineOption"
              autoresize
              class="echart"
            />
            <el-empty v-else description="暂无数据" :image-size="80" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Workflow -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <div>
            <div class="card-header__title">一键月度整理</div>
            <div class="card-header__caption">
              邮箱拉取 → AI 识别 → 自动分类 → 文件归档
            </div>
          </div>
          <div>
            <el-button
              v-if="!isRunning"
              type="primary"
              :loading="workflowStarting"
              @click="handleStart"
            >
              启动整理
            </el-button>
            <el-button v-else type="danger" @click="handleCancel">取消运行</el-button>
          </div>
        </div>
      </template>

      <div class="workflow-opts">
        <el-checkbox
          v-for="opt in flowOptions"
          :key="opt.key"
          v-model="opt.enabled"
          :disabled="isRunning"
          class="workflow-opt"
        >
          <div class="workflow-opt__body">
            <div class="workflow-opt__label">{{ opt.label }}</div>
            <div class="workflow-opt__hint">{{ opt.hint }}</div>
          </div>
        </el-checkbox>
      </div>

      <div v-if="workflow" class="workflow-exec">
        <div class="workflow-exec__head">
          <span class="workflow-exec__id">任务 #{{ workflow.task_id }}</span>
          <el-tag
            :type="
              workflow.status === 'processing'
                ? 'primary'
                : workflow.status === 'completed'
                  ? 'success'
                  : workflow.status === 'failed' || workflow.status === 'cancelled'
                    ? 'danger'
                    : 'info'
            "
            size="small"
          >
            {{ workflow.status }}
          </el-tag>
          <span v-if="workflow.current_step" class="workflow-exec__current">
            当前：{{ workflow.current_step }}
          </span>
        </div>
        <el-progress
          :percentage="workflow.progress"
          :status="
            workflow.status === 'completed'
              ? 'success'
              : workflow.status === 'failed' || workflow.status === 'cancelled'
                ? 'exception'
                : undefined
          "
        />

        <el-table :data="workflow.steps_detail" size="small" class="workflow-steps">
          <el-table-column type="index" label="#" width="60" align="center" />
          <el-table-column prop="step" label="步骤" min-width="160" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="stepTagType(row.status)" size="small">
                {{ stepBadge(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结果 / 错误" min-width="240">
            <template #default="{ row }">
              <span v-if="row.error" class="text-danger">⚠ {{ row.error }}</span>
              <span v-else-if="row.result">{{ row.result }}</span>
              <span v-else class="text-mute">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- Recent invoices -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-header__title">最近处理记录</span>
          <el-button link type="primary" @click="gotoInvoice()">
            查看全部 →
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="statsLoading"
        :data="stats?.recent_invoices || []"
        empty-text="暂无发票记录"
        @row-click="(row: any) => gotoInvoice(row)"
        style="width: 100%; cursor: pointer"
      >
        <el-table-column type="index" label="#" width="60" align="center" />
        <el-table-column prop="invoice_no" label="发票号码" min-width="140">
          <template #default="{ row }">
            {{ row.invoice_no || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="invoice_date" label="开票日期" width="120">
          <template #default="{ row }">
            {{ row.invoice_date || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="seller_name" label="销售方" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.seller_name || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="金额" width="140" align="right">
          <template #default="{ row }">
            <span v-if="row.total != null">¥ {{ formatMoney(row.total) }}</span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category" type="info" size="small" effect="plain">
              {{ row.category }}
            </el-tag>
            <span v-else class="text-mute">未分类</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-if="totalRecords === 0 && !statsLoading"
        description="暂无发票记录"
        :image-size="60"
      />
    </el-card>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row,
.charts-row {
  margin-bottom: 0;
}

.stats-row > .el-col,
.charts-row > .el-col {
  margin-bottom: 16px;
}

.stat-card {
  border-radius: 4px;
}

.stat-card__label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

.stat-card__value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-card__value--primary {
  color: #409eff;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header__title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.card-header__sub,
.card-header__caption {
  font-size: 12px;
  color: #909399;
}

.chart-wrap {
  height: 320px;
  position: relative;
}

.echart {
  width: 100%;
  height: 100%;
}

.section-card {
  border-radius: 4px;
}

.workflow-opts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.workflow-opt {
  align-items: flex-start;
  margin-right: 0;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafbfc;
  height: auto;
}

.workflow-opt :deep(.el-checkbox__label) {
  white-space: normal;
}

.workflow-opt__body {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.workflow-opt__label {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.workflow-opt__hint {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.workflow-exec {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.workflow-exec__head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.workflow-exec__id {
  font-weight: 500;
  color: #303133;
}

.workflow-exec__current {
  font-size: 13px;
  color: #606266;
}

.workflow-steps {
  margin-top: 8px;
}

.text-mute {
  color: #909399;
}

.text-danger {
  color: #f56c6c;
}

@media (max-width: 768px) {
  .workflow-opts {
    grid-template-columns: 1fr;
  }
}
</style>
