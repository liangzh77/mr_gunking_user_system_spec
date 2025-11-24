<template>
  <div class="usage-records-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Document /></el-icon>
          <h2>使用记录</h2>
        </div>
        <el-button type="success" :loading="exporting" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出记录
        </el-button>
      </div>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card" style="margin-top: 20px">
      <el-form :model="filterForm" label-width="80px" :inline="true">
        <el-form-item label="搜索">
          <el-input
            v-model="searchQuery"
            placeholder="搜索会话ID、运营点、应用..."
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
            style="width: 250px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 380px"
          />
        </el-form-item>

        <el-form-item label="运营点">
          <el-select
            v-model="filterForm.site_id"
            placeholder="全部运营点"
            clearable
            style="width: 200px"
          >
            <el-option
              v-for="site in sites"
              :key="site.site_id"
              :label="site.name"
              :value="site.site_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="应用">
          <el-select
            v-model="filterForm.app_id"
            placeholder="全部应用"
            clearable
            style="width: 200px"
          >
            <el-option
              v-for="app in applications"
              :key="app.app_id"
              :label="app.app_name"
              :value="app.app_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 使用记录列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-copyable
        v-loading="loading"
        :data="records"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="session_id" label="会话ID" width="220" show-overflow-tooltip />
        <el-table-column prop="site_name" label="运营点" width="150" />
        <el-table-column prop="app_name" label="应用" width="150" />
        <el-table-column prop="player_count" label="玩家数" width="100" align="center" />
        <el-table-column prop="unit_price" label="单价" width="100">
          <template #default="{ row }">
            ¥{{ formatAmount(row.unit_price) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_cost" label="总费用" width="120">
          <template #default="{ row }">
            <span class="total-cost">¥{{ formatAmount(row.total_cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="使用时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && records.length === 0" class="empty-state">
        <el-empty description="暂无使用记录" />
      </div>

      <!-- 分页 -->
      <div v-if="pagination.total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadRecords"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 统计信息 -->
    <el-card v-if="records.length > 0" style="margin-top: 20px">
      <div class="statistics">
        <div class="stat-item">
          <div class="stat-label">总记录数</div>
          <div class="stat-value">{{ pagination.total }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">当前页记录</div>
          <div class="stat-value">{{ records.length }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">当前页总费用</div>
          <div class="stat-value page-total">¥{{ formatAmount(pageTotal) }}</div>
        </div>
      </div>
    </el-card>

    <!-- 详情Dialog -->
    <el-dialog
      v-model="detailDialogVisible"
      title="使用记录详情"
      width="800px"
    >
      <div v-loading="loadingDetail" class="detail-container">
        <template v-if="detailData">
          <!-- 基本信息 -->
          <el-descriptions :column="2" border>
            <el-descriptions-item label="会话ID">{{ detailData.session_id }}</el-descriptions-item>
            <el-descriptions-item label="运营点">{{ detailData.site_name }}</el-descriptions-item>
            <el-descriptions-item label="应用">{{ detailData.app_name }}</el-descriptions-item>
            <el-descriptions-item label="玩家数">{{ detailData.player_count }}</el-descriptions-item>
            <el-descriptions-item label="单价">¥{{ formatAmount(detailData.unit_price) }}</el-descriptions-item>
            <el-descriptions-item label="总费用">¥{{ formatAmount(detailData.total_cost) }}</el-descriptions-item>
            <el-descriptions-item label="使用时间" :span="2">
              {{ formatDateTime(detailData.created_at) }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 游戏信息 -->
          <div v-if="detailData.game_sessions && detailData.game_sessions.length > 0" style="margin-top: 20px">
            <h3 style="margin-bottom: 10px">游戏信息</h3>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="开始时间">
                {{ detailData.game_sessions[0].start_time ? formatDateTime(detailData.game_sessions[0].start_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="结束时间">
                {{ detailData.game_sessions[0].end_time ? formatDateTime(detailData.game_sessions[0].end_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item v-if="detailData.game_sessions[0].process_info" label="过程信息" :span="2">
                <pre style="white-space: pre-wrap; font-family: monospace">{{ detailData.game_sessions[0].process_info }}</pre>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 头显设备信息 -->
            <div v-if="detailData.game_sessions[0].headset_devices && detailData.game_sessions[0].headset_devices.length > 0" style="margin-top: 10px">
              <h4 style="margin-bottom: 8px">头显设备</h4>
              <el-table v-copyable :data="detailData.game_sessions[0].headset_devices" border size="small">
                <el-table-column prop="device_id" label="设备ID" width="120" />
                <el-table-column prop="device_name" label="设备名称" width="120" />
                <el-table-column prop="start_time" label="开始时间" width="160">
                  <template #default="{ row }">
                    {{ row.start_time ? formatDateTime(row.start_time) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="end_time" label="结束时间" width="160">
                  <template #default="{ row }">
                    {{ row.end_time ? formatDateTime(row.end_time) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="process_info" label="过程信息" min-width="200">
                  <template #default="{ row }">
                    <pre v-if="row.process_info" style="white-space: pre-wrap; font-family: monospace; margin: 0">{{ row.process_info }}</pre>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else style="margin-top: 20px">
            <el-empty description="暂无游戏信息" />
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { UsageRecord, OperationSite, AuthorizedApplication } from '@/types'
import { formatDateTime, formatAmount} from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const exporting = ref(false)
const records = ref<UsageRecord[]>([])
const sites = ref<OperationSite[]>([])
const applications = ref<AuthorizedApplication[]>([])
const dateRange = ref<[string, string] | null>(null)
const searchQuery = ref('')

const filterForm = ref({
  site_id: '',
  app_id: '',
})

const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
})

// 详情相关
const detailDialogVisible = ref(false)
const loadingDetail = ref(false)
const detailData = ref<any>(null)

// 计算当前页总费用
const pageTotal = computed(() => {
  return records.value
    .reduce((sum, record) => sum + parseFloat(record.total_cost), 0)
    .toFixed(2)
})

// 加载使用记录
const loadRecords = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    }

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    if (dateRange.value) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }

    if (filterForm.value.site_id) {
      params.site_id = filterForm.value.site_id
    }

    if (filterForm.value.app_id) {
      params.app_id = filterForm.value.app_id
    }

    const response = await operatorStore.getUsageRecords(params)
    records.value = response?.items || []
    pagination.value.total = response?.total || 0
  } catch (error) {
    console.error('Load usage records error:', error)
    ElMessage.error('加载使用记录失败')
    records.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

// 加载运营点列表
const loadSites = async () => {
  try {
    const response = await operatorStore.getSites()
    sites.value = response || []
  } catch (error) {
    console.error('Load sites error:', error)
    sites.value = []
  }
}

// 加载应用列表
const loadApplications = async () => {
  try {
    const response = await operatorStore.getAuthorizedApplications()
    applications.value = response || []
  } catch (error) {
    console.error('Load applications error:', error)
    applications.value = []
  }
}

// 搜索
const handleSearch = () => {
  pagination.value.page = 1
  loadRecords()
}

// 重置
const handleReset = () => {
  searchQuery.value = ''
  dateRange.value = null
  filterForm.value = {
    site_id: '',
    app_id: '',
  }
  pagination.value.page = 1
  loadRecords()
}

// 页大小变化
const handlePageSizeChange = () => {
  pagination.value.page = 1
  loadRecords()
}

// 导出记录
const handleExport = async () => {
  exporting.value = true
  try {
    const params: any = {
      format: 'excel',
    }

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    if (dateRange.value) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }

    if (filterForm.value.site_id) {
      params.site_id = filterForm.value.site_id
    }

    if (filterForm.value.app_id) {
      params.app_id = filterForm.value.app_id
    }

    // 调用导出API (现在返回blob)
    await operatorStore.exportUsageRecords(params)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export usage records error:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 显示详情
const showDetail = async (record: UsageRecord) => {
  loadingDetail.value = true
  detailDialogVisible.value = true
  detailData.value = null

  try {
    const response = await operatorStore.getUsageRecord(record.usage_id)
    detailData.value = response
  } catch (error) {
    console.error('Get usage record detail error:', error)
    ElMessage.error('获取详情失败')
    detailDialogVisible.value = false
  } finally {
    loadingDetail.value = false
  }
}

onMounted(() => {
  loadSites()
  loadApplications()
  loadRecords()
})
</script>

<style scoped>
.usage-records-page {
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.filter-card :deep(.el-card__body) {
  padding: 20px;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.total-cost {
  color: #F56C6C;
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.statistics {
  display: flex;
  gap: 40px;
  justify-content: center;
}

.stat-item {
  text-align: center;
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

.stat-value.page-total {
  color: #F56C6C;
}
</style>
