<template>
  <div class="print-page">
    <!-- 顶部筛选 / 操作区 -->
    <el-card class="toolbar-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-block">
            <h3 class="title">打印管理</h3>
          </div>
          <span class="caption">
            勾选电子发票 · 按 A4 每页 2 张排版 · 一键合并为可打印 PDF
          </span>
        </div>
      </template>

      <div class="toolbar">
        <div class="toolbar-left">
          <el-button
            type="primary"
            :icon="Printer"
            :disabled="!selectedIds.length"
            :loading="generating"
            @click="handleGenerate"
          >
            生成打印 PDF
          </el-button>
          <span class="selection-info">
            已选择
            <strong>{{ selectedIds.length }}</strong>
            张发票
            <template v-if="selectedIds.length">
              （约
              <strong>{{ Math.ceil(selectedIds.length / 2) }}</strong>
              页）
            </template>
          </span>
        </div>

        <div class="toolbar-right">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索销售方/购买方/内容"
            clearable
            style="width: 220px"
            @clear="loadInvoices"
            @keyup.enter="loadInvoices"
          />
          <el-select
            v-model="filters.category"
            placeholder="分类"
            clearable
            style="width: 140px"
            @change="loadInvoices"
          >
            <el-option
              v-for="cat in categoryOptions"
              :key="cat.id"
              :label="cat.name"
              :value="cat.name"
            />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="handleDateChange"
          />
          <el-button :icon="Refresh" @click="loadInvoices" :loading="loading">
            刷新
          </el-button>
        </div>
      </div>

      <!-- 生成结果横幅 -->
      <transition name="el-fade-in">
        <div v-if="lastResult" class="result-banner">
          <el-icon class="result-icon"><CircleCheckFilled /></el-icon>
          <div class="result-text">
            <div class="result-title">
              已生成打印 PDF：包含
              <strong>{{ lastResult.invoice_count }}</strong> 张发票 ·
              共 <strong>{{ lastResult.page_count }}</strong> 页
            </div>
            <div class="result-sub">
              文件：<code>{{ lastResult.filename }}</code>
            </div>
          </div>
          <div class="result-actions">
            <el-button
              :icon="View"
              size="small"
              @click="handlePreview(lastResult!.filename)"
              :loading="previewingMap[lastResult.filename]"
            >
              预览
            </el-button>
            <el-button
              type="primary"
              :icon="Download"
              size="small"
              @click="handleDownload(lastResult!.filename)"
              :loading="downloadingMap[lastResult.filename]"
            >
              下载
            </el-button>
          </div>
        </div>
      </transition>
    </el-card>

    <!-- 电子发票列表 -->
    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="card-header simple">
          <h3 class="sub-title">电子发票（仅显示 source_type = pdf）</h3>
          <span class="caption">
            共 <strong>{{ pagination.total }}</strong> 张可打印
          </span>
        </div>
      </template>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="invoiceList"
        empty-text="暂无电子发票"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="48" reserve-selection />
        <el-table-column prop="invoice_no" label="发票号码" width="130" show-overflow-tooltip />
        <el-table-column prop="invoice_date" label="开票日期" width="110" />
        <el-table-column
          prop="seller_name"
          label="销售方"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="items"
          label="开票内容"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column prop="total" label="价税合计" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.total">¥ {{ Number(row.total).toFixed(2) }}</span>
            <span v-else class="text-mute">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" effect="plain">
              {{ row.category }}
            </el-tag>
            <span v-else class="text-mute">未分类</span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80" align="center">
          <template #default>
            <el-tag size="small" type="primary" effect="plain">电子</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadInvoices"
          @current-change="loadInvoices"
        />
      </div>
    </el-card>

    <!-- 打印历史 -->
    <el-card class="history-card" shadow="never">
      <template #header>
        <div class="card-header simple">
          <h3 class="sub-title">打印历史</h3>
          <el-button
            :icon="Refresh"
            link
            @click="loadHistory"
            :loading="historyLoading"
          >
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="historyLoading"
        :data="historyList"
        empty-text="暂无打印记录"
        style="width: 100%"
      >
        <el-table-column label="文件名" min-width="340">
          <template #default="{ row }">
            <el-icon class="file-icon"><Document /></el-icon>
            <span class="file-name">{{ row.filename }}</span>
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
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              size="small"
              :loading="previewingMap[row.filename]"
              @click="handlePreview(row.filename)"
            >
              预览
            </el-button>
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
              title="确认删除该打印文件？"
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

    <!-- PDF 预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="`预览：${previewName}`"
      width="80%"
      top="5vh"
      destroy-on-close
      @closed="closePreview"
    >
      <div class="preview-wrap">
        <iframe
          v-if="previewUrl"
          :src="previewUrl"
          class="preview-frame"
        ></iframe>
        <el-empty v-else description="加载预览中..." />
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button
          type="primary"
          :icon="Download"
          @click="handleDownload(previewName)"
          :loading="downloadingMap[previewName]"
        >
          下载
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheckFilled,
  Document,
  Download,
  Printer,
  Refresh,
  View,
} from '@element-plus/icons-vue'

import { getInvoiceList, type Invoice } from '@/api/invoice'
import { getCategories, type Category } from '@/api/category'
import {
  deletePrintFile,
  downloadPrintFile,
  generatePrintPdf,
  getPreviewObjectUrl,
  listPrintFiles,
  type GeneratePrintResult,
  type PrintFile,
} from '@/api/print'

// ---------------------------- state -----------------------------------------
const tableRef = ref<{ clearSelection: () => void } | null>(null)

const filters = reactive({
  keyword: '',
  category: '',
  date_from: '',
  date_to: '',
})
const dateRange = ref<string[]>([])

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const loading = ref(false)
const invoiceList = ref<Invoice[]>([])
const selectedIds = ref<number[]>([])

const categoryOptions = ref<Category[]>([])

const generating = ref(false)
const lastResult = ref<GeneratePrintResult | null>(null)

const historyLoading = ref(false)
const historyList = ref<PrintFile[]>([])

const downloadingMap = reactive<Record<string, boolean>>({})
const previewingMap = reactive<Record<string, boolean>>({})

// 预览相关
const previewVisible = ref(false)
const previewName = ref('')
const previewUrl = ref('')

// ---------------------------- helpers ---------------------------------------
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

// ---------------------------- actions ---------------------------------------
async function loadCategories() {
  try {
    const list = await getCategories()
    categoryOptions.value = list.filter((c) => c.is_active)
  } catch (e) {
    console.error('加载分类失败', e)
  }
}

async function loadInvoices() {
  loading.value = true
  try {
    const res = await getInvoiceList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: filters.keyword || undefined,
      sourceType: 'pdf', // 仅显示电子发票
      category: filters.category || undefined,
      dateFrom: filters.date_from || undefined,
      dateTo: filters.date_to || undefined,
    })
    invoiceList.value = res.items
    pagination.total = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    historyList.value = await listPrintFiles()
  } catch (e) {
    console.error(e)
  } finally {
    historyLoading.value = false
  }
}

function handleDateChange(val: string[] | null) {
  if (val && val.length === 2) {
    filters.date_from = val[0]
    filters.date_to = val[1]
  } else {
    filters.date_from = ''
    filters.date_to = ''
  }
  loadInvoices()
}

function handleSelectionChange(rows: Invoice[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function handleGenerate() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请至少勾选一张发票')
    return
  }
  generating.value = true
  lastResult.value = null
  try {
    const res = await generatePrintPdf([...selectedIds.value])
    lastResult.value = res
    ElMessage.success(
      `已生成 ${res.page_count} 页 / ${res.invoice_count} 张发票`,
    )
    // 清空选中状态，避免重复打印
    tableRef.value?.clearSelection()
    await loadHistory()
  } catch (e) {
    console.error(e)
  } finally {
    generating.value = false
  }
}

async function handleDownload(filename: string) {
  if (!filename) return
  downloadingMap[filename] = true
  try {
    await downloadPrintFile(filename)
  } catch (e) {
    console.error(e)
    ElMessage.error('下载失败')
  } finally {
    downloadingMap[filename] = false
  }
}

async function handlePreview(filename: string) {
  if (!filename) return
  previewingMap[filename] = true
  try {
    // 释放上一次的 ObjectURL
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
    const url = await getPreviewObjectUrl(filename)
    previewUrl.value = url
    previewName.value = filename
    previewVisible.value = true
  } catch (e) {
    console.error(e)
    ElMessage.error('预览失败')
  } finally {
    previewingMap[filename] = false
  }
}

function closePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  previewName.value = ''
}

async function handleDelete(filename: string) {
  try {
    await deletePrintFile(filename)
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
  loadInvoices()
  loadHistory()
})
</script>

<style scoped>
.print-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card,
.list-card,
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

.caption strong {
  color: var(--el-color-primary);
  margin: 0 2px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.selection-info {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.selection-info strong {
  color: var(--el-color-primary);
  font-weight: 600;
  margin: 0 2px;
}

.result-banner {
  margin-top: 12px;
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

.result-actions {
  display: flex;
  gap: 6px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-mute {
  color: var(--el-text-color-secondary);
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

.preview-wrap {
  width: 100%;
  height: 70vh;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  overflow: hidden;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}
</style>
