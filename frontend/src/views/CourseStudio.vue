<template>
  <div class="flex h-[calc(100vh-8rem)] gap-0 lg:gap-4 animate-fade-in">
    <!-- Mobile Back -->
    <button class="fixed top-4 left-4 z-20 lg:hidden btn btn-ghost btn-sm p-2 bg-[var(--color-surface)] shadow-md rounded-xl" @click="router.push('/')">
      <ArrowLeft class="w-5 h-5" />
    </button>

    <!-- ── Sidebar ── -->
    <Transition name="slide-left">
      <aside v-if="!isMobile || showSidebar"
        :class="['flex flex-col border-r lg:border-r-0 border-[var(--color-border)] bg-[var(--color-surface)]',
          isMobile ? 'fixed inset-y-0 left-0 z-30 w-72 shadow-2xl' : 'w-64 shrink-0 rounded-2xl']">
        <!-- 课程信息 -->
        <div class="p-5 border-b border-[var(--color-border)]">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-md mb-3">
            <BookOpen class="w-5 h-5 text-white" />
          </div>
          <h2 class="font-bold text-base truncate">{{ session?.subject || '加载中...' }}</h2>
          <p class="text-xs text-[var(--color-text-secondary)] mt-0.5">{{ items.length }} 个知识点</p>
        </div>

        <!-- 进度 -->
        <div class="px-5 py-4 border-b border-[var(--color-border)]">
          <div class="flex justify-between text-sm mb-2">
            <span class="text-[var(--color-text-secondary)]">学习进度</span>
            <span class="font-semibold text-[var(--color-primary)]">{{ progressPct }}%</span>
          </div>
          <div class="h-2 rounded-full bg-[var(--color-border)] overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-indigo-500 transition-all duration-700"
              :style="{ width: progressPct + '%' }" />
          </div>
        </div>

        <!-- 章节快跳 -->
        <div class="flex-1 overflow-y-auto p-3 space-y-0.5">
          <p class="text-xs font-medium text-[var(--color-text-secondary)] px-3 pb-2">章节导航</p>
          <div v-for="section in groupedSections" :key="section.section_id"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 transition-colors cursor-pointer"
            @click="scrollToSection(section.section_id)">
            <span class="w-1.5 h-1.5 rounded-full shrink-0"
              :class="sectionDone(section) === section.items.length ? 'bg-emerald-400' : 'bg-[var(--color-border)]'"></span>
            <span class="truncate">{{ section.section_title }}</span>
            <span class="ml-auto text-xs">{{ sectionDone(section) }}/{{ section.items.length }}</span>
          </div>
        </div>

        <!-- 底部 -->
        <div class="p-3 border-t border-[var(--color-border)]">
          <button class="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 transition-all" @click="router.push('/')">
            <ArrowLeft class="w-4 h-4" />
            <span>返回首页</span>
          </button>
        </div>
      </aside>
    </Transition>
    <div v-if="isMobile && showSidebar" class="fixed inset-0 bg-black/30 backdrop-blur-sm z-20" @click="showSidebar = false" />

    <!-- ── Main ── -->
    <main class="flex-1 flex flex-col overflow-hidden min-w-0">
      <!-- Top bar -->
      <div class="flex items-center gap-3 pb-3 border-b border-[var(--color-border)]">
        <button class="lg:hidden btn btn-ghost btn-sm p-2 -ml-2" @click="showSidebar = true">
          <PanelLeftOpen class="w-5 h-5" />
        </button>
        <!-- 面包屑 -->
        <div v-if="currentView === 'classroom'" class="flex items-center gap-2 text-sm min-w-0">
          <button class="text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors shrink-0" @click="currentView = 'syllabus'">
            {{ session?.subject }}
          </button>
          <ChevronRight class="w-3 h-3 text-[var(--color-text-secondary)] shrink-0" />
          <span class="font-medium truncate">{{ currentItem?.item_title || '课堂' }}</span>
        </div>
        <h2 v-else class="text-lg font-semibold truncate">{{ session?.subject || '课程' }}</h2>
        <div class="flex-1"></div>
        <!-- 重新生成按钮 -->
        <button v-if="currentView === 'syllabus' && items.length > 0"
          class="btn btn-ghost btn-sm p-1.5 text-[var(--color-text-secondary)] hover:text-red-500 transition-colors" title="重新生成大纲" @click="showRegenConfirm = true">
          <RotateCcw class="w-4 h-4" />
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto py-4">

        <!-- ── 测评 View ── -->
        <StudioAssessment v-if="currentView === 'assessment'" :session-id="sessionId"
          @done="onAssessmentDone" @skip="onAssessmentSkip" />

        <!-- ── 生成动画 ── -->
        <div v-else-if="currentView === 'generating'" class="flex flex-col items-center justify-center py-24 animate-fade-in">
          <div class="relative mb-8">
            <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-xl shadow-[var(--color-primary)]/20">
              <Sparkles class="w-10 h-10 text-white" />
            </div>
            <div class="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-amber-400 flex items-center justify-center text-xs font-bold animate-bounce">⚡</div>
          </div>
          <h3 class="text-xl font-bold mb-2">AI 正在生成课程大纲</h3>
          <p class="text-[var(--color-text-secondary)] text-sm mb-6">规划知识结构...</p>
          <div class="flex gap-2">
            <span class="w-3 h-3 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0s"></span>
            <span class="w-3 h-3 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0.15s"></span>
            <span class="w-3 h-3 rounded-full bg-[var(--color-primary)] animate-bounce" style="animation-delay:0.3s"></span>
          </div>
        </div>

        <!-- ── 课程大纲（主视图） ── -->
        <div v-if="currentView === 'syllabus'" class="max-w-3xl mx-auto space-y-4">
          <!-- 课程描述 + 等级 Tab -->
          <div class="card p-5 space-y-4">
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-md shrink-0">
                <BookOpen class="w-5 h-5 text-white" />
              </div>
              <div class="flex-1 min-w-0">
                <h1 class="text-xl font-bold">{{ session?.subject }}</h1>
                <p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
                  {{ doneCount }}/{{ items.length }} 知识点 · {{ progressPct }}% 完成
                </p>
              </div>
            </div>

            <!-- 等级 Tab（多学期时显示） -->
            <div v-if="courseLevels.length > 1" class="flex gap-2 border-t border-[var(--color-border)] pt-3">
              <button v-for="lv in courseLevels" :key="lv"
                :class="['px-4 py-1.5 rounded-lg text-sm font-medium transition-all',
                  activeLevel === lv ? 'bg-[var(--color-primary)] text-white shadow-sm' : 'bg-[var(--color-bg)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]']"
                @click="activeLevel = lv">
                第{{ lv }}学期
              </button>
            </div>
          </div>

          <!-- 章节列表 -->
          <div v-for="(section, si) in groupedSections" :key="section.section_id"
            :id="'section-' + section.section_id"
            class="card overflow-hidden"
            :style="{ animationDelay: si * 0.12 + 's' }"
            :class="[showSections ? 'animate-slide-up opacity-100' : 'opacity-0']">
            <!-- 章节头 -->
            <div class="px-5 py-4 flex items-center gap-3 cursor-pointer select-none hover:bg-[var(--color-bg)] transition-colors"
              @click="toggleSection(section.section_id)">
              <div class="w-8 h-8 rounded-xl bg-[var(--color-primary-soft)] flex items-center justify-center text-sm font-bold text-[var(--color-primary)] shrink-0">{{ section.section_id }}</div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-sm">{{ section.section_title }}</p>
                <p class="text-xs text-[var(--color-text-secondary)]">
                  {{ sectionDone(section) }}/{{ section.items.length }} 已完成
                </p>
              </div>
              <ChevronRight :class="['w-4 h-4 text-[var(--color-text-secondary)] transition-transform shrink-0',
                expandedSections.has(section.section_id) ? 'rotate-90' : '']" />
            </div>

            <!-- 知识点列表 -->
            <div v-if="expandedSections.has(section.section_id)" class="border-t border-[var(--color-border)]">
              <div v-for="(item, ii) in section.items" :key="item.item_id"
                class="flex items-center gap-3 px-5 py-3.5 hover:bg-[var(--color-bg)] transition-colors cursor-pointer border-b border-[var(--color-border)] last:border-0 group"
                @click="openClassroom(item)"
                :style="{ animationDelay: (si * section.items.length + ii) * 0.06 + 's' }"
                :class="[showItems ? 'animate-slide-up opacity-100' : 'opacity-0']">
                <!-- 状态圈 -->
                <div :class="['w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
                  item.status === 'done' ? 'bg-emerald-100 text-emerald-600' :
                  'bg-[var(--color-border)] text-[var(--color-text-secondary)] group-hover:bg-[var(--color-primary-soft)] group-hover:text-[var(--color-primary)] transition-all']">
                  <Check v-if="item.status === 'done'" class="w-3.5 h-3.5" />
                  <span v-else>{{ item.sort_order + 1 }}</span>
                </div>
                <!-- 内容 -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate group-hover:text-[var(--color-primary)] transition-colors">{{ item.item_title }}</p>
                  <p v-if="item.item_description" class="text-xs text-[var(--color-text-secondary)] truncate">{{ item.item_description }}</p>
                </div>
                <!-- 掌握度 -->
                <div v-if="item.mastery_score > 0" class="text-xs font-semibold mr-2"
                  :class="item.mastery_score >= 80 ? 'text-emerald-500' : item.mastery_score >= 50 ? 'text-amber-500' : 'text-red-500'">
                  {{ item.mastery_score }}
                </div>
                <ArrowRight class="w-4 h-4 text-[var(--color-text-secondary)] opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
              </div>
            </div>
          </div>

          <!-- 底部完成态 -->
          <div v-if="items.length > 0 && doneCount === items.length" class="text-center py-8 animate-fade-in">
            <div class="text-4xl mb-3">🎉</div>
            <p class="text-lg font-bold">课程全部完成！</p>
          </div>
        </div>

        <!-- ── 教室（展开态） ── -->
        <StudioClassroom v-if="currentView === 'classroom'" :session-id="sessionId"
          :item="currentItem" :subject="session?.subject"
          @back="currentView = 'syllabus'" @done="onItemDone" />
      </div>
    </main>
    <!-- ── 确认弹窗 ── -->
    <ConfirmModal
      :visible="showRegenConfirm"
      title="重新生成大纲"
      message="重新生成将清空当前学习进度，确定吗？"
      confirm-text="确定重新生成"
      cancel-text="取消"
      :danger="true"
      @confirm="regenerateSyllabus"
      @cancel="showRegenConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSession, generateSyllabusForSession } from '@/api/learning'
import { ChevronRight, Check, PanelLeftOpen, ArrowLeft, ArrowRight, Sparkles, RotateCcw, BookOpen } from 'lucide-vue-next'
import StudioAssessment from '@/components/studio/StudioAssessment.vue'
import StudioClassroom from '@/components/studio/StudioClassroom.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'

const route = useRoute()
const router = useRouter()
const sessionId = Number(route.params.id)

// State
const session = ref<any>(null)
const items = ref<any[]>([])
const isLoading = ref(true)
const isMobile = ref(false)
const showSidebar = ref(false)

// View management
const currentView = ref<string>('default')
const currentItem = ref<any>(null)
const expandedSections = ref<Set<string>>(new Set())

// Animation
const showSections = ref(false)
const showItems = ref(false)

// Level filter
const courseLevels = computed(() => (session.value?.course_levels || [1]) as number[])
const activeLevel = ref(1)

// Computed
const filteredItems = computed(() => items.value.filter((i: any) => i.level === activeLevel.value))
const groupedSections = computed(() => {
  const map = new Map<string, any>()
  filteredItems.value.forEach((item: any) => {
    if (!map.has(item.section_title)) {
      map.set(item.section_title, { section_id: item.section_id, section_title: item.section_title, items: [] })
    }
    map.get(item.section_title)!.items.push(item)
  })
  return Array.from(map.values())
})
const progressPct = computed(() => {
  if (items.value.length === 0) return 0
  return Math.round((doneCount.value / items.value.length) * 100)
})

const doneCount = computed(() => items.value.filter((i: any) => i.status === 'done').length)

const sectionDone = (section: any) => section.items.filter((i: any) => i.status === 'done').length

// ── 交互 ──────────────────────────────────────────────

function toggleSection(id: string) {
  expandedSections.value.has(id) ? expandedSections.value.delete(id) : expandedSections.value.add(id)
}

function openClassroom(item: any) {
  currentItem.value = item
  currentView.value = 'classroom'
}

function scrollToSection(id: string) {
  expandedSections.value.add(id)
  nextTick(() => {
    const el = document.getElementById('section-' + id)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

// ── 大纲生成 ──────────────────────────────────────────

async function doGenerateSyllabus(force = false) {
  currentView.value = 'generating'
  showSections.value = false
  showItems.value = false
  try {
    await generateSyllabusForSession(sessionId, session.value?.subject || '', force)
    const res: any = await getSession(sessionId)
    session.value = res
    items.value = res.syllabus_items || []
    currentView.value = 'syllabus'
    await nextTick()
    showSections.value = true
    setTimeout(() => { showItems.value = true }, 400)
    const first = groupedSections.value[0]
    if (first) expandedSections.value.add(first.section_id)
  } catch (e) {
    currentView.value = 'syllabus'
  }
}

async function generateSyllabus() { await doGenerateSyllabus(false) }

const showRegenConfirm = ref(false)
async function regenerateSyllabus() {
  showRegenConfirm.value = false
  await doGenerateSyllabus(true)
}

// ── 事件 ──────────────────────────────────────────────

function onAssessmentDone() { generateSyllabus() }

async function onAssessmentSkip() {
  try {
    await fetch(`/api/assessment/skip/${sessionId}`, { method: 'POST' })
    generateSyllabus()
  } catch {}
}

async function onItemDone() {
  // 持久化知识点完成状态
  if (currentItem.value?.id) {
    try {
      await fetch(`/api/syllabus/item/${currentItem.value.id}/complete`, { method: 'POST' })
    } catch {}
  }
  loadSession()
  currentView.value = 'syllabus'
}

// ── 初始化 ────────────────────────────────────────────

async function loadSession() {
  try {
    const res: any = await getSession(sessionId)
    session.value = res
    items.value = res.syllabus_items || []
    if (res.status === 'assessing' && !res.assessment?.completed) {
      currentView.value = 'assessment'
    } else if (items.value.length > 0) {
      currentView.value = 'syllabus'
      showSections.value = true
      showItems.value = true
      const first = groupedSections.value[0]
      if (first) expandedSections.value.add(first.section_id)
    } else if (res.status === 'assessed' || (res.status === 'syllabus_ready' && items.value.length === 0)) {
      await doGenerateSyllabus(false)
    } else {
      currentView.value = 'syllabus'
    }
  } catch {} finally { isLoading.value = false }
}

watch(activeLevel, () => {
  expandedSections.value.clear()
  const first = groupedSections.value[0]
  if (first) expandedSections.value.add(first.section_id)
})

function checkMobile() {
  isMobile.value = window.innerWidth < 1024
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadSession()
})
</script>
