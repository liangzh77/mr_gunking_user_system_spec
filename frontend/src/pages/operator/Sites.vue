<template>
  <div class="sites-page">
    <!-- 页面标题和操作栏 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><OfficeBuilding /></el-icon>
          <h2>运营点管理</h2>
        </div>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          创建运营点
        </el-button>
      </div>
    </el-card>

    <!-- 运营点列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <!-- 搜索栏 -->
      <div class="filter-container" style="margin-bottom: 16px">
        <el-input
          v-model="searchQuery"
          placeholder="搜索运营点名称、地址..."
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
        :data="sites"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="运营点名称" min-width="150" />
        <el-table-column prop="address" label="地址" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" text @click="handleLaunchApp(row)">
              启动应用
            </el-button>
            <el-button type="primary" size="small" text @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" text @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && sites.length === 0" class="empty-state">
        <el-empty description="暂无运营点">
          <el-button type="primary" @click="handleCreate">创建第一个运营点</el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="运营点名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入运营点名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="地址" prop="address">
          <el-input
            v-model="formData.address"
            placeholder="请输入运营点地址"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入运营点描述（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 启动应用对话框 -->
    <el-dialog
      v-model="launchDialogVisible"
      title="启动应用"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="运营点">
          <el-input :value="currentSite?.name" disabled />
        </el-form-item>

        <el-form-item label="选择应用">
          <el-select
            v-model="selectedAppId"
            placeholder="请选择要启动的应用"
            style="width: 100%"
            :loading="loadingApps"
          >
            <el-option
              v-for="app in availableApps"
              :key="app.id"
              :label="app.app_name"
              :value="app.id"
              :disabled="!app.launch_exe_path"
            >
              <span>{{ app.app_name }}</span>
              <span v-if="!app.launch_exe_path" style="color: #999; font-size: 12px; margin-left: 8px">
                (未配置协议名)
              </span>
            </el-option>
          </el-select>
          <div v-if="selectedApp && selectedApp.launch_exe_path" class="form-tip">
            协议: mrgun-{{ selectedApp.launch_exe_path }}://
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="launchDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="launching"
          :disabled="!selectedAppId"
          @click="handleConfirmLaunch"
        >
          启动
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useOperatorStore } from '@/stores/operator'
import type { OperationSite } from '@/types'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

const operatorStore = useOperatorStore()

const loading = ref(false)
const sites = ref<OperationSite[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const editingSite = ref<OperationSite | null>(null)
const searchQuery = ref('')

const formData = ref({
  name: '',
  address: '',
  description: '',
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入运营点名称', trigger: 'blur' },
    { min: 2, max: 100, message: '名称长度应在 2-100 个字符之间', trigger: 'blur' },
  ],
  address: [
    { required: true, message: '请输入运营点地址', trigger: 'blur' },
    { min: 5, max: 200, message: '地址长度应在 5-200 个字符之间', trigger: 'blur' },
  ],
  description: [
    { max: 500, message: '描述长度不能超过 500 个字符', trigger: 'blur' },
  ],
}

const dialogTitle = computed(() => {
  return editingSite.value ? '编辑运营点' : '创建运营点'
})

// 加载运营点列表
const loadSites = async () => {
  loading.value = true
  try {
    const params: any = {}

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    sites.value = await operatorStore.getSites(params)
  } catch (error) {
    console.error('Load sites error:', error)
    ElMessage.error('加载运营点列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  loadSites()
}

// 打开创建对话框
const handleCreate = () => {
  editingSite.value = null
  formData.value = {
    name: '',
    address: '',
    description: '',
  }
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (site: OperationSite) => {
  editingSite.value = site
  formData.value = {
    name: site.name,
    address: site.address,
    description: site.description || '',
    contact_person: site.contact_person || '',
    contact_phone: site.contact_phone || '',
  }
  dialogVisible.value = true
}

// 删除运营点
const handleDelete = async (site: OperationSite) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除运营点"${site.name}"吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    loading.value = true
    await operatorStore.deleteSite(site.site_id)
    ElMessage.success('运营点删除成功')
    await loadSites()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Delete site error:', error)
      ElMessage.error('删除运营点失败')
    }
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (editingSite.value) {
      // 更新运营点
      await operatorStore.updateSite(editingSite.value.site_id, formData.value)
      ElMessage.success('运营点更新成功')
    } else {
      // 创建运营点
      await operatorStore.createSite(formData.value)
      ElMessage.success('运营点创建成功')
    }

    dialogVisible.value = false
    await loadSites()
  } catch (error) {
    console.error('Submit site error:', error)
    ElMessage.error(editingSite.value ? '更新运营点失败' : '创建运营点失败')
  } finally {
    submitting.value = false
  }
}

// 对话框关闭时重置表单
const handleDialogClose = () => {
  formRef.value?.resetFields()
  editingSite.value = null
}

// ========== 启动应用相关 ==========
interface Application {
  id: string
  app_code: string
  app_name: string
  launch_exe_path?: string
}

const launchDialogVisible = ref(false)
const currentSite = ref<OperationSite | null>(null)
const availableApps = ref<Application[]>([])
const loadingApps = ref(false)
const selectedAppId = ref('')
const launching = ref(false)

const selectedApp = computed(() => {
  return availableApps.value.find(app => app.id === selectedAppId.value)
})

// 打开启动应用对话框
const handleLaunchApp = async (site: OperationSite) => {
  currentSite.value = site
  selectedAppId.value = ''
  launchDialogVisible.value = true

  // 加载授权应用列表
  await loadAuthorizedApps()
}

// 加载已授权的应用列表
const loadAuthorizedApps = async () => {
  loadingApps.value = true
  try {
    const response = await http.get('/operators/me/applications')
    const apps = response.data.data?.applications || []
    // 将app_id映射为id，以便el-select可以正确绑定
    availableApps.value = apps.map((app: any) => ({
      id: app.app_id,
      app_code: app.app_code,
      app_name: app.app_name,
      launch_exe_path: app.launch_exe_path
    }))
  } catch (error) {
    console.error('Load authorized apps error:', error)
    ElMessage.error('加载应用列表失败')
  } finally {
    loadingApps.value = false
  }
}

// 确认启动应用
const handleConfirmLaunch = async () => {
  if (!currentSite.value || !selectedApp.value) return

  launching.value = true
  try {
    // 1. 生成TOKEN
    const tokenResponse = await http.post('/operators/generate-headset-token')
    const token = tokenResponse.data.data.token

    // 2. 构建启动URL
    const protocol = `mrgun-${selectedApp.value.launch_exe_path}`
    const appCode = selectedApp.value.app_code
    const siteId = currentSite.value.site_id

    const launchUrl = `${protocol}://start?token=${encodeURIComponent(token)}&app_code=${encodeURIComponent(appCode)}&site_id=${encodeURIComponent(siteId)}`

    console.log('Launch URL:', launchUrl)

    // 3. 尝试启动应用
    // 创建隐藏的链接并自动点击，触发自定义协议
    const link = document.createElement('a')
    link.href = launchUrl
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()

    // 短暂延迟后移除链接
    setTimeout(() => {
      document.body.removeChild(link)
    }, 100)

    ElMessage.success('应用启动指令已发送')
    launchDialogVisible.value = false
  } catch (error: any) {
    console.error('Launch app error:', error)
    ElMessage.error(error?.response?.data?.detail?.message || '启动应用失败')
  } finally {
    launching.value = false
  }
}

onMounted(() => {
  loadSites()
})
</script>

<style scoped>
.sites-page {
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

.empty-state {
  padding: 40px 0;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
