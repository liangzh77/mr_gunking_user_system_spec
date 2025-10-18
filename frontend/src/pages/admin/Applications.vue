<template>
  <div class="applications-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>应用管理</span>
          <el-button type="primary" @click="createApplication">
            <el-icon><Plus /></el-icon>
            创建应用
          </el-button>
        </div>
      </template>

      <!-- 搜索 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="searchKeyword"
            placeholder="应用代码/应用名称"
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
      </el-form>

      <!-- 应用列表 -->
      <el-table
        v-loading="loading"
        :data="applications"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="app_code" label="应用代码" width="180" />
        <el-table-column prop="app_name" label="应用名称" width="200" />
        <el-table-column prop="description" label="描述" min-width="250" />
        <el-table-column prop="price_per_request" label="单价(元/次)" width="130" align="right">
          <template #default="{ row }">
            ¥{{ row.price_per_request.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success" size="small">启用</el-tag>
            <el-tag v-else type="info" size="small">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewDetails(row)">详情</el-button>
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
    <el-dialog v-model="detailsVisible" title="应用详情" width="600px">
      <el-descriptions v-if="currentApplication" :column="2" border>
        <el-descriptions-item label="应用代码">
          {{ currentApplication.app_code }}
        </el-descriptions-item>
        <el-descriptions-item label="应用名称">
          {{ currentApplication.app_name }}
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          {{ currentApplication.description }}
        </el-descriptions-item>
        <el-descriptions-item label="单价">
          ¥{{ currentApplication.price_per_request.toFixed(4) }} / 次
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="currentApplication.is_active" type="success" size="small">启用</el-tag>
          <el-tag v-else type="info" size="small">禁用</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(currentApplication.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDate(currentApplication.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="detailsVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import http from '@/utils/http'

const router = useRouter()

interface Application {
  id: string
  app_code: string
  app_name: string
  description: string
  price_per_request: number
  is_active: boolean
  created_at: string
  updated_at: string
}

const loading = ref(false)
const applications = ref<Application[]>([])
const detailsVisible = ref(false)
const currentApplication = ref<Application | null>(null)
const searchKeyword = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 获取应用列表
const fetchApplications = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }

    const response = await http.get('/admin/admins/applications', { params })
    applications.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch applications:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchApplications()
}

// 查看详情
const viewDetails = (row: Application) => {
  currentApplication.value = row
  detailsVisible.value = true
}

// 行点击
const handleRowClick = (row: Application) => {
  viewDetails(row)
}

// 格式化日期
const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN')
}

// 创建应用
const createApplication = () => {
  router.push('/admin/applications/create')
}

onMounted(() => {
  fetchApplications()
})
</script>

<style scoped>
.applications-page {
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

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
