<template>
  <div class="operators-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>运营商管理</span>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.search"
            placeholder="用户名/姓名/邮箱/手机号"
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

        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 150px"
            @change="handleSearch"
          >
            <el-option label="活跃" value="active" />
            <el-option label="不活跃" value="inactive" />
            <el-option label="已锁定" value="locked" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 运营商列表 -->
      <el-table
        v-loading="loading"
        :data="operators"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="balance" label="账户余额" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'negative-balance': row.balance < 0 }">
              ¥{{ row.balance.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_tier" label="客户等级" width="120" align="center">
          <template #header>
            <span>客户等级</span>
            <el-tooltip
              content="根据月消费自动分级：VIP(≥1万)、普通(1千-1万)、试用(<1千)"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-tag :type="getTierType(row.customer_tier)" size="small">
              {{ getTierLabel(row.customer_tier) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_locked" type="danger" size="small">已锁定</el-tag>
            <el-tag v-else-if="row.is_active" type="success" size="small">活跃</el-tag>
            <el-tag v-else type="info" size="small">不活跃</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">
            {{ row.last_login_at ? formatDateTime(row.last_login_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click.stop="handleEdit(row)">
              修改
            </el-button>
            <el-button type="danger" size="small" text @click.stop="handleDelete(row)">
              删除
            </el-button>
            <el-button
              v-if="row.is_locked"
              size="small"
              type="success"
              @click.stop="handleUnlock(row)"
            >
              解锁
            </el-button>
            <el-button
              v-else-if="row.is_active"
              size="small"
              type="warning"
              @click.stop="handleLock(row)"
            >
              锁定
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
      title="修改运营商信息"
      width="600px"
      @close="handleEditDialogClose"
    >
      <el-form
        ref="editFormRef"
        :model="editFormData"
        :rules="editFormRules"
        label-width="120px"
      >
        <el-form-item label="用户名">
          <el-input v-model="editFormData.username" disabled />
          <div class="form-tip">用户名不可修改</div>
        </el-form-item>

        <el-form-item label="姓名" prop="full_name">
          <el-input
            v-model="editFormData.full_name"
            placeholder="请输入姓名或公司名称"
            clearable
            maxlength="128"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="editFormData.email"
            placeholder="请输入邮箱地址"
            clearable
            maxlength="128"
          />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="editFormData.phone"
            placeholder="请输入手机号"
            clearable
            maxlength="32"
          />
        </el-form-item>

        <el-form-item label="客户等级" prop="customer_tier">
          <el-select v-model="editFormData.customer_tier" style="width: 100%">
            <el-option label="试用" value="trial" />
            <el-option label="普通" value="standard" />
            <el-option label="VIP" value="vip" />
          </el-select>
          <div class="form-tip">根据月消费自动分级，也可手动调整</div>
        </el-form-item>

        <el-form-item label="账户状态" prop="is_active">
          <el-switch
            v-model="editFormData.is_active"
            active-text="活跃"
            inactive-text="不活跃"
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
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, QuestionFilled } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

interface Operator {
  id: string
  username: string
  full_name: string
  email?: string
  phone?: string
  balance: number
  customer_tier: string
  is_active: boolean
  is_locked: boolean
  locked_reason?: string
  locked_at?: string
  last_login_at?: string
  last_login_ip?: string
  created_at: string
  updated_at: string
}

const loading = ref(false)
const operators = ref<Operator[]>([])

const searchForm = reactive({
  search: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 编辑相关
const editVisible = ref(false)
const submitting = ref(false)
const editFormRef = ref<FormInstance>()
const editFormData = reactive({
  id: '',
  username: '',
  full_name: '',
  email: '',
  phone: '',
  customer_tier: 'standard',
  is_active: true,
})

// 表单验证规则
const editFormRules: FormRules = {
  full_name: [
    { required: true, message: '请输入姓名或公司名称', trigger: 'blur' },
    { min: 2, max: 128, message: '姓名长度在2-128个字符', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  phone: [
    { min: 11, max: 32, message: '手机号长度在11-32个字符', trigger: 'blur' },
  ],
  customer_tier: [
    { required: true, message: '请选择客户等级', trigger: 'change' },
  ],
}

// 获取运营商列表
const fetchOperators = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (searchForm.search) {
      params.search = searchForm.search
    }

    if (searchForm.status) {
      params.status = searchForm.status
    }

    const response = await http.get('/admins/operators', { params })
    operators.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch operators:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchOperators()
}

// 修改运营商
const handleEdit = (row: Operator) => {
  editFormData.id = row.id
  editFormData.username = row.username
  editFormData.full_name = row.full_name
  editFormData.email = row.email || ''
  editFormData.phone = row.phone || ''
  editFormData.customer_tier = row.customer_tier
  editFormData.is_active = row.is_active
  editVisible.value = true
}

// 删除运营商
const handleDelete = async (row: Operator) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除运营商 "${row.username}" (${row.full_name}) 吗？此操作不可撤销。`,
      '删除运营商',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 调用后端API删除运营商
    await http.delete(`/admins/operators/${row.id}`)
    ElMessage.success('运营商删除成功')

    // 刷新列表
    await fetchOperators()
  } catch (error: any) {
    // 用户取消或删除失败
    if (error !== 'cancel') {
      console.error('Delete operator failed:', error)
    }
  }
}

// 提交编辑
const handleEditSubmit = async () => {
  if (!editFormRef.value) return

  await editFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      submitting.value = true

      await http.put(`/admins/operators/${editFormData.id}`, {
        full_name: editFormData.full_name,
        email: editFormData.email || undefined,
        phone: editFormData.phone || undefined,
        customer_tier: editFormData.customer_tier,
        is_active: editFormData.is_active,
      })

      ElMessage.success('运营商信息更新成功')
      editVisible.value = false

      // 刷新列表
      await fetchOperators()
    } catch (error: any) {
      console.error('Update operator failed:', error)
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

// 锁定账户
const handleLock = async (row: Operator) => {
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入锁定原因', '锁定账户', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '锁定原因不能为空',
    })

    if (!reason) return

    ElMessage.info('锁定账户功能开发中')
    // TODO: 调用后端API锁定账户
  } catch (error) {
    // 用户取消
  }
}

// 解锁账户
const handleUnlock = async (row: Operator) => {
  try {
    await ElMessageBox.confirm(`确定要解锁账户 "${row.username}" 吗?`, '解锁账户', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    ElMessage.info('解锁账户功能开发中')
    // TODO: 调用后端API解锁账户
  } catch (error) {
    // 用户取消
  }
}

// 获取客户等级类型
const getTierType = (tier: string) => {
  const types: Record<string, any> = {
    trial: 'info',
    standard: '',
    vip: 'warning',
  }
  return types[tier] || ''
}

// 获取客户等级标签
const getTierLabel = (tier: string) => {
  const labels: Record<string, string> = {
    trial: '试用',
    standard: '普通',
    vip: 'VIP',
  }
  return labels[tier] || tier
}

onMounted(() => {
  fetchOperators()
})
</script>

<style scoped>
.operators-page {
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

.negative-balance {
  color: #f56c6c;
  font-weight: 600;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
