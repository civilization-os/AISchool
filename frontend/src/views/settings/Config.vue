<template>
  <div class="max-w-2xl mx-auto space-y-6 animate-fade-in">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold tracking-tight">⚙️ 模型配置</h1>
      <p class="text-[var(--color-text-secondary)]">配置 OpenAI 兼容接口（如 DeepSeek, GPT）</p>
    </div>

    <div class="card p-6 space-y-5">
      <div class="space-y-2">
        <label class="text-sm font-medium">Base URL</label>
        <input v-model="form.baseUrl" class="input" placeholder="https://api.deepseek.com/v1" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium">API Key</label>
        <input v-model="form.apiKey" type="password" class="input" placeholder="sk-..." />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium">模型名称</label>
        <input v-model="form.modelName" class="input" placeholder="deepseek-chat" />
      </div>
      <div class="flex gap-3 pt-2">
        <button class="btn btn-primary btn-md" :disabled="isTesting || !form.apiKey" @click="testConnection">
          <LoaderCircle v-if="isTesting" class="w-4 h-4 animate-spin" />
          <span v-else>测试连接</span>
        </button>
        <button class="btn btn-secondary btn-md" @click="saveConfig">保存配置</button>
      </div>

      <div v-if="testResult" :class="['p-3 rounded-xl text-sm', testResult.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400']">
        {{ testResult.msg }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { LoaderCircle } from 'lucide-vue-next'

const form = reactive({
  baseUrl: localStorage.getItem('llm_base_url') || 'https://api.deepseek.com/v1',
  apiKey: localStorage.getItem('llm_api_key') || '',
  modelName: localStorage.getItem('llm_model_name') || 'deepseek-chat',
})

const isTesting = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)

async function testConnection() {
  isTesting.value = true
  testResult.value = null
  try {
    const res = await fetch('/api/health')
    testResult.value = { ok: true, msg: '✅ 后端连接正常' }
  } catch {
    testResult.value = { ok: false, msg: '❌ 连接失败，请检查配置' }
  } finally {
    isTesting.value = false
  }
}

function saveConfig() {
  localStorage.setItem('llm_base_url', form.baseUrl)
  localStorage.setItem('llm_api_key', form.apiKey)
  localStorage.setItem('llm_model_name', form.modelName)
  testResult.value = { ok: true, msg: '✅ 配置已保存到本地' }
}
</script>
