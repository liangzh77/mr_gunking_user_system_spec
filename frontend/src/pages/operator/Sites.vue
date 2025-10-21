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
      <el-table
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
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { Site } from '@/types'
import dayjs from 'dayjs'

const operatorStore = useOperatorStore()

const loading = ref(false)
const sites = ref<Site[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const editingSite = ref<Site | null>(null)

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

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

// 加载运营点列表
const loadSites = async () => {
  loading.value = true
  try {
    sites.value = await operatorStore.getSites()
  } catch (error) {
    console.error('Load sites error:', error)
    ElMessage.error('加载运营点列表失败')
  } finally {
    loading.value = false
  }
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
const handleEdit = (site: Site) => {
  editingSite.value = site
  formData.value = {
    site_name: site.site_name,
    contact_person: site.contact_person,
    contact_phone: site.contact_phone,
    address: site.address,
  }
  dialogVisible.value = true
}

// 删除运营点
const handleDelete = async (site: Site) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除运营点"${site.site_name}"吗？此操作不可撤销。`,
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
</style>
