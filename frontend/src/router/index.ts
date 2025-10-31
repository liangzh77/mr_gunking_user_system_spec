import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAdminAuthStore } from '@/stores/adminAuth'
import { useFinanceAuthStore } from '@/stores/financeAuth'

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
            {
              path: 'app-requests',
              name: 'OperatorAppRequests',
              component: () => import('@/pages/operator/AppRequests.vue'),
            },
            {
              path: 'messages',
              name: 'Messages',
              component: () => import('@/pages/operator/Messages.vue'),
            },
          ],
        },
      ],
    },
    // ========== 管理员端路由 ==========
    {
      path: '/admin',
      children: [
        {
          path: 'login',
          name: 'AdminLogin',
          component: () => import('@/pages/admin/Login.vue'),
          meta: { requiresAuth: false, requiresAdmin: false },
        },
        {
          path: '',
          component: () => import('@/pages/admin/Layout.vue'),
          meta: { requiresAuth: true, requiresAdmin: true },
          children: [
            {
              path: 'dashboard',
              name: 'AdminDashboard',
              component: () => import('@/pages/admin/Dashboard.vue'),
            },
            {
              path: 'operators',
              name: 'AdminOperators',
              component: () => import('@/pages/admin/Operators.vue'),
            },
            {
              path: 'operator-sites',
              name: 'AdminOperatorSites',
              component: () => import('@/pages/admin/OperatorSites.vue'),
            },
            {
              path: 'applications',
              name: 'AdminApplications',
              component: () => import('@/pages/admin/Applications.vue'),
            },
            {
              path: 'app-requests',
              name: 'AdminAppRequests',
              component: () => import('@/pages/admin/AppRequests.vue'),
            },
            {
              path: 'applications/create',
              name: 'AdminCreateApplication',
              component: () => import('@/pages/admin/CreateApplication.vue'),
            },
            {
              path: 'authorizations',
              name: 'AdminAuthorizations',
              component: () => import('@/pages/admin/Authorizations.vue'),
            },
            {
              path: 'transactions',
              name: 'AdminTransactions',
              component: () => import('@/pages/admin/Transactions.vue'),
            },
          ],
        },
      ],
    },
    // ========== 财务端路由 ==========
    {
      path: '/finance',
      children: [
        {
          path: 'login',
          name: 'FinanceLogin',
          component: () => import('@/pages/finance/Login.vue'),
          meta: { requiresAuth: false, requiresFinance: false },
        },
        {
          path: '',
          component: () => import('@/pages/finance/Layout.vue'),
          meta: { requiresAuth: true, requiresFinance: true },
          children: [
            {
              path: 'dashboard',
              name: 'FinanceDashboard',
              component: () => import('@/pages/finance/Dashboard.vue'),
            },
            {
              path: 'recharge-records',
              name: 'FinanceRechargeRecords',
              component: () => import('@/pages/finance/RechargeRecords.vue'),
            },
            {
              path: 'refunds',
              name: 'FinanceRefunds',
              component: () => import('@/pages/finance/Refunds.vue'),
            },
            {
              path: 'invoices',
              name: 'FinanceInvoices',
              component: () => import('@/pages/finance/Invoices.vue'),
            },
            {
              path: 'reports',
              name: 'FinanceReports',
              component: () => import('@/pages/finance/Reports.vue'),
            },
            {
              path: 'audit-logs',
              name: 'FinanceAuditLogs',
              component: () => import('@/pages/finance/AuditLogs.vue'),
            },
          ],
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
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const adminAuthStore = useAdminAuthStore()
  const financeAuthStore = useFinanceAuthStore()

  // 需要认证的路由
  if (to.meta.requiresAuth) {
    // 管理员路由
    if (to.meta.requiresAdmin) {
      if (!adminAuthStore.isAuthenticated) {
        // 管理员未登录,重定向到管理员登录页
        next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
      } else {
        next()
      }
    }
    // 财务路由
    else if (to.meta.requiresFinance) {
      if (!financeAuthStore.isAuthenticated) {
        // 财务人员未登录,重定向到财务登录页
        next({ name: 'FinanceLogin', query: { redirect: to.fullPath } })
      } else {
        next()
      }
    }
    // 运营商路由
    else {
      if (!authStore.isAuthenticated) {
        // 未登录,重定向到运营商登录页
        next({ name: 'OperatorLogin', query: { redirect: to.fullPath } })
      } else {
        next()
      }
    }
  } else {
    // 已登录用户访问登录页,重定向到对应的仪表盘
    if (adminAuthStore.isAuthenticated && to.name === 'AdminLogin') {
      next({ name: 'AdminDashboard' })
    } else if (financeAuthStore.isAuthenticated && to.name === 'FinanceLogin') {
      next({ name: 'FinanceDashboard' })
    } else if (authStore.isAuthenticated && (to.name === 'OperatorLogin' || to.name === 'OperatorRegister')) {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  }
})

export default router
