// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/MainAppView.vue'), // 👈 Usa tu vista
    meta: { title: 'Benova Multi-Tenant Backend' }
  },
  {
    path: '/documentos',
    name: 'Documentos',
    component: () => import('@/views/DocumentosView.vue'),
    meta: { 
      title: 'Documentos - Benova',
      layout: 'main' 
    }
  }
  // Más rutas...
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta?.title || 'Benova'
  next()
})

export default router
