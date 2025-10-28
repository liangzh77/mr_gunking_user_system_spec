<template>
  <div class="reports-page">
    <!-- 报表生成 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>生成财务报表</span>
            </div>
          </template>

          <el-form :model="reportForm" label-width="100px">
            <el-form-item label="报表类型">
              <el-select v-model="reportForm.report_type" placeholder="请选择报表类型" style="width: 100%">
                <el-option label="日报" value="daily" />
                <el-option label="周报" value="weekly" />
                <el-option label="月报" value="monthly" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>

            <el-form-item label="报表日期" v-if="reportForm.report_type === 'daily'">
              <el-date-picker
                v-model="reportForm.report_date"
                type="date"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="报表周期" v-if="reportForm.report_type === 'weekly'">
              <el-date-picker
                v-model="reportForm.report_week"
                type="week"
                placeholder="选择周"
                format="YYYY-第WW周"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="报表月份" v-if="reportForm.report_type === 'monthly'">
              <el-date-picker
                v-model="reportForm.report_month"
                type="month"
                placeholder="选择月份"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="开始日期" v-if="reportForm.report_type === 'custom'">
              <el-date-picker
                v-model="reportForm.start_date"
                type="date"
                placeholder="选择开始日期"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="结束日期" v-if="reportForm.report_type === 'custom'">
              <el-date-picker
                v-model="reportForm.end_date"
                type="date"
                placeholder="选择结束日期"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="导出格式">
              <el-radio-group v-model="reportForm.export_format">
                <el-radio label="pdf">PDF</el-radio>
                <el-radio label="excel">Excel</el-radio>
                <el-radio label="csv">CSV</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="generateReport" :loading="generating">
                <el-icon><DocumentAdd /></el-icon>
                生成报表
              </el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快速报表</span>
            </div>
          </template>

          <div class="quick-reports">
            <el-button type="success" @click="quickReport('today')" style="width: 100%">
              <el-icon><Calendar /></el-icon>
              今日财务报表
            </el-button>
            <el-button type="warning" @click="quickReport('this_week')" style="width: 100%">
              <el-icon><Calendar /></el-icon>
              本周财务报表
            </el-button>
            <el-button type="danger" @click="quickReport('this_month')" style="width: 100%">
              <el-icon><Calendar /></el-icon>
              本月财务报表
            </el-button>
            <el-button type="info" @click="quickReport('last_month')" style="width: 100%">
              <el-icon><Calendar /></el-icon>
              上月财务报表
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 历史报表 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>历史报表</span>
              <el-button type="primary" size="small" @click="fetchReports">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <el-table :data="reports" v-loading="loading" stripe>
            <el-table-column prop="report_id" label="报表ID" width="120" />
            <el-table-column prop="report_type" label="报表类型" width="100" align="center">
              <template #default="scope">
                <el-tag :type="getReportTypeColor(scope.row.report_type)">
                  {{ getReportTypeLabel(scope.row.report_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="period" label="报表周期" />
            <el-table-column prop="total_recharge" label="总充值" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_recharge }}
              </template>
            </el-table-column>
            <el-table-column prop="total_consumption" label="总消费" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_consumption }}
              </template>
            </el-table-column>
            <el-table-column prop="total_refund" label="总退款" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_refund }}
              </template>
            </el-table-column>
            <el-table-column prop="net_income" label="净收入" align="right">
              <template #default="scope">
                ¥{{ scope.row.net_income }}
              </template>
            </el-table-column>
            <el-table-column prop="generated_at" label="生成时间" width="160" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button
                  type="primary"
                  size="small"
                  @click="downloadReport(scope.row)"
                >
                  <el-icon><Download /></el-icon>
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination">
            <el-pagination
              v-model:current-page="queryParams.page"
              v-model:page-size="queryParams.page_size"
              :total="total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="fetchReports"
              @size-change="fetchReports"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Calendar, Refresh, Download } from '@element-plus/icons-vue'
import http from '@/utils/http'

// 报表表单
const reportForm = reactive({
  report_type: 'daily',
  report_date: new Date(),
  report_week: new Date(),
  report_month: new Date(),
  start_date: new Date(),
  end_date: new Date(),
  export_format: 'pdf',
})

const generating = ref(false)

// 查询参数
const queryParams = reactive({
  page: 1,
  page_size: 20,
})

// 报表列表
const reports = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

// 生成报表
const generateReport = async () => {
  generating.value = true
  try {
    let params: any = {
      report_type: reportForm.report_type,
      format: reportForm.export_format,  // Backend expects 'format', not 'export_format'
    }

    // 根据不同类型添加不同参数
    if (reportForm.report_type === 'daily') {
      const dateStr = formatDate(reportForm.report_date)
      params.start_date = dateStr
      params.end_date = dateStr
    } else if (reportForm.report_type === 'weekly') {
      // For weekly, calculate start and end of the week
      const selectedDate = new Date(reportForm.report_week)
      const dayOfWeek = selectedDate.getDay()
      const startOfWeek = new Date(selectedDate)
      startOfWeek.setDate(selectedDate.getDate() - dayOfWeek)
      const endOfWeek = new Date(startOfWeek)
      endOfWeek.setDate(startOfWeek.getDate() + 6)
      params.start_date = formatDate(startOfWeek)
      params.end_date = formatDate(endOfWeek)
    } else if (reportForm.report_type === 'monthly') {
      // For monthly, calculate start and end of the month
      const selectedDate = new Date(reportForm.report_month)
      const year = selectedDate.getFullYear()
      const month = selectedDate.getMonth()
      const startOfMonth = new Date(year, month, 1)
      const endOfMonth = new Date(year, month + 1, 0)
      params.start_date = formatDate(startOfMonth)
      params.end_date = formatDate(endOfMonth)
    } else if (reportForm.report_type === 'custom') {
      params.start_date = formatDate(reportForm.start_date)
      params.end_date = formatDate(reportForm.end_date)
    }

    await http.post('/finance/reports/generate', params)
    ElMessage.success('报表生成成功')
    fetchReports()
  } catch (error: any) {
    ElMessage.error('报表生成失败')
  } finally {
    generating.value = false
  }
}

// 快速报表
const quickReport = async (period: string) => {
  try {
    await http.post('/finance/reports/generate', {
      report_type: 'quick',
      period: period,
      export_format: 'pdf',
    })
    ElMessage.success('报表生成成功')
    fetchReports()
  } catch (error: any) {
    ElMessage.error('报表生成失败')
  }
}

// 重置表单
const resetForm = () => {
  reportForm.report_type = 'daily'
  reportForm.report_date = new Date()
  reportForm.export_format = 'pdf'
}

// 获取历史报表
const fetchReports = async () => {
  loading.value = true
  try {
    const response = await http.get('/finance/reports', {
      params: queryParams,
    })
    reports.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    ElMessage.error('获取历史报表失败')
  } finally {
    loading.value = false
  }
}

// 下载报表
const downloadReport = async (report: any) => {
  try {
    const response = await http.get(`/finance/reports/${report.report_id}/export`, {
      responseType: 'blob',
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `财务报表_${report.report_id}.${report.export_format}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('报表下载成功')
  } catch (error: any) {
    ElMessage.error('报表下载失败')
  }
}

// 报表类型标签
const getReportTypeColor = (type: string) => {
  switch (type) {
    case 'daily': return 'success'
    case 'weekly': return 'warning'
    case 'monthly': return 'danger'
    case 'custom': return 'info'
    default: return 'info'
  }
}

const getReportTypeLabel = (type: string) => {
  switch (type) {
    case 'daily': return '日报'
    case 'weekly': return '周报'
    case 'monthly': return '月报'
    case 'custom': return '自定义'
    default: return '未知'
  }
}

// 日期格式化
const formatDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatMonth = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

// 页面加载时获取数据
onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.reports-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-reports {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
