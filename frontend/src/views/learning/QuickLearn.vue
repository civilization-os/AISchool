<template>
  <div class="max-w-3xl mx-auto space-y-6 animate-fade-in">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold tracking-tight">⚡ 快速学习</h1>
      <p class="text-[var(--color-text-secondary)]">直接输入知识点，立即获得 AI 教学</p>
    </div>

    <div class="card p-6 space-y-4">
      <div class="flex gap-3">
        <input v-model="topic" class="input flex-1" placeholder="输入你想学习的知识点" @keydown.enter="doLearn" />
        <button class="btn btn-primary btn-lg" :disabled="!topic.trim() || isLoading" @click="doLearn">
          <LoaderCircle v-if="isLoading" class="w-4 h-4 animate-spin" />
          <span v-else>开始教学</span>
        </button>
      </div>

      <div class="flex gap-2 text-sm">
        <input v-model="question" class="input" placeholder="可选：指定要解答的具体问题" />
      </div>
    </div>

    <!-- 内容展示 -->
    <div v-if="content" class="card p-6 prose prose-sm max-w-none">
      <div v-html="renderMd(content)"></div>
    </div>

    <div v-if="isLoading" class="space-y-4">
      <div class="h-4 w-3/4 skeleton"></div>
      <div class="h-4 w-1/2 skeleton"></div>
      <div class="h-4 w-5/6 skeleton"></div>
      <div class="h-4 w-2/3 skeleton"></div>
    </div>

    <div v-if="error" class="card p-4 border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { quickTeach } from '@/api/learning'
import { renderMd } from '@/utils/markdown'
import { LoaderCircle } from 'lucide-vue-next'

const topic = ref('')
const question = ref('')
const content = ref('')
const isLoading = ref(false)
const error = ref('')

async function doLearn() {
  if (!topic.value.trim()) return
  isLoading.value = true
  error.value = ''
  content.value = ''
  try {
    const res: any = await quickTeach(topic.value, question.value || undefined)
    content.value = res.content || ''
  } catch (e: any) {
    error.value = e.message || '请求失败'
  } finally {
    isLoading.value = false
  }
}
</script>
