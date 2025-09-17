<template>
  <div class="system-info">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Cargando información del sistema...</p>
    </div>
    
    <!-- System Info Content -->
    <div v-else-if="systemInfo" class="system-info-content">
      <!-- Main Status -->
      <div class="status-section">
        <div class="status-indicator" :class="getStatusClass(systemInfo.status)">
          <span class="status-icon">{{ getStatusIcon(systemInfo.status) }}</span>
          <div class="status-text">
            <h4>{{ getStatusText(systemInfo.status) }}</h4>
            <p>{{ systemInfo.status_message || 'Sistema funcionando correctamente' }}</p>
          </div>
        </div>
      </div>
      
      <!-- System Details Grid -->
      <div class="details-grid">
        <!-- Version Info -->
        <div class="detail-card">
          <div class="detail-header">
            <span class="detail-icon">🚀</span>
            <h5>Versión del Sistema</h5>
          </div>
          <div class="detail-content">
            <div class="detail-item">
              <span class="detail-label">Versión:</span>
              <span class="detail-value">{{ systemInfo.version || '1.0.0' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Tipo:</span>
              <span class="detail-value">{{ systemInfo.system_type || 'multi-tenant-multi-agent' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Build:</span>
              <span class="detail-value">{{ systemInfo.build || 'latest' }}</span>
            </div>
          </div>
        </div>
        
        <!-- Environment Info -->
        <div class="detail-card">
          <div class="detail-header">
            <span class="detail-icon">🌍</span>
            <h5>Entorno</h5>
          </div>
          <div class="detail-content">
            <div class="detail-item">
              <span class="detail-label">Modo:</span>
              <span class="detail-value">{{ systemInfo.environment || 'production' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Región:</span>
              <span class="detail-value">{{ systemInfo.region || 'us-east-1' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Instancia:</span>
              <span class="detail-value">{{ systemInfo.instance_id || 'railway-001' }}</span>
            </div>
          </div>
        </div>
        
        <!-- Uptime & Performance -->
        <div class="detail-card">
          <div class="detail-header">
            <span class="detail-icon">⏰</span>
            <h5>Rendimiento</h5>
          </div>
          <div class="detail-content">
            <div class="detail-item">
              <span class="detail-label">Uptime:</span>
              <span class="detail-value">{{ formatUptime(systemInfo.uptime) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">CPU:</span>
              <span class="detail-value">{{ formatPercentage(systemInfo.cpu_usage) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Memoria:</span>
              <span class="detail-value">{{ formatMemory(systemInfo.memory_usage) }}</span>
            </div>
          </div>
        </div>
        
        <!-- Services Status -->
        <div class="detail-card">
          <div class="detail-header">
            <span class="detail-icon">🔧</span>
            <h5>Servicios</h5>
          </div>
          <div class="detail-content">
            <div class="services-status">
              <div
                v-for="service in getServices(systemInfo)"
                :key="service.name"
                class="service-item"
                :class="getServiceStatusClass(service.status)"
              >
                <span class="service-icon">{{ getServiceIcon(service.name) }}</span>
                <span class="service-name">{{ service.name }}</span>
                <span class="service-status">{{ service.status }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Additional Information -->
      <div v-if="systemInfo.additional_info" class="additional-info">
        <details class="additional-details">
          <summary>
            <span class="additional-icon">📋</span>
            Información Adicional
          </summary>
          <div class="additional-content">
            <pre>{{ formatAdditionalInfo(systemInfo.additional_info) }}</pre>
          </div>
        </details>
      </div>
      
      <!-- Last Updated -->
      <div class="last-updated">
        <small>
          🕒 Última actualización: {{ formatTimestamp(systemInfo.timestamp || Date.now()) }}
        </small>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else class="error-state">
      <div class="error-icon">❌</div>
      <h4>Error al cargar información del sistema</h4>
      <p>No se pudo obtener la información del estado del sistema.</p>
      <button @click="$emit('refresh')" class="retry-btn">
        🔄 Reintentar
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  systemInfo: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh'])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const systemStatus = computed(() => {
  return props.systemInfo?.status || 'unknown'
})

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Get status class for styling
 */
const getStatusClass = (status) => {
  const classMap = {
    'healthy': 'status-healthy',
    'warning': 'status-warning', 
    'error': 'status-error',
    'critical': 'status-critical',
    'maintenance': 'status-maintenance'
  }
  return classMap[status] || 'status-unknown'
}

/**
 * Get status icon
 */
const getStatusIcon = (status) => {
  const iconMap = {
    'healthy': '✅',
    'warning': '⚠️',
    'error': '❌',
    'critical': '🚨',
    'maintenance': '🔧'
  }
  return iconMap[status] || '❓'
}

/**
 * Get status text
 */
const getStatusText = (status) => {
  const textMap = {
    'healthy': 'Sistema Saludable',
    'warning': 'Advertencias Detectadas',
    'error': 'Errores Encontrados',
    'critical': 'Estado Crítico',
    'maintenance': 'En Mantenimiento'
  }
  return textMap[status] || 'Estado Desconocido'
}

/**
 * Get services from system info
 */
const getServices = (systemInfo) => {
  if (systemInfo.services) {
    return systemInfo.services
  }
  
  // Default services if not provided
  return [
    { name: 'API', status: systemInfo.api_status || 'healthy' },
    { name: 'Database', status: systemInfo.db_status || 'healthy' },
    { name: 'Redis', status: systemInfo.redis_status || 'healthy' },
    { name: 'OpenAI', status: systemInfo.openai_status || 'healthy' }
  ]
}

/**
 * Get service icon
 */
const getServiceIcon = (serviceName) => {
  const iconMap = {
    'API': '🌐',
    'Database': '🗄️',
    'Redis': '🔴',
    'OpenAI': '🤖',
    'Vectorstore': '📊',
    'Storage': '💾'
  }
  return iconMap[serviceName] || '⚙️'
}

/**
 * Get service status class
 */
const getServiceStatusClass = (status) => {
  const classMap = {
    'healthy': 'service-healthy',
    'warning': 'service-warning',
    'error': 'service-error',
    'offline': 'service-offline'
  }
  return classMap[status] || 'service-unknown'
}

/**
 * Format uptime
 */
const formatUptime = (uptime) => {
  if (!uptime) return 'Desconocido'
  
  if (typeof uptime === 'string') return uptime
  
  // Assume uptime is in seconds
  const days = Math.floor(uptime / 86400)
  const hours = Math.floor((uptime % 86400) / 3600)
  const minutes = Math.floor((uptime % 3600) / 60)
  
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

/**
 * Format percentage
 */
const formatPercentage = (value) => {
  if (value === null || value === undefined) return 'N/A'
  
  if (typeof value === 'string') return value
  
  return `${Math.round(value)}%`
}

/**
 * Format memory usage
 */
const formatMemory = (memory) => {
  if (!memory) return 'N/A'
  
  if (typeof memory === 'string') return memory
  
  if (typeof memory === 'object' && memory.used && memory.total) {
    const used = formatBytes(memory.used)
    const total = formatBytes(memory.total)
    const percentage = Math.round((memory.used / memory.total) * 100)
    return `${used} / ${total} (${percentage}%)`
  }
  
  if (typeof memory === 'number') {
    return formatBytes(memory)
  }
  
  return 'N/A'
}

/**
 * Format bytes to human readable format
 */
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Format additional info
 */
const formatAdditionalInfo = (info) => {
  if (typeof info === 'string') return info
  return JSON.stringify(info, null, 2)
}

/**
 * Format timestamp
 */
const formatTimestamp = (timestamp) => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}
</script>

<style scoped>
.system-info {
  width: 100%;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.system-info-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-section {
  padding: 20px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-icon {
  font-size: 2em;
  min-width: 50px;
  text-align: center;
}

.status-text h4 {
  margin: 0 0 5px 0;
  font-size: 1.2em;
  color: var(--text-primary);
}

.status-text p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* Status Classes */
.status-healthy {
  border-left: 4px solid var(--success-color);
  background: rgba(34, 197, 94, 0.05);
}

.status-warning {
  border-left: 4px solid var(--warning-color);
  background: rgba(245, 158, 11, 0.05);
}

.status-error {
  border-left: 4px solid var(--danger-color);
  background: rgba(239, 68, 68, 0.05);
}

.status-critical {
  border-left: 4px solid var(--danger-color);
  background: rgba(239, 68, 68, 0.1);
  animation: pulse-critical 2s infinite;
}

.status-maintenance {
  border-left: 4px solid var(--info-color);
  background: rgba(59, 130, 246, 0.05);
}

.status-unknown {
  border-left: 4px solid var(--text-muted);
  background: rgba(156, 163, 175, 0.05);
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.detail-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.detail-icon {
  font-size: 1.2em;
}

.detail-header h5 {
  margin: 0;
  font-size: 1em;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.detail-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.detail-value {
  color: var(--text-primary);
  font-weight: 600;
}

.services-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.service-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

.service-icon {
  font-size: 1em;
  min-width: 20px;
  text-align: center;
}

.service-name {
  flex: 1;
  color: var(--text-primary);
  font-weight: 500;
}

.service-status {
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Service Status Classes */
.service-healthy {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.service-healthy .service-status {
  color: var(--success-color);
}

.service-warning {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.service-warning .service-status {
  color: var(--warning-color);
}

.service-error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.service-error .service-status {
  color: var(--danger-color);
}

.service-offline {
  background: rgba(156, 163, 175, 0.1);
  border: 1px solid rgba(156, 163, 175, 0.2);
  opacity: 0.7;
}

.service-offline .service-status {
  color: var(--text-muted);
}

.additional-info {
  margin-top: 20px;
}

.additional-details {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
}

.additional-details summary {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
  list-style: none;
}

.additional-details summary::-webkit-details-marker {
  display: none;
}

.additional-details[open] summary::after {
  content: '▲';
  margin-left: auto;
}

.additional-details:not([open]) summary::after {
  content: '▼';
  margin-left: auto;
}

.additional-icon {
  font-size: 1.1em;
}

.additional-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.additional-content pre {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  font-size: 0.8em;
  color: var(--text-secondary);
  margin: 0;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.last-updated {
  text-align: center;
  padding: 12px;
  color: var(--text-muted);
  font-size: 0.85em;
  border-top: 1px solid var(--border-light);
}

.error-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.error-icon {
  font-size: 3em;
  margin-bottom: 15px;
}

.error-state h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.error-state p {
  margin: 0 0 20px 0;
  line-height: 1.4;
}

.retry-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.retry-btn:hover {
  background: var(--primary-color-dark);
}

/* Animations */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-critical {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .details-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .status-indicator {
    flex-direction: column;
    text-align: center;
    gap: 10px;
  }
  
  .detail-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .service-item {
    flex-wrap: wrap;
    gap: 6px;
  }
}

@media (max-width: 480px) {
  .detail-card {
    padding: 12px;
  }
  
  .status-section {
    padding: 16px;
  }
  
  .status-icon {
    font-size: 1.5em;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner {
    animation: none;
  }
  
  .pulse-critical {
    animation: none;
  }
}
</style>
