<template>
  <div class="flex flex-col h-full max-w-3xl mx-auto w-full animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-[var(--color-border)]">
      <div class="flex items-center gap-3">
        <button class="btn btn-ghost btn-sm p-1" @click="$emit('back')"><ArrowLeft class="w-4 h-4" /></button>
        <div>
          <h3 class="font-semibold text-sm">{{ item?.item_title || '课堂' }}</h3>
          <p class="text-xs text-[var(--color-text-secondary)]">{{ subject }}</p>
        </div>
      </div>
      <button v-if="lessonDeck" class="btn btn-ghost btn-sm p-1.5 hover:text-amber-500" @click="regenLesson" title="重新生成"><RotateCcw class="w-4 h-4" /></button>
    </div>

    <div ref="messagesRef" class="flex-1 overflow-y-auto py-4">
      <!-- ── 备课动画 ── -->
      <div v-if="isLoadingLesson" class="flex flex-col items-center justify-center py-16 animate-fade-in">
        <div class="relative mb-6">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-lg"><GraduationCap class="w-8 h-8 text-white" /></div>
          <div class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-amber-400 flex items-center justify-center text-[10px] font-bold animate-bounce">✏️</div>
        </div>
        <h3 class="text-lg font-bold mb-1">AI 正在备课</h3>
        <p class="text-sm text-[var(--color-text-secondary)] mb-4">准备知识卡片...</p>
        <div class="flex gap-2"><span v-for="i in 3" :key="i" class="w-2.5 h-2.5 rounded-full bg-[var(--color-primary)] animate-bounce" :style="{ animationDelay: (i-1)*0.15+'s' }"></span></div>
      </div>

      <!-- ── 卡片叙事流 ── -->
      <div v-if="lessonDeck" class="space-y-4 animate-fade-in">

        <!-- 学习目标 -->
        <div class="card p-4 space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">🎯 学习目标</p>
          <ul class="space-y-1"><li v-for="(o,i) in lessonDeck.objectives" :key="i" class="text-sm flex items-start gap-2"><span class="w-5 h-5 rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary)] flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">{{ i+1 }}</span>{{ o }}</li></ul>
        </div>

        <!-- ── 主线卡片（必看）── -->
        <div v-for="(card, ci) in displayedCards" :key="'main-'+ci" class="space-y-3">
          <!-- 卡片 -->
          <div class="card p-5 animate-fade-in" :key="'c-'+ci">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-lg">{{ card.icon }}</span>
              <span class="text-sm font-semibold">{{ card.label }}</span>
              <span class="badge badge-primary text-[10px] ml-auto">{{ ci+1 }}/{{ displayedCards.length }}</span>
            </div>
            <div class="prose prose-sm max-w-none mb-4" v-html="renderMd(card.content)"></div>

            <!-- 快问快答 -->
            <div v-if="card.checkpoint" class="border-t border-[var(--color-border)] pt-4 mt-4 space-y-3">
              <p class="text-sm font-medium">🔍 {{ card.checkpoint.question }}</p>
              <div v-if="card.checkpoint.options?.length" class="space-y-1.5">
                <button v-for="(opt, oi) in card.checkpoint.options" :key="oi"
                  :class="['w-full text-left px-3 py-2 rounded-lg text-sm border transition-all',
                    checkAnswers[ci] === oi && checkResults[ci] !== null
                      ? (checkResults[ci] ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-red-400 bg-red-50 text-red-700')
                      : checkAnswers[ci] === oi ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]' : 'border-[var(--color-border)] hover:border-[var(--color-primary)]']"
                  :disabled="checkResults[ci] !== null"
                  @click="doCheck(ci, oi)">{{ opt }}</button>
              </div>
              <div v-if="checkResults[ci] !== null" :class="['text-xs p-2 rounded-lg', checkResults[ci] ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700']">
                {{ checkResults[ci] ? '✅ 正确' : '🤔 再想想' }} — {{ card.checkpoint.explanation }}
              </div>
            </div>

            <!-- 下一张引导 -->
            <div v-if="card.next_hint" class="flex items-center justify-between pt-4 mt-4 border-t border-[var(--color-border)]">
              <p class="text-xs text-[var(--color-text-secondary)]">💡 {{ card.next_hint }}</p>
              <button v-if="ci < displayedCards.length - 1" class="btn btn-primary btn-sm" @click="scrollToCard(ci + 1)">下一张 →</button>
              <button v-if="ci === displayedCards.length - 1 && extras.length > 0" class="btn btn-ghost btn-sm text-xs" @click="showExtras = !showExtras">
                {{ showExtras ? '收起拓展' : '+' + extras.length + ' 张拓展卡片' }}
              </button>
              <button v-if="ci === displayedCards.length - 1 && extras.length === 0" class="btn btn-primary btn-sm" @click="showQuiz = true">📝 开始测验</button>
            </div>
          </div>
        </div>

        <!-- ── 拓展卡片 ── -->
        <div v-if="showExtras && extras.length > 0" class="space-y-3 pt-4 border-t border-[var(--color-border)]">
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">📚 拓展阅读</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div v-for="(card, ei) in extras" :key="'x-'+ei" class="card p-4 cursor-pointer hover:shadow-sm hover:-translate-y-0.5 transition-all" @click="openExtraCard(ei)">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-lg">{{ card.icon }}</span>
                <span class="text-sm font-semibold">{{ card.label }}</span>
              </div>
              <p class="text-xs text-[var(--color-text-secondary)] line-clamp-2">{{ plainText(card.content) }}</p>
            </div>
          </div>
          <button v-if="extrasOpened >= extras.length" class="btn btn-primary btn-md w-full" @click="showQuiz = true">📝 开始测验</button>
        </div>

        <!-- 拓展卡片展开 -->
        <div v-if="extraCardVisible" class="card p-5 animate-fade-in space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2"><span class="text-lg">{{ extraCardVisible.icon }}</span><span class="text-sm font-semibold">{{ extraCardVisible.label }}</span></div>
            <button class="btn btn-ghost btn-sm text-xs" @click="extraCardVisible = null">✕ 关闭</button>
          </div>
          <div class="prose prose-sm max-w-none" v-html="renderMd(extraCardVisible.content)"></div>
        </div>

        <!-- 测验入口 -->
        <div v-if="extras.length === 0 && showExtras" class="flex justify-center pt-2">
          <button class="btn btn-primary btn-lg" @click="showQuiz = true">📝 开始测验</button>
        </div>
      </div>

      <!-- ── 测验 ── -->
      <div v-if="showQuiz" class="mt-6 border border-[var(--color-border)] rounded-2xl overflow-hidden animate-slide-up">
        <div class="flex items-center justify-between px-4 py-3 bg-[var(--color-bg)] border-b">
          <span class="text-sm font-semibold">📝 随堂测验</span>
          <button v-if="quizState === 'ready'" class="btn btn-primary btn-sm" @click="genQuiz">开始出题</button>
        </div>
        <div v-if="quizState === 'loading'" class="p-6 text-center text-sm"><LoaderCircle class="w-5 h-5 animate-spin mx-auto mb-2" />AI 正在出题...</div>
        <div v-if="quizState === 'active'" class="p-4 space-y-4">
          <div v-for="(q,i) in quizQuestions" :key="q.id" class="space-y-2">
            <p class="text-sm font-medium">Q{{ i+1 }}. {{ q.question }}</p>
            <div v-if="q.type === 'choice'" class="space-y-1 pl-2">
              <button v-for="opt in q.options" :key="opt" :class="['w-full text-left px-3 py-2 rounded-lg text-sm border', quizAnswers[i]===opt ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]' : 'border-[var(--color-border)] hover:border-[var(--color-primary)]']" @click="quizAnswers[i]=opt">{{ opt }}</button>
            </div>
            <textarea v-else v-model="quizAnswers[i]" class="input text-sm min-h-[60px]" placeholder="答案..." />
          </div>
          <button class="btn btn-primary btn-md w-full" :disabled="!allQuizAnswered" @click="submitQuizAction"><LoaderCircle v-if="quizSubmitting" class="w-4 h-4 animate-spin" /><span v-else>提交</span></button>
        </div>
        <div v-if="quizState === 'result'" class="p-4 space-y-3">
          <div :class="['p-4 rounded-xl text-sm space-y-2', quizResult.passed ? 'bg-emerald-50' : 'bg-amber-50']">
            <div class="flex items-center gap-2"><span class="text-xl">{{ quizResult.passed ? '🎉' : '💪' }}</span><span class="font-bold">{{ quizResult.score }}分</span><span :class="quizResult.passed ? 'text-emerald-600' : 'text-amber-600'">{{ quizResult.passed ? '通过' : '未通过' }}</span></div>
            <p class="text-xs">{{ quizResult.feedback }}</p>
          </div>
          <div class="flex gap-2">
            <button v-if="!quizResult.passed" class="btn btn-secondary btn-md flex-1" @click="retryLesson"><RotateCcw class="w-4 h-4" />重学</button>
            <button class="btn btn-primary btn-md flex-1" @click="finishLesson"><Check class="w-4 h-4" />{{ quizResult.passed ? '标记完成' : '稍后再说' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部追问 -->
    <div class="pt-3 border-t border-[var(--color-border)]"><div class="flex gap-2"><input v-model="userInput" class="input flex-1 text-sm" placeholder="有疑问？" :disabled="isTyping || !lessonDeck" @keydown.enter="sendMessage" /><button class="btn btn-primary btn-sm px-3" :disabled="!userInput.trim() || isTyping" @click="sendMessage"><SendHorizonal class="w-4 h-4" /></button></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { startLesson, askQuestion, startQuiz, submitQuiz as apiSubmitQuiz } from '@/api/learning'
import { renderMd } from '@/utils/markdown'
import { ArrowLeft, SendHorizonal, LoaderCircle, RotateCcw, Check, GraduationCap, Focus, Layout } from 'lucide-vue-next'

const props = defineProps<{ sessionId: number; item: any; subject: string }>()
const emit = defineEmits<{ back: []; done: [] }>()

const lessonDeck = ref<any>(null)
const isLoadingLesson = ref(true)
const isTyping = ref(false)
const conversationId = ref<number | null>(null)
const attempt = ref(1)
const userInput = ref('')
const messagesRef = ref<HTMLElement | null>(null)

// 卡片分组
const displayedCards = computed(() => (lessonDeck.value?.cards || []).filter((c:any) => c.core))
const extras = computed(() => (lessonDeck.value?.cards || []).filter((c:any) => !c.core))
const showExtras = ref(false)
const extraCardVisible = ref<any>(null)
const extrasOpened = ref(0)

// 快问快答
const checkAnswers = ref<number[]>([])
const checkResults = ref<(boolean|null)[]>([])

function doCheck(ci: number, oi: number) {
  checkAnswers.value[ci] = oi
  const cp = displayedCards.value[ci]?.checkpoint
  checkResults.value[ci] = cp ? oi === cp.correct_index : false
}

function scrollToCard(ci: number) {
  nextTick(() => {
    const el = document.querySelectorAll('[id^="card-"]')[ci]
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function openExtraCard(ei: number) {
  extraCardVisible.value = extras.value[ei]
  extrasOpened.value++
}

function plainText(md: string) { return md.replace(/[#*`$\[\]]/g,'').replace(/\n+/g,' ').slice(0,150) }

async function startLessonAction() {
  isLoadingLesson.value = true
  try {
    const res: any = await startLesson(props.sessionId, props.item?.id, attempt.value > 1)
    lessonDeck.value = res.lesson_plan || null
    conversationId.value = res.conversation_id
    checkAnswers.value = new Array(displayedCards.value.length).fill(-1)
    checkResults.value = new Array(displayedCards.value.length).fill(null)
    showExtras.value = false; extraCardVisible.value = null; extrasOpened.value = 0
  } catch {} finally { isLoadingLesson.value = false }
}

async function regenLesson() {
  isLoadingLesson.value = true
  try {
    const res: any = await startLesson(props.sessionId, props.item?.id, true)
    lessonDeck.value = res.lesson_plan || null
    conversationId.value = res.conversation_id
    checkAnswers.value = new Array(displayedCards.value.length).fill(-1)
    checkResults.value = new Array(displayedCards.value.length).fill(null)
    showExtras.value = false; extraCardVisible.value = null; extrasOpened.value = 0
  } catch {} finally { isLoadingLesson.value = false }
}

async function sendMessage() {
  if (!userInput.value.trim() || isTyping.value || !conversationId.value) return
  const q = userInput.value; userInput.value = ''
  isTyping.value = true
  try { await askQuestion(props.sessionId, conversationId.value, q) } catch {} finally { isTyping.value = false }
}

// 测验
const showQuiz = ref(false)
const quizState = ref<'ready'|'loading'|'active'|'result'>('ready')
const quizQuestions = ref<any[]>([])
const quizAnswers = ref<string[]>([])
const quizSubmitting = ref(false)
const quizResult = ref<any>(null)
const quizId = ref(0)
const allQuizAnswered = computed(() => quizAnswers.value.every(a => a?.trim()))

async function genQuiz() { quizState.value = 'loading'; try { const res:any = await startQuiz(props.sessionId, conversationId.value||0, props.item?.id||0); quizQuestions.value=res.questions||[]; quizAnswers.value=new Array(quizQuestions.value.length).fill(''); quizId.value=res.quiz_id||0; quizState.value='active' } catch { quizState.value='ready' } }
async function submitQuizAction() { quizSubmitting.value=true; try { const res:any = await apiSubmitQuiz(props.sessionId, quizId.value, props.item?.id||0, [...quizAnswers.value]); quizResult.value={ score:res.score??85, passed:res.passed??true, feedback:res.feedback||'批改完成' }; quizState.value='result' } catch { quizResult.value={score:0,passed:false,feedback:'提交失败'}; quizState.value='result' } finally { quizSubmitting.value=false } }
function finishLesson() { quizResult.value?.passed ? emit('done') : emit('back') }
function retryLesson() { attempt.value++; showQuiz.value=false; quizState.value='ready'; quizQuestions.value=[]; quizAnswers.value=[]; quizResult.value=null; startLessonAction() }

onMounted(() => { if (props.item) startLessonAction(); else isLoadingLesson.value = false })
</script>
