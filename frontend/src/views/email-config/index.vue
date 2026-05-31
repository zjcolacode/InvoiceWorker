<template>
  <div class="email-config-page">
    <!-- 授权码提示 -->
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="hint-alert"
    >
      <template #title>
        <span style="font-weight: 600">授权码 ≠ 登录密码</span>
      </template>
      <template #default>
        <p style="margin: 4px 0 0; font-size: 13px; line-height: 1.55">
          QQ / 163 / 网易企业邮 等服务需要在邮箱网页端开启 IMAP 服务并申请<strong>"授权码"</strong>，
          再填写到下方密码字段。常见服务器：
          <code>imap.qq.com</code> / <code>imap.163.com</code> /
          <code>imap.exmail.qq.com</code> / <code>outlook.office365.com</code>。
        </p>
      </template>
    </el-alert>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-card__label">已配置邮箱</div>
          <div class="metric-card__value">{{ configs.length }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-card__label">活跃中</div>
          <div class="metric-card__value">{{ activeCount }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-card__label">最近一次拉取</div>
          <div class="metric-card__value metric-card__value--small">
            {{ lastPollLabel }}
          </div>
          <div class="metric-card__sub">{{ lastPollRelative }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-card__label">今日拉取邮件</div>
          <div class="metric-card__value">{{ todayHarvest }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 配置列表 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-header__title">已登记的邮箱</span>
          <div>
            <el-button :icon="Refresh" @click="loadConfigs" :loading="loading">
              刷新
            </el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">
              登记新邮箱
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="configs"
        empty-text="尚无任何邮箱配置 — 点击「登记新邮箱」开始"
        stripe
        style="width: 100%"
      >
        <el-table-column type="index" label="#" width="60" align="center" />
        <el-table-column label="邮箱" min-width="240">
          <template #default="{ row }">
            <span style="margin-right: 8px">{{ row.email_address }}</span>
            <el-tag
              :type="row.is_active ? 'success' : 'info'"
              size="small"
              effect="plain"
            >
              {{ row.is_active ? '启用' : '已暂停' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="服务器 / 端口" min-width="220">
          <template #default="{ row }">
            <span>{{ row.imap_server }}:{{ row.port }}</span>
            <el-tag
              v-if="row.use_ssl"
              type="primary"
              size="small"
              effect="plain"
              style="margin-left: 8px"
            >
              SSL
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="拉取间隔" width="120">
          <template #default="{ row }">
            {{ row.check_interval_minutes }} 分钟
          </template>
        </el-table-column>
        <el-table-column label="最后拉取" width="180">
          <template #default="{ row }">
            <span v-if="row.last_check_at">
              {{ formatDate(row.last_check_at, 'YYYY-MM-DD HH:mm') }}
            </span>
            <span v-else class="text-mute">尚未拉取</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="right" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :loading="fetchingId === row.id"
              @click="handleFetch(row as EmailConfigItem)"
            >
              立即拉取
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              @click="openEdit(row as EmailConfigItem)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDelete(row as EmailConfigItem)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 拉取的邮件列表 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-header__title">拉取的邮件</span>
          <div class="card-header__actions">
            <el-radio-group
              v-model="messageFilter"
              size="small"
              @change="onFilterChange"
            >
              <el-radio-button value="pending">待导入</el-radio-button>
              <el-radio-button value="imported">已导入</el-radio-button>
              <el-radio-button value="all">全部</el-radio-button>
            </el-radio-group>
            <el-button :icon="Refresh" @click="loadMessages" :loading="messagesLoading">
              刷新
            </el-button>
            <el-button
              type="primary"
              :disabled="selectedMessageIds.length === 0 || importing"
              :loading="importing"
              @click="handleImport"
            >
              导入选中 ({{ selectedMessageIds.length }})
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        ref="messageTableRef"
        v-loading="messagesLoading"
        :data="messages"
        empty-text="暂无拉取到的邮件"
        stripe
        style="width: 100%"
        @selection-change="handleMessageSelect"
      >
        <el-table-column
          type="selection"
          width="50"
          :selectable="(row: EmailMessageItem) => !row.is_imported"
        />
        <el-table-column
          label="邮件主题"
          prop="subject"
          min-width="220"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row.subject">{{ row.subject }}</span>
            <span v-else class="text-mute">(无主题)</span>
          </template>
        </el-table-column>
        <el-table-column
          label="发件人"
          prop="sender"
          width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row.sender">{{ row.sender }}</span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
        <el-table-column
          label="附件名"
          prop="attachment_name"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row.attachment_name">{{ row.attachment_name }}</span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100" align="right">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="收件时间" width="170">
          <template #default="{ row }">
            <span v-if="row.received_at">
              {{ formatDate(row.received_at, 'YYYY-MM-DD HH:mm') }}
            </span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.is_imported ? 'success' : 'info'"
              size="small"
              effect="plain"
            >
              {{ row.is_imported ? '已导入' : '待导入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="right" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDeleteMessage(row as EmailMessageItem)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="messagePage"
          :page-size="messagePageSize"
          :total="messageTotal"
          @current-change="onMessagePageChange"
        />
      </div>
    </el-card>

    <!-- 拉取日志 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-header__title">拉取日志</span>
          <el-button :icon="Refresh" @click="loadLogs" :loading="logLoading">
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="logLoading"
        :data="logs"
        empty-text="尚无拉取记录"
        stripe
        style="width: 100%"
      >
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            <span v-if="row.fetch_time">
              {{ formatDate(row.fetch_time, 'YYYY-MM-DD HH:mm:ss') }}
            </span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="220">
          <template #default="{ row }">
            {{ row.email_address || `#${row.config_id}` }}
          </template>
        </el-table-column>
        <el-table-column
          prop="total_emails_checked"
          label="检索"
          width="100"
          align="center"
        />
        <el-table-column label="新增发票" width="120" align="center">
          <template #default="{ row }">
            <span :class="row.new_invoices_count ? 'text-success' : 'text-mute'">
              +{{ row.new_invoices_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="240">
          <template #default="{ row }">
            <span v-if="row.error_message" class="text-danger">
              {{ row.error_message }}
            </span>
            <span v-else class="text-mute">—</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="logPage"
          :page-size="logPageSize"
          :total="logTotal"
          @current-change="onLogPageChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="540px"
      align-center
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="邮箱地址" prop="email_address">
          <el-input
            v-model="form.email_address"
            placeholder="例如 finance@your-company.com"
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="IMAP 服务器" prop="imap_server">
          <el-input
            v-model="form.imap_server"
            placeholder="imap.qq.com / imap.163.com / imap.exmail.qq.com"
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="端口" prop="port">
              <el-input-number
                v-model="form.port"
                :min="1"
                :max="65535"
                :controls="false"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="启用 SSL" prop="use_ssl">
              <el-switch v-model="form.use_ssl" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="拉取频率" prop="check_interval_minutes">
              <el-select v-model="form.check_interval_minutes" style="width: 100%">
                <el-option :value="15" label="每 15 分钟" />
                <el-option :value="30" label="每 30 分钟" />
                <el-option :value="60" label="每 1 小时" />
                <el-option :value="120" label="每 2 小时" />
                <el-option :value="360" label="每 6 小时" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="密码 / 授权码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editing ? '留空则不修改' : '从邮箱网页端获取的授权码'"
            autocomplete="new-password"
          />
        </el-form-item>

        <transition name="el-fade-in">
          <el-alert
            v-if="probeResult"
            :type="probeResult.success ? 'success' : 'error'"
            :title="probeResult.message"
            :closable="false"
            show-icon
            style="margin-top: 4px"
          />
        </transition>
      </el-form>

      <template #footer>
        <el-button :loading="probing" @click="handleProbe">
          {{ probing ? '握手中…' : '测试连接' }}
        </el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">
          {{ editing ? '保存修改' : '登记邮箱' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  createEmailConfig,
  deleteEmailConfig,
  deleteEmailMessage,
  getEmailConfigs,
  getEmailMessages,
  getFetchLogs,
  importEmailMessages,
  manualFetch,
  testConnection,
  updateEmailConfig,
  type EmailConfigItem,
  type EmailFetchLogItem,
  type EmailMessageItem,
  type EmailMessagePage,
  type EmailTestResult,
} from '@/api/email'
import { formatDate } from '@/utils'

/* ------------------------- state ------------------------- */
const configs = ref<EmailConfigItem[]>([])
const loading = ref(false)
const fetchingId = ref<number | null>(null)

const logs = ref<EmailFetchLogItem[]>([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(10)
const logLoading = ref(false)

/* 拉取的邮件列表 */
const messages = ref<EmailMessageItem[]>([])
const messageTotal = ref(0)
const messagePage = ref(1)
const messagePageSize = ref(10)
const messagesLoading = ref(false)
const messageFilter = ref<'pending' | 'imported' | 'all'>('pending')
const selectedMessageIds = ref<number[]>([])
const importing = ref(false)

const dialogVisible = ref(false)
const editing = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)
const probing = ref(false)
const probeResult = ref<EmailTestResult | null>(null)

const form = reactive({
  email_address: '',
  imap_server: '',
  port: 993,
  password: '',
  check_interval_minutes: 30,
  use_ssl: true,
})

const rules: FormRules = {
  email_address: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  imap_server: [{ required: true, message: '请输入 IMAP 服务器', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  check_interval_minutes: [
    { required: true, message: '请选择拉取频率', trigger: 'change' },
  ],
}

/* ------------------------- computed ------------------------- */
const dialogTitle = computed(() => (editing.value ? '修改邮箱配置' : '登记新邮箱'))

const activeCount = computed(() => configs.value.filter((c) => c.is_active).length)

const lastPoll = computed<Date | null>(() => {
  let latest: Date | null = null
  for (const c of configs.value) {
    if (!c.last_check_at) continue
    const d = new Date(c.last_check_at)
    if (!latest || d > latest) latest = d
  }
  return latest
})

const lastPollLabel = computed(() => {
  if (!lastPoll.value) return '—'
  return formatDate(lastPoll.value, 'HH:mm:ss')
})

const lastPollRelative = computed(() => {
  if (!lastPoll.value) return '从未'
  const diff = Math.max(0, Date.now() - lastPoll.value.getTime())
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
})

const todayHarvest = computed(() => {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth()
  const d = today.getDate()
  let total = 0
  for (const log of logs.value) {
    if (!log.fetch_time) continue
    const dt = new Date(log.fetch_time)
    if (dt.getFullYear() === y && dt.getMonth() === m && dt.getDate() === d) {
      total += log.new_invoices_count || 0
    }
  }
  return total
})

/* ------------------------- helpers ------------------------- */
function statusLabel(s: string) {
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    partial: '部分成功',
  }
  return map[s] || s
}

function statusTagType(s: string): 'success' | 'warning' | 'danger' | 'info' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'partial') return 'warning'
  return 'info'
}

function formatFileSize(bytes: number | null | undefined): string {
  const n = Number(bytes ?? 0)
  if (!n || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

/* ------------------------- data loaders ------------------------- */
async function loadConfigs() {
  loading.value = true
  try {
    const data = (await getEmailConfigs()) as unknown as EmailConfigItem[]
    configs.value = data || []
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  logLoading.value = true
  try {
    const data = (await getFetchLogs({
      page: logPage.value,
      pageSize: logPageSize.value,
    })) as unknown as { total: number; items: EmailFetchLogItem[] }
    logs.value = data?.items || []
    logTotal.value = data?.total || 0
  } catch {
    /* swallow */
  } finally {
    logLoading.value = false
  }
}

function onLogPageChange(p: number) {
  logPage.value = p
  loadLogs()
}

/* 拉取邮件列表加载 / 勾选 / 导入 / 删除 */
async function loadMessages() {
  messagesLoading.value = true
  try {
    const isImported =
      messageFilter.value === 'all' ? undefined : messageFilter.value === 'imported'
    const data = (await getEmailMessages({
      page: messagePage.value,
      pageSize: messagePageSize.value,
      isImported,
    })) as unknown as EmailMessagePage
    messages.value = data?.items || []
    messageTotal.value = data?.total || 0
  } catch {
    /* swallow */
  } finally {
    messagesLoading.value = false
  }
}

function onFilterChange() {
  messagePage.value = 1
  selectedMessageIds.value = []
  loadMessages()
}

function onMessagePageChange(p: number) {
  messagePage.value = p
  loadMessages()
}

function handleMessageSelect(rows: EmailMessageItem[]) {
  selectedMessageIds.value = rows.filter((r) => !r.is_imported).map((r) => r.id)
}

async function handleImport() {
  if (selectedMessageIds.value.length === 0) return
  importing.value = true
  try {
    const res = (await importEmailMessages(
      selectedMessageIds.value,
    )) as unknown as {
      success: boolean
      imported_count: number
      skipped_count: number
      requested: number
    }
    if (res?.skipped_count) {
      ElMessage.warning(
        `导入完成 · 成功 ${res.imported_count} 张 · 跳过 ${res.skipped_count} 张`,
      )
    } else {
      ElMessage.success(`已导入 ${res?.imported_count ?? 0} 张发票`)
    }
    selectedMessageIds.value = []
    await loadMessages()
  } catch {
    /* swallow */
  } finally {
    importing.value = false
  }
}

async function handleDeleteMessage(row: EmailMessageItem) {
  try {
    await ElMessageBox.confirm(
      row.is_imported
        ? `该邮件已导入发票管理，删除后仅移除拉取记录，不影响已导入的发票。是否继续？`
        : `确认删除该邮件记录？未导入的附件临时文件也将被删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteEmailMessage(row.id)
    ElMessage.success('已删除')
    await loadMessages()
  } catch {
    /* swallow */
  }
}

/* ------------------------- form actions ------------------------- */
function resetForm() {
  form.email_address = ''
  form.imap_server = ''
  form.port = 993
  form.password = ''
  form.check_interval_minutes = 30
  form.use_ssl = true
  probeResult.value = null
  formRef.value?.clearValidate()
}

function openCreate() {
  editing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: EmailConfigItem) {
  editing.value = true
  editingId.value = row.id
  form.email_address = row.email_address
  form.imap_server = row.imap_server
  form.port = row.port
  form.password = ''
  form.check_interval_minutes = row.check_interval_minutes
  form.use_ssl = row.use_ssl
  probeResult.value = null
  dialogVisible.value = true
}

async function handleProbe() {
  if (!form.email_address || !form.imap_server || !form.password) {
    ElMessage.warning('请先填写邮箱、IMAP 服务器、密码后再测试连接')
    return
  }
  probing.value = true
  probeResult.value = null
  try {
    const res = (await testConnection({
      email_address: form.email_address,
      imap_server: form.imap_server,
      port: form.port,
      password: form.password,
      use_ssl: form.use_ssl,
    })) as unknown as EmailTestResult
    probeResult.value = res
    if (res.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(res.message || '连接失败')
    }
  } catch {
    probeResult.value = { success: false, message: '请求失败' }
  } finally {
    probing.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value
    .validate()
    .then(() => true)
    .catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editing.value && editingId.value != null) {
      const payload: Record<string, unknown> = {
        email_address: form.email_address,
        imap_server: form.imap_server,
        port: form.port,
        check_interval_minutes: form.check_interval_minutes,
        use_ssl: form.use_ssl,
      }
      if (form.password) payload.password = form.password
      await updateEmailConfig(editingId.value, payload as never)
      ElMessage.success('修改已保存')
    } else {
      if (!form.password) {
        ElMessage.warning('请输入密码或授权码')
        saving.value = false
        return
      }
      await createEmailConfig({
        email_address: form.email_address,
        imap_server: form.imap_server,
        port: form.port,
        password: form.password,
        check_interval_minutes: form.check_interval_minutes,
        use_ssl: form.use_ssl,
      })
      ElMessage.success('邮箱已登记')
    }
    dialogVisible.value = false
    await loadConfigs()
  } catch {
    /* swallow */
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: EmailConfigItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除邮箱「${row.email_address}」的配置？此操作不可撤销。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteEmailConfig(row.id)
    ElMessage.success('已删除')
    await loadConfigs()
  } catch {
    /* swallow */
  }
}

async function handleFetch(row: EmailConfigItem) {
  fetchingId.value = row.id
  try {
    const res = (await manualFetch(row.id)) as unknown as {
      total_emails_checked: number
      new_invoices_found: number
      status: string
      errors: string[]
    }
    if (res.status === 'failed') {
      ElMessage.error(`拉取失败：${res.errors?.[0] || '未知错误'}`)
    } else {
      ElMessage.success(
        `拉取完成 · 检索 ${res.total_emails_checked} 封 · 新增邮件附件 ${res.new_invoices_found} 份`,
      )
    }
    messagePage.value = 1
    messageFilter.value = 'pending'
    selectedMessageIds.value = []
    await Promise.all([loadConfigs(), loadLogs(), loadMessages()])
  } catch {
    /* swallow */
  } finally {
    fetchingId.value = null
  }
}

/* ------------------------- lifecycle ------------------------- */
onMounted(() => {
  loadConfigs()
  loadLogs()
  loadMessages()
})
</script>

<style scoped>
.email-config-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hint-alert :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 6px;
  border-radius: 3px;
  font-family: ui-monospace, Menlo, monospace;
  font-size: 12px;
  margin: 0 2px;
}

.metrics-row > .el-col {
  margin-bottom: 16px;
}

.metric-card {
  border-radius: 4px;
}

.metric-card__label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-card__value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.metric-card__value--small {
  font-size: 18px;
}

.metric-card__sub {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.section-card {
  border-radius: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-header__title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.text-mute {
  color: #909399;
}

.text-success {
  color: #67c23a;
  font-weight: 500;
}

.text-danger {
  color: #f56c6c;
}
</style>
