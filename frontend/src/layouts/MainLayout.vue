<template>
  <div :class="['min-h-screen', isDark ? 'dark' : '']">
    <!-- ── 背景 ── -->
    <div class="fixed inset-0 -z-10 overflow-hidden">
      <!-- 主渐变 -->
      <div class="absolute inset-0 bg-gradient-to-br from-indigo-50 via-white to-amber-50 dark:from-gray-950 dark:via-gray-900 dark:to-indigo-950" />
      <!-- 装饰光晕 -->
      <div class="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-indigo-200/30 dark:bg-indigo-800/10 blur-3xl animate-pulse-soft" />
      <div class="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-amber-200/20 dark:bg-amber-800/10 blur-3xl animate-pulse-soft" style="animation-delay: 2s" />
      <div class="absolute top-1/2 left-1/3 w-64 h-64 rounded-full bg-cyan-200/15 dark:bg-cyan-800/10 blur-3xl animate-pulse-soft" style="animation-delay: 4s" />
      <!-- 网格纹理 -->
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMwMDAiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
    </div>

    <!-- ── 顶栏 ── -->
    <header class="sticky top-0 z-50 backdrop-blur-xl bg-white/70 dark:bg-gray-950/70 border-b border-[var(--color-border)]/50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <!-- 左: Logo + 导航 -->
        <div class="flex items-center gap-1 sm:gap-2">
          <router-link to="/launchpad" class="flex items-center gap-2.5 mr-4 sm:mr-8 group">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-sm group-hover:shadow-md group-hover:scale-105 transition-all">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span class="text-base font-bold tracking-tight hidden sm:block bg-gradient-to-r from-indigo-600 to-cyan-600 bg-clip-text text-transparent">AI School</span>
          </router-link>

          <router-link to="/launchpad"
            :class="['px-3 py-1.5 rounded-lg text-sm font-medium transition-all', isActive('/launchpad') ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800']">
            <LayoutDashboard class="w-4 h-4 inline mr-1.5" />启动台
          </router-link>

          <router-link to="/settings/config"
            :class="['px-3 py-1.5 rounded-lg text-sm font-medium transition-all', isActive('/settings') ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800']">
            <Settings class="w-4 h-4 inline mr-1.5" />配置
          </router-link>
        </div>

        <!-- 右: 工具 -->
        <div class="flex items-center gap-2">
          <!-- 后端状态 -->
          <span class="hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full"
            :class="backendHealthy ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'">
            <span :class="['w-1.5 h-1.5 rounded-full', backendHealthy ? 'bg-emerald-500' : 'bg-red-500']" />
            {{ backendHealthy ? '已连接' : '离线' }}
          </span>

          <!-- 黑暗模式 -->
          <button class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all" @click="toggleDark">
            <Sun v-if="isDark" class="w-4 h-4" />
            <Moon v-else class="w-4 h-4" />
          </button>

          <!-- 头像 -->
          <div class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white text-xs font-semibold shadow-sm cursor-pointer">
            {{ userInitial }}
          </div>
        </div>
      </div>
    </header>

    <!-- ── 主内容 ── -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <router-view v-slot="{ Component }">
        <transition name="slide-up" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLearningStore } from '@/stores/learning'
import { LayoutDashboard, Settings, Sun, Moon } from 'lucide-vue-next'

const route = useRoute()
const learningStore = useLearningStore()

const isDark = ref(false)

const isActive = (path: string) => route.path.startsWith(path)
const userInitial = '学'
const backendHealthy = computed(() => learningStore.backendStatus === 'healthy')

const toggleDark = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  if (localStorage.getItem('theme') === 'dark') {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
  learningStore.checkBackend()
})
</script>
