<template>
  <div class="authorizations-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Key /></el-icon>
          <h2>授权管理</h2>
        </div>
        <div class="actions-section">
          <el-button type="primary" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 搜索筛选 -->
    <el-card class="filter-card" style="margin-top: 20px">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="运营商">
          <el-input
            v-model="filterForm.search"
            placeholder="搜索运营商用户名或名称"
            clearable
            style="width: 250px"
            @change="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 运营商授权列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-loading="loading"
        :data="operators"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="运营商名称" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column label="已授权应用" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="auth in row.authorizations || []"
              :key="auth.id"
              type="success"
              style="margin-right: 5px"
              closable
              @close="handleRevokeAuth(row.id, auth.application_id)"
            >
              {{ auth.application_name }}
            </el-tag>
            <span v-if="!row.authorizations || row.authorizations.length === 0" style="color: #999">
              暂无授权
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleAuthorize(row)">
              <el-icon><Plus /></el-icon>
              授权应用
            </el-button>
            <el-button type="info" size="small" text @click="handleViewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!loading && operators.length === 0" class="empty-state">
        <el-empty description="暂无运营商数据" />
      </div>

      <!-- 分页 -->
      <el-pagination
        v-if="total > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; text-align: right"
      />
    </el-card>

    <!-- 授权对话框 -->
    <el-dialog
      v-model="authorizeDialogVisible"
      title="授权应用"
      width="600px"
      @close="handleAuthorizeDialogClose"
    >
      <el-form
        ref="authorizeFormRef"
        :model="authorizeForm"
        :rules="authorizeRules"
        label-width="100px"
      >
        <el-form-item label="运营商">
          <el-input :value="currentOperator?.full_name" disabled />
        </el-form-item>

        <el-form-item label="选择应用" prop="application_id">
          <el-select
            v-model="authorizeForm.application_id"
            placeholder="请选择要授权的应用"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="app in availableApplications"
              :key="app.id"
              :label="`${app.name} (${app.game_name})`"
              :value="app.id"
            >
              <div style="display: flex; justify-content: space-between;">
                <span>{{ app.name }}</span>
                <span style="color: #999; font-size: 12px">{{ app.game_name }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="过期时间">
          <el-date-picker
            v-model="authorizeForm.expires_at"
            type="datetime"
            placeholder="选择过期时间(可选)"
            style="width: 100%"
            :disabled-date="disabledDate"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="authorizeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="authorizing" @click="handleConfirmAuthorize">
          确认授权
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Key, Refresh, Search, Plus } from '@element-plus/icons-vue'
import http from '@/utils/http'

// 数据定义
const loading = ref(false)
const operators = ref<any[]>([])
const applications = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 筛选表单
const filterForm = reactive({
  search: ''
})

// 授权对话框
const authorizeDialogVisible = ref(false)
const authorizing = ref(false)
const currentOperator = ref<any>(null)
const authorizeFormRef = ref<FormInstance>()
const authorizeForm = reactive({
  application_id: '',
  expires_at: null as Date | null
})

const authorizeRules: FormRules = {
  application_id: [
    { required: true, message: '请选择要授权的应用', trigger: 'change' }
  ]
}

// 计算可用应用(排除已授权的)
const availableApplications = computed(() => {
  if (!currentOperator.value) return applications.value

  const authorizedAppIds = (currentOperator.value.authorizations || []).map(
    (auth: any) => auth.application_id
  )

  return applications.value.filter(app => !authorizedAppIds.includes(app.id))
})

// 禁用过去的日期
const disabledDate = (time: Date) => {
  return time.getTime() < Date.now() - 8.64e7
}

// 加载运营商列表
const loadOperators = async () => {
  try {
    loading.value = true
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }

    if (filterForm.search) {
      params.search = filterForm.search
    }

    const response = await http.get('/admins/operators', { params })

    operators.value = response.data.items
    total.value = response.data.total

    // 为每个运营商加载授权信息
    await loadAuthorizationsForOperators()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载运营商列表失败')
  } finally {
    loading.value = false
  }
}

// 为运营商加载授权信息(通过应用列表推断)
const loadAuthorizationsForOperators = async () => {
  // 注意: 这是一个简化实现
  // 实际应该有专门的API返回每个运营商的授权列表
  // 这里我们暂时不显示已授权应用,在实际使用时需要后端支持
  operators.value.forEach(op => {
    op.authorizations = []
  })
}

// 加载应用列表
const loadApplications = async () => {
  try {
    const response = await http.get('/admins/applications', { params: { page: 1, page_size: 100 } })
    applications.value = response.data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载应用列表失败')
  }
}

// 刷新
const handleRefresh = () => {
  loadOperators()
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadOperators()
}

// 重置
const handleReset = () => {
  filterForm.search = ''
  handleSearch()
}

// 分页
const handlePageChange = (page: number) => {
  currentPage.value = page
  loadOperators()
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadOperators()
}

// 授权应用
const handleAuthorize = (operator: any) => {
  currentOperator.value = operator
  authorizeForm.application_id = ''
  authorizeForm.expires_at = null
  authorizeDialogVisible.value = true
}

// 确认授权
const handleConfirmAuthorize = async () => {
  if (!authorizeFormRef.value) return

  await authorizeFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      authorizing.value = true

      await http.post(`/admins/operators/${currentOperator.value.id}/applications`, {
        application_id: authorizeForm.application_id,
        expires_at: authorizeForm.expires_at?.toISOString()
      })

      ElMessage.success('授权成功')
      authorizeDialogVisible.value = false
      loadOperators() // 刷新列表
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '授权失败')
    } finally {
      authorizing.value = false
    }
  })
}

// 撤销授权
const handleRevokeAuth = async (operatorId: string, appId: string) => {
  try {
    await ElMessageBox.confirm(
      '确定要撤销该应用的授权吗?撤销后运营商将无法继续使用该应用。',
      '确认撤销',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await http.delete(`/admins/operators/${operatorId}/applications/${appId}`)
    ElMessage.success('授权已撤销')
    loadOperators() // 刷新列表
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '撤销授权失败')
    }
  }
}

// 查看详情
const handleViewDetail = (operator: any) => {
  ElMessage.info('查看运营商详情功能待实现')
  // TODO: 跳转到运营商详情页或弹出详情对话框
}

// 关闭授权对话框
const handleAuthorizeDialogClose = () => {
  authorizeFormRef.value?.resetFields()
}

// 初始化
onMounted(() => {
  loadOperators()
  loadApplications()
})
</script>

<style scoped lang="scss">
.authorizations-page {
  padding: 20px;
}

.header-card {
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .title-section {
      display: flex;
      align-items: center;
      gap: 12px;

      h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
      }
    }

    .actions-section {
      display: flex;
      gap: 10px;
    }
  }
}

.filter-card {
  .filter-form {
    margin-bottom: 0;
  }
}

.list-card {
  .empty-state {
    padding: 40px 0;
  }
}
</style>
