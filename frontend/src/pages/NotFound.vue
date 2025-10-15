<template>
  <el-result icon="warning" title="404" sub-title="页面不存在">
    <template #extra>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </template>
  </el-result>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/operator/dashboard')
}
</script>

<style scoped>
.el-result {
  padding: 100px 0;
}
</style>
