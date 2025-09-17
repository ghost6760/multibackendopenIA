<template>
  <div id="notificationContainer" class="notification-container">
    <TransitionGroup name="notification" tag="div">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="[
          'notification',
          `notification-${notification.type}`,
          { 'notification-show': true }
        ]"
        @click="handleNotificationClick(notification)"
      >
        <!-- Icon based on type -->
        <div class="notification-icon">
          {{ getNotificationIcon(notification.type) }}
        </div>
        
        <!-- Content -->
        <div class="notification-content">
          <div class="notification-message">
            {{ notification.message }}
          </div>
          
          <!-- Action button if present -->
          <button
            v-if="notification.action"
            @click.stop="handleActionClick(notification)"
            class="notification-action-btn"
          >
            {{ notification.action.text }}
          </button>
          
          <!-- Timestamp for debugging (only in dev mode) -->
          <div v-if="showTimestamps" class="notification-timestamp">
            {{ formatTimestamp(notification.timestamp) }}
          </div>
        </div>
        
        <!-- Close button -->
        <button
          @click.stop="dismissNotification(notification.id)"
          class="notification-close"
          :title="`Cerrar ${notification.type}`"
        >
          ✕
        </button>
        
        <!-- Progress bar for notifications with duration -->
        <div
          v-if="notification.duration > 0"
          class="notification-progress"
          :style="{ animationDuration: `${notification.duration}ms` }"
        ></div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { hideNotification } = useNotifications()

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const notifications = computed(() => appStore.notifications)

const showTimestamps = computed(() => {
  return import.meta.env.DEV || appStore.adminApiKey
})

// ============================================================================
// MÉTODOS DE MANEJO DE NOTIFICACIONES
// ============================================================================

/**
 * Obtiene el ícono apropiado para cada tipo de notificación
 */
const getNotificationIcon = (type) => {
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  }
  
  return icons[type] || 'ℹ️'
}

/**
 * Maneja el click en la notificación (para cerrar)
 */
const handleNotificationClick = (notification) => {
  // Solo cerrar si no tiene acción
  if (!notification.action) {
    dismissNotification(notification.id)
  }
}

/**
 * Maneja el click en el botón de acción
 */
const handleActionClick = (notification) => {
  if (notification.action && typeof notification.action.callback === 'function') {
    try {
      notification.action.callback()
    } catch (error) {
      console.error('Error executing notification action:', error)
      appStore.addToLog(`Notification action error: ${error.message}`, 'error')
    }
  }
  
  // Cerrar la notificación después de ejecutar la acción
  dismissNotification(notification.id)
}

/**
 * Cierra una notificación específica
 */
const dismissNotification = (notificationId) => {
  hideNotification(notificationId)
}

/**
 * Cierra todas las notificaciones
 */
const dismissAllNotifications = () => {
  notifications.value.forEach(notification => {
    dismissNotification(notification.id)
  })
}

/**
 * Formatea el timestamp para mostrar
 */
const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

/**
 * Maneja teclas de teclado para notificaciones
 */
const handleKeyPress = (event) => {
  // Escapar cierra todas las notificaciones
  if (event.key === 'Escape' && notifications.value.length > 0) {
    dismissAllNotifications()
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Event listeners para interacción con teclado
  document.addEventListener('keydown', handleKeyPress)
  
  appStore.addToLog('AppNotifications component mounted', 'info')
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyPress)
})
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  max-width: 400px;
  pointer-events: none; /* Allow clicks through the container */
}

.notification {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  pointer-events: auto; /* Re-enable clicks for notifications */
  
  /* Base styles */
  background: var(--bg-secondary);
  border-left: 4px solid var(--primary-color);
  color: var(--text-primary);
  
  /* Hover effect */
  transition: all 0.3s ease;
}

.notification:hover {
  transform: translateX(-5px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

/* Notification types */
.notification-success {
  border-left-color: var(--success-color);
  background: rgba(34, 197, 94, 0.1);
}

.notification-error {
  border-left-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.1);
}

.notification-warning {
  border-left-color: var(--warning-color);
  background: rgba(245, 158, 11, 0.1);
}

.notification-info {
  border-left-color: var(--info-color);
  background: rgba(59, 130, 246, 0.1);
}

/* Icon */
.notification-icon {
  font-size: 1.2em;
  min-width: 24px;
  text-align: center;
  margin-top: 2px;
}

/* Content */
.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-message {
  font-weight: 500;
  line-height: 1.4;
  word-wrap: break-word;
}

.notification-action-btn {
  margin-top: 8px;
  padding: 4px 12px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
}

.notification-action-btn:hover {
  background: var(--primary-color-dark);
}

.notification-timestamp {
  font-size: 0.8em;
  color: var(--text-muted);
  margin-top: 4px;
}

/* Close button */
.notification-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.2em;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  min-width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--text-primary);
}

/* Progress bar */
.notification-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: currentColor;
  opacity: 0.6;
  animation: progress-shrink linear forwards;
}

@keyframes progress-shrink {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

/* Transitions */
.notification-enter-active {
  transition: all 0.3s ease-out;
}

.notification-leave-active {
  transition: all 0.3s ease-in;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}

/* Responsive design */
@media (max-width: 768px) {
  .notification-container {
    top: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
  
  .notification {
    padding: 12px;
    margin-bottom: 8px;
  }
  
  .notification:hover {
    transform: none; /* Disable hover transform on mobile */
  }
  
  .notification-message {
    font-size: 0.9em;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .notification {
    border: 2px solid;
  }
  
  .notification-success {
    border-color: var(--success-color);
  }
  
  .notification-error {
    border-color: var(--danger-color);
  }
  
  .notification-warning {
    border-color: var(--warning-color);
  }
  
  .notification-info {
    border-color: var(--info-color);
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .notification {
    transition: none;
  }
  
  .notification:hover {
    transform: none;
  }
  
  .notification-enter-active,
  .notification-leave-active {
    transition: opacity 0.2s ease;
  }
  
  .notification-enter-from,
  .notification-leave-to {
    transform: none;
  }
  
  .notification-progress {
    animation: none;
    width: 0;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .notification {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  
  .notification:hover {
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
  }
  
  .notification-close:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}
</style>
