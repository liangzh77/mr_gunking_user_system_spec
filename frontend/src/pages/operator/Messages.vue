<template>
  <div class="messages-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>消息中心</span>
          <el-badge :value="unreadCount" :hidden="unreadCount === 0">
            <el-button @click="markAllRead">全部标记为已读</el-button>
          </el-badge>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="消息类型">
          <el-select
            v-model="typeFilter"
            placeholder="全部类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="系统通知" value="system" />
            <el-option label="价格变更" value="price_change" />
            <el-option label="余额提醒" value="balance_alert" />
            <el-option label="审核结果" value="review_result" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="readFilter"
            placeholder="全部状态"
            clearable
            style="width: 120px"
            @change="handleFilter"
          >
            <el-option label="未读" value="unread" />
            <el-option label="已读" value="read" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 消息列表 -->
      <el-table
        v-loading="loading"
        :data="messages"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column width="60" align="center">
          <template #default="{ row }">
            <el-icon v-if="!row.is_read" :size="12" color="#f56c6c">
              <CircleFilled />
            </el-icon>
          </template>
        </el-table-column>

        <el-table-column prop="title" label="标题" min-width="250">
          <template #default="{ row }">
            <span :class="{ 'unread-title': !row.is_read }">{{ row.title }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)" size="small">
              {{ getTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewDetails(row)">查看</el-button>
            <el-button
              v-if="!row.is_read"
              size="small"
              type="primary"
              @click.stop="markAsRead(row)"
            >
              标记已读
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleFilter"
        @current-change="handleFilter"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailsVisible"
      :title="currentMessage?.title"
      width="600px"
      @close="handleDialogClose"
    >
      <div v-if="currentMessage" class="message-details">
        <div class="message-meta">
          <el-tag :type="getTypeTagType(currentMessage.type)" size="small">
            {{ getTypeLabel(currentMessage.type) }}
          </el-tag>
          <span class="message-time">{{ formatDate(currentMessage.created_at) }}</span>
        </div>

        <div class="message-content">
          {{ currentMessage.content }}
        </div>

        <div v-if="currentMessage.metadata" class="message-metadata">
          <el-descriptions title="相关信息" :column="1" border>
            <el-descriptions-item
              v-for="(value, key) in currentMessage.metadata"
              :key="key"
              :label="key"
            >
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <template #footer>
        <el-button @click="detailsVisible = false">关闭</el-button>
        <el-button
          v-if="currentMessage && !currentMessage.is_read"
          type="primary"
          @click="markAsRead(currentMessage)"
        >
          标记为已读
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleFilled } from '@element-plus/icons-vue'
import http from '@/utils/http'

interface Message {
  message_id: string
  title: string
  content: string
  type: string
  is_read: boolean
  metadata?: Record<string, any>
  created_at: string
}

const loading = ref(false)
const messages = ref<Message[]>([])
const detailsVisible = ref(false)
const currentMessage = ref<Message | null>(null)
const typeFilter = ref('')
const readFilter = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 计算未读数量
const unreadCount = computed(() => {
  return messages.value.filter(m => !m.is_read).length
})

// 获取消息列表
const fetchMessages = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (typeFilter.value) {
      params.type = typeFilter.value
    }

    if (readFilter.value) {
      params.is_read = readFilter.value === 'read'
    }

    const response = await http.get('/operators/me/messages', { params })
    messages.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch messages:', error)
  } finally {
    loading.value = false
  }
}

// 筛选
const handleFilter = () => {
  pagination.page = 1
  fetchMessages()
}

// 行点击
const handleRowClick = (row: Message) => {
  viewDetails(row)
}

// 查看详情
const viewDetails = (row: Message) => {
  currentMessage.value = row
  detailsVisible.value = true

  // 如果未读，自动标记为已读
  if (!row.is_read) {
    markAsRead(row, false)
  }
}

// 标记为已读
const markAsRead = async (message: Message, showMessage = true) => {
  try {
    await http.post(`/operators/me/messages/${message.message_id}/read`)
    message.is_read = true

    if (showMessage) {
      ElMessage.success('已标记为已读')
    }

    // 如果当前显示的是该消息，更新状态
    if (currentMessage.value?.message_id === message.message_id) {
      currentMessage.value.is_read = true
    }
  } catch (error) {
    console.error('Failed to mark as read:', error)
  }
}

// 全部标记为已读
const markAllRead = async () => {
  try {
    await http.post('/operators/me/messages/mark-all-read')
    ElMessage.success('所有消息已标记为已读')
    await fetchMessages()
  } catch (error) {
    console.error('Failed to mark all as read:', error)
  }
}

// 对话框关闭
const handleDialogClose = () => {
  currentMessage.value = null
}

// 获取类型标签颜色
const getTypeTagType = (type: string) => {
  const types: Record<string, any> = {
    system: 'info',
    price_change: 'warning',
    balance_alert: 'danger',
    review_result: 'success',
  }
  return types[type] || 'info'
}

// 获取类型标签文本
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    system: '系统通知',
    price_change: '价格变更',
    balance_alert: '余额提醒',
    review_result: '审核结果',
  }
  return labels[type] || type
}

// 格式化日期
const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchMessages()
})
</script>

<style scoped>
.messages-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.filter-form {
  margin-bottom: 20px;
}

.unread-title {
  font-weight: 600;
  color: #303133;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.message-details {
  padding: 8px 0;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.message-time {
  font-size: 14px;
  color: #909399;
}

.message-content {
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
  margin-bottom: 16px;
}

.message-metadata {
  margin-top: 16px;
}
</style>
