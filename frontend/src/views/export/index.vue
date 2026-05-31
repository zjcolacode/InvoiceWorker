<template>
  <div class="export-page">
    <!-- 导出配置 -->
    <el-card class="config-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-block">
            <h3 class="title">数据导出</h3>
          </div>
          <span class="caption">按月、按分类、按明细 — 一键生成 Excel，离线交付。</span>
        </div>
      </template>

      <el-form
        :model="form"
        label-width="100px"
        label-position="right"
        class="export-form"
      >
        <el-form-item label="导出模式">
          <el-radio-group v-model="form.mode" class="mode-group">
            <el-radio-button value="monthly_summary">
              <div class="mode-cell">
                <span class="mode-name">月度汇总表</span>
                <span class="mode-desc">按日期汇总每天数据</span>
              </div>
            </el-radio-button>
            <el-radio-button value="category_summary">
              <div class="mode-cell">
                <span class="mode-name">分类汇总表</span>
                <span class="mode-desc">按费用类别统计</span>
              </div>
            </el-radio-button>
            <el-radio-button value="detail">
              <div class="mode-cell">
                <span class="mode-name">明细表</span>
                <span class="mode-desc">所有发票详细列表</span>
              </div>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="所属月份">
          <el-date-picker
            v-model="form.month"
            type="month"
            placeholder="选择年月"
            format="YYYY 年 MM 月"
            value-format="YYYY-MM"
            style="width: 220px"
            :clearable="false"
          />
        </el-form-item>

        <el-form-item label="分类筛选">
          <el-select
            v-model="form.category"
            placeholder="全部分类"
            clearable
            filterable
            style="width: 220px"
            :loading="categoryLoading"
          >
            <el-option
              v-for="c in categories"
              :key="c.id"
              :label="c.name"
              :value="c.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="来源类型">
          <el-select
            v-model="form.source_type"
            placeholder="全部"
            clearable
            style="width: 220px"
          >
            <el-option label="全部" :value="''" />
            <el-option label="电子发票 (PDF)" value="pdf" />
            <el-option label="纸质发票" value="paper" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :icon="Download"
            :loading="generating"
            size="large"
            @click="handleGenerate"
          >
            生成并导出
          </el-button>
          <el-button :icon="Refresh" @click="resetForm" :disabled="generating">
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 结果提示 -->
      <transition name="el-fade-in">
        <div v-if="lastResult" class="result-banner">
          <el-icon class="result-icon"><CircleCheckFilled /></el-icon>
          <div class="result-text">
            <div class="result-title">
              已生成
              <el-tag size="small" type="primary" effect="plain" class="mode-tag">
                {{ modeLabel(lastResultMode) }}
              </el-tag>
              ，共
              <strong>{{ lastResult.record_count }}</strong> 条记录
            </div>
            <div class="result-sub">
              文件：<code>{{ lastResult.filename }}</code>
            </div>
          </div>
          <div class="result-actions">
            <el-button
              type="primary"
              :icon="Download"
              size="small"
              @click="handleDownload(lastResult!.filename)"
              :loading="downloadingMap[lastResult.filename]"
            >
              立即下载
            </el-button>
          </div>
        </div>
      </transition>
    </el-card>

    <!-- 导出历史 -->
    <el-card class="history-card" shadow="never">
      <template #header>
        <div class="card-header simple">
          <h3 class="sub-title">导出历史</h3>
          <el-button :icon="Refresh" link @click="loadHistory" :loading="historyLoading">
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="historyLoading"
        :data="historyList"
        border
        stripe
        empty-text="暂无导出记录"
        style="width: 100%"
      >
        <el-table-column label="文件名" min-width="320">
          <template #default="{ row }">
            <el-icon class="file-icon"><Document /></el-icon>
            <span class="file-name">{{ row.filename }}</span>
          </template>
        </el-table-column>
        <el-table-column label="导出模式" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="modeTagType(row.mode)" effect="plain" size="small">
              {{ modeLabel(row.mode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="120" align="right">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="200" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :loading="downloadingMap[row.filename]"
              @click="handleDownload(row.filename)"
            >
              下载
            </el-button>
            <el-popconfirm
              title="确认删除该导出文件？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row.filename)"
            >
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheckFilled,
  Document,
  Download,
  Refresh,
} from '@element-plus/icons-vue'

import {
  deleteExportFile,
  downloadExport,
  generateExport,
  getExportHistory,
  type ExportFile,
  type ExportMode,
  type ExportResult,
} from '@/api/export'
import { getCategories, type Category } from '@/api/category'

// ----------------------------- state ---------------------------------------
const today = new Date()
const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

const form = reactive<{
  mode: ExportMode
  month: string
  category: string
  source_type: string
}>({
  mode: 'detail',
  month: defaultMonth,
  category: '',
  source_type: '',
})

const categories = ref<Category[]>([])
const categoryLoading = ref(false)

const generating = ref(false)
const lastResult = ref<ExportResult | null>(null)
const lastResultMode = ref<ExportMode>('detail')

const historyLoading = ref(false)
const historyList = ref<ExportFile[]>([])
const downloadingMap = reactive<Record<string, boolean>>({})

// ----------------------------- helpers -------------------------------------
const MODE_LABEL: Record<string, string> = {
  monthly: '月度汇总',
  monthly_summary: '月度汇总',
  category: '分类汇总',
  category_summary: '分类汇总',
  detail: '明细表',
}
const MODE_TAG: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
  monthly: 'primary',
  monthly_summary: 'primary',
  category: 'success',
  category_summary: 'success',
  detail: 'warning',
}

function modeLabel(mode?: string | null) {
  if (!mode) return '未知'
  return MODE_LABEL[mode] || mode
}

function modeTagType(mode?: string | null) {
  if (!mode) return 'info'
  return MODE_TAG[mode] || 'info'
}

function formatSize(bytes: number) {
  if (!bytes && bytes !== 0) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function parseMonth(value: string): { year: number; month: number } | null {
  if (!value) return null
  const m = value.match(/^(\d{4})-(\d{1,2})$/)
  if (!m) return null
  return { year: Number(m[1]), month: Number(m[2]) }
}

// ----------------------------- actions -------------------------------------
async function loadCategories() {
  categoryLoading.value = true
  try {
    categories.value = await getCategories()
  } catch (e) {
    console.error(e)
  } finally {
    categoryLoading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    historyList.value = await getExportHistory()
  } catch (e) {
    console.error(e)
  } finally {
    historyLoading.value = false
  }
}

function resetForm() {
  form.mode = 'detail'
  form.month = defaultMonth
  form.category = ''
  form.source_type = ''
  lastResult.value = null
}

async function handleGenerate() {
  const ym = parseMonth(form.month)
  if (!ym) {
    ElMessage.warning('请选择年月')
    return
  }

  generating.value = true
  lastResult.value = null
  try {
    const res = await generateExport({
      mode: form.mode,
      year: ym.year,
      month: ym.month,
      category: form.category || undefined,
      source_type: form.source_type || undefined,
    })
    lastResult.value = res
    lastResultMode.value = form.mode
    if (res.record_count === 0) {
      ElMessage.warning('已生成空表：所选条件下没有匹配的发票')
    } else {
      ElMessage.success(`成功生成，共 ${res.record_count} 条记录`)
    }
    await loadHistory()
  } catch (e) {
    console.error(e)
  } finally {
    generating.value = false
  }
}

async function handleDownload(filename: string) {
  downloadingMap[filename] = true
  try {
    await downloadExport(filename)
  } catch (e) {
    console.error(e)
    ElMessage.error('下载失败')
  } finally {
    downloadingMap[filename] = false
  }
}

async function handleDelete(filename: string) {
  try {
    await deleteExportFile(filename)
    ElMessage.success('已删除')
    if (lastResult.value?.filename === filename) {
      lastResult.value = null
    }
    await loadHistory()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadCategories()
  loadHistory()
})
</script>

<style scoped>
.export-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-card,
.history-card {
  border-radius: 4px;
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.card-header.simple {
  align-items: center;
}

.title-block {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.sub-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.caption {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.export-form {
  margin-top: 4px;
}

.mode-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.mode-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 12px;
  line-height: 1.3;
}

.mode-name {
  font-size: 14px;
  font-weight: 600;
}

.mode-desc {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

:deep(.el-radio-button.is-active) .mode-desc {
  color: rgba(255, 255, 255, 0.8);
}

.result-banner {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: linear-gradient(
    90deg,
    rgba(64, 158, 255, 0.08),
    rgba(103, 194, 58, 0.08)
  );
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.result-icon {
  font-size: 26px;
  color: var(--el-color-success);
}

.result-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-title {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.result-title strong {
  color: var(--el-color-primary);
  margin: 0 2px;
}

.result-sub code {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 1px 6px;
  border-radius: 3px;
  color: var(--el-text-color-regular);
}

.mode-tag {
  margin: 0 4px;
}

.file-icon {
  vertical-align: middle;
  color: var(--el-color-primary);
  margin-right: 6px;
}

.file-name {
  vertical-align: middle;
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 12.5px;
  color: var(--el-text-color-regular);
}
</style>
