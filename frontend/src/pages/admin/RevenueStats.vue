<template>
  <div class="coming-soon-page">
    <el-card class="coming-soon-card">
      <div class="content">
        <el-icon class="icon" :size="80">
          <Money />
        </el-icon>
        <h1 class="title">收入统计</h1>
        <p class="subtitle">功能开发中，敬请期待</p>
        <el-divider />
        <div class="features">
          <h3>即将推出的功能：</h3>
          <ul>
            <li>
              <el-icon><Check /></el-icon>
              <span>收入趋势图表展示</span>
            </li>
            <li>
              <el-icon><Check /></el-icon>
              <span>按应用分类收入统计</span>
            </li>
            <li>
              <el-icon><Check /></el-icon>
              <span>运营商贡献度分析</span>
            </li>
            <li>
              <el-icon><Check /></el-icon>
              <span>收入预测与对比分析</span>
            </li>
          </ul>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Money, Check } from '@element-plus/icons-vue'
</script>

<style scoped>
.coming-soon-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 40px;
}

.coming-soon-card {
  max-width: 600px;
  width: 100%;
}

.content {
  text-align: center;
  padding: 40px 20px;
}

.icon {
  color: #409eff;
  margin-bottom: 24px;
}

.title {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
}

.subtitle {
  font-size: 18px;
  color: #909399;
  margin: 0 0 32px 0;
}

.features {
  text-align: left;
  margin-top: 32px;
}

.features h3 {
  font-size: 18px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 20px 0;
}

.features ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.features li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  font-size: 16px;
  color: #606266;
}

.features li .el-icon {
  color: #67c23a;
  font-size: 18px;
}
</style>
