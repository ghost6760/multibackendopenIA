<template>
  <div class="system-log-container" :class="{ 'log-collapsed': isCollapsed }">
    <!-- Log Header -->
    <div class="log-header" @click="toggleCollapse">
      <div class="log-title">
        <span class="log-icon">📋</span>
        <h4>Registro del Sistema</h4>
        <span class="log-count">({{ logEntries.length }})</span>
      </div>
      
      <div class="log-header-actions">
        <!-- Status indicators -->
        <div class="status-indicators">
          <span v-if="errorCount > 0" class="status-indicator error" :title="`${errorCount} errores`">
            ❌ {{ errorCount }}
          </span>
          <span v-if="warningCount > 0" class="status-indicator warning" :title="`${warningCount} advertencias`">
            ⚠️ {{ warningCount }}
          </span>
          <span class="status-indicator info" :title="`${infoCount} mensajes informativos`">
            ℹ️ {{ infoCount }}
          </span>
        </div>
        
        <!-- Controls -->
        <div class="log-controls">
          <button 
            @click.stop="toggleAutoScroll" 
            :class="['control-btn', { 'active': autoScroll }]"
            title="Auto-scroll"
          >
            {{ autoScroll ? '📌' : '📌' }}
          </button>
          
          <button 
            @click.stop="clearLog" 
            class="control-btn clear-btn"
            title="Limpiar log"
          >
            🗑️
          </button>
          
          <button 
            @click.stop="exportLog" 
            class="control-btn"
            title="Exportar log"
          >
            📥
          </button>
        </div>
        
        <!-- Collapse button -->
        <button class="collapse-btn" :title="isCollapsed ? 'Expandir' : 'Colapsar'">
          {{ isCollapsed ? '▲' : '▼' }}
        </button>
      </div>
    </div>
    
    <!-- Log Content -->
    <Transition name="log-content">
      <div v-show="!isCollapsed" class="log-content">
        <!-- Filters -->
        <div class="log-filters">
          <div class="filter-group">
            <label>Filtrar por nivel:</label>
            <div class="level-filters">
              <button
                v-for="level in availableLevels"
                :key="level"
                @click="toggleLevelFilter(level)"
                :class="['level-filter', level, { 'active': activeLevels.includes(level) }]"
              >
                {{ getLevelIcon(level) }} {{ level.toUpperCase() }}
              </button>
            </div>
          </div>
          
          <div class="filter-group">
            <label for="logSearch">Buscar en logs:</label>
            <input
              id="logSearch"
              v-model="searchQuery"
              type="text"
              placeholder="Buscar mensaje..."
              class="search-input"
            >
          </div>
          
          <div class="filter-group">
            <label>Tiempo:</label>
            <select v-model="timeFilter" class="time-filter">
              <option value="all">Todo el tiempo</option>
              <option value="last-hour">Última hora</option>
              <option value="last-day">Último día</option>
              <option value="current-session">Sesión actual</option>
            </select>
          </div>
        </div>
        
        <!-- Log Entries -->
        <div 
          ref="logContainer"
          class="log-entries" 
          :class="{ 'auto-scroll': autoScroll }"
          @scroll="handleScroll"
        >
          <div
            v-for="(entry, index) in filteredEntries"
            :key="entry.id || index"
            :class="['log-entry', `level-${entry.level}`, { 'log-entry-new': isNewEntry(entry) }]"
            @click="selectEntry(entry)"
          >
            <!-- Entry header -->
            <div class="entry-header">
              <span class="entry-timestamp">
                {{ formatTimestamp(entry.timestamp) }}
              </span>
              <span :class="['entry-level', `level-${entry.level}`]">
                {{ getLevelIcon(entry.level) }} [{{ entry.level.toUpperCase() }}]
              </span>
              <span v-if="entry.source" class="entry-source">
                🏷️ {{ entry.source }}
              </span>
            </div>
            
            <!-- Entry message -->
            <div class="entry-message">
              <span v-html="highlightSearch(entry.message)"></span>
            </div>
            
            <!-- Entry details (if available) -->
            <div v-if="entry.details" class="entry-details">
              <details>
                <summary>Ver detalles</summary>
                <pre>{{ formatDetails(entry.details) }}</pre>
              </details>
            </div>
            
            <!-- Entry actions -->
            <div class="entry-actions">
              <button @click.stop="copyEntry(entry)" class="entry-action" title="Copiar">
                📋
              </button>
              <button 
                v-if="entry.level === 'error'" 
                @click.stop="reportError(entry)" 
                class="entry-action" 
                title="Reportar error"
              >
                🚨
              </button>
            </div>
          </div>
          
          <!-- Empty state -->
          <div v-if="filteredEntries.length === 0" class="log-empty">
            <div class="empty-icon">📝</div>
            <h4>No hay entradas de log</h4>
            <p v-if="hasActiveFilters">
              No se encontraron entradas que coincidan con los filtros activos.
            </p>
            <p v-else>
              Las entradas del registro del sistema aparecerán aquí.
            </p>
            <button v-if="hasActiveFilters" @click="clearFilters" class="btn-outline">
              🗑️ Limpiar filtros
            </button>
          </div>
        </div>
        
        <!-- Log Stats -->
        <div class="log-stats">
          <div class="stats-group">
            <span class="stat">
              📊 Mostrando {{ filteredEntries.length }} de {{ logEntries.length }}
            </span>
            <span v-if="lastEntry" class="stat">
              🕒 Última entrada: {{ formatTimestamp(lastEntry.timestamp) }}
            </span>
          </div>
          
          <div class="stats-actions">
            <button @click="scrollToTop" class="stats-btn" title="Ir al inicio">
              ⬆️ Inicio
            </button>
            <button @click="scrollToBottom" class="stats-btn" title="Ir al final">
              ⬇️ Final
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS
// ============================================================================

const props = defineProps({
  maxEntries: {
    type: Number,
    default: 100
  },
  autoScrollDefault: {
    type: Boolean,
    default: true
  },
  collapsedDefault: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isCollapsed = ref(props.collapsedDefault)
const autoScroll = ref(props.autoScrollDefault)
const searchQuery = ref('')
const timeFilter = ref('all')
const activeLevels = ref(['info', 'warning', 'error'])
const selectedEntry = ref(null)
const logContainer = ref(null)
const newEntryIds = ref(new Set())

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const logEntries = computed(() => appStore.systemLog)

const availableLevels = computed(() => {
  const levels = new Set(logEntries.value.map(entry => entry.level))
  return Array.from(levels).sort()
})

const errorCount = computed(() => 
  logEntries.value.filter(entry => entry.level === 'error').length
)

const warningCount = computed(() => 
  logEntries.value.filter(entry => entry.level === 'warning').length
)

const infoCount = computed(() => 
  logEntries.value.filter(entry => entry.level === 'info').length
)

const lastEntry = computed(() => {
  return logEntries.value[logEntries.value.length - 1]
})

const filteredEntries = computed(() => {
  let entries = logEntries.value

  // Filter by level
  entries = entries.filter(entry => activeLevels.value.includes(entry.level))

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    entries = entries.filter(entry => 
      entry.message.toLowerCase().includes(query) ||
      entry.level.toLowerCase().includes(query)
    )
  }

  // Filter by time
  if (timeFilter.value !== 'all') {
    const now = Date.now()
    const cutoff = {
      'last-hour': now - (60 * 60 * 1000),
      'last-day': now - (24 * 60 * 60 * 1000),
      'current-session': appStore.sessionStartTime || now - (60 * 60 * 1000)
    }[timeFilter.value]

    entries = entries.filter(entry => {
      const entryTime = new Date(entry.timestamp).getTime()
      return entryTime >= cutoff
    })
  }

  return entries
})

const hasActiveFilters = computed(() => {
  return searchQuery.value.trim() !== '' || 
         timeFilter.value !== 'all' || 
         activeLevels.value.length !== availableLevels.value.length
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Toggle collapse state
 */
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  
  if (!isCollapsed.value) {
    nextTick(() => {
      if (autoScroll.value) {
        scrollToBottom()
      }
    })
  }
}

/**
 * Toggle auto scroll
 */
const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
  
  if (autoScroll.value) {
    nextTick(() => scrollToBottom())
  }
  
  showNotification(
    `Auto-scroll ${autoScroll.value ? 'activado' : 'desactivado'}`, 
    'info', 
    2000
  )
}

/**
 * Clear log
 */
const clearLog = () => {
  if (confirm('¿Estás seguro de que quieres limpiar el registro del sistema?')) {
    appStore.clearSystemLog()
    newEntryIds.value.clear()
    selectedEntry.value = null
    showNotification('✅ Registro del sistema limpiado', 'success')
  }
}

/**
 * Export log
 */
const exportLog = () => {
  try {
    const logData = {
      timestamp: new Date().toISOString(),
      total_entries: logEntries.value.length,
      exported_entries: filteredEntries.value.length,
      filters: {
        levels: activeLevels.value,
        search: searchQuery.value,
        time: timeFilter.value
      },
      entries: filteredEntries.value
    }
    
    const blob = new Blob([JSON.stringify(logData, null, 2)], { 
      type: 'application/json' 
    })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `system_log_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification('✅ Log exportado correctamente', 'success')
    appStore.addToLog('System log exported', 'info')
    
  } catch (error) {
    console.error('Error exporting log:', error)
    showNotification('❌ Error al exportar el log', 'error')
  }
}

/**
 * Toggle level filter
 */
const toggleLevelFilter = (level) => {
  const index = activeLevels.value.indexOf(level)
  if (index > -1) {
    activeLevels.value.splice(index, 1)
  } else {
    activeLevels.value.push(level)
  }
}

/**
 * Clear all filters
 */
const clearFilters = () => {
  searchQuery.value = ''
  timeFilter.value = 'all'
  activeLevels.value = [...availableLevels.value]
  showNotification('Filtros limpiados', 'info', 2000)
}

/**
 * Select log entry
 */
const selectEntry = (entry) => {
  selectedEntry.value = selectedEntry.value === entry ? null : entry
}

/**
 * Copy entry to clipboard
 */
const copyEntry = async (entry) => {
  try {
    const text = `[${entry.timestamp}] [${entry.level.toUpperCase()}] ${entry.message}`
    await navigator.clipboard.writeText(text)
    showNotification('📋 Entrada copiada al portapapeles', 'success', 2000)
  } catch (error) {
    console.error('Error copying entry:', error)
    showNotification('❌ Error al copiar', 'error')
  }
}

/**
 * Report error entry
 */
const reportError = (entry) => {
  const errorReport = {
    timestamp: entry.timestamp,
    message: entry.message,
    level: entry.level,
    details: entry.details,
    userAgent: navigator.userAgent,
    url: window.location.href
  }
  
  console.warn('Error report:', errorReport)
  showNotification('🚨 Error reportado para análisis', 'warning')
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Get level icon
 */
const getLevelIcon = (level) => {
  const icons = {
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'debug': '🐛',
    'success': '✅'
  }
  return icons[level] || 'ℹ️'
}

/**
 * Format timestamp
 */
const formatTimestamp = (timestamp) => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('es-ES', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timestamp
  }
}

/**
 * Format details object
 */
const formatDetails = (details) => {
  if (typeof details === 'string') return details
  return JSON.stringify(details, null, 2)
}

/**
 * Highlight search terms
 */
const highlightSearch = (text) => {
  if (!searchQuery.value.trim()) return escapeHTML(text)
  
  const query = searchQuery.value.trim()
  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi')
  
  return escapeHTML(text).replace(regex, '<mark class="search-highlight">$1</mark>')
}

/**
 * Escape HTML
 */
const escapeHTML = (text) => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Escape RegExp
 */
const escapeRegExp = (string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Check if entry is new
 */
const isNewEntry = (entry) => {
  return newEntryIds.value.has(entry.id)
}

/**
 * Scroll to top
 */
const scrollToTop = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = 0
  }
}

/**
 * Scroll to bottom
 */
const scrollToBottom = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

/**
 * Handle scroll events
 */
const handleScroll = () => {
  if (!logContainer.value || !autoScroll.value) return
  
  const { scrollTop, scrollHeight, clientHeight } = logContainer.value
  const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10
  
  if (!isAtBottom) {
    autoScroll.value = false
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Auto-scroll to bottom on mount
  if (autoScroll.value && !isCollapsed.value) {
    nextTick(() => scrollToBottom())
  }
  
  appStore.addToLog('SystemLog component mounted', 'info')
})

onUnmounted(() => {
  newEntryIds.value.clear()
})

// ============================================================================
// WATCHERS
// ============================================================================

// Watch for new log entries
watch(() => logEntries.value.length, (newLength, oldLength) => {
  if (newLength > oldLength) {
    // Mark new entries
    const newEntries = logEntries.value.slice(oldLength)
    newEntries.forEach(entry => {
      if (entry.id) {
        newEntryIds.value.add(entry.id)
      }
    })
    
    // Auto-scroll if enabled and not collapsed
    if (autoScroll.value && !isCollapsed.value) {
      nextTick(() => scrollToBottom())
    }
    
    // Remove new entry markers after 3 seconds
    setTimeout(() => {
      newEntries.forEach(entry => {
        if (entry.id) {
          newEntryIds.value.delete(entry.id)
        }
      })
    }, 3000)
  }
})

// Auto-scroll when auto-scroll is enabled
watch(autoScroll, (enabled) => {
  if (enabled && !isCollapsed.value) {
    nextTick(() => scrollToBottom())
  }
})
</script>

<style scoped>
.system-log-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-top: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.log-collapsed {
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
  flex-wrap: wrap;
  gap: 10px;
}

.log-header:hover {
  background: var(--bg-secondary);
}

.log-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
}

.log-title h4 {
  margin: 0;
  font-size: 1em;
}

.log-count {
  color: var(--text-muted);
  font-size: 0.9em;
  font-weight: normal;
}

.log-header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-indicators {
  display: flex;
  gap: 8px;
}

.status-indicator {
  font-size: 0.8em;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.status-indicator.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.status-indicator.warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.status-indicator.info {
  background: rgba(59, 130, 246, 0.1);
  color: var(--info-color);
}

.log-controls {
  display: flex;
  gap: 4px;
}

.control-btn {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.control-btn.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.clear-btn:hover {
  background: var(--danger-color);
  border-color: var(--danger-color);
  color: white;
}

.collapse-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: color 0.2s ease;
}

.collapse-btn:hover {
  color: var(--text-primary);
}

.log-content {
  padding: 16px;
}

.log-content-enter-active,
.log-content-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  opacity: 1;
}

.log-content-enter-from,
.log-content-leave-to {
  max-height: 0;
  opacity: 0;
  padding: 0 16px;
}

.log-filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  font-size: 0.9em;
  font-weight: 500;
  color: var(--text-primary);
}

.level-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.level-filter {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
  transition: all 0.2s ease;
}

.level-filter:hover {
  background: var(--bg-primary);
}

.level-filter.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.level-filter.error.active {
  background: var(--danger-color);
  border-color: var(--danger-color);
}

.level-filter.warning.active {
  background: var(--warning-color);
  border-color: var(--warning-color);
}

.search-input,
.time-filter {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9em;
}

.search-input:focus,
.time-filter:focus {
  outline: none;
  border-color: var(--primary-color);
}

.log-entries {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
}

.log-entry {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}

.log-entry:hover {
  background: var(--bg-tertiary);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry-new {
  animation: highlight-new 3s ease-out;
}

.log-entry.level-error {
  border-left: 3px solid var(--danger-color);
}

.log-entry.level-warning {
  border-left: 3px solid var(--warning-color);
}

.log-entry.level-info {
  border-left: 3px solid var(--info-color);
}

.entry-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 4px;
  font-size: 0.8em;
  flex-wrap: wrap;
}

.entry-timestamp {
  color: var(--text-muted);
  font-family: monospace;
  min-width: 70px;
}

.entry-level {
  font-weight: 600;
  min-width: 80px;
}

.entry-level.level-error {
  color: var(--danger-color);
}

.entry-level.level-warning {
  color: var(--warning-color);
}

.entry-level.level-info {
  color: var(--info-color);
}

.entry-source {
  color: var(--text-secondary);
  font-size: 0.9em;
}

.entry-message {
  color: var(--text-primary);
  line-height: 1.4;
  word-wrap: break-word;
}

.entry-details {
  margin-top: 8px;
}

.entry-details summary {
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.9em;
}

.entry-details pre {
  background: var(--bg-tertiary);
  padding: 8px;
  border-radius: 4px;
  font-size: 0.8em;
  overflow-x: auto;
  margin-top: 4px;
}

.entry-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.log-entry:hover .entry-actions {
  opacity: 1;
}

.entry-action {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8em;
  transition: all 0.2s ease;
}

.entry-action:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

:deep(.search-highlight) {
  background: #ffeb3b;
  color: #000;
  padding: 1px 2px;
  border-radius: 2px;
}

.log-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 2em;
  margin-bottom: 10px;
  opacity: 0.5;
}

.log-empty h4 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.log-empty p {
  margin: 0 0 15px 0;
  line-height: 1.4;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--primary-color);
  color: var(--primary-color);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-outline:hover {
  background: var(--primary-color);
  color: white;
}

.log-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  font-size: 0.8em;
  color: var(--text-secondary);
  flex-wrap: wrap;
  gap: 10px;
}

.stats-group {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.stats-actions {
  display: flex;
  gap: 6px;
}

.stats-btn {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
  transition: all 0.2s ease;
}

.stats-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

@keyframes highlight-new {
  0% {
    background: rgba(102, 126, 234, 0.3);
  }
  100% {
    background: transparent;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .log-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .log-header-actions {
    justify-content: space-between;
  }
  
  .log-filters {
    gap: 8px;
  }
  
  .level-filters {
    gap: 4px;
  }
  
  .entry-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .entry-actions {
    position: static;
    opacity: 1;
    margin-top: 8px;
    justify-content: flex-end;
  }
  
  .log-stats {
    flex-direction: column;
    align-items: stretch;
  }
  
  .stats-actions {
    justify-content: center;
  }
}
</style>
