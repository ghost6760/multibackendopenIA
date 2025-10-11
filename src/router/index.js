// src/router/index.js - SOLO VISTAS QUE EXISTEN
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
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

export const navigationRoutes = routes.filter(route => 
  route.meta?.icon && route.path !== '/'
)

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta?.title || 'Benova Multi-Tenant Backend'
  next()
})

export default router
