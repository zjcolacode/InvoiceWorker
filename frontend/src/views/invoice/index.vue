<template>
  <div class="invoice-page">
    <!-- 顶部操作栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="showUpload = true">
            <el-icon><Upload /></el-icon> 上传发票
          </el-button>
          <el-button @click="handleBatchRecognize" :disabled="!selectedIds.length">
            批量识别
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索销售方/购买方/内容"
            clearable
            style="width: 200px"
            @clear="loadData"
            @keyup.enter="loadData"
          />
          <el-select v-model="filters.source_type" placeholder="来源类型" clearable style="width: 120px" @change="loadData">
            <el-option label="电子发票" value="pdf" />
            <el-option label="纸质发票" value="paper" />
          </el-select>
          <el-select
            v-model="filters.category"
            placeholder="分类"
            clearable
            style="width: 120px"
            @change="loadData"
          >
            <el-option
              v-for="cat in categoryOptions"
              :key="cat.id"
              :label="cat.name"
              :value="cat.name"
            />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="loadData">
            <el-option label="待识别" value="pending" />
            <el-option label="已识别" value="recognized" />
            <el-option label="识别失败" value="failed" />
          </el-select>
          <el-select
            v-if="isAdmin"
            v-model="filters.owner_user_id"
            placeholder="上传者"
            clearable
            filterable
            style="width: 140px"
            @change="loadData"
          >
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
            style="width: 240px"
          />
          <el-button @click="loadData">
            <el-icon><Search /></el-icon>
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never" style="margin-top: 16px">
      <el-table
        :data="invoiceList"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="invoice_no" label="发票号码" width="120" show-overflow-tooltip />
        <el-table-column prop="invoice_date" label="开票日期" width="110" />
        <el-table-column prop="seller_name" label="销售方" min-width="150" show-overflow-tooltip />
        <el-table-column prop="items" label="开票内容" min-width="150" show-overflow-tooltip />
        <el-table-column prop="total" label="价税合计" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.total">¥ {{ Number(row.total).toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="150">
          <template #default="{ row }">
            <el-select
              v-model="row.category"
              placeholder="选择分类"
              size="small"
              clearable
              class="category-select"
              @change="handleCategoryChange(row as Invoice)"
            >
              <el-option
                v-for="cat in categoryOptions"
                :key="cat.id"
                :label="cat.name"
                :value="cat.name"
              >
                <span class="cat-option">
                  <span class="cat-dot" :style="{ background: cat.color }" />
                  {{ cat.name }}
                </span>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="source_type" label="来源" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'pdf' ? undefined : 'warning'" size="small">
              {{ row.source_type === 'pdf' ? '电子' : '纸质' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isAdmin"
          prop="uploader_username"
          label="上传者"
          width="110"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span>{{ row.uploader_username || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              <el-icon v-if="row.status === 'recognizing'" class="is-loading" style="margin-right: 2px; vertical-align: middle">
                <Loading />
              </el-icon>
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row as Invoice)">详情</el-button>
            <el-button
              link
              type="primary"
              size="small"
              :loading="row.status === 'recognizing'"
              :disabled="row.status === 'recognized' || row.status === 'recognizing'"
              @click="handleRecognize(row.id)"
            >识别</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 上传对话框 -->
    <UploadDialog v-model="showUpload" @success="loadData" />

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="发票详情" width="600px">
      <el-descriptions :column="2" border v-if="currentInvoice">
        <el-descriptions-item label="发票号码">{{ currentInvoice.invoice_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开票日期">{{ currentInvoice.invoice_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="销售方">{{ currentInvoice.seller_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="购买方">{{ currentInvoice.buyer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开票内容" :span="2">{{ currentInvoice.items || '-' }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ currentInvoice.amount ? '¥' + currentInvoice.amount : '-' }}</el-descriptions-item>
        <el-descriptions-item label="税额">{{ currentInvoice.tax ? '¥' + currentInvoice.tax : '-' }}</el-descriptions-item>
        <el-descriptions-item label="价税合计">{{ currentInvoice.total ? '¥' + currentInvoice.total : '-' }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ currentInvoice.category || '-' }}</el-descriptions-item>
        <el-descriptions-item label="来源类型">{{ currentInvoice.source_type === 'pdf' ? '电子发票' : '纸质发票' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentInvoice.status === 'recognized' ? '已识别' : currentInvoice.status === 'failed' ? '识别失败' : '待识别' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Search, Loading } from '@element-plus/icons-vue'
import { getInvoiceList, deleteInvoice, recognizeInvoice, updateInvoiceCategory } from '@/api/invoice'
import type { Invoice } from '@/api/invoice'
import { getCategories, type Category } from '@/api/category'
import { getUsers } from '@/api/user'
import type { UserInfo } from '@/api/auth'
import { setSuppressErrorMessage } from '@/api/request'
import { useUserStore } from '@/stores/user'
import UploadDialog from './upload.vue'

// 当前用户
const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

// 上传对话框
const showUpload = ref(false)

// 分类选项
const categoryOptions = ref<Category[]>([])

// admin 专用：上传者选项
const userOptions = ref<UserInfo[]>([])

// 筛选
const filters = reactive({
  keyword: '',
  source_type: '',
  status: '',
  category: '',
  date_from: '',
  date_to: '',
  owner_user_id: undefined as number | undefined,
})
const dateRange = ref<string[]>([])

// 分页
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 数据
const loading = ref(false)
const invoiceList = ref<Invoice[]>([])
const selectedIds = ref<number[]>([])

// 详情
const detailVisible = ref(false)
const currentInvoice = ref<Invoice | null>(null)

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const res = await getInvoiceList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: filters.keyword || undefined,
      sourceType: filters.source_type || undefined,
      status: filters.status || undefined,
      category: filters.category || undefined,
      dateFrom: filters.date_from || undefined,
      dateTo: filters.date_to || undefined,
      ownerUserId: isAdmin.value ? filters.owner_user_id ?? undefined : undefined,
    })
    invoiceList.value = res.items
    pagination.total = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 日期范围变更
function handleDateChange(val: string[] | null) {
  if (val && val.length === 2) {
    filters.date_from = val[0]
    filters.date_to = val[1]
  } else {
    filters.date_from = ''
    filters.date_to = ''
  }
  loadData()
}

// 选择变更
function handleSelectionChange(rows: Invoice[]) {
  selectedIds.value = rows.map((r) => r.id)
}

// 状态类型映射
function statusType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  if (status === 'recognized') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'recognizing') return 'warning'
  return 'info'
}

// 状态文字映射
function statusText(status: string): string {
  if (status === 'recognized') return '已识别'
  if (status === 'failed') return '识别失败'
  if (status === 'recognizing') return '识别中'
  return '待识别'
}

// 识别
async function handleRecognize(id: number) {
  // 1. 找到当前行，设置为识别中（本地状态）
  const row = invoiceList.value.find((item) => item.id === id)
  if (row) {
    row.status = 'recognizing'
  }

  // 2. 提示用户
  ElMessage.info('正在识别中，请稍候...')

  try {
    // 3. 调用识别API
    const res = await recognizeInvoice(id)
    if (res.success) {
      // 4. 成功
      ElMessage.success('发票识别成功！')
      await loadData()
    } else {
      // 5. 业务失败
      ElMessage.error('识别失败：' + (res.error || '未知错误'))
      if (row) {
        row.status = 'failed'
      }
    }
  } catch (error: unknown) {
    // 6. 异常失败
    const msg = error instanceof Error ? error.message : '未知错误'
    ElMessage.error('识别失败：' + msg)
    if (row) {
      row.status = 'failed'
    }
    console.error(error)
  }
}

// 批量识别（串行调用以避免AI接口并发限流）
async function handleBatchRecognize() {
  if (!selectedIds.value.length) return

  // 拷贝一份当前选中ID，避免后续操作引起选中变化导致循环异常
  const ids = [...selectedIds.value]

  // 先将所有选中行状态设为 识别中（前端立即反馈）
  invoiceList.value.forEach((item) => {
    if (ids.includes(item.id)) {
      item.status = 'recognizing'
    }
  })

  ElMessage.info(`开始批量识别 ${ids.length} 张发票...`)

  // 批量识别期间抑制axios拦截器的自动错误弹窗
  setSuppressErrorMessage(true)

  let successCount = 0
  let failCount = 0

  try {
    // 串行调用 + 失败自动重试1次，避免因网络抖动导致误报失败
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i]
      let success = false
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const res = await recognizeInvoice(id)
          if (res?.success) {
            success = true
            break
          }
        } catch (error) {
          console.error(`识别发票ID=${id} 第${attempt + 1}次失败:`, error)
          // 第一次失败后等待2秒再重试
          if (attempt === 0) {
            await new Promise((r) => setTimeout(r, 2000))
          }
        }
      }
      if (success) {
        successCount++
      } else {
        failCount++
      }
      // 每张处理完后立即刷新数据，让用户实时看到识别结果
      await loadData()
      // loadData 后 invoiceList 被重新赋值，需要重新标记后续未处理行的"识别中"状态
      // 同时把当前刚处理失败的行标记为 failed（数据库可能还是 pending）
      if (!success) {
        const row = invoiceList.value.find((item) => item.id === id)
        if (row) row.status = 'failed'
      }
      // 把后续尚未处理的行恢复为"识别中"
      for (let j = i + 1; j < ids.length; j++) {
        const pendingRow = invoiceList.value.find((item) => item.id === ids[j])
        if (pendingRow && pendingRow.status !== 'recognized') {
          pendingRow.status = 'recognizing'
        }
      }
    }
  } finally {
    // 无论成功失败，恢复自动错误提示
    setSuppressErrorMessage(false)
  }

  if (successCount > 0) {
    ElMessage.success(`成功识别 ${successCount} 张发票`)
  }
  if (failCount > 0) {
    ElMessage.warning(`${failCount} 张发票识别失败`)
  }
}

// 删除
async function handleDelete(id: number) {
  try {
    await deleteInvoice(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

// 显示详情
function showDetail(row: Invoice) {
  currentInvoice.value = row
  detailVisible.value = true
}

// 加载分类选项
async function loadCategories() {
  try {
    const list = await getCategories()
    // 仅展示启用中的分类
    categoryOptions.value = list.filter((c) => c.is_active)
  } catch (e) {
    console.error('加载分类失败', e)
  }
}

// admin 加载全部用户用于上传者筛选
async function loadUsersForAdmin() {
  if (!isAdmin.value) return
  try {
    const res = await getUsers({ page: 1, page_size: 200 })
    userOptions.value = res.items
  } catch (e) {
    console.error('加载用户列表失败', e)
  }
}

// 发票分类变更
async function handleCategoryChange(row: Invoice) {
  try {
    await updateInvoiceCategory(row.id, row.category || '')
    ElMessage.success('分类已更新')
  } catch (e) {
    console.error(e)
    ElMessage.error('分类更新失败')
    await loadData()
  }
}

onMounted(() => {
  loadCategories()
  loadUsersForAdmin()
  loadData()
})
</script>

<style scoped>
.invoice-page {
  padding: 0;
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
  gap: 8px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.category-select {
  width: 100%;
}

.cat-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.cat-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
