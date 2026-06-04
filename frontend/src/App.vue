<template>
  <div :class="['app-root', { dark: isDark }]">
    <!-- 路由视图 -->
    <router-view v-slot="{ Component, route }">
      <transition name="slide-up" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </transition>
    </router-view>

    <!-- 通知容器 -->
    <div class="toast-container">
      <transition-group name="fade">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
        >
          {{ toast.message }}
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, provide, onMounted, onUnmounted } from 'vue'

const isDark = ref(false)
const toasts = ref<{ id: number; type: string; message: string }[]>([])
let toastId = 0

// 设置主题
const themeStore = (window as any).__themeStore
if (themeStore) {
  isDark.value = themeStore.theme === 'dark'
}

provide('toast', (message: string, type = 'info') => {
  const id = ++toastId
  toasts.value.push({ id, type, message })
  setTimeout(() => {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx > -1) toasts.value.splice(idx, 1)
  }, 3000)
})

// 键盘快捷键
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    // 关闭任何打开的模态框等
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  // 隐藏加载动画
  const el = document.getElementById('loading')
  if (el) {
    el.classList.add('hidden')
    setTimeout(() => el.remove(), 500)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style>
/* 全局样式已由 main.css 提供 */
</style>
