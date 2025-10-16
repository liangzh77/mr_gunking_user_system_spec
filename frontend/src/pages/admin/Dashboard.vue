<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #409eff">
            <el-icon :size="32"><UserFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">运营商总数</div>
            <div class="stat-value">--</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #67c23a">
            <el-icon :size="32"><Grid /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">应用总数</div>
            <div class="stat-value">{{ stats.applicationsCount }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #e6a23c">
            <el-icon :size="32"><List /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日交易</div>
            <div class="stat-value">--</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #f56c6c">
            <el-icon :size="32"><Money /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日收入</div>
            <div class="stat-value">--</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待处理事项</span>
            </div>
          </template>
          <div class="pending-items">
            <div class="pending-item">
              <el-icon :size="20" color="#e6a23c"><Document /></el-icon>
              <span>待审核授权申请</span>
              <el-badge :value="0" class="badge" />
            </div>
            <div class="pending-item">
              <el-icon :size="20" color="#f56c6c"><RefreshLeft /></el-icon>
              <span>待处理退款</span>
              <el-badge :value="0" class="badge" />
            </div>
            <div class="pending-item">
              <el-icon :size="20" color="#409eff"><Tickets /></el-icon>
              <span>待审核发票</span>
              <el-badge :value="0" class="badge" />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统信息</span>
            </div>
          </template>
          <div class="system-info">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="当前管理员">
                {{ adminAuthStore.profile?.full_name || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="角色">
                {{ roleLabel }}
              </el-descriptions-item>
              <el-descriptions-item label="用户名">
                {{ adminAuthStore.profile?.username || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="系统版本">
                v0.1.0
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快速访问</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/admin/operators')">
              <el-icon><UserFilled /></el-icon>
              运营商管理
            </el-button>
            <el-button type="success" @click="$router.push('/admin/applications')">
              <el-icon><Grid /></el-icon>
              应用管理
            </el-button>
            <el-button type="warning" @click="$router.push('/admin/app-requests')">
              <el-icon><Document /></el-icon>
              授权审核
            </el-button>
            <el-button type="info" @click="$router.push('/admin/refunds')">
              <el-icon><RefreshLeft /></el-icon>
              退款审核
            </el-button>
            <el-button type="danger" @click="$router.push('/admin/usage-stats')">
              <el-icon><TrendCharts /></el-icon>
              数据统计
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useAdminAuthStore } from '@/stores/adminAuth'

const adminAuthStore = useAdminAuthStore()

// 统计数据（暂时使用固定值，后续可以从API获取）
const stats = reactive({
  operatorsCount: 0,
  applicationsCount: 3, // 初始化时创建了3个应用
  todayTransactions: 0,
  todayRevenue: 0,
})

// 角色标签
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
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-right: 16px;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.pending-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.pending-item:hover {
  background-color: #e4e7ed;
}

.pending-item span {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.badge {
  margin-left: auto;
}

.system-info {
  padding: 8px 0;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
