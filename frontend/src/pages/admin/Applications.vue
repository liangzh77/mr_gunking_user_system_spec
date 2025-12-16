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
        <el-table-column prop="app_name" label="应用名称" width="180" />
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="最新版本" width="150">
          <template #default="{ row }">
            <div class="version-cell">
              <span v-if="row.latest_version" class="version-tag">v{{ row.latest_version }}</span>
              <span v-else class="text-muted">暂无</span>
              <el-upload
                class="upload-btn"
                :action="`${apiBaseUrl}/admins/applications/${row.id}/upload-apk`"
                :headers="uploadHeaders"
                :show-file-list="false"
                :before-upload="beforeApkUpload"
                :on-success="(response: any) => handleUploadSuccess(response, row)"
                :on-error="handleUploadError"
                accept=".apk"
              >
                <el-button type="primary" size="small" link>
                  <el-icon><Upload /></el-icon>
                  上传
                </el-button>
              </el-upload>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="模式单价" width="200">
          <template #default="{ row }">
            <div v-if="row.modes && row.modes.length > 0" class="mode-prices">
              <span v-for="(mode, index) in getSortedModes(row.modes)" :key="mode.id" class="price-item">
                ¥{{ formatAmount(Number(mode.price || 0)) }}<template v-if="index < row.modes.length - 1">、</template>
              </span>
            </div>
            <span v-else class="text-muted">暂无</span>
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
      width="900px"
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

        <el-form-item label="游戏模式">
          <div class="modes-section">
            <div class="modes-header">
              <el-button type="primary" size="small" @click="handleAddMode">
                <el-icon><Plus /></el-icon>
                新增模式
              </el-button>
            </div>

            <el-table
              v-loading="modesLoading"
              :data="currentModes"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="mode_name" label="模式名称" width="150" />
              <el-table-column prop="price" label="价格（元）" width="110" align="right">
                <template #default="{ row }">
                  ¥{{ formatAmount(Number(row.price || 0)) }}
                </template>
              </el-table-column>
              <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
              <el-table-column prop="is_active" label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_active" type="success" size="small">启用</el-tag>
                  <el-tag v-else type="info" size="small">禁用</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140">
                <template #default="{ row }">
                  <el-button type="primary" size="small" text @click="handleEditMode(row)">
                    编辑
                  </el-button>
                  <el-popconfirm
                    title="确定删除该模式吗？"
                    @confirm="handleDeleteMode(row)"
                  >
                    <template #reference>
                      <el-button type="danger" size="small" text>
                        删除
                      </el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>

            <el-empty v-if="!modesLoading && currentModes.length === 0" description="暂无游戏模式，请添加" />
          </div>
        </el-form-item>

        <el-form-item label="玩家数">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item prop="min_players" style="margin-bottom: 0">
                <template #label>
                  <span style="font-size: 13px">最小</span>
                </template>
                <el-input-number
                  v-model="editFormData.min_players"
                  :min="1"
                  :max="100"
                  :controls="false"
                  style="width: 100%"
                  @change="handleMinPlayersChange"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="max_players" style="margin-bottom: 0">
                <template #label>
                  <span style="font-size: 13px">最大</span>
                </template>
                <el-input-number
                  v-model="editFormData.max_players"
                  :min="1"
                  :max="100"
                  :controls="false"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
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

    <!-- 模式编辑对话框 -->
    <el-dialog
      v-model="modeDialogVisible"
      :title="modeDialogTitle"
      width="500px"
      @close="handleModeDialogClose"
    >
      <el-form
        ref="modeFormRef"
        :model="modeFormData"
        :rules="modeFormRules"
        label-width="100px"
      >
        <el-form-item label="模式名称" prop="mode_name">
          <el-input
            v-model="modeFormData.mode_name"
            placeholder="例如：5分钟、10分钟"
            clearable
            maxlength="64"
          />
        </el-form-item>

        <el-form-item label="价格" prop="price">
          <el-input-number
            v-model="modeFormData.price"
            :min="0.01"
            :max="9999.99"
            :step="0.01"
            :controls="false"
            :formatter="formatPrice"
            :parser="parsePrice"
            placeholder="请输入价格"
            style="width: 100%"
          />
          <div class="form-tip">该模式的价格（元）</div>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="modeFormData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模式描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="状态" prop="is_active">
          <el-switch
            v-model="modeFormData.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="modeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="modeSubmitting" @click="handleModeSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules, type UploadRawFile } from 'element-plus'
import { formatDateTime, formatAmount} from '@/utils/format'
import http from '@/utils/http'

// API基础地址
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// 上传请求头
const uploadHeaders = computed(() => {
  const token = localStorage.getItem('admin_access_token')
  return {
    Authorization: token ? `Bearer ${token}` : ''
  }
})

const router = useRouter()

// 价格格式化函数：小数部分为零时不显示小数
const formatPrice = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined || value === '') return ''
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return ''

  // 如果是整数或小数部分为零，不显示小数部分
  if (num === Math.floor(num)) {
    return num.toString()
  }
  // 否则显示最多两位小数，去掉尾部的零
  return num.toFixed(2).replace(/\.?0+$/, '')
}

// 价格解析函数：从字符串转换为数字
const parsePrice = (value: string | undefined): number | null => {
  if (!value || value === '') return null as any
  const num = parseFloat(value)
  return isNaN(num) ? null as any : num
}

interface ApplicationMode {
  id: string
  application_id: string
  mode_name: string
  price: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

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
  latest_version?: string
  apk_url?: string
  modes?: ApplicationMode[]
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
  min_players: 1,
  max_players: 1,
  is_active: true,
  launch_exe_path: '',
})

// 模式管理相关
const modesLoading = ref(false)
const currentModes = ref<ApplicationMode[]>([])
const modeDialogVisible = ref(false)
const modeDialogTitle = ref('新增模式')
const modeFormRef = ref<FormInstance>()
const modeSubmitting = ref(false)
const modeFormData = reactive({
  id: '',
  mode_name: '',
  price: null as any,
  description: '',
  is_active: true,
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

// 获取应用模式列表
const fetchModes = async (appId: string) => {
  modesLoading.value = true
  try {
    const response = await http.get(`/admins/applications/${appId}/modes`)
    // 按价格从低到高排序
    currentModes.value = response.data.sort((a: ApplicationMode, b: ApplicationMode) => {
      return Number(a.price) - Number(b.price)
    })
  } catch (error) {
    console.error('Failed to fetch modes:', error)
    currentModes.value = []
  } finally {
    modesLoading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchApplications()
}

// 获取按价格排序的模式列表
const getSortedModes = (modes: ApplicationMode[]) => {
  if (!modes || modes.length === 0) return []
  return [...modes].sort((a, b) => Number(a.price) - Number(b.price))
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
  min_players: [
    { required: true, message: '请输入最小玩家数', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '最小玩家数范围在1-100', trigger: 'blur' },
  ],
  max_players: [
    { required: true, message: '请输入最大玩家数', trigger: 'blur' },
    { type: 'number', validator: validatePlayerRange, trigger: 'blur' },
  ],
}

// 模式表单验证规则
const modeFormRules: FormRules = {
  mode_name: [
    { required: true, message: '请输入模式名称', trigger: 'blur' },
    { min: 1, max: 64, message: '模式名称长度在1-64个字符', trigger: 'blur' },
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', min: 0.01, max: 9999.99, message: '价格范围在0.01-9999.99元', trigger: 'blur' },
  ],
  description: [
    { max: 200, message: '描述长度不能超过200个字符', trigger: 'blur' },
  ],
}

// 最小玩家数变化时，确保最大玩家数不小于最小玩家数
const handleMinPlayersChange = (value: number) => {
  if (editFormData.max_players < value) {
    editFormData.max_players = value
  }
}

// 打开编辑对话框
const handleEdit = async (row: Application) => {
  editFormData.id = row.id
  editFormData.app_code = row.app_code
  editFormData.app_name = row.app_name
  editFormData.description = row.description || ''
  editFormData.min_players = row.min_players
  editFormData.max_players = row.max_players
  editFormData.is_active = row.is_active
  editFormData.launch_exe_path = row.launch_exe_path || ''
  editVisible.value = true

  // 加载模式列表
  await fetchModes(row.id)
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
        description: editFormData.description || null,
        min_players: editFormData.min_players,
        max_players: editFormData.max_players,
        is_active: editFormData.is_active,
        launch_exe_path: editFormData.launch_exe_path || null,
      })

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
  currentModes.value = []
}

// 新增模式
const handleAddMode = () => {
  modeDialogTitle.value = '新增模式'
  modeFormData.id = ''
  modeFormData.mode_name = ''
  modeFormData.price = null as any
  modeFormData.description = ''
  modeFormData.is_active = true
  modeDialogVisible.value = true
}

// 编辑模式
const handleEditMode = (row: ApplicationMode) => {
  modeDialogTitle.value = '编辑模式'
  modeFormData.id = row.id
  modeFormData.mode_name = row.mode_name
  modeFormData.price = Number(row.price)
  modeFormData.description = row.description || ''
  modeFormData.is_active = row.is_active
  modeDialogVisible.value = true
}

// 提交模式
const handleModeSubmit = async () => {
  if (!modeFormRef.value) return

  await modeFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      modeSubmitting.value = true

      const payload = {
        mode_name: modeFormData.mode_name,
        price: modeFormData.price,
        description: modeFormData.description || null,
        is_active: modeFormData.is_active,
      }

      if (modeFormData.id) {
        // 更新模式
        await http.put(`/admins/applications/${editFormData.id}/modes/${modeFormData.id}`, payload)
        ElMessage.success('模式更新成功')
      } else {
        // 创建模式
        await http.post(`/admins/applications/${editFormData.id}/modes`, payload)
        ElMessage.success('模式创建成功')
      }

      modeDialogVisible.value = false
      await fetchModes(editFormData.id)
      await fetchApplications() // 刷新应用列表以更新模式数量
    } catch (error: any) {
      console.error('Mode operation failed:', error)
      // 错误已在http拦截器中处理
    } finally {
      modeSubmitting.value = false
    }
  })
}

// 删除模式
const handleDeleteMode = async (row: ApplicationMode) => {
  try {
    await http.delete(`/admins/applications/${editFormData.id}/modes/${row.id}`)
    ElMessage.success('模式删除成功')
    await fetchModes(editFormData.id)
    await fetchApplications() // 刷新应用列表以更新模式数量
  } catch (error: any) {
    console.error('Delete mode failed:', error)
    // 错误已在http拦截器中处理
  }
}

// 模式对话框关闭时重置表单
const handleModeDialogClose = () => {
  modeFormRef.value?.resetFields()
}

// 创建应用
const createApplication = () => {
  router.push('/admin/applications/create')
}

// APK上传前验证
const beforeApkUpload = (file: UploadRawFile) => {
  const isApk = file.name.toLowerCase().endsWith('.apk')
  if (!isApk) {
    ElMessage.error('只能上传APK文件!')
    return false
  }

  // 验证文件名格式是否包含版本号
  const versionPattern = /[_-]v?(\d+\.\d+(\.\d+)?)(\.apk)?$/i
  if (!versionPattern.test(file.name)) {
    ElMessage.error('文件名格式不正确，请使用如 AppName_1.0.3.apk 的格式')
    return false
  }

  // 限制文件大小为500MB
  const maxSize = 500 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过500MB!')
    return false
  }

  return true
}

// APK上传成功处理
const handleUploadSuccess = (response: any, row: Application) => {
  if (response && response.latest_version) {
    ElMessage.success(`版本 ${response.latest_version} 上传成功`)
    // 更新本地数据
    row.latest_version = response.latest_version
    row.apk_url = response.apk_url
    // 刷新列表
    fetchApplications()
  } else {
    ElMessage.error('上传失败，请重试')
  }
}

// APK上传失败处理
const handleUploadError = (error: Error) => {
  console.error('Upload error:', error)
  ElMessage.error('上传失败，请检查文件名格式是否正确')
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

.modes-section {
  width: 100%;
}

.modes-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 12px;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}

.mode-prices {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.6;
}

.price-item {
  color: #409EFF;
  font-weight: 500;
  white-space: nowrap;
}

.text-muted {
  color: #909399;
  font-size: 13px;
}

.version-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-tag {
  color: #67C23A;
  font-weight: 500;
  font-size: 13px;
}

.upload-btn {
  display: inline-flex;
}

.upload-btn :deep(.el-upload) {
  display: inline-flex;
}
</style>
