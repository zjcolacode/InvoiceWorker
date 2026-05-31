<template>
  <div class="ledger">
    <!-- 装饰性背景 -->
    <div class="ledger__grain" aria-hidden="true"></div>
    <div class="ledger__rule" aria-hidden="true"></div>

    <!-- 顶部"控制台"标题区 -->
    <header class="console">
      <div class="console__overline">
        <span class="dot dot--live"></span>
        <span>SYSTEM · 06</span>
        <span class="sep">/</span>
        <span>INBOX_INTAKE</span>
        <span class="sep">/</span>
        <span class="mono">{{ nowStamp }}</span>
      </div>
      <h1 class="console__title">
        <span class="word">邮箱</span>
        <span class="word italic">接入</span>
        <span class="word ampersand">&amp;</span>
        <span class="word">轮询</span>
      </h1>
      <p class="console__subtitle">
        Configure inbound IMAP mailboxes &mdash; schedule fetch &mdash; harvest invoice attachments.
      </p>

      <!-- 统计 ribbon -->
      <div class="metrics">
        <div class="metric">
          <span class="metric__label">CONFIGURED</span>
          <span class="metric__value">{{ pad2(configs.length) }}</span>
          <span class="metric__suffix">mailbox{{ configs.length === 1 ? '' : 'es' }}</span>
        </div>
        <div class="metric">
          <span class="metric__label">ACTIVE</span>
          <span class="metric__value">{{ pad2(activeCount) }}</span>
          <span class="metric__suffix">polling</span>
        </div>
        <div class="metric">
          <span class="metric__label">LAST POLL</span>
          <span class="metric__value mono small">{{ lastPollLabel }}</span>
          <span class="metric__suffix">{{ lastPollRelative }}</span>
        </div>
        <div class="metric">
          <span class="metric__label">TODAY HARVEST</span>
          <span class="metric__value">{{ todayHarvest }}</span>
          <span class="metric__suffix">new invoices</span>
        </div>
      </div>
    </header>

    <!-- 授权码提示 -->
    <el-alert
      class="hint"
      type="info"
      :closable="false"
      show-icon
    >
      <template #title>
        <span class="hint__title">授权码 ≠ 登录密码</span>
      </template>
      <template #default>
        <p class="hint__body">
          QQ / 163 / 网易企业邮 等服务需要在邮箱网页端开启 IMAP 服务并申请<em>"授权码"</em>，
          再填写到下方密码字段。常见服务器:
          <code>imap.qq.com</code> / <code>imap.163.com</code> /
          <code>imap.exmail.qq.com</code> / <code>outlook.office365.com</code>。
        </p>
      </template>
    </el-alert>

    <!-- 配置列表卡片 -->
    <section class="card">
      <div class="card__head">
        <div class="card__head-left">
          <span class="filing">FILE NO. 06-A</span>
          <h2 class="card__title">已登记的邮箱</h2>
        </div>
        <div class="card__head-right">
          <button class="btn-ghost" @click="loadConfigs" :disabled="loading">
            <span class="btn-ghost__icon">↻</span>
            <span>刷新</span>
          </button>
          <button class="btn-solid" @click="openCreate">
            <span class="btn-solid__plus">＋</span>
            <span>登记新邮箱</span>
          </button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="configs"
        class="ledger-table"
        empty-text="尚无任何邮箱配置 — 点击「登记新邮箱」开始"
        stripe
      >
        <el-table-column type="index" label="№" width="60">
          <template #default="{ $index }">
            <span class="mono mute">{{ pad2($index + 1) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="邮箱" min-width="220">
          <template #default="{ row }">
            <div class="cell-email">
              <span class="cell-email__addr">{{ row.email_address }}</span>
              <span
                class="ribbon"
                :class="row.is_active ? 'ribbon--on' : 'ribbon--off'"
              >
                {{ row.is_active ? 'ACTIVE' : 'PAUSED' }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="服务器 / 端口" min-width="240">
          <template #default="{ row }">
            <div class="cell-server">
              <span class="mono">{{ row.imap_server }}</span>
              <span class="cell-server__port mono">:{{ row.port }}</span>
              <span v-if="row.use_ssl" class="ssl">SSL</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="间隔" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.check_interval_minutes }} min</span>
          </template>
        </el-table-column>

        <el-table-column label="最后拉取" width="200">
          <template #default="{ row }">
            <span class="mono small mute">
              {{ row.last_check_at ? formatDate(row.last_check_at, 'YYYY-MM-DD HH:mm') : '— 尚未拉取 —' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" align="right">
          <template #default="{ row }">
            <div class="ops">
              <button
                class="op op--fetch"
                :disabled="fetchingId === row.id"
                @click="handleFetch(row as EmailConfigItem)"
                title="立即拉取"
              >
                {{ fetchingId === row.id ? '拉取中…' : '立即拉取' }}
              </button>
              <button class="op" @click="openEdit(row as EmailConfigItem)" title="编辑">编辑</button>
              <button class="op op--danger" @click="handleDelete(row as EmailConfigItem)" title="删除">删除</button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 拉取日志卡片 -->
    <section class="card">
      <div class="card__head">
        <div class="card__head-left">
          <span class="filing">FILE NO. 06-B</span>
          <h2 class="card__title">拉取日志</h2>
        </div>
        <div class="card__head-right">
          <button class="btn-ghost" @click="loadLogs" :disabled="logLoading">
            <span class="btn-ghost__icon">↻</span>
            <span>刷新日志</span>
          </button>
        </div>
      </div>

      <el-table
        v-loading="logLoading"
        :data="logs"
        class="ledger-table"
        empty-text="尚无拉取记录"
      >
        <el-table-column label="时间" width="190">
          <template #default="{ row }">
            <span class="mono small">
              {{ row.fetch_time ? formatDate(row.fetch_time, 'YYYY-MM-DD HH:mm:ss') : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="邮箱" prop="email_address" min-width="220">
          <template #default="{ row }">
            <span>{{ row.email_address || `#${row.config_id}` }}</span>
          </template>
        </el-table-column>
        <el-table-column label="检索" width="100" align="center">
          <template #default="{ row }">
            <span class="mono mute">{{ row.total_emails_checked }}</span>
          </template>
        </el-table-column>
        <el-table-column label="新增发票" width="120" align="center">
          <template #default="{ row }">
            <span class="harvest" :class="{ 'harvest--zero': !row.new_invoices_count }">
              +{{ row.new_invoices_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <span class="status-pill" :class="`status-pill--${row.status}`">
              <span class="status-pill__dot"></span>
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="240">
          <template #default="{ row }">
            <span v-if="row.error_message" class="err">{{ row.error_message }}</span>
            <span v-else class="mute">—</span>
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
    </section>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="540px"
      align-center
      class="dossier-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="dossier">
        <div class="dossier__seal">
          <span class="dossier__seal-text">SEAL · 06</span>
        </div>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="dossier__form"
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

          <div class="row">
            <el-form-item label="端口" prop="port">
              <el-input-number
                v-model="form.port"
                :min="1"
                :max="65535"
                :controls="false"
                style="width: 140px"
              />
            </el-form-item>

            <el-form-item label="SSL" prop="use_ssl">
              <el-switch v-model="form.use_ssl" />
            </el-form-item>

            <el-form-item label="拉取频率" prop="check_interval_minutes">
              <el-select v-model="form.check_interval_minutes" style="width: 160px">
                <el-option :value="15" label="每 15 分钟" />
                <el-option :value="30" label="每 30 分钟" />
                <el-option :value="60" label="每 1 小时" />
                <el-option :value="120" label="每 2 小时" />
                <el-option :value="360" label="每 6 小时" />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item label="密码 / 授权码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              :placeholder="editing ? '留空则不修改' : '从邮箱网页端获取的授权码'"
              autocomplete="new-password"
            />
          </el-form-item>

          <!-- 测试连接结果 -->
          <transition name="probe">
            <div v-if="probeResult" class="probe" :class="`probe--${probeResult.success ? 'ok' : 'err'}`">
              <span class="probe__dot"></span>
              <span class="probe__text">{{ probeResult.message }}</span>
            </div>
          </transition>
        </el-form>
      </div>

      <template #footer>
        <div class="dossier__footer">
          <button
            class="btn-ghost"
            :disabled="probing"
            @click="handleProbe"
          >
            <span class="dot dot--blue"></span>
            <span>{{ probing ? '握手中…' : '测试连接' }}</span>
          </button>
          <span class="spacer"></span>
          <button class="btn-ghost" @click="dialogVisible = false">取消</button>
          <button
            class="btn-solid"
            :disabled="saving"
            @click="handleSubmit"
          >
            {{ saving ? '保存中…' : (editing ? '保存修改' : '登记邮箱') }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createEmailConfig,
  deleteEmailConfig,
  getEmailConfigs,
  getFetchLogs,
  manualFetch,
  testConnection,
  updateEmailConfig,
  type EmailConfigItem,
  type EmailFetchLogItem,
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
  check_interval_minutes: [{ required: true, message: '请选择拉取频率', trigger: 'change' }],
}

/* ------------------------- computed ------------------------- */
const dialogTitle = computed(() =>
  editing.value ? '修改邮箱档案' : '登记新邮箱档案'
)

const activeCount = computed(() =>
  configs.value.filter((c) => c.is_active).length
)

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
  if (!lastPoll.value) return '— : —'
  return formatDate(lastPoll.value, 'HH:mm:ss')
})

const lastPollRelative = computed(() => {
  if (!lastPoll.value) return 'never'
  const diff = Math.max(0, Date.now() - lastPoll.value.getTime())
  const min = Math.floor(diff / 60000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h} h ago`
  return `${Math.floor(h / 24)} d ago`
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

const nowStamp = ref('')
function tickClock() {
  nowStamp.value = formatDate(new Date(), 'YYYY.MM.DD · HH:mm')
}

/* ------------------------- helpers ------------------------- */
function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    partial: '部分成功',
  }
  return map[s] || s
}

/* ------------------------- data loaders ------------------------- */
async function loadConfigs() {
  loading.value = true
  try {
    const data = (await getEmailConfigs()) as unknown as EmailConfigItem[]
    configs.value = data || []
  } catch (e) {
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
  } catch (e) {
    /* swallow */
  } finally {
    logLoading.value = false
  }
}

function onLogPageChange(p: number) {
  logPage.value = p
  loadLogs()
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
  } catch (e) {
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
  } catch (e) {
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
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
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
        `拉取完成 · 检索 ${res.total_emails_checked} 封 · 新增 ${res.new_invoices_found} 张发票`
      )
    }
    await Promise.all([loadConfigs(), loadLogs()])
  } catch {
    /* swallow */
  } finally {
    fetchingId.value = null
  }
}

/* ------------------------- lifecycle ------------------------- */
onMounted(() => {
  tickClock()
  setInterval(tickClock, 30_000)
  loadConfigs()
  loadLogs()
})
</script>

<style scoped lang="scss">
/* ------ 字体: 引入特色字体. 避免 Inter / Roboto / Arial. ------ */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,800;1,9..144,500;1,9..144,700&family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

.ledger {
  --ink:        #0a1628;
  --ink-soft:   #1f2c3f;
  --paper:      #f3ecdd;
  --paper-2:    #ebe3d2;
  --paper-edge: #d8cfba;
  --iron:       #6b6862;
  --vermilion:  #c43a1d;
  --mariner:    #1f3d6b;
  --verdigris:  #3f6b56;
  --amber:      #b07a1f;

  --serif: 'Fraunces', 'Cormorant Garamond', Georgia, serif;
  --sans:  'Manrope', system-ui, sans-serif;
  --mono:  'JetBrains Mono', ui-monospace, monospace;

  position: relative;
  min-height: 100%;
  padding: 40px 56px 80px;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--sans);
  letter-spacing: 0.01em;
  overflow: hidden;

  @media (max-width: 1024px) {
    padding: 24px 20px 60px;
  }
}

/* 噪点 + 装饰 ----------------------------------------------- */
.ledger__grain {
  position: absolute; inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(rgba(10, 22, 40, 0.06) 1px, transparent 1px),
    radial-gradient(rgba(10, 22, 40, 0.04) 1px, transparent 1px);
  background-size: 3px 3px, 7px 7px;
  background-position: 0 0, 1px 2px;
  opacity: 0.65;
  mix-blend-mode: multiply;
}
.ledger__rule {
  position: absolute;
  inset: 16px 24px;
  pointer-events: none;
  border: 1px solid rgba(10, 22, 40, 0.18);
  outline: 1px solid rgba(10, 22, 40, 0.08);
  outline-offset: 4px;

  @media (max-width: 1024px) { inset: 8px 8px; }
}

/* console header --------------------------------------------- */
.console {
  position: relative;
  z-index: 1;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--paper-edge);
  margin-bottom: 28px;
}
.console__overline {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--iron);
  text-transform: uppercase;
  margin-bottom: 10px;

  .sep { opacity: 0.4; }
}
.dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--iron);
}
.dot--live {
  background: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(196, 58, 29, 0.18);
  animation: pulse 1.6s ease-in-out infinite;
}
.dot--blue { background: var(--mariner); }
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%      { transform: scale(1.25); opacity: 0.7; }
}

.console__title {
  font-family: var(--serif);
  font-size: clamp(40px, 6vw, 72px);
  line-height: 0.96;
  letter-spacing: -0.02em;
  margin: 0;
  color: var(--ink);
  font-weight: 600;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.18em;

  .word.italic    { font-style: italic; font-weight: 500; color: var(--vermilion); }
  .word.ampersand { font-style: italic; font-weight: 400; color: var(--iron); }
}
.console__subtitle {
  margin: 14px 0 0;
  font-family: var(--serif);
  font-style: italic;
  font-size: 17px;
  color: var(--iron);
  max-width: 720px;
}

/* metrics ribbon --------------------------------------------- */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  margin-top: 32px;
  border-top: 1px solid var(--paper-edge);
  border-bottom: 1px solid var(--paper-edge);

  @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
}
.metric {
  padding: 18px 22px;
  border-right: 1px solid var(--paper-edge);
  display: flex;
  flex-direction: column;
  gap: 4px;

  &:last-child { border-right: none; }

  &__label {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.22em;
    color: var(--iron);
    text-transform: uppercase;
  }
  &__value {
    font-family: var(--serif);
    font-size: 38px;
    line-height: 1;
    font-weight: 600;
    color: var(--ink);

    &.mono { font-family: var(--mono); font-size: 26px; font-weight: 500; }
    &.small { font-size: 22px; }
  }
  &__suffix {
    font-family: var(--sans);
    font-size: 12px;
    color: var(--iron);
    letter-spacing: 0.04em;
  }
}

/* hint alert ------------------------------------------------- */
.hint {
  position: relative;
  z-index: 1;
  margin-bottom: 24px;
  border-left: 3px solid var(--vermilion);
  background: var(--paper-2);

  :deep(.el-alert__title) { font-weight: 600; }
}
.hint__title {
  font-family: var(--serif);
  font-style: italic;
  font-size: 17px;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.hint__body {
  margin: 4px 0 0;
  font-size: 13.5px;
  color: var(--ink-soft);
  line-height: 1.55;

  em { font-family: var(--serif); font-style: italic; color: var(--vermilion); font-size: 14px; }
  code {
    font-family: var(--mono);
    font-size: 12.5px;
    padding: 1px 5px;
    background: rgba(10, 22, 40, 0.08);
    border-radius: 2px;
    margin: 0 2px;
  }
}

/* card ------------------------------------------------------- */
.card {
  position: relative;
  z-index: 1;
  background: var(--paper-2);
  border: 1px solid var(--paper-edge);
  margin-bottom: 28px;
  box-shadow: 0 1px 0 rgba(10, 22, 40, 0.04), 0 18px 30px -22px rgba(10, 22, 40, 0.18);
}
.card__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 22px 26px 14px;
  border-bottom: 1px solid var(--paper-edge);
  flex-wrap: wrap;
  gap: 16px;
}
.card__head-left { display: flex; flex-direction: column; gap: 4px; }
.card__head-right { display: flex; gap: 10px; }
.filing {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.22em;
  color: var(--vermilion);
  text-transform: uppercase;
}
.card__title {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.05;
  margin: 0;
  letter-spacing: -0.01em;
  color: var(--ink);
}

/* buttons ---------------------------------------------------- */
.btn-ghost,
.btn-solid {
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 9px 16px;
  border: 1px solid var(--ink);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  transition: all 0.18s ease;
  display: inline-flex; align-items: center; gap: 8px;
  border-radius: 0;
  height: auto;

  &:disabled { opacity: 0.5; cursor: not-allowed; }
  &:not(:disabled):hover {
    background: var(--ink);
    color: var(--paper);
  }
}
.btn-ghost__icon { font-size: 14px; }
.btn-solid {
  background: var(--ink);
  color: var(--paper);

  &:not(:disabled):hover {
    background: var(--vermilion);
    border-color: var(--vermilion);
  }
}
.btn-solid__plus { font-family: var(--serif); font-size: 18px; line-height: 0.7; }

/* table styling ---------------------------------------------- */
.ledger-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(10, 22, 40, 0.04);
  --el-table-border-color: var(--paper-edge);
  --el-table-header-bg-color: transparent;
  --el-table-header-text-color: var(--iron);
  --el-table-text-color: var(--ink);

  background: transparent !important;

  :deep(.el-table__inner-wrapper::before) { display: none; }
  :deep(th.el-table__cell) {
    background: transparent !important;
    border-bottom: 1px solid var(--paper-edge);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--iron);
    padding: 10px 0;
  }
  :deep(td.el-table__cell) {
    background: transparent !important;
    border-bottom: 1px dashed var(--paper-edge);
    font-size: 14px;
    padding: 14px 0;
  }
  :deep(.el-table__empty-text) {
    font-family: var(--serif);
    font-style: italic;
    color: var(--iron);
    font-size: 16px;
  }
}

.cell-email {
  display: flex; align-items: center; gap: 10px;
  &__addr { font-weight: 600; color: var(--ink); }
}
.ribbon {
  display: inline-flex; align-items: center;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  padding: 2px 7px;
  border-radius: 1px;

  &--on  { background: rgba(63, 107, 86, 0.14); color: var(--verdigris); border: 1px solid rgba(63, 107, 86, 0.4); }
  &--off { background: rgba(176, 122, 31, 0.14); color: var(--amber); border: 1px solid rgba(176, 122, 31, 0.4); }
}
.cell-server { display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  &__port { color: var(--vermilion); font-weight: 600; }
}
.ssl {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  padding: 1px 5px;
  background: var(--ink);
  color: var(--paper);
}
.ops { display: flex; gap: 6px; justify-content: flex-end; }
.op {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 5px 10px;
  border: 1px solid var(--paper-edge);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  text-transform: uppercase;
  transition: all 0.15s;
  border-radius: 0;

  &:hover:not(:disabled) {
    background: var(--ink);
    color: var(--paper);
    border-color: var(--ink);
  }
  &:disabled { opacity: 0.5; cursor: not-allowed; }

  &--fetch {
    border-color: var(--mariner);
    color: var(--mariner);
    &:hover:not(:disabled) { background: var(--mariner); border-color: var(--mariner); color: var(--paper); }
  }
  &--danger {
    border-color: rgba(196, 58, 29, 0.5);
    color: var(--vermilion);
    &:hover:not(:disabled) { background: var(--vermilion); border-color: var(--vermilion); color: var(--paper); }
  }
}

/* status pill ------------------------------------------------ */
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  padding: 3px 8px;
  border: 1px solid currentColor;
  text-transform: uppercase;

  &__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  &--success { color: var(--verdigris); }
  &--failed  { color: var(--vermilion); }
  &--partial { color: var(--amber); }
}
.harvest {
  font-family: var(--mono);
  font-weight: 600;
  font-size: 14px;
  color: var(--verdigris);
  &--zero { color: var(--iron); }
}
.err  { color: var(--vermilion); font-size: 13px; }
.mute { color: var(--iron); }
.mono { font-family: var(--mono); }
.small { font-size: 12.5px; }

/* pager ------------------------------------------------------ */
.pager {
  padding: 14px 26px 18px;
  display: flex; justify-content: flex-end;

  :deep(.el-pagination .el-pager li),
  :deep(.el-pagination button) {
    background: transparent !important;
    color: var(--ink);
    font-family: var(--mono);
    border-radius: 0 !important;
  }
  :deep(.el-pagination.is-background .el-pager li.is-active) {
    background: var(--ink) !important;
    color: var(--paper) !important;
  }
}

/* dialog ----------------------------------------------------- */
.dossier-dialog {
  :deep(.el-dialog) {
    background: var(--paper);
    border: 1px solid var(--ink);
    border-radius: 0;
    box-shadow: 0 30px 60px -20px rgba(10, 22, 40, 0.45);
    overflow: hidden;
  }
  :deep(.el-dialog__header) {
    padding: 20px 28px 8px;
    border-bottom: 1px solid var(--paper-edge);
    margin: 0;
  }
  :deep(.el-dialog__title) {
    font-family: var(--serif);
    font-style: italic;
    font-size: 22px;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
  }
  :deep(.el-dialog__body) { padding: 0; }
  :deep(.el-dialog__footer) {
    border-top: 1px solid var(--paper-edge);
    padding: 14px 24px;
    background: var(--paper-2);
  }
}
.dossier {
  position: relative;
  padding: 24px 28px 16px;
}
.dossier__seal {
  position: absolute;
  top: -10px;
  right: 22px;
  width: 76px; height: 76px;
  border: 1.5px solid var(--vermilion);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  transform: rotate(-12deg);
  pointer-events: none;
  opacity: 0.85;

  &::before {
    content: '';
    position: absolute; inset: 5px;
    border: 1px dashed rgba(196, 58, 29, 0.5);
    border-radius: 50%;
  }
  &-text {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.22em;
    color: var(--vermilion);
    text-transform: uppercase;
  }
}

.dossier__form {
  :deep(.el-form-item__label) {
    font-family: var(--mono);
    font-size: 10.5px !important;
    letter-spacing: 0.16em;
    color: var(--iron) !important;
    text-transform: uppercase;
    padding-bottom: 4px !important;
  }
  :deep(.el-input__wrapper),
  :deep(.el-input-number),
  :deep(.el-select__wrapper) {
    background: transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    border-bottom: 1px solid var(--paper-edge) !important;
    padding: 0 !important;
    transition: border-color 0.18s;

    &:hover, &.is-focus, &:focus-within {
      border-bottom-color: var(--ink) !important;
    }
  }
  :deep(.el-input__inner) {
    font-family: var(--mono);
    font-size: 14px;
    color: var(--ink);
    height: 36px;

    &::placeholder { color: rgba(107, 104, 98, 0.6); font-style: italic; }
  }
  :deep(.el-input-number .el-input__inner) {
    text-align: left;
    padding-left: 0;
  }
  :deep(.el-input-number .el-input__wrapper) { padding-left: 0 !important; }
  :deep(.el-switch.is-checked .el-switch__core) {
    background: var(--ink) !important;
    border-color: var(--ink) !important;
  }
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 18px;
  align-items: end;

  @media (max-width: 600px) { grid-template-columns: 1fr; }
}

.probe {
  margin-top: 10px;
  padding: 10px 14px;
  display: flex; align-items: center; gap: 10px;
  font-family: var(--mono);
  font-size: 12.5px;
  border-left: 3px solid;

  &__dot { width: 8px; height: 8px; border-radius: 50%; }
  &__text { flex: 1; word-break: break-all; }

  &--ok  { background: rgba(63, 107, 86, 0.1); border-color: var(--verdigris); color: var(--verdigris); .probe__dot { background: var(--verdigris); } }
  &--err { background: rgba(196, 58, 29, 0.1); border-color: var(--vermilion); color: var(--vermilion); .probe__dot { background: var(--vermilion); } }
}
.probe-enter-active, .probe-leave-active { transition: all 0.25s ease; }
.probe-enter-from, .probe-leave-to { opacity: 0; transform: translateY(-4px); }

.dossier__footer {
  display: flex; align-items: center; gap: 10px;
  .spacer { flex: 1; }
}
</style>
