<template>
  <div class="operators-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>运营商管理</span>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.search"
            placeholder="用户名/姓名/邮箱/手机号"
            clearable
            style="width: 300px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 150px"
            @change="handleSearch"
          >
            <el-option label="活跃" value="active" />
            <el-option label="不活跃" value="inactive" />
            <el-option label="已锁定" value="locked" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 运营商列表 -->
      <el-table
        v-loading="loading"
        :data="operators"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="balance" label="账户余额" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'negative-balance': row.balance < 0 }">
              ¥{{ row.balance.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_tier" label="客户等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTierType(row.customer_tier)" size="small">
              {{ getTierLabel(row.customer_tier) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_locked" type="danger" size="small">已锁定</el-tag>
            <el-tag v-else-if="row.is_active" type="success" size="small">活跃</el-tag>
            <el-tag v-else type="info" size="small">不活跃</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">
            {{ row.last_login_at ? formatDate(row.last_login_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewDetails(row)">详情</el-button>
            <el-button
              v-if="row.is_locked"
              size="small"
              type="success"
              @click.stop="handleUnlock(row)"
            >
              解锁
            </el-button>
            <el-button
              v-else-if="row.is_active"
              size="small"
              type="warning"
              @click.stop="handleLock(row)"
            >
              锁定
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSearch"
        @current-change="handleSearch"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailsVisible" title="运营商详情" width="600px">
      <el-descriptions v-if="currentOperator" :column="2" border>
        <el-descriptions-item label="用户名">
          {{ currentOperator.username }}
        </el-descriptions-item>
        <el-descriptions-item label="姓名">
          {{ currentOperator.full_name }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ currentOperator.email || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          {{ currentOperator.phone || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="账户余额">
          <span :class="{ 'negative-balance': currentOperator.balance < 0 }">
            ¥{{ currentOperator.balance.toFixed(2) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="客户等级">
          <el-tag :type="getTierType(currentOperator.customer_tier)" size="small">
            {{ getTierLabel(currentOperator.customer_tier) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="账户状态">
          <el-tag v-if="currentOperator.is_locked" type="danger" size="small">已锁定</el-tag>
          <el-tag v-else-if="currentOperator.is_active" type="success" size="small">活跃</el-tag>
          <el-tag v-else type="info" size="small">不活跃</el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentOperator.is_locked" label="锁定原因">
          {{ currentOperator.locked_reason || '-' }}
        </el-descriptions-item>
        <el-descriptions-item v-if="currentOperator.is_locked" label="锁定时间">
          {{ currentOperator.locked_at ? formatDate(currentOperator.locked_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后登录时间">
          {{ currentOperator.last_login_at ? formatDate(currentOperator.last_login_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后登录IP">
          {{ currentOperator.last_login_ip || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(currentOperator.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDate(currentOperator.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import http from '@/utils/http'

interface Operator {
  id: string
  username: string
  full_name: string
  email?: string
  phone?: string
  balance: number
  customer_tier: string
  is_active: boolean
  is_locked: boolean
  locked_reason?: string
  locked_at?: string
  last_login_at?: string
  last_login_ip?: string
  created_at: string
  updated_at: string
}

const loading = ref(false)
const operators = ref<Operator[]>([])
const detailsVisible = ref(false)
const currentOperator = ref<Operator | null>(null)

const searchForm = reactive({
  search: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 获取运营商列表
const fetchOperators = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (searchForm.search) {
      params.search = searchForm.search
    }

    if (searchForm.status) {
      params.status = searchForm.status
    }

    const response = await http.get('/admins/operators', { params })
    operators.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch operators:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchOperators()
}

// 查看详情
const viewDetails = (row: Operator) => {
  currentOperator.value = row
  detailsVisible.value = true
}

// 行点击
const handleRowClick = (row: Operator) => {
  viewDetails(row)
}

// 锁定账户
const handleLock = async (row: Operator) => {
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入锁定原因', '锁定账户', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '锁定原因不能为空',
    })

    if (!reason) return

    ElMessage.info('锁定账户功能开发中')
    // TODO: 调用后端API锁定账户
  } catch (error) {
    // 用户取消
  }
}

// 解锁账户
const handleUnlock = async (row: Operator) => {
  try {
    await ElMessageBox.confirm(`确定要解锁账户 "${row.username}" 吗?`, '解锁账户', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    ElMessage.info('解锁账户功能开发中')
    // TODO: 调用后端API解锁账户
  } catch (error) {
    // 用户取消
  }
}

// 格式化日期
const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN')
}

// 获取客户等级类型
const getTierType = (tier: string) => {
  const types: Record<string, any> = {
    bronze: '',
    silver: 'info',
    gold: 'warning',
    platinum: 'danger',
  }
  return types[tier] || ''
}

// 获取客户等级标签
const getTierLabel = (tier: string) => {
  const labels: Record<string, string> = {
    bronze: '铜牌',
    silver: '银牌',
    gold: '金牌',
    platinum: '白金',
  }
  return labels[tier] || tier
}

onMounted(() => {
  fetchOperators()
})
</script>

<style scoped>
.operators-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.search-form {
  margin-bottom: 20px;
}

.negative-balance {
  color: #f56c6c;
  font-weight: 600;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
