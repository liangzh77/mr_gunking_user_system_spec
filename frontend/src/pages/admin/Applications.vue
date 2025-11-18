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
        v-copyable
        v-loading="loading"
        :data="applications"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="app_name" label="应用名称" width="200" />
        <el-table-column prop="description" label="描述" min-width="250" />
        <el-table-column prop="price_per_player" label="单价(元/人)" width="130" align="right">
          <template #default="{ row }">
            ¥{{ Number(row.price_per_player || 0).toFixed(2) }}
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
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click.stop="handleEdit(row)">
              编辑
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

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editVisible"
      title="编辑应用"
      width="600px"
      @close="handleEditDialogClose"
    >
      <el-form
        ref="editFormRef"
        :model="editFormData"
        :rules="editFormRules"
        label-width="120px"
      >
        <el-form-item label="应用名称" prop="app_name">
          <el-input
            v-model="editFormData.app_name"
            placeholder="请输入应用名称"
            clearable
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="应用描述" prop="description">
          <el-input
            v-model="editFormData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入应用描述（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="单价" prop="price_per_player">
          <el-input-number
            v-model="editFormData.price_per_player"
            :min="0.01"
            :max="999.99"
            :precision="2"
            :step="0.1"
            controls-position="right"
            style="width: 100%"
          />
          <div class="form-tip">每位玩家的单价（元/人）</div>
        </el-form-item>

        <el-form-item label="最小玩家数" prop="min_players">
          <el-input-number
            v-model="editFormData.min_players"
            :min="1"
            :max="100"
            controls-position="right"
            style="width: 100%"
            @change="handleMinPlayersChange"
          />
        </el-form-item>

        <el-form-item label="最大玩家数" prop="max_players">
          <el-input-number
            v-model="editFormData.max_players"
            :min="1"
            :max="100"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="协议名" prop="launch_exe_path">
          <el-input
            v-model="editFormData.launch_exe_path"
            placeholder="例如: notepad (可选)"
            clearable
            maxlength="100"
          />
          <div class="form-tip">自定义协议名称，头显Server安装时会自动注册 mrgun-{协议名}:// 协议</div>
        </el-form-item>

        <el-form-item label="状态" prop="is_active">
          <el-switch
            v-model="editFormData.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEditSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

const router = useRouter()

interface Application {
  id: string
  app_code: string
  app_name: string
  description: string
  price_per_player: number
  min_players: number
  max_players: number
  is_active: boolean
  launch_exe_path?: string
  created_at: string
  updated_at: string
}

const loading = ref(false)
const applications = ref<Application[]>([])
const searchKeyword = ref('')

// 编辑相关
const editVisible = ref(false)
const editFormRef = ref<FormInstance>()
const submitting = ref(false)
const editFormData = reactive({
  id: '',
  app_code: '',
  app_name: '',
  description: '',
  price_per_player: 0,
  min_players: 1,
  max_players: 1,
  is_active: true,
  launch_exe_path: '',
})

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

    const response = await http.get('/admins/applications', { params })
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

// 玩家数量范围验证
const validatePlayerRange = (_rule: any, value: number, callback: any) => {
  if (value < 1) {
    callback(new Error('最大玩家数不能小于1'))
  } else if (value < editFormData.min_players) {
    callback(new Error('最大玩家数不能小于最小玩家数'))
  } else {
    callback()
  }
}

// 表单验证规则
const editFormRules: FormRules = {
  app_name: [
    { required: true, message: '请输入应用名称', trigger: 'blur' },
    { min: 2, max: 64, message: '应用名称长度在2-64个字符', trigger: 'blur' },
  ],
  description: [
    { max: 500, message: '描述长度不能超过500个字符', trigger: 'blur' },
  ],
  price_per_player: [
    { required: true, message: '请输入单价', trigger: 'blur' },
    { type: 'number', min: 0.01, max: 999.99, message: '单价范围在0.01-999.99元', trigger: 'blur' },
  ],
  min_players: [
    { required: true, message: '请输入最小玩家数', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '最小玩家数范围在1-100', trigger: 'blur' },
  ],
  max_players: [
    { required: true, message: '请输入最大玩家数', trigger: 'blur' },
    { type: 'number', validator: validatePlayerRange, trigger: 'blur' },
  ],
}

// 最小玩家数变化时，确保最大玩家数不小于最小玩家数
const handleMinPlayersChange = (value: number) => {
  if (editFormData.max_players < value) {
    editFormData.max_players = value
  }
}

// 打开编辑对话框
const handleEdit = (row: Application) => {
  editFormData.id = row.id
  editFormData.app_code = row.app_code
  editFormData.app_name = row.app_name
  editFormData.description = row.description || ''
  editFormData.price_per_player = Number(row.price_per_player)
  editFormData.min_players = row.min_players
  editFormData.max_players = row.max_players
  editFormData.is_active = row.is_active
  editFormData.launch_exe_path = row.launch_exe_path || ''
  editVisible.value = true
}

// 提交编辑
const handleEditSubmit = async () => {
  if (!editFormRef.value) return

  await editFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      submitting.value = true

      // 更新基本信息（包括玩家数范围和状态）
      await http.put(`/admins/applications/${editFormData.id}`, {
        app_name: editFormData.app_name,
        description: editFormData.description || undefined,
        min_players: editFormData.min_players,
        max_players: editFormData.max_players,
        is_active: editFormData.is_active,
        launch_exe_path: editFormData.launch_exe_path || undefined,
      })

      // 如果价格变化了，单独更新价格
      const originalApp = applications.value.find(app => app.id === editFormData.id)
      if (originalApp && Number(originalApp.price_per_player) !== editFormData.price_per_player) {
        await http.put(`/admins/applications/${editFormData.id}/price`, {
          new_price: editFormData.price_per_player,
        })
      }

      ElMessage.success('应用更新成功')
      editVisible.value = false
      await fetchApplications()
    } catch (error: any) {
      console.error('Update application failed:', error)
      // 错误已在http拦截器中处理
    } finally {
      submitting.value = false
    }
  })
}

// 编辑对话框关闭时重置表单
const handleEditDialogClose = () => {
  editFormRef.value?.resetFields()
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

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}
</style>
