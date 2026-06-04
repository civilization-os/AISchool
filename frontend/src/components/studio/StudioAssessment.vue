<template>
  <div class="max-w-2xl mx-auto space-y-5 animate-fade-in">
    <!-- Start -->
    <div v-if="!questions && !isLoading" class="text-center py-12 space-y-4">
      <div class="text-5xl">📝</div>
      <h2 class="text-xl font-semibold">入学测评</h2>
      <p class="text-sm text-[var(--color-text-secondary)]">完成诊断测试，AI 将定制个性化学习方案</p>
      <div class="flex gap-3 justify-center">
        <button class="btn btn-primary btn-lg" @click="startAssessment">开始测评</button>
        <button class="btn btn-secondary btn-lg" @click="$emit('skip')">
          <SkipForward class="w-4 h-4" />
          跳过测评
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading && !questions" class="text-center py-12">
      <LoaderCircle class="w-8 h-8 animate-spin mx-auto text-[var(--color-primary)]" />
      <p class="text-sm text-[var(--color-text-secondary)] mt-4">AI 正在生成诊断题目...</p>
    </div>

    <!-- Questions -->
    <div v-if="questions" class="space-y-5">
      <div class="flex items-center gap-3">
        <div class="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
          <div class="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500"
            :style="{ width: answeredRatio + '%' }"></div>
        </div>
        <span class="text-sm font-medium shrink-0">{{ currentIndex + 1 }}/{{ questions.length }}</span>
      </div>

      <div class="card p-6 space-y-5">
        <div class="flex items-start gap-3">
          <span class="w-7 h-7 rounded-full bg-[var(--color-primary)] text-white text-sm font-bold flex items-center justify-center shrink-0">
            {{ currentIndex + 1 }}
          </span>
          <div class="space-y-1 flex-1">
            <span class="text-xs text-[var(--color-text-secondary)] font-mono">{{ currentQuestion.domain }}</span>
            <p class="text-base font-medium">{{ currentQuestion.question }}</p>
          </div>
        </div>

        <div v-if="currentQuestion.type === 'choice'" class="space-y-2 pl-10">
          <button
            v-for="opt in currentQuestion.options" :key="opt"
            :class="['w-full text-left p-3 rounded-xl border text-sm transition-all',
              answers[currentIndex] === opt
                ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary)] font-medium'
                : 'border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-bg)]']"
            @click="selectAnswer(opt)"
          >{{ opt }}</button>
        </div>

        <textarea v-else
          v-model="openAnswer"
          class="input min-h-[100px] resize-y text-sm"
          placeholder="输入你的答案..."
          @input="saveOpenAnswer"
        />
      </div>

      <div class="flex items-center justify-between">
        <button class="btn btn-secondary btn-sm" :disabled="currentIndex === 0" @click="prev">← 上一题</button>
        <div class="flex gap-1.5">
          <button v-for="(_, i) in questions" :key="i"
            :class="['w-7 h-7 rounded-full text-xs font-medium transition-all',
              i === currentIndex ? 'bg-[var(--color-primary)] text-white' :
              answers[i] ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' :
              'bg-[var(--color-border)] text-[var(--color-text-secondary)]']"
            @click="currentIndex = i">{{ i + 1 }}</button>
        </div>
        <button v-if="currentIndex < questions.length - 1" class="btn btn-primary btn-sm" @click="next">下一题 →</button>
        <button v-else class="btn btn-primary btn-sm" :disabled="isSubmitting" @click="submit">
          <LoaderCircle v-if="isSubmitting" class="w-3 h-3 animate-spin" />
          <span v-else>提交测评</span>
        </button>
      </div>
    </div>

    <!-- Result -->
    <div v-if="result" class="card p-6 space-y-4 animate-slide-up text-center">
      <div class="text-4xl">🎯</div>
      <h2 class="text-xl font-bold">测评完成！</h2>
      <p class="text-sm text-[var(--color-text-secondary)]">综合得分：<span class="text-xl font-bold text-[var(--color-primary)]">{{ result.overall_score }}</span></p>
      <button class="btn btn-primary btn-lg mt-4" @click="$emit('done')">查看学习大纲 →</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { startAssessment, submitAssessment } from '@/api/learning'
import { LoaderCircle, SkipForward } from 'lucide-vue-next'

const props = defineProps<{ sessionId: number }>()
const emit = defineEmits<{ done: []; skip: [] }>()

const questions = ref<any[] | null>(null)
const answers = ref<string[]>([])
const currentIndex = ref(0)
const isLoading = ref(false)
const isSubmitting = ref(false)
const result = ref<any>(null)
const openAnswer = ref('')

const currentQuestion = computed(() => questions.value?.[currentIndex.value] || {})
const answeredRatio = computed(() => {
  if (!questions.value?.length) return 0
  return ((answers.value.filter(a => a).length) / questions.value.length) * 100
})

async function startAssessment() {
  isLoading.value = true
  try {
    const res: any = await startAssessment(props.sessionId, 2, false)
    questions.value = res.questions || []
    answers.value = new Array(questions.value.length).fill('')
  } catch {} finally { isLoading.value = false }
}

function selectAnswer(opt: string) { answers.value[currentIndex.value] = opt }
function saveOpenAnswer() { answers.value[currentIndex.value] = openAnswer.value }
function next() {
  if (currentIndex.value < (questions.value?.length || 0) - 1) {
    currentIndex.value++
    openAnswer.value = answers.value[currentIndex.value] || ''
  }
}
function prev() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    openAnswer.value = answers.value[currentIndex.value] || ''
  }
}
watch(currentIndex, () => { openAnswer.value = answers.value[currentIndex.value] || '' })

async function submit() {
  isSubmitting.value = true
  try {
    const res: any = await submitAssessment(props.sessionId, answers.value)
    result.value = res
  } catch {} finally { isSubmitting.value = false }
}
</script>
