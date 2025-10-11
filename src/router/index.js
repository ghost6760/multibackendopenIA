// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Importar la vista principal (tu app actual)
const MainAppView = () => import('@/views/MainAppView.vue')

// ============================================================================
// RUTAS - SOLO LA PRINCIPAL POR AHORA
// ============================================================================
const routes = [
  {
    path: '/',
    name: 'Home',
    component: MainAppView,
    meta: {
      title: 'Benova Multi-Tenant Backend'
    }
  },
  // Ruta catch-all
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// ============================================================================
// CREAR ROUTER
// ============================================================================
const router = createRouter({
  history: createWebHistory(),
  routes
})

// ============================================================================
// NAVIGATION GUARDS
// ============================================================================
router.beforeEach((to, from, next) => {
  document.title = to.meta?.title || 'Benova Multi-Tenant Backend'
  console.log(`📍 Router: ${from.path} → ${to.path}`)
  next()
})

export default router
