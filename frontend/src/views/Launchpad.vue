<template>
  <div class="space-y-8 animate-fade-in">
    <!-- ── Hero ── -->
    <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-blue-500 to-cyan-400 p-8 sm:p-12 text-white">
      <div class="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/5"></div>
      <div class="absolute -bottom-10 -left-10 w-40 h-40 rounded-full bg-white/5"></div>

      <div class="relative space-y-5 max-w-2xl">
        <div class="space-y-2">
          <h1 class="text-3xl sm:text-4xl font-bold tracking-tight">今天想学什么？</h1>
          <p class="text-white/70">输入你想学的课程，AI 为你定制完整教学方案</p>
        </div>

        <!-- 输入区 -->
        <div class="flex gap-3">
          <div class="relative flex-1">
            <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
            <input v-model="query" class="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 text-white placeholder-white/50 text-base focus:outline-none focus:bg-white/25 focus:border-white/40 transition-all"
              placeholder="例如：微积分、Python、英语语法..."
              @input="onQueryInput" @keydown.enter="handleCreate" />
          </div>
          <button class="px-8 py-3.5 rounded-2xl bg-white text-indigo-600 font-semibold text-base hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
            :disabled="!query.trim() || isCreating" @click="handleCreate">
            <LoaderCircle v-if="isCreating" class="w-5 h-5 animate-spin mx-auto" />
            <span v-else>创建课程 →</span>
          </button>
        </div>

        <!-- 规整结果 -->
        <div v-if="normalized?.name" class="bg-white/10 backdrop-blur-sm rounded-2xl p-4 space-y-3 animate-slide-up">
          <div class="flex items-center gap-3">
            <span class="text-sm text-white/60">课程名称</span>
            <input v-model="normalized.name"
              class="flex-1 bg-transparent border-b border-white/30 text-white font-medium text-base focus:outline-none focus:border-white/60 pb-0.5"
              @click.stop />
          </div>

          <!-- 难度模式选择 -->
          <div class="space-y-2">
            <span class="text-sm text-white/60">难度模式</span>
            <div class="grid grid-cols-3 gap-2">
              <button v-for="mode in difficultyModes" :key="mode.levels.length"
                :class="['p-3 rounded-xl text-left border transition-all',
                  selectedMode.levels.join() === mode.levels.join()
                    ? 'bg-white border-white text-indigo-700'
                    : 'bg-white/10 border-white/20 text-white/80 hover:bg-white/20']"
                @click="selectedMode = mode">
                <div class="text-lg mb-1">{{ mode.icon }}</div>
                <div class="text-sm font-semibold">{{ mode.label }}</div>
                <div class="text-xs mt-0.5 opacity-70">{{ mode.desc }}</div>
              </button>
            </div>
          </div>
        </div>

        <!-- 热门 -->
        <div class="flex flex-wrap gap-2">
          <span class="text-white/50 text-sm">热门：</span>
          <button v-for="s in hotSubjects" :key="s"
            class="px-3 py-1 rounded-full bg-white/10 text-white/80 hover:bg-white/20 text-sm transition-all"
            @click="query = s; onQueryInput()">{{ s }}</button>
        </div>
      </div>
    </div>

    <!-- ── 活跃课程 ── -->
    <div v-if="sessions.length > 0" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold">📖 继续学习</h2>
        <span class="text-sm text-[var(--color-text-secondary)]">{{ sessions.length }} 门课程</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="s in sessions" :key="s.session_id"
          class="card p-5 cursor-pointer group relative overflow-hidden" @click="router.push(`/course/${s.session_id}`)">
          <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[var(--color-primary)] to-indigo-500"></div>
          <div class="flex items-start justify-between mb-4 pt-1">
            <h3 class="font-semibold text-base">{{ s.subject }}</h3>
            <span :class="['badge shrink-0', statusBadge(s.status)]">{{ statusLabel(s.status) }}</span>
          </div>
          <div class="flex items-center gap-4">
            <div class="relative w-14 h-14">
              <svg class="w-14 h-14 -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--color-border)" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="progressColor(s.progress_pct)" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="97.4" :stroke-dashoffset="97.4 - (97.4 * s.progress_pct) / 100"
                  class="transition-all duration-700 ease-out" />
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-xs font-bold"
                :style="{ color: progressColor(s.progress_pct) }">{{ s.progress_pct }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="h-2 rounded-full bg-[var(--color-border)] overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700 ease-out"
                  :style="{ width: s.progress_pct + '%', background: `linear-gradient(90deg, ${progressColor(s.progress_pct)}, var(--color-primary))` }" />
              </div>
              <p class="text-xs text-[var(--color-text-secondary)] mt-1.5">{{ formatDate(s.updated_at) }}</p>
            </div>
            <ChevronRight class="w-5 h-5 text-[var(--color-text-secondary)] group-hover:text-[var(--color-primary)] group-hover:translate-x-1 transition-all" />
          </div>
        </div>
      </div>
    </div>

    <!-- ── 空状态 ── -->
    <div v-else-if="!isLoading" class="text-center py-16 space-y-4">
      <div class="text-6xl">✨</div>
      <p class="text-lg font-medium">开始你的第一门课程</p>
      <p class="text-sm text-[var(--color-text-secondary)]">在上方输入你想学习的主题</p>
    </div>

    <!-- ── 骨架 ── -->
    <div v-if="isLoading" class="space-y-4">
      <div class="h-6 w-32 skeleton rounded-lg"></div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-36 skeleton rounded-2xl"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStudentSessions, createSession } from '@/api/learning'
import { LoaderCircle, ChevronRight, Search } from 'lucide-vue-next'

const router = useRouter()
const query = ref('')
const isCreating = ref(false)
const isLoading = ref(false)
const sessions = ref<any[]>([])

const hotSubjects = ['Python 编程', '机器学习', '微积分', '英语语法', '数据结构']

// 课程规整
const normalized = ref<{ name: string; description: string }>({ name: '', description: '' })

// 难度模式
const difficultyModes = [
  { icon: '🏁', label: '单学期', desc: '全部内容一学期', levels: [1] },
  { icon: '📗📘', label: '双学期', desc: '基础 + 进阶', levels: [1, 2] },
  { icon: '📗📘📕', label: '三学期', desc: '入门 + 进阶 + 高级', levels: [1, 2, 3] },
]
const selectedMode = ref(difficultyModes[0] ?? difficultyModes[0])
let normalizeTimer: any = null

async function onQueryInput() {
  clearTimeout(normalizeTimer)
  const text = query.value.trim()
  if (!text) { normalized.value = { name: '', description: '' }; return }

  // 立即用输入内容占位，按钮立即可点
  normalized.value = { name: text, description: '' }

  // 后台调用 API 精炼
  normalizeTimer = setTimeout(async () => {
    try {
      const res = await fetch('/api/course/normalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      })
      const data = await res.json()
      normalized.value = { name: data.name || text, description: data.description || '' }
      const suggested = data.levels?.length || 1
      const match = difficultyModes.reduce((prev, curr) =>
        Math.abs(curr.levels.length - suggested) < Math.abs(prev.levels.length - suggested) ? curr : prev
      )
      selectedMode.value = match
    } catch { /* 保持已有名称 */ }
  }, 500)
}

async function handleCreate() {
  const name = normalized.value?.name || query.value.trim()
  if (!name) return
  isCreating.value = true
  try {
    const res: any = await createSession(name, '学习者', selectedMode.value.levels)
    router.push(`/course/${res.session_id}`)
  } catch { alert('创建失败') }
  finally { isCreating.value = false }
}

// 状态辅助
const statusBadge = (s: string) => ({ assessing: 'badge-warning', learning: 'badge-primary', finished: 'badge-success' }[s] || 'badge-warning')
const statusLabel = (s: string) => ({ assessing: '测评中', learning: '学习中', finished: '已完成' }[s] || s)
const progressColor = (p: number) => p < 30 ? '#ef4444' : p < 70 ? '#f59e0b' : '#10b981'
const formatDate = (d: string) => d ? new Date(d).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : ''

onMounted(async () => {
  isLoading.value = true
  try {
    const res: any = await getStudentSessions()
    sessions.value = res.sessions || []
  } catch {} finally { isLoading.value = false }
})
</script>
