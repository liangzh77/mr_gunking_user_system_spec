<template>
  <div class="authorizations-page">
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Key /></el-icon>
          <h2>应用授权管理</h2>
        </div>
        <div class="actions-section">
          <el-button
            v-if="selectedOperator && !isEditing"
            type="primary"
            @click="handleEdit"
          >
            <el-icon><Edit /></el-icon>
            编辑授权
          </el-button>
          <template v-if="isEditing">
            <el-button type="success" @click="handleSaveEdit">
              <el-icon><Check /></el-icon>
              保存
            </el-button>
            <el-button @click="handleCancelEdit">
              <el-icon><Close /></el-icon>
              取消
            </el-button>
          </template>
          <el-button @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="main-content" style="margin-top: 20px">
      <el-row :gutter="20">
        <!-- 左侧：运营商列表 -->
        <el-col :span="8">
          <div class="section-title">
            <el-icon><UserFilled /></el-icon>
            <span>运营商列表</span>
          </div>
          <el-input
            v-model="operatorSearch"
            placeholder="搜索运营商名称或用户名"
            clearable
            style="margin: 16px 0"
            @input="handleOperatorSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <div class="operator-list">
            <div
              v-for="operator in filteredOperators"
              :key="operator.id"
              :class="['operator-item', { active: selectedOperator?.id === operator.id }]"
              @click="handleSelectOperator(operator)"
            >
              <div class="operator-info">
                <div class="operator-name">{{ operator.full_name }}</div>
                <div class="operator-username">@{{ operator.username }}</div>
              </div>
              <div class="operator-meta">
                <el-tag :type="getCategoryType(operator.category)" size="small">
                  {{ getCategoryLabel(operator.category) }}
                </el-tag>
                <div class="authorized-count">
                  已授权: {{ getAuthorizedCount(operator.id) }}
                </div>
              </div>
            </div>
            <el-empty
              v-if="filteredOperators.length === 0"
              description="暂无运营商"
              :image-size="80"
            />
          </div>
        </el-col>

        <!-- 右侧：应用列表 -->
        <el-col :span="16">
          <div class="section-title">
            <el-icon><Grid /></el-icon>
            <span>应用列表</span>
            <span v-if="selectedOperator" class="selected-operator-info">
              当前选中: {{ selectedOperator.full_name }}
            </span>
          </div>
          <div v-if="!selectedOperator" class="empty-placeholder">
            <el-empty description="请先选择一个运营商" :image-size="120" />
          </div>
          <div v-else class="application-list">
            <el-input
              v-model="appSearch"
              placeholder="搜索应用名称"
              clearable
              style="margin: 16px 0"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <div class="app-grid">
              <div
                v-for="app in filteredApplications"
                :key="app.id"
                :class="[
                  'app-card',
                  {
                    authorized: isAuthorized(app.id),
                    selected: isEditing && editingAuthorizations.has(app.id)
                  }
                ]"
                @click="handleAppClick(app)"
              >
                <div class="app-header">
                  <div class="app-name">{{ app.name }}</div>
                  <el-icon
                    v-if="isAuthorized(app.id)"
                    :size="20"
                    color="#67c23a"
                    class="authorized-icon"
                  >
                    <CircleCheckFilled />
                  </el-icon>
                </div>
                <div class="app-game">{{ app.game_name }}</div>
                <div class="app-code">{{ app.app_code }}</div>
                <div class="app-price">¥{{ app.price_per_hour }}/小时</div>
                <div v-if="isEditing" class="app-checkbox">
                  <el-checkbox
                    :model-value="editingAuthorizations.has(app.id)"
                    @change="handleAppToggle(app.id, $event)"
                    @click.stop
                  />
                </div>
              </div>
            </div>
            <el-empty
              v-if="filteredApplications.length === 0"
              description="暂无应用"
              :image-size="80"
            />
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Key,
  Edit,
  Check,
  Close,
  Refresh,
  Search,
  UserFilled,
  Grid,
  CircleCheckFilled
} from '@element-plus/icons-vue'
import http from '@/utils/http'

// 类型定义
interface Operator {
  id: string
  username: string
  full_name: string
  email: string
  phone: string
  category: string
  balance: string
}

interface Application {
  id: string
  name: string
  app_code: string
  game_name: string
  price_per_hour: string
}

interface Authorization {
  operator_id: string
  application_id: string
}

// 数据状态
const loading = ref(false)
const operators = ref<Operator[]>([])
const applications = ref<Application[]>([])
const authorizations = ref<Authorization[]>([])
const selectedOperator = ref<Operator | null>(null)
const isEditing = ref(false)
const editingAuthorizations = ref<Set<string>>(new Set())

// 搜索
const operatorSearch = ref('')
const appSearch = ref('')

// 计算属性：过滤后的运营商列表
const filteredOperators = computed(() => {
  if (!operatorSearch.value) return operators.value

  const keyword = operatorSearch.value.toLowerCase()
  return operators.value.filter(
    (op) =>
      op.full_name.toLowerCase().includes(keyword) ||
      op.username.toLowerCase().includes(keyword)
  )
})

// 计算属性：过滤后的应用列表
const filteredApplications = computed(() => {
  if (!appSearch.value) return applications.value

  const keyword = appSearch.value.toLowerCase()
  return applications.value.filter(
    (app) =>
      app.name.toLowerCase().includes(keyword) ||
      app.game_name.toLowerCase().includes(keyword) ||
      app.app_code.toLowerCase().includes(keyword)
  )
})

// 加载运营商列表
const loadOperators = async () => {
  try {
    loading.value = true
    const response = await http.get('/admins/operators', {
      params: { page: 1, page_size: 100 }
    })
    operators.value = response.data.items
  } catch (error: any) {
    console.error('Failed to load operators:', error)
    ElMessage.error(error.response?.data?.detail || '加载运营商列表失败')
  } finally {
    loading.value = false
  }
}

// 加载应用列表
const loadApplications = async () => {
  try {
    const response = await http.get('/admins/applications', {
      params: { page: 1, page_size: 100 }
    })
    applications.value = response.data.items
  } catch (error: any) {
    console.error('Failed to load applications:', error)
    ElMessage.error(error.response?.data?.detail || '加载应用列表失败')
  }
}

// 加载授权关系
const loadAuthorizations = async () => {
  try {
    // 注意：由于没有统一的授权列表接口，我们需要为每个运营商查询授权关系
    // 为了性能考虑，我们暂时不在初始化时加载，而是在选择运营商时按需加载
    authorizations.value = []
  } catch (error: any) {
    console.error('Failed to load authorizations:', error)
    authorizations.value = []
  }
}

// 判断应用是否已授权给当前选中的运营商
const isAuthorized = (appId: string): boolean => {
  if (!selectedOperator.value) return false
  return authorizations.value.some(
    (auth) => auth.operator_id === selectedOperator.value!.id && auth.application_id === appId
  )
}

// 获取运营商已授权的应用数量
const getAuthorizedCount = (operatorId: string): number => {
  return authorizations.value.filter((auth) => auth.operator_id === operatorId).length
}

// 获取客户分类标签
const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    trial: '试用',
    normal: '普通',
    vip: 'VIP'
  }
  return labels[category] || category
}

// 获取客户分类标签类型
const getCategoryType = (category: string): string => {
  const types: Record<string, string> = {
    trial: 'info',
    normal: '',
    vip: 'warning'
  }
  return types[category] || ''
}

// 选择运营商
const handleSelectOperator = (operator: Operator) => {
  selectedOperator.value = operator
  isEditing.value = false
  editingAuthorizations.value.clear()
}

// 运营商搜索
const handleOperatorSearch = () => {
  // 搜索逻辑在 computed 中处理
}

// 进入编辑模式
const handleEdit = () => {
  if (!selectedOperator.value) return

  isEditing.value = true
  // 初始化编辑状态：将当前已授权的应用加入编辑集合
  editingAuthorizations.value = new Set(
    authorizations.value
      .filter((auth) => auth.operator_id === selectedOperator.value!.id)
      .map((auth) => auth.application_id)
  )
}

// 应用点击事件
const handleAppClick = (app: Application) => {
  if (!isEditing.value) return
  handleAppToggle(app.id, !editingAuthorizations.value.has(app.id))
}

// 切换应用授权状态（编辑模式）
const handleAppToggle = (appId: string, checked: boolean) => {
  if (!isEditing.value) return

  if (checked) {
    editingAuthorizations.value.add(appId)
  } else {
    editingAuthorizations.value.delete(appId)
  }
}

// 保存编辑
const handleSaveEdit = async () => {
  if (!selectedOperator.value) return

  try {
    loading.value = true

    // 获取当前已授权的应用ID集合
    const currentAuthorized = new Set(
      authorizations.value
        .filter((auth) => auth.operator_id === selectedOperator.value!.id)
        .map((auth) => auth.application_id)
    )

    // 计算需要新增的授权
    const toAdd = Array.from(editingAuthorizations.value).filter((id) => !currentAuthorized.has(id))

    // 计算需要撤销的授权
    const toRemove = Array.from(currentAuthorized).filter(
      (id) => !editingAuthorizations.value.has(id)
    )

    // 执行新增授权
    for (const appId of toAdd) {
      await http.post(`/admins/operators/${selectedOperator.value.id}/applications`, {
        application_id: appId
      })
    }

    // 执行撤销授权
    for (const appId of toRemove) {
      await http.delete(`/admins/operators/${selectedOperator.value.id}/applications/${appId}`)
    }

    ElMessage.success('授权更新成功')

    // 更新本地授权状态
    // 添加新授权
    for (const appId of toAdd) {
      authorizations.value.push({
        operator_id: selectedOperator.value.id,
        application_id: appId
      })
    }
    // 移除撤销的授权
    authorizations.value = authorizations.value.filter(
      (auth) =>
        !(auth.operator_id === selectedOperator.value!.id && toRemove.includes(auth.application_id))
    )

    // 退出编辑模式
    isEditing.value = false
  } catch (error: any) {
    console.error('Failed to save authorizations:', error)
    ElMessage.error(error.response?.data?.detail || '授权更新失败')
  } finally {
    loading.value = false
  }
}

// 取消编辑
const handleCancelEdit = () => {
  isEditing.value = false
  editingAuthorizations.value.clear()
}

// 刷新
const handleRefresh = async () => {
  await Promise.all([loadOperators(), loadApplications(), loadAuthorizations()])
  ElMessage.success('刷新成功')
}

// 初始化
onMounted(async () => {
  await Promise.all([loadOperators(), loadApplications(), loadAuthorizations()])
})
</script>

<style scoped lang="scss">
.authorizations-page {
  padding: 20px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;

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

  .main-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    .el-row {
      flex: 1;
      overflow: hidden;
    }

    .el-col {
      height: 100%;
      display: flex;
      flex-direction: column;
    }
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    padding-bottom: 12px;
    border-bottom: 2px solid #e4e7ed;

    .selected-operator-info {
      margin-left: auto;
      font-size: 14px;
      font-weight: normal;
      color: #409eff;
    }
  }

  .operator-list {
    flex: 1;
    overflow-y: auto;
    margin-top: 16px;

    .operator-item {
      padding: 16px;
      border: 1px solid #e4e7ed;
      border-radius: 8px;
      margin-bottom: 12px;
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        border-color: #409eff;
        background-color: #f0f9ff;
      }

      &.active {
        border-color: #409eff;
        background-color: #ecf5ff;
        box-shadow: 0 2px 12px rgba(64, 158, 255, 0.3);
      }

      .operator-info {
        margin-bottom: 8px;

        .operator-name {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin-bottom: 4px;
        }

        .operator-username {
          font-size: 12px;
          color: #909399;
        }
      }

      .operator-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;

        .authorized-count {
          font-size: 12px;
          color: #67c23a;
          font-weight: 500;
        }
      }
    }
  }

  .application-list {
    flex: 1;
    overflow-y: auto;
    margin-top: 16px;

    .app-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;

      .app-card {
        position: relative;
        padding: 20px;
        border: 2px solid #e4e7ed;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s;
        background-color: #fff;

        &:hover {
          border-color: #409eff;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        &.authorized {
          border-color: #67c23a;
          background-color: #f0f9ff;

          .app-header .app-name {
            color: #67c23a;
          }
        }

        &.selected {
          border-color: #409eff;
          background-color: #ecf5ff;
          box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
        }

        .app-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;

          .app-name {
            font-size: 16px;
            font-weight: 600;
            color: #303133;
          }

          .authorized-icon {
            flex-shrink: 0;
          }
        }

        .app-game {
          font-size: 14px;
          color: #606266;
          margin-bottom: 4px;
        }

        .app-code {
          font-size: 12px;
          color: #909399;
          font-family: monospace;
          margin-bottom: 8px;
        }

        .app-price {
          font-size: 14px;
          color: #f56c6c;
          font-weight: 600;
        }

        .app-checkbox {
          position: absolute;
          top: 12px;
          right: 12px;
        }
      }
    }
  }

  .empty-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
