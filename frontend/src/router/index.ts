import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },
      {
        path: 'invoice',
        name: 'Invoice',
        component: () => import('@/views/invoice/index.vue'),
        meta: { title: '发票管理', icon: 'Document' },
      },
      {
        path: 'email-config',
        name: 'EmailConfig',
        component: () => import('@/views/email-config/index.vue'),
        meta: { title: '邮箱配置', icon: 'Message', roles: ['admin'] },
      },
      {
        path: 'export',
        name: 'Export',
        component: () => import('@/views/export/index.vue'),
        meta: { title: '数据导出', icon: 'Download' },
      },
      {
        path: 'print',
        name: 'Print',
        component: () => import('@/views/print/index.vue'),
        meta: { title: '打印管理', icon: 'Printer' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'categories',
        name: 'Categories',
        component: () => import('@/views/categories/index.vue'),
        meta: { title: '分类管理', icon: 'Collection', roles: ['admin', 'operator'] },
      },
      {
        path: 'reimbursement',
        name: 'Reimbursement',
        component: () => import('@/views/reimbursement/index.vue'),
        meta: { title: '报销单管理', icon: 'Ticket' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const TITLE = '发票整理数字员工'

router.beforeEach(async (to, _from, next) => {
  const store = useUserStore()

  // page title
  if (to.meta?.title) document.title = `${to.meta.title} · ${TITLE}`
  else document.title = TITLE

  const requiresAuth = to.matched.some((r) => r.meta?.requiresAuth !== false && r.meta?.requiresAuth)

  // Public route + already logged-in → bounce to dashboard
  if (to.path === '/login' && store.isLoggedIn) {
    return next('/dashboard')
  }

  // Protected route + no token → login
  if (requiresAuth && !store.isLoggedIn) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  // Protected route + token but no profile yet → fetch
  if (requiresAuth && store.isLoggedIn && !store.userInfo) {
    try {
      await store.getUserInfo()
    } catch {
      store.logout()
      return next({ path: '/login' })
    }
  }

  // Role gate via meta.roles
  const roles = to.matched
    .map((r) => (r.meta?.roles as string[] | undefined))
    .filter(Boolean)
    .pop()
  if (roles && roles.length > 0 && !store.hasRole(roles)) {
    ElMessage.warning('您没有权限访问该页面')
    return next('/dashboard')
  }

  // 菜单权限拦截：访问需要登录的页面时，检查是否在用户菜单权限内
  // admin 忽略；路由路径以 / 开头且存在于带鉴权的主布局下
  if (requiresAuth && store.userInfo && to.path !== '/dashboard' && to.path !== '/') {
    const normalized = to.path.replace(/\/$/, '') || to.path
    // 仅对主布局下的顶级菜单项验证（避免影响嵌套子路由）
    const topLevel = '/' + normalized.split('/').filter(Boolean)[0]
    const knownMenuPaths = [
      '/dashboard',
      '/invoice',
      '/email-config',
      '/export',
      '/print',
      '/users',
      '/categories',
      '/reimbursement',
    ]
    if (knownMenuPaths.includes(topLevel) && !store.canAccessMenu(topLevel)) {
      ElMessage.warning('您没有权限访问该菜单')
      return next('/dashboard')
    }
  }

  next()
})

export default router
