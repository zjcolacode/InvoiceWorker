<template>
  <div class="ledger" :class="{ 'is-collapsed': collapsed }">
    <!-- ━━━━━━━━━━ Sidebar ━━━━━━━━━━ -->
    <aside class="ledger__aside">
      <div class="brand">
        <div class="brand__mark">
          <span class="stamp">整</span>
        </div>
        <div v-show="!collapsed" class="brand__meta">
          <div class="eyebrow">Invoice · Worker</div>
          <div class="brand__title">发票整理<br />数字员工</div>
        </div>
      </div>

      <div class="ledger__rule" />

      <nav class="nav">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          router
        >
          <el-menu-item
            v-for="(item, idx) in visibleMenus"
            :key="item.path"
            :index="item.path"
          >
            <span class="nav__index">{{ String(idx + 1).padStart(2, '0') }}</span>
            <el-icon class="nav__icon">
              <component :is="item.icon" />
            </el-icon>
            <template #title>
              <span class="nav__label">{{ item.title }}</span>
              <span v-if="item.roles?.includes('admin')" class="nav__tag">ADM</span>
            </template>
          </el-menu-item>
        </el-menu>
      </nav>

      <div v-show="!collapsed" class="ledger__foot">
        <div class="serial">SYS · v1.0.0</div>
        <div class="serial">{{ todayStamp }}</div>
      </div>
    </aside>

    <!-- ━━━━━━━━━━ Main column ━━━━━━━━━━ -->
    <section class="ledger__main">
      <header class="topbar">
        <div class="topbar__left">
          <button class="iconbtn" :title="collapsed ? '展开' : '收起'" @click="collapsed = !collapsed">
            <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </button>
          <div class="crumb">
            <span class="eyebrow">Section</span>
            <span class="crumb__sep">/</span>
            <span class="crumb__title">{{ currentTitle }}</span>
          </div>
        </div>

        <div class="topbar__right">
          <div class="ticker serial">
            <span class="ticker__dot" />
            <span>系统在线</span>
            <span class="ticker__sep">·</span>
            <span>{{ nowStamp }}</span>
          </div>

          <el-dropdown trigger="click" @command="onUserCmd">
            <button class="user">
              <span class="user__avatar">{{ initial }}</span>
              <span class="user__col">
                <span class="user__name">{{ userInfo?.username || '—' }}</span>
                <span class="user__role">{{ roleLabel }}</span>
              </span>
              <el-icon class="user__caret"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ userInfo?.email || '—' }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div class="ledger__rule" />

      <main class="content">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  ArrowDown,
  Document,
  Download,
  Expand,
  Fold,
  Message,
  Odometer,
  Printer,
  User,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { Role } from '@/api/auth'

interface MenuItem {
  path: string
  title: string
  icon: any
  roles?: Role[]
}

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const collapsed = ref(false)

const allMenus: MenuItem[] = [
  { path: '/dashboard', title: '仪表盘', icon: Odometer },
  { path: '/invoice', title: '发票管理', icon: Document },
  { path: '/email-config', title: '邮箱配置', icon: Message, roles: ['admin'] },
  { path: '/export', title: '数据导出', icon: Download },
  { path: '/print', title: '打印管理', icon: Printer },
  { path: '/users', title: '用户管理', icon: User, roles: ['admin'] },
]

const visibleMenus = computed(() => allMenus.filter((m) => store.hasRole(m.roles)))
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta?.title as string) || '—')

const userInfo = computed(() => store.userInfo)
const initial = computed(() => (store.username || '·').slice(0, 1).toUpperCase())
const roleLabel = computed(() => {
  switch (store.role) {
    case 'admin': return '管理员 · ADMIN'
    case 'operator': return '操作员 · OPERATOR'
    case 'viewer': return '观察者 · VIEWER'
    default: return '—'
  }
})

const todayStamp = computed(() => {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
})

const now = ref(new Date())
const nowStamp = computed(() => {
  const d = now.value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

let timer: number | undefined
onMounted(() => {
  timer = window.setInterval(() => { now.value = new Date() }, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})

async function onUserCmd(cmd: string) {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出登录？', '退出', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      })
      store.logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch { /* user cancelled */ }
  }
}
</script>

<style scoped>
.ledger {
  --aside: 248px;
  --aside-collapsed: 76px;
  --topbar: 68px;

  display: grid;
  grid-template-columns: var(--aside) 1fr;
  min-height: 100vh;
  background: var(--paper);
  background-image:
    linear-gradient(var(--rule-faint) 1px, transparent 1px),
    linear-gradient(90deg, var(--rule-faint) 1px, transparent 1px);
  background-size: 80px 80px;
  background-position: -1px -1px;
  transition: grid-template-columns 0.28s ease;
}
.ledger.is-collapsed { grid-template-columns: var(--aside-collapsed) 1fr; }

/* ─── Sidebar ─── */
.ledger__aside {
  border-right: var(--hair);
  padding: 22px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  background: var(--paper);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 22px;
}
.brand__mark .stamp { width: 42px; height: 42px; font-size: 20px; }
.brand__meta { line-height: 1.05; }
.brand__title {
  font-family: var(--serif);
  font-style: italic;
  font-weight: 400;
  font-size: 19px;
  letter-spacing: -0.01em;
  margin-top: 4px;
  color: var(--ink);
}

.ledger__rule { height: 1px; background: var(--rule-soft); margin: 0; }

.nav { flex: 1; overflow-y: auto; padding: 6px 0; }
:deep(.el-menu) { padding: 0 12px; }
:deep(.el-menu-item) {
  border-radius: 0 !important;
  margin: 2px 0;
  padding-left: 14px !important;
  display: flex;
  align-items: center;
  gap: 10px;
}
.nav__index {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--mute-2);
  width: 18px;
}
.nav__icon { font-size: 16px; color: var(--ink); }
.nav__label { flex: 1; }
.nav__tag {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--stamp);
  border: 1px solid var(--stamp-soft);
  padding: 1px 5px;
  border-radius: 1px;
  margin-left: auto;
}

.ledger.is-collapsed .nav__index,
.ledger.is-collapsed .nav__tag { display: none; }

.ledger__foot {
  padding: 10px 22px 4px;
  border-top: 1px solid var(--rule-soft);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ─── Main column ─── */
.ledger__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  height: var(--topbar);
  padding: 0 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  background: var(--paper);
  position: sticky;
  top: 0;
  z-index: 10;
}
.topbar__left { display: flex; align-items: center; gap: 18px; }
.topbar__right { display: flex; align-items: center; gap: 22px; }

.iconbtn {
  width: 36px; height: 36px;
  border: 1px solid var(--rule-soft);
  background: transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ink);
  transition: all 0.18s ease;
}
.iconbtn:hover { border-color: var(--ink); color: var(--stamp); }

.crumb { display: flex; align-items: baseline; gap: 10px; }
.crumb__sep { color: var(--mute-2); font-family: var(--mono); }
.crumb__title {
  font-family: var(--serif);
  font-style: italic;
  font-size: 22px;
  letter-spacing: -0.01em;
  color: var(--ink);
}

.ticker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-variant-numeric: tabular-nums;
  color: var(--mute);
}
.ticker__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--stamp);
  box-shadow: 0 0 0 3px var(--stamp-soft);
  animation: pulse 1.6s ease-in-out infinite;
}
.ticker__sep { color: var(--mute-2); }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.user {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  background: transparent;
  border: 1px solid var(--rule-soft);
  cursor: pointer;
  transition: border-color 0.18s ease;
}
.user:hover { border-color: var(--ink); }
.user__avatar {
  width: 28px; height: 28px;
  background: var(--ink);
  color: var(--paper);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-style: italic;
  font-size: 14px;
}
.user__col { display: flex; flex-direction: column; line-height: 1.1; text-align: left; }
.user__name { font-size: 13px; color: var(--ink); font-weight: 500; }
.user__role {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--mute);
  text-transform: uppercase;
  margin-top: 2px;
}
.user__caret { color: var(--mute); font-size: 12px; }

/* ─── Content ─── */
.content {
  flex: 1;
  padding: 8px 32px 40px;
  min-height: calc(100vh - var(--topbar));
}

.page-enter-active, .page-leave-active { transition: all 0.32s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 960px) {
  .ledger { grid-template-columns: var(--aside-collapsed) 1fr; }
  .topbar { padding: 0 18px; }
  .content { padding: 6px 18px 32px; }
  .ticker { display: none; }
}
</style>
