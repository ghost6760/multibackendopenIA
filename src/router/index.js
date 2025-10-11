// src/router/index.js - VERSIÓN COMPLETA SIN ERRORES
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/MainAppView.vue'),
    meta: { 
      title: 'Benova Multi-Tenant Backend' 
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
      title: 'Dashboard - Benova',
      icon: '📊',
      label: 'Dashboard',
      requiresCompany: true
    }
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
  },
  {
    path: '/conversaciones',
    name: 'Conversaciones',
    component: () => import('@/views/ConversacionesView.vue'),
    meta: {
      title: 'Conversaciones - Benova',
      icon: '💬',
      label: 'Conversaciones',
      requiresCompany: true
    }
  },
  {
    path: '/multimedia',
    name: 'Multimedia',
    component: () => import('@/views/MultimediaView.vue'),
    meta: {
      title: 'Multimedia - Benova',
      icon: '🎥',
      label: 'Multimedia',
      requiresCompany: true
    }
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: () => import('@/views/PromptsView.vue'),
    meta: {
      title: 'Prompts - Benova',
      icon: '🎭',
      label: 'Prompts',
      requiresCompany: true
    }
  },
  {
    path: '/administracion',
    name: 'Administracion',
    component: () => import('@/views/AdministracionView.vue'),
    meta: {
      title: 'Administración - Benova',
      icon: '🔧',
      label: 'Administración',
      requiresCompany: true
    }
  },
  {
    path: '/enterprise',
    name: 'Enterprise',
    component: () => import('@/views/EnterpriseView.vue'),
    meta: {
      title: 'Enterprise - Benova',
      icon: '🏢',
      label: 'Enterprise',
      requiresCompany: true
    }
  },
  {
    path: '/health',
    name: 'HealthCheck',
    component: () => import('@/views/HealthCheckView.vue'),
    meta: {
      title: 'Health Check - Benova',
      icon: '💚',
      label: 'Health Check',
      requiresCompany: false
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// Exportar rutas de navegación para MainLayout
export const navigationRoutes = routes.filter(route => 
  route.meta?.icon && route.path !== '/'
)

// Crear router
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
  document.title = to.meta?.title || 'Benova Multi-Tenant Backend'
  next()
})

export default router
