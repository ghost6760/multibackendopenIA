<template>
  <div 
    class="stats-card"
    :class="[
      `stats-card-${type}`,
      { 
        'stats-card-highlight': highlight,
        'stats-card-loading': loading,
        'stats-card-clickable': clickable
      }
    ]"
    @click="handleClick"
  >
    <!-- Card Header -->
    <div class="stats-header">
      <div class="stats-icon">
        <span v-if="!loading">{{ icon }}</span>
        <div v-else class="loading-icon">⏳</div>
      </div>
      
      <div class="stats-actions" v-if="showActions">
        <button
          v-if="refreshable"
          @click.stop="$emit('refresh')"
          :disabled="loading"
          class="stats-action-btn"
          title="Actualizar"
        >
          <span v-if="loading">⏳</span>
          <span v-else>🔄</span>
        </button>
        
        <button
          v-if="expandable"
          @click.stop="toggleExpanded"
          class="stats-action-btn"
          :title="isExpanded ? 'Contraer' : 'Expandir'"
        >
          {{ isExpanded ? '▲' : '▼' }}
        </button>
      </div>
    </div>
    
    <!-- Card Content -->
    <div class="stats-content">
      <h3 class="stats-title">{{ title }}</h3>
      
      <div class="stats-value-section">
        <div class="stats-main-value" :class="{ 'loading': loading }">
          <span v-if="!loading" class="stats-value">{{ displayValue }}</span>
          <div v-else class="loading-placeholder">Cargando...</div>
        </div>
        
        <div v-if="subtitle && !loading" class="stats-subtitle">
          {{ subtitle }}
        </div>
        
        <div v-if="trend" class="stats-trend" :class="`trend-${trend.direction}`">
          <span class="trend-icon">{{ getTrendIcon(trend.direction) }}</span>
          <span class="trend-value">{{ trend.value }}</span>
          <span v-if="trend.period" class="trend-period">{{ trend.period }}</span>
        </div>
      </div>
      
      <!-- Progress bar (if applicable) -->
      <div v-if="progress !== null && !loading" class="stats-progress">
        <div class="progress-bar">
          <div 
            class="progress-fill"
            :style="{ width: `${Math.min(100, Math.max(0, progress))}%` }"
          ></div>
        </div>
        <div class="progress-label">
          {{ Math.round(progress) }}%
        </div>
      </div>
      
      <!-- Additional info -->
      <div v-if="additionalInfo && !loading" class="stats-additional">
        <div
          v-for="(info, index) in additionalInfo"
          :key="index"
          class="additional-item"
        >
          <span class="additional-label">{{ info.label }}:</span>
          <span class="additional-value">{{ info.value }}</span>
        </div>
      </div>
    </div>
    
    <!-- Expanded Content -->
    <Transition name="expanded-content">
      <div v-if="isExpanded && expandedContent" class="stats-expanded">
        <div class="expanded-header">
          <h4>Detalles</h4>
        </div>
        <div class="expanded-body">
          <!-- Slot for custom expanded content -->
          <slot name="expanded" :data="expandedContent">
            <div class="expanded-default">
              <pre>{{ formatExpandedContent(expandedContent) }}</pre>
            </div>
          </slot>
        </div>
      </div>
    </Transition>
    
    <!-- Status Indicator -->
    <div v-if="status" class="stats-status" :class="`status-${status}`">
      <span class="status-dot"></span>
    </div>
    
    <!-- Loading Overlay -->
    <div v-if="loading" class="stats-loading-overlay">
      <div class="loading-spinner">⏳</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  icon: {
    type: String,
    default: '📊'
  },
  type: {
    type: String,
    default: 'default', // 'default', 'success', 'warning', 'error', 'info'
    validator: (value) => ['default', 'success', 'warning', 'error', 'info'].includes(value)
  },
  subtitle: {
    type: String,
    default: ''
  },
  highlight: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  },
  refreshable: {
    type: Boolean,
    default: false
  },
  expandable: {
    type: Boolean,
    default: false
  },
  expandedContent: {
    type: [Object, Array, String],
    default: null
  },
  trend: {
    type: Object,
    default: null
    // Expected format: { direction: 'up'|'down'|'stable', value: '5%', period: 'vs último mes' }
  },
  progress: {
    type: Number,
    default: null, // 0-100
    validator: (value) => value === null || (value >= 0 && value <= 100)
  },
  additionalInfo: {
    type: Array,
    default: null
    // Expected format: [{ label: 'Label', value: 'Value' }]
  },
  status: {
    type: String,
    default: null, // 'online', 'offline', 'warning', 'error'
    validator: (value) => value === null || ['online', 'offline', 'warning', 'error'].includes(value)
  }
})

const emit = defineEmits(['click', 'refresh', 'expand', 'collapse'])

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isExpanded = ref(false)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    // Format numbers with appropriate separators
    if (props.value >= 1000000) {
      return (props.value / 1000000).toFixed(1) + 'M'
    } else if (props.value >= 1000) {
      return (props.value / 1000).toFixed(1) + 'K'
    }
    return props.value.toLocaleString()
  }
  return props.value
})

const showActions = computed(() => {
  return props.refreshable || props.expandable
})

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Handle card click
 */
const handleClick = () => {
  if (props.clickable && !props.loading) {
    emit('click')
  }
}

/**
 * Toggle expanded state
 */
const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
  
  if (isExpanded.value) {
    emit('expand')
  } else {
    emit('collapse')
  }
}

/**
 * Get trend icon based on direction
 */
const getTrendIcon = (direction) => {
  const icons = {
    'up': '📈',
    'down': '📉',
    'stable': '➡️'
  }
  return icons[direction] || '➡️'
}

/**
 * Format expanded content for display
 */
const formatExpandedContent = (content) => {
  if (typeof content === 'string') {
    return content
  }
  return JSON.stringify(content, null, 2)
}
</script>

<style scoped>
.stats-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  transition: all 0.3s ease;
  overflow: hidden;
}

.stats-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stats-card-clickable {
  cursor: pointer;
}

.stats-card-clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.stats-card-highlight {
  border-color: var(--warning-color);
  background: rgba(245, 158, 11, 0.05);
}

.stats-card-loading {
  opacity: 0.8;
  pointer-events: none;
}

/* Card Types */
.stats-card-success {
  border-left: 4px solid var(--success-color);
}

.stats-card-warning {
  border-left: 4px solid var(--warning-color);
}

.stats-card-error {
  border-left: 4px solid var(--danger-color);
}

.stats-card-info {
  border-left: 4px solid var(--info-color);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.stats-icon {
  font-size: 1.8em;
  min-width: 40px;
  text-align: center;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

.stats-actions {
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.stats-card:hover .stats-actions {
  opacity: 1;
}

.stats-action-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.stats-action-btn:hover:not(:disabled) {
  background: var(--bg-primary);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.stats-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stats-content {
  position: relative;
}

.stats-title {
  margin: 0 0 10px 0;
  font-size: 0.95em;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stats-value-section {
  margin-bottom: 15px;
}

.stats-main-value {
  margin-bottom: 8px;
}

.stats-value {
  font-size: 2.2em;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.loading-placeholder {
  font-size: 1.2em;
  color: var(--text-muted);
  animation: pulse 1.5s ease-in-out infinite;
}

.stats-subtitle {
  font-size: 0.9em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.stats-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85em;
  font-weight: 500;
}

.trend-up {
  color: var(--success-color);
}

.trend-down {
  color: var(--danger-color);
}

.trend-stable {
  color: var(--text-muted);
}

.trend-icon {
  font-size: 1.1em;
}

.trend-period {
  color: var(--text-muted);
  font-weight: normal;
}

.stats-progress {
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.3s ease;
  border-radius: 3px;
}

.progress-label {
  font-size: 0.8em;
  color: var(--text-secondary);
  text-align: right;
  font-weight: 500;
}

.stats-additional {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.additional-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85em;
}

.additional-label {
  color: var(--text-secondary);
}

.additional-value {
  color: var(--text-primary);
  font-weight: 500;
}

.stats-expanded {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.expanded-content-enter-active,
.expanded-content-leave-active {
  transition: all 0.3s ease;
  max-height: 300px;
  opacity: 1;
}

.expanded-content-enter-from,
.expanded-content-leave-to {
  max-height: 0;
  opacity: 0;
}

.expanded-header {
  margin-bottom: 12px;
}

.expanded-header h4 {
  margin: 0;
  font-size: 1em;
  font-weight: 600;
  color: var(--text-primary);
}

.expanded-body {
  max-height: 200px;
  overflow-y: auto;
}

.expanded-default pre {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  font-size: 0.8em;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.stats-status {
  position: absolute;
  top: 15px;
  right: 15px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  animation: pulse-status 2s infinite;
}

.status-online .status-dot {
  background: var(--success-color);
}

.status-offline .status-dot {
  background: var(--text-muted);
}

.status-warning .status-dot {
  background: var(--warning-color);
}

.status-error .status-dot {
  background: var(--danger-color);
}

.stats-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.loading-spinner {
  font-size: 1.5em;
  animation: spin 1s linear infinite;
}

/* Animations */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes pulse-status {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .stats-card {
    padding: 16px;
  }
  
  .stats-icon {
    font-size: 1.5em;
  }
  
  .stats-value {
    font-size: 1.8em;
  }
  
  .stats-title {
    font-size: 0.9em;
  }
  
  .additional-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  
  .stats-actions {
    opacity: 1; /* Always show on mobile */
  }
}

@media (max-width: 480px) {
  .stats-header {
    flex-direction: column;
    gap: 10px;
  }
  
  .stats-actions {
    align-self: flex-end;
  }
  
  .stats-value {
    font-size: 1.6em;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .stats-loading-overlay {
    background: rgba(0, 0, 0, 0.8);
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .stats-card {
    border-width: 2px;
  }
  
  .progress-bar {
    border: 1px solid var(--border-color);
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .stats-card {
    transition: none;
  }
  
  .stats-card-clickable:hover {
    transform: none;
  }
  
  .loading-icon,
  .loading-spinner {
    animation: none;
  }
  
  .pulse-status {
    animation: none;
  }
  
  .expanded-content-enter-active,
  .expanded-content-leave-active {
    transition: opacity 0.2s ease;
  }
}
</style>
