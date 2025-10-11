// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'

// ============================================================================
// LAZY LOADING DE VISTAS
// ============================================================================
const HomeView = () => import('@/views/HomeView.vue')
const DashboardView = () => import('@/views/DashboardView.vue')
const DocumentosView = () => import('@/views/DocumentosView.vue')
const ConversacionesView = () => import('@/views/ConversacionesView.vue')
const MultimediaView = () => import('@/views/MultimediaView.vue')
const PromptsView = () => import('@/views/PromptsView.vue')
const AdministracionView = () => import('@/views/AdministracionView.vue')
const EnterpriseView = () => import('@/views/EnterpriseView.vue')
const HealthCheckView = () => import('@/views/HealthCheckView.vue')

// ============================================================================
// RUTAS
// ============================================================================
const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: {
      title: 'Benova Multi-Tenant Backend',
      layout: 'empty', // Sin layout de tabs (muestra todos los tabs dentro)
      requiresCompany: false
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: {
      title: 'Dashboard - Benova',
      icon: '📊',
      label: 'Dashboard',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/documentos',
    name: 'Documentos',
    component: DocumentosView,
    meta: {
      title: 'Documentos - Benova',
      icon: '📄',
      label: 'Documentos',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/conversaciones',
    name: 'Conversaciones',
    component: ConversacionesView,
    meta: {
      title: 'Conversaciones - Benova',
      icon: '💬',
      label: 'Conversaciones',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/multimedia',
    name: 'Multimedia',
    component: MultimediaView,
    meta: {
      title: 'Multimedia - Benova',
      icon: '🎥',
      label: 'Multimedia',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: PromptsView,
    meta: {
      title: 'Prompts - Benova',
      icon: '🎭',
      label: 'Prompts',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/administracion',
    name: 'Administracion',
    component: AdministracionView,
    meta: {
      title: 'Administración - Benova',
      icon: '🔧',
      label: 'Administración',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/enterprise',
    name: 'Enterprise',
    component: EnterpriseView,
    meta: {
      title: 'Enterprise - Benova',
      icon: '🏢',
      label: 'Enterprise',
      layout: 'main',
      requiresCompany: true
    }
  },
  {
    path: '/health-check',
    name: 'HealthCheck',
    component: HealthCheckView,
    meta: {
      title: 'Health Check - Benova',
      icon: '💚',
      label: 'Health Check',
      layout: 'main',
      requiresCompany: false
    }
  },
  // Catch-all para 404
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
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// ============================================================================
// NAVIGATION GUARDS
// ============================================================================
router.beforeEach((to, from, next) => {
  // Cambiar título
  document.title = to.meta.title || 'Benova Multi-Tenant Backend'
  
  // Verificar empresa si es requerida
  if (to.meta.requiresCompany) {
    const appStore = useAppStore()
    if (!appStore.currentCompanyId) {
      console.warn(`⚠️ Route ${to.path} requires company selection`)
    }
  }
  
  next()
})

router.afterEach((to, from) => {
  console.log(`📍 Navigated: ${from.path} → ${to.path}`)
})

export default router

// ============================================================================
// EXPORTAR RUTAS PARA NAVEGACIÓN
// ============================================================================
export const navigationRoutes = routes.filter(route => 
  route.meta?.layout === 'main' && route.path !== '/'
)
