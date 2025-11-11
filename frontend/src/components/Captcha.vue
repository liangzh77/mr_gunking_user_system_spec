<template>
  <div class="captcha-container">
    <el-input
      v-model="captchaInput"
      placeholder="请输入验证码"
      :size="size"
      maxlength="4"
      @input="handleInput"
    >
      <template #prefix>
        <el-icon><Key /></el-icon>
      </template>
    </el-input>
    <div class="captcha-image" @click="refreshCaptcha" :title="'点击刷新验证码'">
      <img v-if="captchaUrl" :src="captchaUrl" alt="验证码" />
      <div v-else class="captcha-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineEmits, defineProps } from 'vue'
import axios from 'axios'

interface Props {
  size?: 'default' | 'large' | 'small'
  apiBaseUrl?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'large',
  apiBaseUrl: '',
})

const emit = defineEmits<{
  (e: 'update:captchaKey', value: string): void
  (e: 'update:captchaCode', value: string): void
}>()

const captchaInput = ref('')
const captchaUrl = ref('')
const captchaKey = ref('')

// 获取验证码
const fetchCaptcha = async () => {
  try {
    captchaUrl.value = ''
    const response = await axios.get(`${props.apiBaseUrl}/api/v1/common/captcha`, {
      responseType: 'json',
    })

    captchaKey.value = response.data.captcha_key
    captchaUrl.value = `data:image/png;base64,${response.data.image_base64}`

    // 通知父组件captcha_key
    emit('update:captchaKey', captchaKey.value)
  } catch (error) {
    console.error('Failed to fetch captcha:', error)
  }
}

// 刷新验证码
const refreshCaptcha = () => {
  captchaInput.value = ''
  emit('update:captchaCode', '')
  fetchCaptcha()
}

// 处理输入
const handleInput = (value: string) => {
  emit('update:captchaCode', value)
}

// 组件挂载时获取验证码
onMounted(() => {
  fetchCaptcha()
})

// 暴露刷新方法给父组件
defineExpose({
  refresh: refreshCaptcha,
})
</script>

<style scoped>
.captcha-container {
  display: flex;
  gap: 10px;
  align-items: center;
}

.captcha-container .el-input {
  flex: 1;
}

.captcha-image {
  width: 120px;
  height: 40px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f7fa;
  transition: border-color 0.3s;
}

.captcha-image:hover {
  border-color: #409eff;
}

.captcha-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.captcha-loading {
  color: #909399;
  font-size: 20px;
}
</style>
