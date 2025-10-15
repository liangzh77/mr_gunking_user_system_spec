<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>MR游戏运营管理系统</h2>
          <p>财务人员登录</p>
        </div>
      </template>
      <el-result icon="info" title="财务功能开发中" sub-title="该模块将在Phase 8实现" />
    </el-card>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 450px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #303133;
}

.card-header p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}
</style>
