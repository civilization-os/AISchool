<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="onCancel">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />

        <!-- 弹窗 -->
        <div class="relative bg-[var(--color-surface)] rounded-2xl shadow-2xl max-w-sm w-full p-6 animate-slide-up">
          <!-- 图标 -->
          <div class="w-12 h-12 rounded-2xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle class="w-6 h-6 text-amber-500" />
          </div>

          <!-- 标题 -->
          <h3 class="text-lg font-bold text-center mb-2">{{ title }}</h3>

          <!-- 描述 -->
          <p class="text-sm text-[var(--color-text-secondary)] text-center mb-6">{{ message }}</p>

          <!-- 按钮 -->
          <div class="flex gap-3">
            <button class="btn btn-secondary btn-md flex-1" @click="onCancel">{{ cancelText }}</button>
            <button class="btn btn-primary btn-md flex-1" :class="danger ? '!bg-red-500 hover:!bg-red-600' : ''" @click="onConfirm">
              <LoaderCircle v-if="loading" class="w-4 h-4 animate-spin" />
              <span v-else>{{ confirmText }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { AlertTriangle, LoaderCircle } from 'lucide-vue-next'

defineProps<{
  visible: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{ confirm: []; cancel: [] }>()
const onConfirm = () => emit('confirm')
const onCancel = () => emit('cancel')
</script>
