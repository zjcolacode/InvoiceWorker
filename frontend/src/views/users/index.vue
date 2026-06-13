<template>
  <div class="users-page">
    <!-- 页眉 -->
    <header class="page-hero">
      <div class="page-hero__title">
        <span class="page-hero__eyebrow">Administration</span>
        <h1>用户管理</h1>
        <p>管理账户身份、角色与可访问的菜单边界。</p>
      </div>
      <div class="page-hero__actions">
        <el-button :icon="Refresh" plain @click="loadUsers">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
      </div>
    </header>

    <!-- 指标条 -->
    <section class="meter-row">
      <div class="meter">
        <span class="meter__label">总账户</span>
        <span class="meter__value">{{ total }}</span>
      </div>
      <div class="meter">
        <span class="meter__label">启用中</span>
        <span class="meter__value">{{ activeCount }}</span>
      </div>
      <div class="meter">
        <span class="meter__label">管理员</span>
        <span class="meter__value">{{ adminCount }}</span>
      </div>
    </section>

    <!-- 表格卡片 -->
    <el-card shadow="never" class="table-card">
      <el-table
        v-loading="loading"
        :data="userList"
        style="width: 100%"
        row-key="id"
        :row-class-name="rowClassName"
        empty-text="暂无用户"
      >
        <el-table-column label="账户" min-width="220">
          <template #default="{ row }">
            <div class="cell-user">
              <span class="avatar" :data-role="row.role">{{ initialOf(row.username) }}</span>
              <div class="cell-user__meta">
                <div class="cell-user__name">
                  {{ row.username }}
                  <span v-if="row.id === currentUserId" class="self-flag">您</span>
                </div>
                <div class="cell-user__sub">ID · {{ row.id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <span class="role-chip" :data-role="row.role">
              <span class="role-chip__dot" />
              {{ roleLabel(row.role) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="full_name" label="员工姓名" width="120">
          <template #default="{ row }">
            <span v-if="row.full_name">{{ row.full_name }}</span>
            <span v-else class="placeholder">—</span>
          </template>
        </el-table-column>

        <el-table-column prop="position" label="员工岗位" width="120">
          <template #default="{ row }">
            <span v-if="row.position">{{ row.position }}</span>
            <span v-else class="placeholder">—</span>
          </template>
        </el-table-column>

        <el-table-column label="邮箱" min-width="220">
          <template #default="{ row }">
            <span v-if="row.email">{{ row.email }}</span>
            <span v-else class="placeholder">—</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-pill" :data-active="row.is_active">
              <span class="status-pill__dot" />
              {{ row.is_active ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="菜单权限" width="160">
          <template #default="{ row }">
            <span v-if="row.role === 'admin'" class="perms-summary perms-summary--all">
              全部菜单
            </span>
            <span v-else class="perms-summary">
              {{ (row.menu_permissions?.length ?? 0) }} / {{ menus.length }} 项
            </span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEdit(row as UserInfo)">编辑</el-button>
            <el-button
              type="primary"
              link
              size="small"
              :disabled="row.role === 'admin'"
              @click="openPermissions(row as UserInfo)"
            >
              权限
            </el-button>
            <el-popconfirm
              :title="`确认删除用户 ${row.username}？此操作不可撤销。`"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row as UserInfo)"
            >
              <template #reference>
                <el-button
                  type="danger"
                  link
                  size="small"
                  :disabled="row.id === currentUserId"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="editingId ? '编辑用户' : '新增用户'"
      width="520px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="92px"
        label-position="right"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="3-50 字符，唯一"
            maxlength="50"
            :disabled="editingId !== null && form.username === 'admin'"
            show-word-limit
          />
        </el-form-item>
        <el-form-item
          :label="editingId ? '重置密码' : '密码'"
          :prop="editingId ? undefined : 'password'"
        >
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="editingId ? '留空则不修改密码' : '至少 6 位'"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item v-if="!editingId || form.password" label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio-button label="admin">管理员</el-radio-button>
            <el-radio-button label="operator">操作员</el-radio-button>
            <el-radio-button label="viewer">观察者</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="员工姓名">
          <el-input v-model="form.full_name" placeholder="可选" maxlength="100" />
        </el-form-item>
        <el-form-item label="员工岗位">
          <el-input v-model="form.position" placeholder="可选" maxlength="100" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="可选" maxlength="100" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 菜单权限弹窗 -->
    <el-dialog
      v-model="permsDialogVisible"
      title="菜单权限配置"
      width="540px"
      :close-on-click-modal="false"
      append-to-body
    >
      <div v-if="permsTarget" class="perms-intro">
        为用户 <strong>{{ permsTarget.username }}</strong> 分配可访问的菜单：
      </div>

      <div class="perms-toolbar">
        <el-button link size="small" @click="selectAllPerms">全选</el-button>
        <el-divider direction="vertical" />
        <el-button link size="small" @click="selectedPerms = []">清空</el-button>
      </div>

      <el-checkbox-group v-model="selectedPerms" class="perms-grid">
        <label
          v-for="menu in menus"
          :key="menu.path"
          class="perm-item"
          :data-checked="selectedPerms.includes(menu.path)"
        >
          <el-checkbox :label="menu.path" :value="menu.path">
            <span class="perm-item__body">
              <span class="perm-item__title">{{ menu.title }}</span>
              <span class="perm-item__path">{{ menu.path }}</span>
            </span>
          </el-checkbox>
        </label>
      </el-checkbox-group>

      <template #footer>
        <el-button @click="permsDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="permsSaving" @click="handleSavePerms">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  createUser,
  deleteUser,
  getMenuList,
  getUsers,
  updateUser,
  updateUserPermissions,
  type MenuItem,
} from '@/api/user'
import type { Role, UserInfo } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const currentUserId = computed(() => store.userInfo?.id ?? -1)

// ---------------- 列表 ----------------
const loading = ref(false)
const userList = ref<UserInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const activeCount = computed(() => userList.value.filter((u) => u.is_active).length)
const adminCount = computed(() => userList.value.filter((u) => u.role === 'admin').length)

async function loadUsers() {
  loading.value = true
  try {
    const res = await getUsers({ page: page.value, page_size: pageSize.value })
    userList.value = res.items
    total.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// ---------------- 菜单列表 ----------------
const menus = ref<MenuItem[]>([])

async function loadMenus() {
  try {
    menus.value = await getMenuList()
  } catch (e) {
    console.error(e)
  }
}

// ---------------- 新增/编辑 ----------------
const formDialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

interface UserForm {
  username: string
  password: string
  confirmPassword: string
  role: Role
  email: string
  full_name: string
  position: string
}

const form = reactive<UserForm>({
  username: '',
  password: '',
  confirmPassword: '',
  role: 'operator',
  email: '',
  full_name: '',
  position: '',
})

const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

function resetForm() {
  form.username = ''
  form.password = ''
  form.confirmPassword = ''
  form.role = 'operator'
  form.email = ''
  form.full_name = ''
  form.position = ''
  editingId.value = null
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  formDialogVisible.value = true
}

function openEdit(row: UserInfo) {
  resetForm()
  editingId.value = row.id
  form.username = row.username
  form.role = row.role
  form.email = row.email || ''
  form.full_name = row.full_name || ''
  form.position = row.position || ''
  formDialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 密码确认校验（仅在设置密码时）
  if (form.password && form.password !== form.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  submitting.value = true
  try {
    if (editingId.value) {
      await updateUser(editingId.value, {
        username: form.username,
        role: form.role,
        email: form.email || null,
        full_name: form.full_name || null,
        position: form.position || null,
        ...(form.password ? { password: form.password } : {}),
      })
      ElMessage.success('已保存')
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        role: form.role,
        email: form.email || null,
        full_name: form.full_name || null,
        position: form.position || null,
      })
      ElMessage.success('用户创建成功')
    }
    formDialogVisible.value = false
    await loadUsers()
  } catch (e) {
    console.error(e)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: UserInfo) {
  if (row.id === currentUserId.value) {
    ElMessage.warning('不能删除自己')
    return
  }
  try {
    await deleteUser(row.id)
    ElMessage.success(`已删除用户：${row.username}`)
    await loadUsers()
  } catch (e) {
    console.error(e)
  }
}

// ---------------- 菜单权限 ----------------
const permsDialogVisible = ref(false)
const permsSaving = ref(false)
const permsTarget = ref<UserInfo | null>(null)
const selectedPerms = ref<string[]>([])

function openPermissions(row: UserInfo) {
  permsTarget.value = row
  selectedPerms.value = [...(row.menu_permissions ?? [])]
  permsDialogVisible.value = true
}

function selectAllPerms() {
  selectedPerms.value = menus.value.map((m) => m.path)
}

async function handleSavePerms() {
  if (!permsTarget.value) return
  permsSaving.value = true
  try {
    const updated = await updateUserPermissions(permsTarget.value.id, selectedPerms.value)
    // 局部更新表格
    const idx = userList.value.findIndex((u) => u.id === updated.id)
    if (idx !== -1) userList.value[idx] = updated
    // 若是当前用户，同步刷新 store
    if (updated.id === currentUserId.value) {
      await store.getUserInfo()
    }
    ElMessage.success('权限已更新')
    permsDialogVisible.value = false
  } catch (e) {
    console.error(e)
  } finally {
    permsSaving.value = false
  }
}

// ---------------- 渲染辅助 ----------------
function initialOf(name: string) {
  return (name || 'U').slice(0, 1).toUpperCase()
}

function roleLabel(role: Role) {
  switch (role) {
    case 'admin':
      return '管理员'
    case 'operator':
      return '操作员'
    case 'viewer':
      return '观察者'
    default:
      return role
  }
}

function formatTime(iso?: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

function rowClassName({ row }: { row: any }) {
  return row.id === currentUserId.value ? 'is-self-row' : ''
}

onMounted(() => {
  loadUsers()
  loadMenus()
})
</script>

<style scoped>
.users-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ---------- 页眉 ---------- */
.page-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 4px 4px 12px;
  border-bottom: 1px solid #e5e7eb;
}

.page-hero__eyebrow {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #c0a062;
  font-weight: 600;
  margin-bottom: 4px;
}

.page-hero__title h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #1f2937;
}

.page-hero__title p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.page-hero__actions {
  display: flex;
  gap: 10px;
}

/* ---------- 指标条 ---------- */
.meter-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.meter {
  background: #ffffff;
  border: 1px solid #eef0f3;
  border-left: 3px solid #c0a062;
  border-radius: 4px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meter__label {
  font-size: 12px;
  color: #6b7280;
  letter-spacing: 0.06em;
}

.meter__value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
}

/* ---------- 表格卡片 ---------- */
.table-card {
  border: 1px solid #eef0f3;
}

.table-card :deep(.el-card__body) {
  padding: 8px 0 16px;
}

.table-card :deep(.el-table__row.is-self-row) {
  background: #fbf8f1;
}

.table-card :deep(.el-table th.el-table__cell) {
  background: #fafbfc;
  font-weight: 600;
  color: #374151;
}

/* ---------- 账户单元格 ---------- */
.cell-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  color: #ffffff;
  background: #6b7280;
  flex-shrink: 0;
}

.avatar[data-role='admin'] {
  background: #1f2937;
}

.avatar[data-role='operator'] {
  background: #2563eb;
}

.avatar[data-role='viewer'] {
  background: #9ca3af;
}

.cell-user__meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.cell-user__name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.cell-user__sub {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

.self-flag {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  background: #c0a062;
  color: #fff;
  letter-spacing: 0.05em;
}

/* ---------- 角色芯片 ---------- */
.role-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid;
  line-height: 1.6;
}

.role-chip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.role-chip[data-role='admin'] {
  color: #1f2937;
  border-color: #1f2937;
  background: #f3f4f6;
}
.role-chip[data-role='admin'] .role-chip__dot {
  background: #1f2937;
}

.role-chip[data-role='operator'] {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: #eff6ff;
}
.role-chip[data-role='operator'] .role-chip__dot {
  background: #2563eb;
}

.role-chip[data-role='viewer'] {
  color: #4b5563;
  border-color: #d1d5db;
  background: #f9fafb;
}
.role-chip[data-role='viewer'] .role-chip__dot {
  background: #9ca3af;
}

/* ---------- 状态药丸 ---------- */
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.status-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d1d5db;
}

.status-pill[data-active='true'] {
  color: #047857;
}

.status-pill[data-active='true'] .status-pill__dot {
  background: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.18);
}

/* ---------- 权限摘要 ---------- */
.perms-summary {
  font-size: 12px;
  color: #6b7280;
  font-variant-numeric: tabular-nums;
}

.perms-summary--all {
  color: #c0a062;
  font-weight: 600;
}

.time-cell {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: #6b7280;
}

.placeholder {
  color: #cbd5e1;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px 4px;
}

/* ---------- 权限弹窗 ---------- */
.perms-intro {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 10px;
}

.perms-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.perms-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.perm-item {
  display: block;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #ffffff;
}

.perm-item:hover {
  border-color: #c0a062;
  background: #fdfbf6;
}

.perm-item[data-checked='true'] {
  border-color: #1f2937;
  background: #f3f4f6;
}

.perm-item :deep(.el-checkbox) {
  height: auto;
  width: 100%;
  margin-right: 0;
}

.perm-item :deep(.el-checkbox__label) {
  width: 100%;
}

.perm-item__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.perm-item__title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.perm-item__path {
  font-size: 11px;
  color: #9ca3af;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
  letter-spacing: 0.02em;
}
</style>
