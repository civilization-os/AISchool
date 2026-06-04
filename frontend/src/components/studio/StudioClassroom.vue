<template>
  <div class="flex flex-col h-full max-w-3xl mx-auto w-full animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-[var(--color-border)]">
      <div class="flex items-center gap-3">
        <button class="btn btn-ghost btn-sm p-1" @click="$emit('back')">
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <h3 class="font-semibold text-sm">{{ item?.item_title || '课堂' }}</h3>
          <p class="text-xs text-[var(--color-text-secondary)]">{{ subject }}</p>
          <span v-if="attempt > 1" class="text-xs text-amber-500">第 {{ attempt }} 次学习</span>
        </div>
      </div>
      <div class="flex items-center gap-1">
        <button v-if="lessonDeck && !focusMode" class="btn btn-ghost btn-sm p-1.5" @click="focusMode = true" title="专注模式">
          <Focus class="w-4 h-4" />
        </button>
        <button v-if="focusMode" class="btn btn-ghost btn-sm p-1.5" @click="focusMode = false" title="浏览全部">
          <Layout class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div ref="messagesRef" class="flex-1 overflow-y-auto py-4">
      <!-- ── 备课动画 ── -->
      <div v-if="isLoadingLesson" class="flex flex-col items-center justify-center py-16 animate-fade-in">
        <div class="relative mb-6">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-lg">
            <GraduationCap class="w-8 h-8 text-white" />
          </div>
          <div class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-amber-400 flex items-center justify-center text-[10px] font-bold animate-bounce">✏️</div>
        </div>
        <h3 class="text-lg font-bold mb-1">AI 正在备课</h3>
        <p class="text-sm text-[var(--color-text-secondary)] mb-4">从多个维度准备知识点...</p>
        <div class="flex gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0s"></span>
          <span class="w-2.5 h-2.5 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0.15s"></span>
          <span class="w-2.5 h-2.5 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0.3s"></span>
        </div>
      </div>

      <!-- ── 专注模式：单卡全屏 ── -->
      <div v-if="lessonDeck && focusMode" class="space-y-4 animate-fade-in">
        <!-- 进度 -->
        <div class="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
          <span class="font-medium text-[var(--color-text)]">{{ currentCard.icon }} {{ currentCard.label }}</span>
          <span class="ml-auto">{{ cardIndex + 1 }} / {{ lessonDeck.cards.length }}</span>
        </div>
        <!-- 卡片内容 -->
        <div class="card p-6 animate-fade-in min-h-[40vh]" :key="cardIndex">
          <div class="prose prose-sm max-w-none" v-html="renderMd(currentCard.content)"></div>
        </div>
        <!-- 导航 -->
        <div class="flex items-center justify-between">
          <button class="btn btn-ghost btn-sm" :disabled="cardIndex === 0" @click="cardIndex--">← 上一张</button>
          <div class="flex gap-1.5">
            <span v-for="(_, i) in lessonDeck.cards" :key="i"
              :class="['w-2 h-2 rounded-full transition-all', i === cardIndex ? 'bg-[var(--color-primary)] w-4' : 'bg-[var(--color-border)]']"></span>
          </div>
          <button v-if="cardIndex < lessonDeck.cards.length - 1" class="btn btn-ghost btn-sm" @click="cardIndex++">下一张 →</button>
          <button v-if="cardIndex === lessonDeck.cards.length - 1" class="btn btn-primary btn-md" @click="showQuiz = true">📝 开始测验</button>
        </div>
      </div>

      <!-- ── 浏览模式：全部平铺 ── -->
      <div v-if="lessonDeck && !focusMode" class="space-y-6 animate-fade-in">
        <!-- 教学目标 -->
        <div class="card p-4 space-y-2">
          <p class="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">🎯 学习目标</p>
          <ul class="space-y-1.5">
            <li v-for="(obj, i) in lessonDeck.objectives" :key="i" class="text-sm flex items-start gap-2">
              <span class="w-5 h-5 rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary)] flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">{{ i + 1 }}</span>
              {{ obj }}
            </li>
          </ul>
        </div>

        <!-- 卡片网格 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div v-for="(card, i) in lessonDeck.cards" :key="i"
            class="card p-4 cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all group"
            @click="cardIndex = i; focusMode = true">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-lg">{{ card.icon }}</span>
              <span class="text-sm font-semibold">{{ card.label || card.title }}</span>
              <span v-if="i === 0" class="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary)] ml-auto">必读</span>
            </div>
            <p class="text-xs text-[var(--color-text-secondary)] line-clamp-3 leading-relaxed">{{ plainText(card.content) }}</p>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="flex justify-center pt-2">
          <button class="btn btn-primary btn-lg" @click="showQuiz = true">📝 开始测验</button>
        </div>
      </div>

      <!-- ── 测验 ── -->
      <div v-if="showQuiz" class="mt-6 border border-[var(--color-border)] rounded-2xl overflow-hidden animate-slide-up">
        <div class="flex items-center justify-between px-4 py-3 bg-[var(--color-bg)] border-b">
          <span class="text-sm font-semibold">📝 随堂测验</span>
          <button v-if="quizState === 'ready'" class="btn btn-primary btn-sm" @click="genQuiz">开始出题</button>
        </div>
        <div v-if="quizState === 'loading'" class="p-6 text-center text-sm text-[var(--color-text-secondary)]">
          <LoaderCircle class="w-5 h-5 animate-spin mx-auto mb-2" />AI 正在出题...
        </div>
        <div v-if="quizState === 'active'" class="p-4 space-y-4">
          <div v-for="(q, i) in quizQuestions" :key="q.id" class="space-y-2">
            <p class="text-sm font-medium">Q{{ i + 1 }}. {{ q.question }}</p>
            <div v-if="q.type === 'choice'" class="space-y-1 pl-2">
              <button v-for="opt in q.options" :key="opt"
                :class="['w-full text-left px-3 py-2 rounded-lg text-sm border', quizAnswers[i] === opt ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]' : 'border-[var(--color-border)] hover:border-[var(--color-primary)]']"
                @click="quizAnswers[i] = opt">{{ opt }}</button>
            </div>
            <textarea v-else v-model="quizAnswers[i]" class="input text-sm min-h-[60px]" placeholder="输入答案..." />
          </div>
          <button class="btn btn-primary btn-md w-full" :disabled="!allQuizAnswered" @click="submitQuizAction">
            <LoaderCircle v-if="quizSubmitting" class="w-4 h-4 animate-spin" /><span v-else>提交答案</span>
          </button>
        </div>
        <div v-if="quizState === 'result'" class="p-4 space-y-3">
          <div :class="['p-4 rounded-xl text-sm space-y-2', quizResult.passed ? 'bg-emerald-50' : 'bg-amber-50']">
            <div class="flex items-center gap-2"><span class="text-xl">{{ quizResult.passed ? '🎉' : '💪' }}</span><span class="font-bold">{{ quizResult.score }} 分</span><span :class="quizResult.passed ? 'text-emerald-600' : 'text-amber-600'">{{ quizResult.passed ? '通过' : '未通过' }}</span></div>
            <p class="text-xs">{{ quizResult.feedback }}</p>
          </div>
          <div class="flex gap-2">
            <button v-if="!quizResult.passed" class="btn btn-secondary btn-md flex-1" @click="retryLesson"><RotateCcw class="w-4 h-4" />重学</button>
            <button class="btn btn-primary btn-md flex-1" @click="finishLesson"><Check class="w-4 h-4" />{{ quizResult.passed ? '标记完成' : '稍后再说' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 底部追问 ── -->
    <div class="pt-3 border-t border-[var(--color-border)]">
      <div class="flex gap-2">
        <input v-model="userInput" class="input flex-1 text-sm" placeholder="有疑问？输入你的问题..." :disabled="isTyping || !lessonDeck" @keydown.enter="sendMessage" />
        <button class="btn btn-primary btn-sm px-3" :disabled="!userInput.trim() || isTyping" @click="sendMessage"><SendHorizonal class="w-4 h-4" /></button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { startLesson, askQuestion, startQuiz, submitQuiz as apiSubmitQuiz } from '@/api/learning'
import { renderMd } from '@/utils/markdown'
import { ArrowLeft, SendHorizonal, LoaderCircle, RotateCcw, Check, GraduationCap, Focus, Layout } from 'lucide-vue-next'

const props = defineProps<{ sessionId: number; item: any; subject: string }>()
const emit = defineEmits<{ back: []; done: [] }>()

// 卡片
const lessonDeck = ref<any>(null)
const cardIndex = ref(0)
const focusMode = ref(false)
const currentCard = computed(() => {
  const cards = lessonDeck.value?.cards
  if (!cards || cardIndex.value >= cards.length) return { content: '' }
  return cards[cardIndex.value]
})

// 教学
const isLoadingLesson = ref(true)
const isTyping = ref(false)
const conversationId = ref<number | null>(null)
const attempt = ref(1)
const userInput = ref('')
const messagesRef = ref<HTMLElement | null>(null)

function plainText(md: string) {
  return md.replace(/[#*`$\[\]]/g, '').replace(/\n+/g, ' ').slice(0, 150)
}

async function startLessonAction() {
  isLoadingLesson.value = true
  try {
    const res: any = await startLesson(props.sessionId, props.item?.id, attempt.value > 1)
    lessonDeck.value = res.lesson_plan || null
    conversationId.value = res.conversation_id
    cardIndex.value = 0
  } catch {} finally { isLoadingLesson.value = false; scrollToBottom() }
}

async function sendMessage() {
  if (!userInput.value.trim() || isTyping.value || !conversationId.value) return
  const q = userInput.value; userInput.value = ''
  isTyping.value = true
  try { await askQuestion(props.sessionId, conversationId.value, q) } catch {}
  finally { isTyping.value = false }
}

// 测验
const showQuiz = ref(false)
const quizState = ref<'ready' | 'loading' | 'active' | 'result'>('ready')
const quizQuestions = ref<any[]>([])
const quizAnswers = ref<string[]>([])
const quizSubmitting = ref(false)
const quizResult = ref<any>(null)
const quizId = ref(0)
const allQuizAnswered = computed(() => quizAnswers.value.every(a => a?.trim()))

async function genQuiz() {
  quizState.value = 'loading'
  try {
    const res: any = await startQuiz(props.sessionId, conversationId.value || 0, props.item?.id || 0)
    quizQuestions.value = res.questions || []
    quizAnswers.value = new Array(quizQuestions.value.length).fill('')
    quizId.value = res.quiz_id || 0
    quizState.value = 'active'
  } catch { quizState.value = 'ready' }
}

async function submitQuizAction() {
  quizSubmitting.value = true
  try {
    const res: any = await apiSubmitQuiz(props.sessionId, quizId.value, props.item?.id || 0, [...quizAnswers.value])
    quizResult.value = { score: res.score ?? 85, passed: res.passed ?? true, feedback: res.feedback || '批改完成' }
    quizState.value = 'result'
  } catch { quizResult.value = { score: 0, passed: false, feedback: '提交失败' }; quizState.value = 'result' }
  finally { quizSubmitting.value = false }
}

function finishLesson() { quizResult.value?.passed ? emit('done') : emit('back') }
function retryLesson() { attempt.value++; showQuiz.value = false; quizState.value = 'ready'; quizQuestions.value = []; quizAnswers.value = []; quizResult.value = null; startLessonAction() }
function scrollToBottom() { nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight }) }

onMounted(() => { if (props.item) startLessonAction(); else isLoadingLesson.value = false })
</script>
