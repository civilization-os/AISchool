<template>
  <div class="max-w-2xl mx-auto w-full space-y-5 animate-fade-in">
    <!-- Start -->
    <div v-if="!questions && !isLoading" class="text-center py-12 space-y-4">
      <div class="text-5xl">{{ isMidterm ? '📋' : '🏆' }}</div>
      <h2 class="text-xl font-semibold">{{ isMidterm ? '期中考试' : '期末考试' }}</h2>
      <p class="text-sm text-[var(--color-text-secondary)]">检验你的掌握程度</p>
      <button class="btn btn-primary btn-lg" @click="genExam">开始考试</button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="text-center py-12">
      <LoaderCircle class="w-8 h-8 animate-spin mx-auto text-[var(--color-primary)]" />
    </div>

    <!-- Questions -->
    <div v-if="questions" class="space-y-5">
      <div class="flex items-center gap-3">
        <div class="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
          <div class="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500 transition-all"
            :style="{ width: answeredRatio + '%' }"></div>
        </div>
        <span class="text-sm font-medium shrink-0">{{ answeredCount }}/{{ questions.length }}</span>
      </div>

      <div v-for="(q, i) in questions" :key="q.id" class="card p-5 space-y-3">
        <div class="flex items-start gap-2">
          <span class="text-xs font-mono text-[var(--color-text-secondary)] mt-0.5 shrink-0">#{{ i + 1 }}</span>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <span class="text-xs text-[var(--color-text-secondary)] font-mono">{{ q.domain || '' }}</span>
              <span :class="['text-xs px-1.5 py-0.5 rounded', diffClass(q.difficulty)]">{{ diffLabel(q.difficulty) }}</span>
              <span class="text-xs text-[var(--color-text-secondary)]">{{ q.score_weight || 5 }}分</span>
            </div>
            <p class="text-sm font-medium">{{ q.question }}</p>
          </div>
        </div>

        <div v-if="q.type === 'choice'" class="space-y-1.5 pl-6">
          <button v-for="opt in q.options" :key="opt"
            :class="['w-full text-left px-3 py-2 rounded-lg border text-sm transition-all',
              answers[i] === opt ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary)] font-medium' :
              'border-[var(--color-border)] hover:border-[var(--color-primary)]']"
            @click="answers[i] = opt">{{ opt }}</button>
        </div>
        <textarea v-else v-model="answers[i]" class="input min-h-[80px] resize-y text-sm" placeholder="输入你的答案..." />
      </div>

      <button class="btn btn-primary btn-lg w-full" :disabled="isSubmitting" @click="submit">
        <LoaderCircle v-if="isSubmitting" class="w-4 h-4 animate-spin" />
        <span v-else>📤 交卷 ({{ answeredCount }}/{{ questions.length }})</span>
      </button>
    </div>

    <!-- Result -->
    <div v-if="result" class="card p-6 space-y-4 animate-slide-up text-center">
      <span class="text-5xl">{{ result.score >= 80 ? '🎉' : result.score >= 60 ? '👍' : '📚' }}</span>
      <h2 class="text-xl font-bold">{{ result.score >= 80 ? '太棒了！' : result.score >= 60 ? '不错！' : '继续加油！' }}</h2>
      <p class="text-sm">得分：<span class="text-2xl font-bold" :class="result.score >= 80 ? 'text-emerald-500' : result.score >= 60 ? 'text-amber-500' : 'text-red-500'">{{ result.score }}</span></p>
      <button class="btn btn-secondary btn-lg mt-4" @click="$emit('back')">返回大纲</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { generateExam as apiGenerateExam, submitExam as apiSubmitExam } from '@/api/learning'
import { LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{ sessionId: number; examType: string; subject: string }>()
const emit = defineEmits<{ back: [] }>()

const isMidterm = props.examType === 'midterm'
const questions = ref<any[] | null>(null)
const answers = ref<string[]>([])
const isLoading = ref(false)
const isSubmitting = ref(false)
const result = ref<any>(null)
const examId = ref(0)

const answeredCount = computed(() => answers.value.filter(a => a).length)
const answeredRatio = computed(() => {
  if (!questions.value?.length) return 0
  return (answeredCount.value / questions.value.length) * 100
})

async function genExam() {
  isLoading.value = true
  try {
    const res: any = await apiGenerateExam(props.sessionId, props.examType as 'midterm' | 'final')
    questions.value = res.questions || []
    examId.value = res.exam_id
    answers.value = new Array(questions.value.length).fill('')
  } catch {} finally { isLoading.value = false }
}

async function submit() {
  isSubmitting.value = true
  try {
    const res: any = await apiSubmitExam(props.sessionId, examId.value, [...answers.value])
    result.value = res
  } catch {} finally { isSubmitting.value = false }
}

const diffClass = (d: string) => {
  const map: Record<string, string> = {
    easy: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    hard: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }
  return map[d] || 'bg-gray-100'
}
const diffLabel = (d: string) => ({ easy: '易', medium: '中', hard: '难' })[d] || d
</script>
