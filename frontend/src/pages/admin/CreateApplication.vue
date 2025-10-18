<template>
  <div class="create-application-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>创建应用</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        style="max-width: 600px"
      >
        <el-form-item label="应用代码" prop="app_code">
          <el-input
            v-model="formData.app_code"
            placeholder="请输入应用代码（英文、数字、下划线）"
            clearable
            maxlength="32"
            show-word-limit
          />
          <div class="form-tip">应用的唯一标识，创建后不可修改</div>
        </el-form-item>

        <el-form-item label="应用名称" prop="app_name">
          <el-input
            v-model="formData.app_name"
            placeholder="请输入应用名称"
            clearable
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="应用描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入应用描述（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="单价" prop="price_per_player">
          <el-input-number
            v-model="formData.price_per_player"
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
            v-model="formData.min_players"
            :min="1"
            :max="100"
            controls-position="right"
            style="width: 100%"
            @change="handleMinPlayersChange"
          />
        </el-form-item>

        <el-form-item label="最大玩家数" prop="max_players">
          <el-input-number
            v-model="formData.max_players"
            :min="1"
            :max="100"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            创建应用
          </el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import http from '@/utils/http'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

interface ApplicationFormData {
  app_code: string
  app_name: string
  description: string
  price_per_player: number
  min_players: number
  max_players: number
}

const formData = reactive<ApplicationFormData>({
  app_code: '',
  app_name: '',
  description: '',
  price_per_player: 1.0,
  min_players: 1,
  max_players: 4,
})

// 应用代码验证规则
const validateAppCode = (_rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入应用代码'))
  } else if (!/^[a-zA-Z0-9_]+$/.test(value)) {
    callback(new Error('应用代码只能包含英文、数字和下划线'))
  } else if (value.length < 3) {
    callback(new Error('应用代码长度不能少于3个字符'))
  } else {
    callback()
  }
}

// 玩家数量范围验证
const validatePlayerRange = (_rule: any, value: number, callback: any) => {
  if (value < 1) {
    callback(new Error('最大玩家数不能小于1'))
  } else if (value < formData.min_players) {
    callback(new Error('最大玩家数不能小于最小玩家数'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  app_code: [
    { required: true, validator: validateAppCode, trigger: 'blur' },
  ],
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
  if (formData.max_players < value) {
    formData.max_players = value
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      loading.value = true

      await http.post('/admin/admins/applications', {
        app_code: formData.app_code,
        app_name: formData.app_name,
        description: formData.description || undefined,
        price_per_player: formData.price_per_player,
        min_players: formData.min_players,
        max_players: formData.max_players,
      })

      ElMessage.success('应用创建成功')

      // 延迟跳转，让用户看到成功消息
      setTimeout(() => {
        router.push('/admin/applications')
      }, 1000)
    } catch (error: any) {
      console.error('Create application failed:', error)
      // 错误已在http拦截器中处理
    } finally {
      loading.value = false
    }
  })
}

// 重置表单
const handleReset = () => {
  formRef.value?.resetFields()
  formData.app_code = ''
  formData.app_name = ''
  formData.description = ''
  formData.price_per_player = 1.0
  formData.min_players = 1
  formData.max_players = 4
}

// 返回应用列表
const goBack = () => {
  router.push('/admin/applications')
}
</script>

<style scoped>
.create-application-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
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
