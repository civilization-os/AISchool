<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center gap-3 p-4 border-b border-[var(--color-border)]">
      <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--color-primary)] to-indigo-500 flex items-center justify-center shadow-sm">
        <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold truncate">{{ session?.subject || '课程' }}</p>
        <p class="text-xs text-[var(--color-text-secondary)]">{{ progressPct }}% 已完成</p>
      </div>
      <button class="lg:hidden btn btn-ghost btn-sm p-1" @click="$emit('close')">
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Progress bar -->
    <div class="px-4 pt-3">
      <div class="h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
        <div class="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-indigo-500 transition-all duration-700"
          :style="{ width: progressPct + '%' }"></div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto p-3 space-y-1">
      <button
        :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all',
          currentView === 'assessment' ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' :
          'text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 hover:text-[var(--color-text)]']"
        @click="$emit('navigate', 'assessment')"
      >
        <ClipboardCheck class="w-4 h-4" />
        <span>入学测评</span>
        <Check v-if="hasAssessment" class="w-3.5 h-3.5 ml-auto text-emerald-500" />
      </button>

      <button
        :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all',
          currentView === 'syllabus' || currentView === 'default' ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' :
          'text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 hover:text-[var(--color-text)]']"
        @click="$emit('navigate', 'syllabus')"
      >
        <ListTree class="w-4 h-4" />
        <span>学习大纲</span>
        <span class="text-xs ml-auto opacity-60">{{ doneCount }}/{{ totalCount }}</span>
      </button>

      <!-- Sections as sub-items -->
      <div class="ml-6 space-y-0.5">
        <div
          v-for="section in sections"
          :key="section.section_id"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/30 transition-colors cursor-pointer"
          @click="scrollToSection(section.section_id)"
        >
          <span class="w-1.5 h-1.5 rounded-full"
            :class="sectionDone(section) === section.items.length ? 'bg-emerald-400' : 'bg-[var(--color-border)]'"></span>
          <span class="truncate">{{ section.section_title }}</span>
          <span class="ml-auto opacity-50">{{ sectionDone(section) }}/{{ section.items.length }}</span>
        </div>
      </div>

      <!-- Exams -->
      <div class="pt-2 border-t border-[var(--color-border)]">
        <div v-if="hasMidterm" class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-emerald-600 dark:text-emerald-400">
          <CheckCircle class="w-4 h-4" />
          <span>期中考试 已完成</span>
        </div>
        <button
          v-else
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 transition-all"
          :class="currentView === 'exam' ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' : ''"
          @click="$emit('navigate', 'exam')"
        >
          <FileText class="w-4 h-4" />
          <span>期中考试</span>
          <span class="text-xs ml-auto">{{ examProgress }}%</span>
        </button>
      </div>
    </nav>

    <!-- Bottom -->
    <div class="p-3 border-t border-[var(--color-border)]">
      <button class="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]/40 transition-all" @click="router.push('/')">
        <ArrowLeft class="w-4 h-4" />
        <span>返回首页</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ClipboardCheck, ListTree, FileText, Check, CheckCircle, ArrowLeft, X } from 'lucide-vue-next'

const props = defineProps<{
  items: any[]
  currentView: string
  progressPct: number
  session: any
}>()

defineEmits<{ navigate: [view: string, item?: any]; close: [] }>()

const router = useRouter()

const sections = computed(() => {
  const map = new Map<string, any>()
  props.items.forEach((item: any) => {
    if (!map.has(item.section_title)) {
      map.set(item.section_title, { section_id: item.section_id, section_title: item.section_title, items: [] })
    }
    map.get(item.section_title)!.items.push(item)
  })
  return Array.from(map.values())
})

const doneCount = computed(() => props.items.filter((i: any) => i.status === 'done').length)
const totalCount = computed(() => props.items.length)
const hasAssessment = computed(() => props.session?.assessment?.completed)
const hasMidterm = computed(() => props.session?.exam_unlock?.has_midterm)
const examProgress = computed(() => props.session?.exam_unlock?.progress || 0)

const sectionDone = (section: any) => section.items.filter((i: any) => i.status === 'done').length

function scrollToSection(id: string) {
  // Emit navigate to switch to syllabus view
  // Could also scroll to the section if already in syllabus view
}
</script>
