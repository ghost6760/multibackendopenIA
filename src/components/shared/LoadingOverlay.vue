<template>
  <Transition name="overlay" appear>
    <div 
      class="loading-overlay"
      :class="{ 
        'loading-overlay-dark': darkMode,
        'loading-overlay-blur': useBlur
      }"
      @click="handleOverlayClick"
    >
      <!-- Loading content -->
      <div class="loading-content" :class="{ 'loading-content-large': largeSpinner }">
        <!-- Spinner -->
        <div class="loading-spinner" :class="spinnerClass">
          <div v-if="spinnerType === 'default'" class="spinner-default">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
          </div>
          
          <div v-else-if="spinnerType === 'dots'" class="spinner-dots">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
          </div>
          
          <div v-else-if="spinnerType === 'pulse'" class="spinner-pulse">
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
          </div>
          
          <div v-else-if="spinnerType === 'emoji'" class="spinner-emoji">
            {{ currentEmoji }}
          </div>
          
          <div v-else class="spinner-simple">⏳</div>
        </div>
        
        <!-- Loading message -->
        <div class="loading-message">
          <h3 class="loading-title">{{ currentTitle }}</h3>
          <p v-if="currentMessage" class="loading-text">{{ currentMessage }}</p>
          
          <!-- Progress bar (if applicable) -->
          <div v-if="showProgress" class="loading-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill"
                :style="{ width: `${progress}%` }"
              ></div>
            </div>
            <div class="progress-text">{{ progress }}%</div>
          </div>
          
          <!-- Estimated time -->
          <div v-if="estimatedTime > 0" class="estimated-time">
            <small>⏱️ Tiempo estimado: {{ formatTime(estimatedTime) }}</small>
          </div>
          
          <!-- Cancel button (if applicable) -->
          <div v-if="showCancelButton" class="loading-actions">
            <button @click="handleCancel" class="cancel-btn">
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
      
      <!-- Background pattern (optional) -->
      <div v-if="showPattern" class="loading-pattern">
        <div class="pattern-grid">
          <div v-for="i in 20" :key="i" class="pattern-dot"></div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'

// ============================================================================
// PROPS
// ============================================================================

const props = defineProps({
  title: {
    type: String,
    default: 'Cargando...'
  },
  message: {
    type: String,
    default: ''
  },
  spinnerType: {
    type: String,
    default: 'default', // 'default', 'dots', 'pulse', 'emoji', 'simple'
    validator: (value) => ['default', 'dots', 'pulse', 'emoji', 'simple'].includes(value)
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  useBlur: {
    type: Boolean,
    default: true
  },
  largeSpinner: {
    type: Boolean,
    default: false
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 100
  },
  estimatedTime: {
    type: Number,
    default: 0 // in seconds
  },
  showCancelButton: {
    type: Boolean,
    default: false
  },
  cancelable: {
    type: Boolean,
    default: false
  },
  showPattern: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['cancel', 'overlay-click'])

// ============================================================================
// STORES
// ============================================================================

const appStore = useAppStore()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const currentEmoji = ref('⏳')
const emojiIndex = ref(0)
const loadingStartTime = ref(Date.now())
const currentTitleIndex = ref(0)
const currentMessageIndex = ref(0)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const spinnerClass = computed(() => {
  return {
    'spinner-large': props.largeSpinner,
    [`spinner-${props.spinnerType}`]: true
  }
})

const currentTitle = computed(() => {
  // If no custom title provided, cycle through default ones
  if (props.title !== 'Cargando...') {
    return props.title
  }
  
  const titles = [
    'Cargando...',
    'Procesando...',
    'Un momento...',
    'Trabajando...'
  ]
  
  return titles[currentTitleIndex.value % titles.length]
})

const currentMessage = computed(() => {
  if (props.message) {
    return props.message
  }
  
  const messages = [
    'Esto puede tomar unos segundos',
    'Preparando la información',
    'Conectando con el servidor',
    'Procesando su solicitud'
  ]
  
  return messages[currentMessageIndex.value % messages.length]
})

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Handle overlay click
 */
const handleOverlayClick = (event) => {
  // Only emit if clicked on overlay background, not on content
  if (event.target === event.currentTarget) {
    emit('overlay-click')
    
    if (props.cancelable) {
      handleCancel()
    }
  }
}

/**
 * Handle cancel button click
 */
const handleCancel = () => {
  emit('cancel')
  appStore.addToLog('Loading cancelled by user', 'info')
}

/**
 * Format time in human readable format
 */
const formatTime = (seconds) => {
  if (seconds < 60) {
    return `${seconds}s`
  }
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (remainingSeconds === 0) {
    return `${minutes}m`
  }
  
  return `${minutes}m ${remainingSeconds}s`
}

/**
 * Cycle through emojis for emoji spinner
 */
const cycleEmojis = () => {
  const emojis = ['⏳', '⌛', '🔄', '⚙️', '🔧', '⭐', '💫', '✨']
  emojiIndex.value = (emojiIndex.value + 1) % emojis.length
  currentEmoji.value = emojis[emojiIndex.value]
}

/**
 * Cycle through titles and messages
 */
const cycleTexts = () => {
  currentTitleIndex.value = (currentTitleIndex.value + 1) % 4
  currentMessageIndex.value = (currentMessageIndex.value + 1) % 4
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

let emojiInterval = null
let textInterval = null

onMounted(() => {
  // Start emoji animation for emoji spinner
  if (props.spinnerType === 'emoji') {
    emojiInterval = setInterval(cycleEmojis, 500)
  }
  
  // Cycle through titles and messages if using defaults
  if (props.title === 'Cargando...' && !props.message) {
    textInterval = setInterval(cycleTexts, 3000)
  }
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden'
  
  // Add keyboard listener for ESC
  document.addEventListener('keydown', handleKeyDown)
  
  appStore.addToLog('Loading overlay mounted', 'info')
})

onUnmounted(() => {
  // Cleanup intervals
  if (emojiInterval) {
    clearInterval(emojiInterval)
  }
  
  if (textInterval) {
    clearInterval(textInterval)
  }
  
  // Restore body scroll
  document.body.style.overflow = ''
  
  // Remove keyboard listener
  document.removeEventListener('keydown', handleKeyDown)
})

/**
 * Handle keyboard events
 */
const handleKeyDown = (event) => {
  // ESC key cancels if cancelable
  if (event.key === 'Escape' && props.cancelable) {
    handleCancel()
  }
}

// ============================================================================
// WATCHERS
// ============================================================================

// Restart emoji animation when spinner type changes
watch(() => props.spinnerType, (newType) => {
  if (emojiInterval) {
    clearInterval(emojiInterval)
    emojiInterval = null
  }
  
  if (newType === 'emoji') {
    emojiInterval = setInterval(cycleEmojis, 500)
  }
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.loading-overlay-dark {
  background: rgba(0, 0, 0, 0.8);
  color: white;
}

.loading-overlay-blur {
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.loading-content {
  text-align: center;
  padding: 40px;
  background: var(--bg-secondary);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--border-color);
  max-width: 400px;
  min-width: 300px;
}

.loading-content-large {
  min-width: 400px;
  padding: 60px;
}

.loading-overlay-dark .loading-content {
  background: rgba(30, 30, 30, 0.95);
  border-color: rgba(255, 255, 255, 0.1);
}

.loading-spinner {
  margin-bottom: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.spinner-large {
  transform: scale(1.5);
}

/* Default Spinner (Rings) */
.spinner-default {
  position: relative;
  width: 60px;
  height: 60px;
}

.spinner-ring {
  position: absolute;
  border: 4px solid transparent;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1.5s linear infinite;
}

.spinner-ring:nth-child(1) {
  width: 60px;
  height: 60px;
  animation-delay: 0s;
}

.spinner-ring:nth-child(2) {
  width: 45px;
  height: 45px;
  top: 7.5px;
  left: 7.5px;
  border-top-color: var(--success-color);
  animation-delay: -0.4s;
}

.spinner-ring:nth-child(3) {
  width: 30px;
  height: 30px;
  top: 15px;
  left: 15px;
  border-top-color: var(--warning-color);
  animation-delay: -0.8s;
}

.spinner-ring:nth-child(4) {
  width: 15px;
  height: 15px;
  top: 22.5px;
  left: 22.5px;
  border-top-color: var(--danger-color);
  animation-delay: -1.2s;
}

/* Dots Spinner */
.spinner-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: dots-bounce 1.4s ease-in-out infinite both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

/* Pulse Spinner */
.spinner-pulse {
  position: relative;
  width: 60px;
  height: 60px;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 3px solid var(--primary-color);
  border-radius: 50%;
  opacity: 0;
  animation: pulse 2s linear infinite;
}

.pulse-ring:nth-child(1) { animation-delay: 0s; }
.pulse-ring:nth-child(2) { animation-delay: 0.7s; }
.pulse-ring:nth-child(3) { animation-delay: 1.4s; }

/* Emoji Spinner */
.spinner-emoji {
  font-size: 3em;
  animation: emoji-bounce 1s ease-in-out infinite;
}

/* Simple Spinner */
.spinner-simple {
  font-size: 3em;
  animation: spin 2s linear infinite;
}

.loading-message {
  color: var(--text-primary);
}

.loading-title {
  margin: 0 0 10px 0;
  font-size: 1.4em;
  font-weight: 600;
  color: var(--text-primary);
}

.loading-text {
  margin: 0 0 20px 0;
  color: var(--text-secondary);
  line-height: 1.5;
}

.loading-progress {
  margin: 20px 0;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  font-size: 0.9em;
  color: var(--text-secondary);
  font-weight: 500;
}

.estimated-time {
  margin-top: 15px;
  color: var(--text-muted);
}

.loading-actions {
  margin-top: 20px;
}

.cancel-btn {
  background: var(--danger-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
}

.cancel-btn:hover {
  background: var(--danger-color-dark);
}

/* Background Pattern */
.loading-pattern {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.1;
  pointer-events: none;
}

.pattern-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(4, 1fr);
  width: 100%;
  height: 100%;
  gap: 20px;
  padding: 40px;
}

.pattern-dot {
  background: var(--primary-color);
  border-radius: 50%;
  animation: pattern-pulse 3s ease-in-out infinite;
}

.pattern-dot:nth-child(odd) {
  animation-delay: 0s;
}

.pattern-dot:nth-child(even) {
  animation-delay: 1.5s;
}

/* Animations */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes dots-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes pulse {
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(1);
    opacity: 0;
  }
}

@keyframes emoji-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes pattern-pulse {
  0%, 100% {
    opacity: 0.3;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

/* Transition animations */
.overlay-enter-active {
  transition: all 0.3s ease-out;
}

.overlay-leave-active {
  transition: all 0.3s ease-in;
}

.overlay-enter-from {
  opacity: 0;
  backdrop-filter: blur(0px);
  -webkit-backdrop-filter: blur(0px);
}

.overlay-enter-from .loading-content {
  transform: scale(0.8) translateY(20px);
  opacity: 0;
}

.overlay-leave-to {
  opacity: 0;
  backdrop-filter: blur(0px);
  -webkit-backdrop-filter: blur(0px);
}

.overlay-leave-to .loading-content {
  transform: scale(0.8) translateY(-20px);
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .loading-content {
    margin: 20px;
    padding: 30px 20px;
    min-width: auto;
  }
  
  .loading-content-large {
    padding: 40px 30px;
    min-width: auto;
  }
  
  .loading-title {
    font-size: 1.2em;
  }
  
  .spinner-large {
    transform: scale(1.2);
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .loading-overlay {
    background: rgba(255, 255, 255, 0.95);
  }
  
  .loading-overlay-dark {
    background: rgba(0, 0, 0, 0.95);
  }
  
  .loading-content {
    border-width: 2px;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .spinner-ring,
  .spinner-simple,
  .spinner-emoji {
    animation: none;
  }
  
  .dot {
    animation: none;
    opacity: 0.8;
  }
  
  .pulse-ring {
    animation: none;
    opacity: 0.3;
  }
  
  .pattern-dot {
    animation: none;
    opacity: 0.2;
  }
  
  .overlay-enter-active,
  .overlay-leave-active {
    transition: opacity 0.2s ease;
  }
}
</style>
