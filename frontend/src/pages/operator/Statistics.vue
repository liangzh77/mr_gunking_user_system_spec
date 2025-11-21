<template>
  <div class="statistics-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><DataAnalysis /></el-icon>
          <h2>统计分析</h2>
        </div>
        <el-button type="success" :loading="exporting" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出报表
        </el-button>
      </div>
    </el-card>

    <!-- 时间范围选择 -->
    <el-card class="filter-card" style="margin-top: 20px">
      <el-form :inline="true">
        <el-form-item label="统计周期">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 380px"
            @change="handleDateChange"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计Tabs -->
    <el-card style="margin-top: 20px">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 按运营点统计 -->
        <el-tab-pane label="按运营点统计" name="site">
          <el-table
            v-loading="siteLoading"
            :data="siteStatistics"
            v-copyable
            stripe
            style="width: 100%"
            :default-sort="{ prop: 'total_cost', order: 'descending' }"
          >
            <el-table-column prop="site_name" label="运营点" min-width="150" />
            <el-table-column prop="total_players" label="总玩家数" width="120" align="center" sortable />
            <el-table-column prop="total_cost" label="总费用" width="150" sortable>
              <template #default="{ row }">
                <span class="total-cost">¥{{ row.total_cost }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!siteLoading && siteStatistics.length === 0" class="empty-state">
            <el-empty description="暂无统计数据" />
          </div>
        </el-tab-pane>

        <!-- 按应用统计 -->
        <el-tab-pane label="按应用统计" name="application">
          <el-table
            v-loading="appLoading"
            :data="appStatistics"
            v-copyable
            stripe
            style="width: 100%"
            :default-sort="{ prop: 'total_cost', order: 'descending' }"
          >
            <el-table-column prop="app_name" label="应用名称" min-width="150" />
            <el-table-column prop="total_players" label="总玩家数" width="120" align="center" sortable />
            <el-table-column prop="total_cost" label="总费用" width="150" sortable>
              <template #default="{ row }">
                <span class="total-cost">¥{{ row.total_cost }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!appLoading && appStatistics.length === 0" class="empty-state">
            <el-empty description="暂无统计数据" />
          </div>
        </el-tab-pane>

        <!-- 消费趋势 -->
        <el-tab-pane label="消费趋势" name="trend">
          <div class="trend-controls">
            <el-radio-group v-model="dimension" @change="loadTrendData">
              <el-radio-button value="day">按天</el-radio-button>
              <el-radio-button value="week">按周</el-radio-button>
              <el-radio-button value="month">按月</el-radio-button>
            </el-radio-group>
          </div>

          <div v-loading="trendLoading" class="trend-summary">
            <el-descriptions :column="2" border class="copyable-descriptions">
              <el-descriptions-item label="总玩家数">
                <span class="copyable-value" @click="handleCopyValue(trendSummary.total_players)">
                  {{ trendSummary.total_players }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="总费用">
                <span class="copyable-value total-cost" @click="handleCopyValue(`¥${trendSummary.total_cost}`)">
                  ¥{{ trendSummary.total_cost }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <el-table
            v-loading="trendLoading"
            :data="trendData"
            v-copyable
            stripe
            style="width: 100%; margin-top: 20px"
          >
            <el-table-column prop="date" label="日期" width="180" />
            <el-table-column prop="total_players" label="玩家数" width="120" align="center" />
            <el-table-column prop="total_cost" label="费用" width="150">
              <template #default="{ row }">
                <span class="total-cost">¥{{ row.total_cost }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!trendLoading && trendData.length === 0" class="empty-state">
            <el-empty description="暂无统计数据" />
          </div>
        </el-tab-pane>

        <!-- 玩家分布 -->
        <el-tab-pane label="玩家分布" name="distribution">
          <div v-loading="distributionLoading" class="distribution-summary">
            <el-alert
              :title="`最常见的玩家数量: ${distributionInfo.most_common_player_count} 人`"
              type="info"
              :closable="false"
            />
          </div>

          <el-table
            v-loading="distributionLoading"
            :data="distributionData"
            v-copyable
            stripe
            style="width: 100%; margin-top: 20px"
            :default-sort="{ prop: 'session_count', order: 'descending' }"
          >
            <el-table-column prop="player_count" label="玩家数" width="120" align="center" />
            <el-table-column prop="session_count" label="场次数量" width="120" align="center" sortable />
            <el-table-column prop="percentage" label="占比" width="120">
              <template #default="{ row }">
                {{ row.percentage.toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="total_cost" label="总费用" width="150">
              <template #default="{ row }">
                <span class="total-cost">¥{{ row.total_cost }}</span>
              </template>
            </el-table-column>
            <el-table-column label="进度条" min-width="200">
              <template #default="{ row }">
                <el-progress :percentage="row.percentage" :stroke-width="16" />
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!distributionLoading && distributionData.length === 0" class="empty-state">
            <el-empty description="暂无统计数据" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { SiteStatistics, ApplicationStatistics, ChartDataPoint, PlayerDistributionItem } from '@/types'
import { copyToClipboard } from '@/utils/clipboard'

const operatorStore = useOperatorStore()

const activeTab = ref('site')
const dateRange = ref<[string, string] | null>(null)
const dimension = ref<'day' | 'week' | 'month'>('day')
const exporting = ref(false)

const siteLoading = ref(false)
const appLoading = ref(false)
const trendLoading = ref(false)
const distributionLoading = ref(false)

const siteStatistics = ref<SiteStatistics[]>([])
const appStatistics = ref<ApplicationStatistics[]>([])
const trendData = ref<ChartDataPoint[]>([])
const distributionData = ref<PlayerDistributionItem[]>([])

const trendSummary = reactive({
  total_sessions: 0,
  total_players: 0,
  total_cost: '0.00',
  avg_players_per_session: 0,
})

const distributionInfo = reactive({
  total_sessions: 0,
  most_common_player_count: 0,
})

// 计算平均费用
const calculateAvgCost = (totalCost: string, totalSessions: number) => {
  if (totalSessions === 0) return '0.00'
  return (parseFloat(totalCost) / totalSessions).toFixed(2)
}

// 获取请求参数
const getParams = () => {
  const params: any = {}
  if (dateRange.value) {
    params.start_time = dateRange.value[0]
    params.end_time = dateRange.value[1]
  }
  return params
}

// 加载按运营点统计
const loadSiteStatistics = async () => {
  siteLoading.value = true
  try {
    const response = await operatorStore.getStatisticsBySite(getParams())
    siteStatistics.value = response.sites || []
  } catch (error) {
    console.error('Load site statistics error:', error)
    ElMessage.error('加载运营点统计失败')
  } finally {
    siteLoading.value = false
  }
}

// 加载按应用统计
const loadAppStatistics = async () => {
  appLoading.value = true
  try {
    const response = await operatorStore.getStatisticsByApplication(getParams())
    appStatistics.value = response.applications || []
  } catch (error) {
    console.error('Load application statistics error:', error)
    ElMessage.error('加载应用统计失败')
  } finally {
    appLoading.value = false
  }
}

// 加载消费趋势
const loadTrendData = async () => {
  trendLoading.value = true
  try {
    const params = {
      ...getParams(),
      dimension: dimension.value,
    }
    const response = await operatorStore.getStatisticsByTime(params)
    trendData.value = response.chart_data || []
    Object.assign(trendSummary, response.summary)
  } catch (error) {
    console.error('Load trend data error:', error)
    ElMessage.error('加载消费趋势失败')
  } finally {
    trendLoading.value = false
  }
}

// 加载玩家分布
const loadDistributionData = async () => {
  distributionLoading.value = true
  try {
    const response = await operatorStore.getPlayerDistribution(getParams())
    distributionData.value = response.distribution || []
    distributionInfo.total_sessions = response.total_sessions
    distributionInfo.most_common_player_count = response.most_common_player_count
  } catch (error) {
    console.error('Load distribution data error:', error)
    ElMessage.error('加载玩家分布失败')
  } finally {
    distributionLoading.value = false
  }
}

// Tab切换
const handleTabChange = (tabName: string) => {
  switch (tabName) {
    case 'site':
      if (siteStatistics.value.length === 0) loadSiteStatistics()
      break
    case 'application':
      if (appStatistics.value.length === 0) loadAppStatistics()
      break
    case 'trend':
      if (trendData.value.length === 0) loadTrendData()
      break
    case 'distribution':
      if (distributionData.value.length === 0) loadDistributionData()
      break
  }
}

// 时间范围变化
const handleDateChange = () => {
  // 重新加载当前Tab的数据
  switch (activeTab.value) {
    case 'site':
      loadSiteStatistics()
      break
    case 'application':
      loadAppStatistics()
      break
    case 'trend':
      loadTrendData()
      break
    case 'distribution':
      loadDistributionData()
      break
  }
}

// 复制值到剪贴板
const handleCopyValue = async (value: string | number) => {
  const text = String(value)
  const success = await copyToClipboard(text)
  if (success) {
    ElMessage.success({
      message: '已复制',
      duration: 1000,
      showClose: false,
    })
  } else {
    ElMessage.error('复制失败')
  }
}

// 导出报表
const handleExport = async () => {
  exporting.value = true
  try {
    const reportTypeMap: Record<string, string> = {
      site: 'site',
      application: 'application',
      trend: 'consumption',
      distribution: 'player_distribution',
    }

    const params: any = {
      format: 'excel',
      report_type: reportTypeMap[activeTab.value],
      ...getParams(),
    }

    if (activeTab.value === 'trend') {
      params.dimension = dimension.value
    }

    // 调用导出API (现在返回blob)
    await operatorStore.exportStatistics(params)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export statistics error:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadSiteStatistics()
})
</script>

<style scoped>
.statistics-page {
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

.total-cost {
  color: #F56C6C;
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
}

.trend-controls {
  margin-bottom: 20px;
}

.trend-summary {
  margin-top: 20px;
}

.distribution-summary {
  margin-bottom: 20px;
}

.copyable-value {
  cursor: copy;
  padding: 2px 4px;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.copyable-value:hover {
  background-color: #e6f7ff;
}
</style>
