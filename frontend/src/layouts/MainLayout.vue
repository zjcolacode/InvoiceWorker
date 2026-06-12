<template>
  <el-container class="layout">
    <!-- Sidebar -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="layout__aside">
      <div class="layout__logo">
        <span v-if="!collapsed">发票整理系统</span>
        <span v-else>发</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
        class="layout__menu"
      >
        <el-menu-item
          v-for="item in visibleMenus"
          :key="item.path"
          :index="item.path"
        >
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <template #title>
            <span>{{ item.title }}</span>
          </template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main column -->
    <el-container>
      <el-header class="layout__header">
        <div class="layout__header-left">
          <el-icon class="layout__collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="layout__header-right">
          <el-dropdown trigger="click" @command="onUserCmd">
            <span class="layout__user">
              <el-avatar :size="28" class="layout__avatar">{{ initial }}</el-avatar>
              <span class="layout__username">{{ userInfo?.username || '未登录' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ userInfo?.email || '—' }}</el-dropdown-item>
                <el-dropdown-item disabled>{{ roleLabel }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout__main">
        <router-view v-slot="{ Component, route: r }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="r.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  ArrowDown,
  Collection,
  Document,
  Download,
  Expand,
  Fold,
  Message,
  Odometer,
  Printer,
  Ticket,
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
  { path: '/categories', title: '分类管理', icon: Collection, roles: ['admin', 'operator'] },
  { path: '/reimbursement', title: '报销单管理', icon: Ticket },
]

// admin 看到全量菜单；其他角色仅看到被分配的菜单
// 同时保留路由 meta.roles 判断作为二重保障
const visibleMenus = computed(() =>
  allMenus.filter((m) => store.hasRole(m.roles) && store.canAccessMenu(m.path)),
)
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta?.title as string) || '—')

const userInfo = computed(() => store.userInfo)
const initial = computed(() => (store.username || 'U').slice(0, 1).toUpperCase())
const roleLabel = computed(() => {
  switch (store.role) {
    case 'admin':
      return '管理员'
    case 'operator':
      return '操作员'
    case 'viewer':
      return '观察者'
    default:
      return '—'
  }
})

async function onUserCmd(cmd: string) {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出登录？', '提示', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      })
      store.logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch {
      /* user cancelled */
    }
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

/* Sidebar */
.layout__aside {
  background: #304156;
  transition: width 0.28s ease;
  overflow: hidden;
}

.layout__logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  background: #2b3a4d;
  letter-spacing: 1px;
  white-space: nowrap;
}

.layout__menu {
  border-right: none;
}

.layout__menu:not(.el-menu--collapse) {
  width: 220px;
}

/* Header */
.layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid var(--app-border);
  padding: 0 20px;
  height: 60px;
}

.layout__header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.layout__collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.layout__collapse-btn:hover {
  color: var(--app-primary);
}

.layout__header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.layout__user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.layout__user:hover {
  background: #f5f7fa;
}

.layout__avatar {
  background: var(--app-primary);
  color: #ffffff;
}

.layout__username {
  font-size: 14px;
  color: #303133;
}

/* Main */
.layout__main {
  background: var(--app-bg);
  padding: 20px;
  min-height: calc(100vh - 60px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
