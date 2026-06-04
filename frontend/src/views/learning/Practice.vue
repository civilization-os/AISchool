<template>
  <div class="max-w-3xl mx-auto space-y-6 animate-fade-in">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold tracking-tight">📝 探索练习</h1>
      <p class="text-[var(--color-text-secondary)]">生成各难度级别的练习题</p>
    </div>

    <div class="card p-6 space-y-4">
      <div class="flex gap-3">
        <input v-model="topic" class="input flex-1" placeholder="输入练习主题" @keydown.enter="doPractice" />
        <select v-model="difficulty" class="input w-32">
          <option value="easy">基础</option>
          <option value="medium" selected>中等</option>
          <option value="hard">困难</option>
        </select>
      </div>
      <div class="flex gap-2 items-center">
        <label class="text-sm text-[var(--color-text-secondary)]">题目数量：</label>
        <input v-model.number="count" type="range" min="3" max="10" class="w-32" />
        <span class="text-sm font-medium">{{ count }}</span>
        <button class="btn btn-primary btn-md ml-auto" :disabled="!topic.trim() || isLoading" @click="doPractice">
          <LoaderCircle v-if="isLoading" class="w-4 h-4 animate-spin" />
          <span v-else>生成题目</span>
        </button>
      </div>
    </div>

    <div v-if="content" class="card p-6 prose prose-sm max-w-none" v-html="renderMd(content)"></div>

    <div v-if="isLoading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-24 skeleton"></div>
    </div>

    <div v-if="error" class="card p-4 text-sm text-red-700 bg-red-50 dark:bg-red-900/10">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { generatePractice } from '@/api/learning'
import { renderMd } from '@/utils/markdown'
import { LoaderCircle } from 'lucide-vue-next'

const topic = ref('')
const difficulty = ref('medium')
const count = ref(5)
const content = ref('')
const isLoading = ref(false)
const error = ref('')

async function doPractice() {
  if (!topic.value.trim()) return
  isLoading.value = true
  error.value = ''
  content.value = ''
  try {
    const res: any = await generatePractice(topic.value, difficulty.value, count.value)
    content.value = res.content || res.questions || ''
  } catch (e: any) {
    error.value = e.message || '请求失败'
  } finally {
    isLoading.value = false
  }
}
</script>
