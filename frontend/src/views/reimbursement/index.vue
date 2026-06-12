<template>
  <div class="reimbursement-page">
    <!-- 核销操作区 -->
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <span class="page-title">报销单管理</span>
          <span class="page-subtitle">上传发票明细清单，自动核销系统中的发票记录</span>
        </div>
      </template>

      <!-- 上传区域 -->
      <div class="upload-area">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.csv"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :on-exceed="handleExceed"
          drag
          class="upload-dragger"
          @click="handleUploadClick"
        >
          <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">仅支持 .xlsx / .csv 格式，文件需包含「发票号码」列</div>
          </template>
        </el-upload>
        <el-button
          type="primary"
          :icon="Check"
          :loading="verifying"
          :disabled="!selectedFile"
          @click="handleVerify"
          style="margin-top: 16px"
        >
          核销发票
        </el-button>
      </div>

      <!-- 核销结果 -->
      <div v-if="result" class="result-area">
        <el-divider content-position="left">核销结果</el-divider>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="上传总数">
            <span class="result-number">{{ result.total_count }}</span> 条
          </el-descriptions-item>
          <el-descriptions-item label="成功核销">
            <span class="result-number result-success">{{ result.matched_count }}</span> 条
          </el-descriptions-item>
          <el-descriptions-item label="未匹配">
            <span class="result-number" :class="{ 'result-danger': result.unmatched_count > 0 }">
              {{ result.unmatched_count }}
            </span> 条
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="result.unmatched_count > 0" class="unmatched-area">
          <div class="unmatched-title">未匹配的发票号码：</div>
          <div class="unmatched-list">
            <el-tag
              v-for="(no, idx) in result.unmatched_details"
              :key="idx"
              type="warning"
              size="small"
              class="unmatched-tag"
            >
              {{ no }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 历史记录区 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="page-header">
          <span class="page-title">核销历史记录</span>
        </div>
      </template>

      <el-table
        v-loading="historyLoading"
        :data="historyRecords"
        border
        stripe
        style="width: 100%"
        empty-text="暂无核销记录"
      >
        <el-table-column prop="created_at" label="核销时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="uploader_username" label="操作人" width="110">
          <template #default="{ row }">
            {{ row.uploader_username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="total_count" label="总数" width="80" align="center" />
        <el-table-column prop="matched_count" label="已核销" width="90" align="center">
          <template #default="{ row }">
            <span style="color: #67C23A; font-weight: 600">{{ row.matched_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unmatched_count" label="未匹配" width="90" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.unmatched_count > 0 ? '#F56C6C' : '', fontWeight: 600 }">
              {{ row.unmatched_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.unmatched_count > 0"
              type="primary"
              link
              size="small"
              @click="showUnmatched(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="historyPagination.page"
          v-model:page-size="historyPagination.pageSize"
          :total="historyPagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadHistory"
          @current-change="loadHistory"
        />
      </div>
    </el-card>

    <!-- 未匹配详情弹窗 -->
    <el-dialog v-model="unmatchedDialogVisible" title="未匹配的发票号码" width="560px">
      <div class="unmatched-list">
        <el-tag
          v-for="(no, idx) in currentUnmatchedList"
          :key="idx"
          type="warning"
          size="small"
          class="unmatched-tag"
        >
          {{ no }}
        </el-tag>
      </div>
      <template #footer>
        <el-button @click="unmatchedDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance } from 'element-plus'
import {
  uploadReimbursementFile,
  getReimbursementRecords,
  type ReimbursementResult,
  type ReimbursementRecord,
} from '@/api/reimbursement'

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const verifying = ref(false)
const result = ref<ReimbursementResult | null>(null)

// 历史记录
const historyLoading = ref(false)
const historyRecords = ref<ReimbursementRecord[]>([])
const historyPagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 未匹配弹窗
const unmatchedDialogVisible = ref(false)
const currentUnmatchedList = ref<string[]>([])

function handleFileChange(file: UploadFile) {
  selectedFile.value = (file.raw as File) || null
}

function handleFileRemove() {
  selectedFile.value = null
}

function handleExceed() {
  ElMessage.warning('仅支持上传一个文件，请先移除已选文件')
}

// 修复：原生文件选择器关闭后浏览器窗口焦点丢失，导致页面无法响应点击
function handleUploadClick() {
  setTimeout(() => {
    window.focus()
  }, 300)

  nextTick(() => {
    const input = uploadRef.value?.$el?.querySelector(
      'input[type=file]',
    ) as HTMLInputElement | null
    if (input && !input.dataset.focusBound) {
      input.dataset.focusBound = '1'
      input.addEventListener(
        'cancel',
        () => {
          setTimeout(() => window.focus(), 100)
        },
        { once: true },
      )
    }
  })
}

async function handleVerify() {
  if (!selectedFile.value) return
  verifying.value = true
  result.value = null
  try {
    const res = await uploadReimbursementFile(selectedFile.value)
    result.value = res
    if (res.matched_count > 0) {
      ElMessage.success(`核销完成，成功匹配 ${res.matched_count} 条发票`)
    } else {
      ElMessage.warning('核销完成，但未匹配到任何发票')
    }
    // 清空上传组件
    uploadRef.value?.clearFiles()
    selectedFile.value = null
    // 刷新历史记录
    await loadHistory()
  } catch (e) {
    console.error(e)
  } finally {
    verifying.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await getReimbursementRecords({
      page: historyPagination.page,
      pageSize: historyPagination.pageSize,
    })
    historyRecords.value = res.items
    historyPagination.total = res.total
  } catch (e) {
    console.error(e)
  } finally {
    historyLoading.value = false
  }
}

function showUnmatched(record: ReimbursementRecord) {
  currentUnmatchedList.value = record.unmatched_details || []
  unmatchedDialogVisible.value = true
}

function formatTime(dt?: string | null): string {
  if (!dt) return '-'
  const d = new Date(dt)
  if (isNaN(d.getTime())) return dt
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 初始化加载历史记录
loadHistory()
</script>

<style scoped>
.reimbursement-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-dragger {
  width: 100%;
  max-width: 560px;
}

.result-area {
  margin-top: 8px;
}

.result-number {
  font-weight: 700;
  font-size: 16px;
}

.result-success {
  color: #67C23A;
}

.result-danger {
  color: #F56C6C;
}

.unmatched-area {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fdf6ec;
  border-radius: 6px;
  border: 1px solid #faecd8;
}

.unmatched-title {
  font-size: 13px;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
  font-weight: 500;
}

.unmatched-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.unmatched-tag {
  margin: 0;
}
</style>
