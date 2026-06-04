import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/launchpad',
      children: [
        {
          path: 'launchpad',
          name: 'Launchpad',
          component: () => import('@/views/Launchpad.vue'),
          meta: { title: 'AI School' }
        },
        {
          path: 'course/:id',
          name: 'CourseStudio',
          component: () => import('@/views/CourseStudio.vue'),
          meta: { title: '学习工作室' }
        },
        {
          path: 'learn',
          name: 'QuickLearn',
          component: () => import('@/views/learning/QuickLearn.vue'),
          meta: { title: '快速学习' }
        },
        {
          path: 'practice',
          name: 'Practice',
          component: () => import('@/views/learning/Practice.vue'),
          meta: { title: '练习题' }
        },
        {
          path: 'settings/config',
          name: 'ModelConfig',
          component: () => import('@/views/settings/Config.vue'),
          meta: { title: '模型配置' }
        },
        {
          path: 'docs/api',
          name: 'ApiDocs',
          component: () => import('@/views/docs/ApiDocs.vue'),
          meta: { title: 'API 文档' }
        },
        {
          path: '/:pathMatch(.*)*',
          name: 'NotFound',
          component: () => import('@/views/error/404.vue')
        }
      ]
    }
  ]
})

router.beforeEach((to) => {
  if (to.meta?.title) document.title = `${to.meta.title} — AI School`
  return true
})

export default router
