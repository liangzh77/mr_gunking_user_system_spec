<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>MR管理后台</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>管理面板</span>
        </el-menu-item>

        <el-sub-menu index="operators">
          <template #title>
            <el-icon><UserFilled /></el-icon>
            <span>运营商管理</span>
          </template>
          <el-menu-item index="/admin/operators">
            <el-icon><User /></el-icon>
            <span>运营商列表</span>
          </el-menu-item>
          <el-menu-item index="/admin/operator-sites">
            <el-icon><OfficeBuilding /></el-icon>
            <span>运营点管理</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="applications">
          <template #title>
            <el-icon><Grid /></el-icon>
            <span>应用管理</span>
          </template>
          <el-menu-item index="/admin/applications">
            <el-icon><Collection /></el-icon>
            <span>应用列表</span>
          </el-menu-item>
          <el-menu-item index="/admin/app-requests">
            <el-icon><Document /></el-icon>
            <span>授权申请</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="finance">
          <template #title>
            <el-icon><Wallet /></el-icon>
            <span>财务管理</span>
          </template>
          <el-menu-item index="/admin/transactions">
            <el-icon><List /></el-icon>
            <span>交易记录</span>
          </el-menu-item>
          <el-menu-item index="/admin/refunds">
            <el-icon><RefreshLeft /></el-icon>
            <span>退款审核</span>
          </el-menu-item>
          <el-menu-item index="/admin/invoices">
            <el-icon><Tickets /></el-icon>
            <span>发票审核</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="data">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>数据统计</span>
          </template>
          <el-menu-item index="/admin/usage-stats">
            <el-icon><TrendCharts /></el-icon>
            <span>使用统计</span>
          </el-menu-item>
          <el-menu-item index="/admin/revenue-stats">
            <el-icon><Money /></el-icon>
            <span>收入统计</span>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="breadcrumb">{{ breadcrumb }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="adminAuthStore.profile" :type="roleTagType" effect="dark">
            {{ roleLabel }}
          </el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ adminAuthStore.profile?.full_name || '管理员' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人信息
                </el-dropdown-item>
                <el-dropdown-item command="changePassword">
                  <el-icon><Lock /></el-icon>
                  修改密码
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
import {
  UserFilled,
  User,
  Odometer,
  OfficeBuilding,
  Grid,
  Collection,
  Document,
  Wallet,
  List,
  RefreshLeft,
  Tickets,
  DataAnalysis,
  TrendCharts,
  Money,
  Setting,
  ArrowDown,
  Lock,
  SwitchButton,
} from '@element-plus/icons-vue'
import { useAdminAuthStore } from '@/stores/adminAuth'

const router = useRouter()
const route = useRoute()
const adminAuthStore = useAdminAuthStore()

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 面包屑
const breadcrumbMap: Record<string, string> = {
  '/admin/dashboard': '管理面板',
  '/admin/operators': '运营商列表',
  '/admin/operator-sites': '运营点管理',
  '/admin/applications': '应用列表',
  '/admin/app-requests': '授权申请',
  '/admin/transactions': '交易记录',
  '/admin/refunds': '退款审核',
  '/admin/invoices': '发票审核',
  '/admin/usage-stats': '使用统计',
  '/admin/revenue-stats': '收入统计',
  '/admin/settings': '系统设置',
}
const breadcrumb = computed(() => breadcrumbMap[route.path] || '')

// 角色标签
const roleTagType = computed(() => {
  switch (adminAuthStore.profile?.role) {
    case 'super_admin':
      return 'danger'
    case 'admin':
      return 'warning'
    case 'finance':
      return 'success'
    default:
      return 'info'
  }
})

const roleLabel = computed(() => {
  switch (adminAuthStore.profile?.role) {
    case 'super_admin':
      return '超级管理员'
    case 'admin':
      return '管理员'
    case 'finance':
      return '财务'
    default:
      return '未知'
  }
})

// 下拉菜单命令处理
const handleCommand = async (command: string) => {
  if (command === 'profile') {
    ElMessage.info('个人信息功能开发中')
  } else if (command === 'changePassword') {
    ElMessage.info('修改密码功能开发中')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })

      await adminAuthStore.logout()
      ElMessage.success('已退出登录')
      router.push('/admin/login')
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
