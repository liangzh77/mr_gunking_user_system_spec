<template>
  <el-result icon="warning" title="404" sub-title="页面不存在">
    <template #extra>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </template>
  </el-result>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const goHome = () => {
  // 根据当前路径前缀判断应返回哪个首页
  const path = route.path

  if (path.startsWith('/admin')) {
    router.push('/admin/dashboard')
  } else if (path.startsWith('/finance')) {
    router.push('/finance/dashboard')
  } else {
    router.push('/operator/dashboard')
  }
}
</script>

<style scoped>
.el-result {
  padding: 100px 0;
}
</style>
