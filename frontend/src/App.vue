<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAdminAuthStore } from '@/stores/adminAuth'
import { useFinanceAuthStore } from '@/stores/financeAuth'
// Force HMR update

const router = useRouter()
const authStore = useAuthStore()
const adminAuthStore = useAdminAuthStore()
const financeAuthStore = useFinanceAuthStore()

onMounted(() => {
  // 根据当前路由判断应该获取哪个用户的信息
  const currentPath = router.currentRoute.value.path

  if (currentPath.startsWith('/admin')) {
    // 管理员路由
    if (adminAuthStore.isAuthenticated) {
      adminAuthStore.fetchProfile()
    }
  } else if (currentPath.startsWith('/finance')) {
    // 财务路由
    if (financeAuthStore.isAuthenticated) {
      financeAuthStore.fetchProfile()
    }
  } else {
    // 运营商路由
    if (authStore.isAuthenticated) {
      authStore.fetchProfile()
    }
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

/* 全局表格样式 - 防止文本换行,超出部分截断 */
.el-table .el-table__cell {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.el-table .cell {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* 确保表格列本身也不换行 */
.el-table__body-wrapper .el-table__cell .cell {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* 针对所有表格内容 */
.el-table td.el-table__cell div,
.el-table th.el-table__cell div {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
</style>
