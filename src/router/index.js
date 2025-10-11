// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/MainAppView.vue'),
    meta: { title: 'Benova Multi-Tenant Backend' }
  },
  {
    path: '/documentos',
    name: 'Documentos',
    component: () => import('@/views/DocumentosView.vue'),
    meta: {
      title: 'Documentos - Benova',
      icon: '📄',
      label: 'Documentos',
      requiresCompany: true
    }
  // Más rutas...
]

// ============================================================================
// 🆕 EXPORTAR RUTAS DE NAVEGACIÓN (para MainLayout)
// ============================================================================
export const navigationRoutes = routes.filter(route => 
  route.meta?.icon && route.path !== '/'
)

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
