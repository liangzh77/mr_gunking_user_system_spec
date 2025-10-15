import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/operator/login',
    },
    // ========== 运营商端路由 ==========
    {
      path: '/operator',
      children: [
        {
          path: 'login',
          name: 'OperatorLogin',
          component: () => import('@/pages/operator/Login.vue'),
          meta: { requiresAuth: false },
        },
        {
          path: 'register',
          name: 'OperatorRegister',
          component: () => import('@/pages/operator/Register.vue'),
          meta: { requiresAuth: false },
        },
        {
          path: '',
          component: () => import('@/pages/operator/Layout.vue'),
          meta: { requiresAuth: true },
          children: [
            {
              path: 'dashboard',
              name: 'Dashboard',
              component: () => import('@/pages/operator/Dashboard.vue'),
            },
            {
              path: 'profile',
              name: 'Profile',
              component: () => import('@/pages/operator/Profile.vue'),
            },
            {
              path: 'recharge',
              name: 'Recharge',
              component: () => import('@/pages/operator/Recharge.vue'),
            },
            {
              path: 'transactions',
              name: 'Transactions',
              component: () => import('@/pages/operator/Transactions.vue'),
            },
            {
              path: 'refunds',
              name: 'Refunds',
              component: () => import('@/pages/operator/Refunds.vue'),
            },
            {
              path: 'invoices',
              name: 'Invoices',
              component: () => import('@/pages/operator/Invoices.vue'),
            },
            {
              path: 'sites',
              name: 'Sites',
              component: () => import('@/pages/operator/Sites.vue'),
            },
            {
              path: 'applications',
              name: 'Applications',
              component: () => import('@/pages/operator/Applications.vue'),
            },
            {
              path: 'usage-records',
              name: 'UsageRecords',
              component: () => import('@/pages/operator/UsageRecords.vue'),
            },
            {
              path: 'statistics',
              name: 'Statistics',
              component: () => import('@/pages/operator/Statistics.vue'),
            },
          ],
        },
      ],
    },
    // ========== 管理员端路由 (预留) ==========
    {
      path: '/admin',
      children: [
        {
          path: 'login',
          name: 'AdminLogin',
          component: () => import('@/pages/admin/Login.vue'),
          meta: { requiresAuth: false },
        },
      ],
    },
    // ========== 财务端路由 (预留) ==========
    {
      path: '/finance',
      children: [
        {
          path: 'login',
          name: 'FinanceLogin',
          component: () => import('@/pages/finance/Login.vue'),
          meta: { requiresAuth: false },
        },
      ],
    },
    // ========== 404 ==========
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/pages/NotFound.vue'),
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 需要认证的路由
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      // 未登录,重定向到登录页
      next({ name: 'OperatorLogin', query: { redirect: to.fullPath } })
    } else {
      next()
    }
  } else {
    // 已登录用户访问登录页,重定向到仪表盘
    if (authStore.isAuthenticated && (to.name === 'OperatorLogin' || to.name === 'OperatorRegister')) {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  }
})

export default router
