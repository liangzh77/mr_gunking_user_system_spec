<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>MR财务后台</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/finance/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>财务面板</span>
        </el-menu-item>

        <el-menu-item index="/finance/recharge-records">
          <el-icon><CreditCard /></el-icon>
          <span>充值记录</span>
        </el-menu-item>

        <el-sub-menu index="审核">
          <template #title>
            <el-icon><DocumentChecked /></el-icon>
            <span>审核管理</span>
          </template>
          <el-menu-item index="/finance/refunds">
            <el-icon><RefreshLeft /></el-icon>
            <span>退款审核</span>
          </el-menu-item>
          <el-menu-item index="/finance/invoices">
            <el-icon><Tickets /></el-icon>
            <span>发票审核</span>
          </el-menu-item>
          <el-menu-item index="/finance/bank-transfers">
            <el-icon><Money /></el-icon>
            <span>银行转账审核</span>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/finance/reports">
          <el-icon><Document /></el-icon>
          <span>财务报表</span>
        </el-menu-item>

        <el-menu-item index="/finance/audit-logs">
          <el-icon><List /></el-icon>
          <span>审计日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/finance/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="breadcrumb">{{ breadcrumb }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag type="success" effect="dark">财务人员</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ financeAuthStore.profile?.full_name || '财务人员' }}</span>
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
  CreditCard,
  DocumentChecked,
  RefreshLeft,
  Tickets,
  Document,
  List,
  ArrowDown,
  Lock,
  SwitchButton,
  Money,
} from '@element-plus/icons-vue'
import { useFinanceAuthStore } from '@/stores/financeAuth'

const router = useRouter()
const route = useRoute()
const financeAuthStore = useFinanceAuthStore()

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 面包屑
const breadcrumbMap: Record<string, string> = {
  '/finance/dashboard': '财务面板',
  '/finance/recharge-records': '充值记录',
  '/finance/refunds': '退款审核',
  '/finance/invoices': '发票审核',
  '/finance/bank-transfers': '银行转账审核',
  '/finance/reports': '财务报表',
  '/finance/audit-logs': '审计日志',
}
const breadcrumb = computed(() => breadcrumbMap[route.path] || '')

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

      await financeAuthStore.logout()
      ElMessage.success('已退出登录')
      router.push('/finance/login')
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
