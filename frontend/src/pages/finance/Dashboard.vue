<template>
  <div class="dashboard">
    <!-- 今日财务概览 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #67c23a">
            <el-icon :size="32"><Money /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日充值</div>
            <div class="stat-value">¥{{ dashboard.today_recharge || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #e6a23c">
            <el-icon :size="32"><Wallet /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日消费</div>
            <div class="stat-value">¥{{ dashboard.today_consumption || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #f56c6c">
            <el-icon :size="32"><RefreshLeft /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日退款</div>
            <div class="stat-value">¥{{ dashboard.today_refund || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #409eff">
            <el-icon :size="32"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日净收入</div>
            <div class="stat-value">¥{{ dashboard.today_net_income || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运营商统计 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #909399">
            <el-icon :size="32"><UserFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">运营商总数</div>
            <div class="stat-value">{{ dashboard.total_operators || 0 }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #5a3bbd">
            <el-icon :size="32"><Avatar /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日活跃运营商</div>
            <div class="stat-value">{{ dashboard.active_operators_today || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Top客户列表 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>消费Top客户</span>
              <el-button type="primary" size="small" @click="fetchTopCustomers">刷新</el-button>
            </div>
          </template>
          <el-table :data="topCustomers" stripe>
            <el-table-column prop="rank" label="排名" width="80" align="center" />
            <el-table-column prop="operator_name" label="运营商名称" />
            <el-table-column prop="total_consumption" label="累计消费" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_consumption }}
              </template>
            </el-table-column>
            <el-table-column prop="total_recharge" label="累计充值" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_recharge }}
              </template>
            </el-table-column>
            <el-table-column prop="current_balance" label="当前余额" align="right">
              <template #default="scope">
                ¥{{ scope.row.current_balance }}
              </template>
            </el-table-column>
            <el-table-column prop="customer_tier" label="客户分类" width="100" align="center">
              <template #default="scope">
                <el-tag :type="getTierType(scope.row.customer_tier)">
                  {{ getTierLabel(scope.row.customer_tier) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 待处理事项 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待处理事项</span>
            </div>
          </template>
          <div class="pending-items">
            <div class="pending-item" @click="$router.push('/finance/refunds')">
              <el-icon :size="20" color="#f56c6c"><RefreshLeft /></el-icon>
              <span>待审核退款</span>
              <el-badge :value="pendingRefunds" class="badge" />
            </div>
            <div class="pending-item" @click="$router.push('/finance/invoices')">
              <el-icon :size="20" color="#409eff"><Tickets /></el-icon>
              <span>待审核发票</span>
              <el-badge :value="pendingInvoices" class="badge" />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快速操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/finance/refunds')">
              <el-icon><RefreshLeft /></el-icon>
              退款审核
            </el-button>
            <el-button type="success" @click="$router.push('/finance/invoices')">
              <el-icon><Tickets /></el-icon>
              发票审核
            </el-button>
            <el-button type="info" @click="$router.push('/finance/reports')">
              <el-icon><Document /></el-icon>
              财务报表
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Money,
  Wallet,
  RefreshLeft,
  TrendCharts,
  UserFilled,
  Avatar,
  Tickets,
  Document,
} from '@element-plus/icons-vue'
import http from '@/utils/http'

// 仪表盘数据
const dashboard = ref({
  today_recharge: '0.00',
  today_consumption: '0.00',
  today_refund: '0.00',
  today_net_income: '0.00',
  total_operators: 0,
  active_operators_today: 0,
})

// Top客户列表
const topCustomers = ref<any[]>([])

// 待处理数量
const pendingRefunds = ref(0)
const pendingInvoices = ref(0)

// 获取仪表盘数据
const fetchDashboard = async () => {
  try {
    const response = await http.get('/finance/dashboard')
    dashboard.value = response.data
  } catch (error: any) {
    ElMessage.error('获取财务概览失败')
  }
}

// 获取Top客户
const fetchTopCustomers = async () => {
  try {
    const response = await http.get('/finance/top-customers', {
      params: { limit: 10 }
    })
    topCustomers.value = response.data.customers || []
  } catch (error: any) {
    ElMessage.error('获取Top客户失败')
  }
}

// 客户分类标签
const getTierType = (tier: string) => {
  switch (tier) {
    case 'vip': return 'danger'
    case 'standard': return 'success'
    case 'trial': return 'info'
    default: return 'info'
  }
}

const getTierLabel = (tier: string) => {
  switch (tier) {
    case 'vip': return 'VIP'
    case 'standard': return '普通'
    case 'trial': return '试用'
    default: return '未知'
  }
}

// 页面加载时获取数据
onMounted(() => {
  fetchDashboard()
  fetchTopCustomers()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
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
}

.pending-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.pending-item:hover {
  background-color: #f5f7fa;
}

.pending-item span {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.badge {
  margin-left: auto;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
