<template>
  <div class="applications-page">
    <!-- 页面标题和操作栏 -->
    <el-card class="header-card">
      <div class="title-section">
        <el-icon :size="24"><Grid /></el-icon>
        <h2>已授权应用</h2>
      </div>
    </el-card>

    <!-- 应用列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <!-- 搜索栏 -->
      <div class="filter-container" style="margin-bottom: 16px">
        <el-input
          v-model="searchQuery"
          placeholder="搜索应用名称、描述..."
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleSearch" style="margin-left: 12px">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>

      <el-table
        v-copyable
        v-loading="loading"
        :data="applications"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="app_name" label="应用名称" min-width="150" />
        <el-table-column prop="description" label="应用描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="price_per_player" label="单价" width="120">
          <template #default="{ row }">
            <span class="price">¥{{ formatAmount(row.price_per_player) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="玩家限制" width="150">
          <template #default="{ row }">
            <span>{{ row.min_players }} - {{ row.max_players }} 人</span>
          </template>
        </el-table-column>
        <el-table-column prop="authorized_at" label="授权时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.authorized_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default>
            <el-tag type="success" size="small">已授权</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && applications.length === 0" class="empty-state">
        <el-empty description="暂无已授权应用">
          <el-text type="info">请联系管理员申请应用授权</el-text>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useOperatorStore } from '@/stores/operator'
import type { AuthorizedApplication } from '@/types'
import { formatDateTime, formatAmount} from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const applications = ref<AuthorizedApplication[]>([])
const searchQuery = ref('')

// 加载已授权应用列表
const loadApplications = async () => {
  loading.value = true
  try {
    const params: any = {}

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    applications.value = await operatorStore.getAuthorizedApplications(params)
  } catch (error) {
    console.error('Load applications error:', error)
    ElMessage.error('加载应用列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  loadApplications()
}

onMounted(() => {
  loadApplications()
})
</script>

<style scoped>
.applications-page {
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 0;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.price {
  color: #409EFF;
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}
</style>
