<template>
  <div class="max-w-3xl mx-auto space-y-6 animate-fade-in">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold tracking-tight">📖 API 文档</h1>
      <p class="text-[var(--color-text-secondary)]">AI School 后端 API 接口说明</p>
    </div>

    <div class="card p-6 space-y-4">
      <p class="text-sm text-[var(--color-text-secondary)]">
        后端 API 基于 FastAPI 构建，完整的 Swagger 文档可通过以下地址访问：
      </p>
      <a :href="apiDocsUrl" target="_blank" class="btn btn-primary btn-md">
        <ExternalLink class="w-4 h-4" />
        打开 API 文档
      </a>
    </div>

    <div class="space-y-4">
      <h3 class="font-semibold">核心端点</h3>
      <div v-for="ep in endpoints" :key="ep.path" class="card p-4 space-y-2">
        <div class="flex items-center gap-2">
          <span :class="['px-2 py-0.5 text-xs font-bold rounded', methodColor(ep.method)]">{{ ep.method }}</span>
          <code class="text-sm font-mono">{{ ep.path }}</code>
        </div>
        <p class="text-sm text-[var(--color-text-secondary)]">{{ ep.desc }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ExternalLink } from 'lucide-vue-next'

const apiDocsUrl = `${import.meta.env.VITE_API_BASE_URL?.replace('/api', '') || 'http://localhost:8000'}/docs`

const endpoints = [
  { method: 'GET', path: '/health', desc: '健康检查' },
  { method: 'POST', path: '/session/create', desc: '创建学习会话' },
  { method: 'GET', path: '/session/{id}', desc: '获取会话详情' },
  { method: 'POST', path: '/assessment/start/{session_id}', desc: '开始入学测评' },
  { method: 'POST', path: '/assessment/submit/{session_id}', desc: '提交测评答案' },
  { method: 'POST', path: '/syllabus/generate/{session_id}', desc: '生成学习大纲' },
  { method: 'POST', path: '/classroom/start/{session_id}', desc: '开始上课' },
  { method: 'POST', path: '/classroom/ask/{session_id}', desc: '课堂提问' },
  { method: 'POST', path: '/classroom/start-quiz/{session_id}', desc: '开始随堂测验' },
  { method: 'POST', path: '/classroom/submit-quiz/{session_id}', desc: '提交测验' },
  { method: 'POST', path: '/exam/generate/{session_id}', desc: '生成期中/期末试卷' },
  { method: 'POST', path: '/exam/submit/{session_id}', desc: '提交考试' },
]

const methodColor = (m: string) => {
  const map: Record<string, string> = {
    GET: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    PUT: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    DELETE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }
  return map[m] || 'bg-gray-100 text-gray-700'
}
</script>
