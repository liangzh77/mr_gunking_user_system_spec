<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>MR运营系统</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="['finance', 'sites', 'data']"
        :unique-opened="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/operator/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>

        <el-sub-menu index="finance">
          <template #title>
            <el-icon><Wallet /></el-icon>
            <span>财务管理</span>
          </template>
          <el-menu-item index="/operator/recharge">
            <el-icon><CreditCard /></el-icon>
            <span>在线充值</span>
          </el-menu-item>
          <el-menu-item index="/operator/transactions">
            <el-icon><List /></el-icon>
            <span>交易记录</span>
          </el-menu-item>
          <el-menu-item index="/operator/refunds">
            <el-icon><RefreshLeft /></el-icon>
            <span>退款管理</span>
          </el-menu-item>
          <el-menu-item index="/operator/invoices">
            <el-icon><Document /></el-icon>
            <span>发票管理</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="sites">
          <template #title>
            <el-icon><OfficeBuilding /></el-icon>
            <span>运营点管理</span>
          </template>
          <el-menu-item index="/operator/sites">
            <el-icon><MapLocation /></el-icon>
            <span>运营点列表</span>
          </el-menu-item>
          <el-menu-item index="/operator/applications">
            <el-icon><Grid /></el-icon>
            <span>已授权应用</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="data">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>数据分析</span>
          </template>
          <el-menu-item index="/operator/usage-records">
            <el-icon><Tickets /></el-icon>
            <span>使用记录</span>
          </el-menu-item>
          <el-menu-item index="/operator/statistics">
            <el-icon><TrendCharts /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/operator/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/operator/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="breadcrumb">{{ breadcrumb }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="authStore.profile" :type="tierTagType" effect="dark">
            {{ tierLabel }}
          </el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ authStore.profile?.username || '用户' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 面包屑
const breadcrumbMap: Record<string, string> = {
  '/operator/dashboard': '仪表盘',
  '/operator/profile': '个人中心',
  '/operator/recharge': '在线充值',
  '/operator/transactions': '交易记录',
  '/operator/refunds': '退款管理',
  '/operator/invoices': '发票管理',
  '/operator/sites': '运营点列表',
  '/operator/applications': '已授权应用',
  '/operator/usage-records': '使用记录',
  '/operator/statistics': '统计分析',
}
const breadcrumb = computed(() => breadcrumbMap[route.path] || '')

// 客户分类标签
const tierTagType = computed(() => {
  switch (authStore.profile?.customer_tier) {
    case 'vip':
      return 'danger'
    case 'regular':
      return 'success'
    case 'trial':
      return 'info'
    default:
      return 'info'
  }
})

const tierLabel = computed(() => {
  switch (authStore.profile?.customer_tier) {
    case 'vip':
      return 'VIP客户'
    case 'regular':
      return '普通客户'
    case 'trial':
      return '试用客户'
    default:
      return '未知'
  }
})

// 下拉菜单命令处理
const handleCommand = async (command: string) => {
  if (command === 'profile') {
    router.push('/operator/profile')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })

      await authStore.logout()
      ElMessage.success('已退出登录')
      router.push('/operator/login')
    } catch (error) {
      // 用户取消
    }
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background-color: #2b3a4a;
}

.logo h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.el-menu {
  border-right: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #303133;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
