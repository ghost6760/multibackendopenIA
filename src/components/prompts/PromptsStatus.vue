<template>
  <div class="prompts-status-container">
    <!-- Header -->
    <div class="status-header">
      <h3>🤖 Estado del Sistema de Prompts</h3>
      <div class="status-actions">
        <button 
          @click="refreshStatus"
          class="btn-refresh"
          :disabled="isLoading"
          title="Actualizar estado"
        >
          <span v-if="isLoading">⏳</span>
          <span v-else>🔄</span>
          Actualizar
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !systemStatus" class="loading-section">
      <div class="loading-spinner"></div>
      <p>Cargando estado del sistema...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-section">
      <h4>❌ Error cargando estado</h4>
      <p>{{ error }}</p>
      <button @click="refreshStatus" class="btn-retry">🔄 Reintentar</button>
    </div>

    <!-- Main Status Display -->
    <div v-else-if="systemStatus" class="status-content">
      
      <!-- Database Status -->
      <div class="status-card database-status" :class="databaseStatusClass">
        <div class="status-card-header">
          <h4>🗄️ Estado de Base de Datos</h4>
          <div class="status-indicator" :class="databaseStatusClass">
            <span class="status-dot"></span>
            <span class="status-text">{{ databaseStatusText }}</span>
          </div>
        </div>
        
        <div class="status-card-body">
          <!-- PostgreSQL Status -->
          <div class="status-detail">
            <span class="detail-label">PostgreSQL:</span>
            <span class="detail-value" :class="{ 'success': systemStatus.postgresql_available, 'error': !systemStatus.postgresql_available }">
              {{ systemStatus.postgresql_available ? '✅ Disponible' : '❌ No disponible' }}
            </span>
          </div>
          
          <!-- Tables Status -->
          <div class="status-detail" v-if="systemStatus.postgresql_available">
            <span class="detail-label">Tablas:</span>
            <span class="detail-value" :class="{ 'success': systemStatus.tables_exist, 'warning': !systemStatus.tables_exist }">
              {{ systemStatus.tables_exist ? '✅ Creadas' : '⚠️ No creadas' }}
            </span>
          </div>
          
          <!-- Fallback Status -->
          <div class="status-detail" v-if="systemStatus.fallback_active">
            <span class="detail-label">Modo Fallback:</span>
            <span class="detail-value warning">
              ⚠️ Activo ({{ systemStatus.fallback_used || systemStatus.fallback_active }})
            </span>
          </div>
          
          <!-- Custom Prompts Count -->
          <div class="status-detail" v-if="systemStatus.total_custom_prompts !== undefined">
            <span class="detail-label">Prompts Personalizados:</span>
            <span class="detail-value">{{ systemStatus.total_custom_prompts || 0 }}</span>
          </div>
          
          <!-- Migration Button -->
          <div v-if="showMigrationButton" class="migration-section">
            <button 
              @click="migrateToPostgreSQL"
              class="btn-migrate"
              :disabled="isMigrating"
            >
              <span v-if="isMigrating">⏳ Migrando...</span>
              <span v-else">🚀 Migrar a PostgreSQL</span>
            </button>
            <p class="migration-help">Crea las tablas necesarias en PostgreSQL</p>
          </div>
        </div>
      </div>

      <!-- Performance Metrics -->
      <div v-if="systemStatus.metrics" class="status-card performance-metrics">
        <div class="status-card-header">
          <h4>📊 Métricas de Rendimiento</h4>
        </div>
        
        <div class="status-card-body">
          <div class="metrics-grid">
            <div v-if="systemStatus.metrics.avg_response_time" class="metric-item">
              <span class="metric-label">Tiempo promedio:</span>
              <span class="metric-value">{{ systemStatus.metrics.avg_response_time }}ms</span>
            </div>
            
            <div v-if="systemStatus.metrics.total_requests" class="metric-item">
              <span class="metric-label">Total requests:</span>
              <span class="metric-value">{{ systemStatus.metrics.total_requests }}</span>
            </div>
            
            <div v-if="systemStatus.metrics.cache_hit_rate" class="metric-item">
              <span class="metric-label">Cache hit rate:</span>
              <span class="metric-value">{{ systemStatus.metrics.cache_hit_rate }}%</span>
            </div>
            
            <div v-if="systemStatus.metrics.error_rate" class="metric-item">
              <span class="metric-label">Error rate:</span>
              <span class="metric-value" :class="{ 'error': systemStatus.metrics.error_rate > 5 }">
                {{ systemStatus.metrics.error_rate }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- System Health -->
      <div class="status-card system-health">
        <div class="status-card-header">
          <h4>🏥 Salud del Sistema</h4>
        </div>
        
        <div class="status-card-body">
          <div class="health-grid">
            <!-- API Status -->
            <div class="health-item">
              <span class="health-label">API:</span>
              <span class="health-value success">✅ Operativo</span>
            </div>
            
            <!-- Agents Status -->
            <div class="health-item" v-if="systemStatus.agents_status">
              <span class="health-label">Agentes:</span>
              <span class="health-value" :class="getAgentsStatusClass()">
                {{ getAgentsStatusText() }}
              </span>
            </div>
            
            <!-- Last Update -->
            <div class="health-item" v-if="systemStatus.last_updated">
              <span class="health-label">Última actualización:</span>
              <span class="health-value">{{ formatDateTime(systemStatus.last_updated) }}</span>
            </div>
            
            <!-- Uptime -->
            <div class="health-item" v-if="systemStatus.uptime">
              <span class="health-label">Uptime:</span>
              <span class="health-value">{{ formatUptime(systemStatus.uptime) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- System Tools -->
      <div class="status-card system-tools">
        <div class="status-card-header">
          <h4>🔧 Herramientas del Sistema</h4>
        </div>
        
        <div class="status-card-body">
          <div class="tools-grid">
            <button 
              @click="repairAllPrompts"
              class="tool-button repair-btn"
              :disabled="isProcessing"
            >
              <span v-if="isProcessing">⏳ Reparando...</span>
              <span v-else>🔧 Reparar Todos los Prompts</span>
            </button>
            
            <button 
              @click="validatePrompts"
              class="tool-button validate-btn"
              :disabled="isProcessing"
            >
              <span v-if="isProcessing">⏳ Validando...</span>
              <span v-else>✅ Validar Prompts</span>
            </button>
            
            <button 
              @click="optimizeDatabase"
              class="tool-button optimize-btn"
              :disabled="isProcessing || !systemStatus.postgresql_available"
            >
              <span v-if="isProcessing">⏳ Optimizando...</span>
              <span v-else>⚡ Optimizar BD</span>
            </button>
            
            <button 
              @click="exportSystemReport"
              class="tool-button export-btn"
              :disabled="isProcessing"
            >
              <span v-if="isProcessing">⏳ Exportando...</span>
              <span v-else">📄 Exportar Reporte</span>
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Last Updated Info -->
    <div v-if="lastUpdated" class="status-footer">
      <small>Última actualización: {{ formatDateTime(lastUpdated) }}</small>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const systemStatus = ref(null)
const isLoading = ref(false)
const isMigrating = ref(false)
const isProcessing = ref(false)
const error = ref(null)
const lastUpdated = ref(null)
const refreshInterval = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const databaseStatusClass = computed(() => {
  if (!systemStatus.value) return 'unknown'
  
  const { postgresql_available, tables_exist, fallback_active } = systemStatus.value
  
  if (postgresql_available && tables_exist && !fallback_active) {
    return 'success'
  } else if (postgresql_available && !tables_exist) {
    return 'warning'
  } else if (fallback_active) {
    return 'warning'
  } else {
    return 'error'
  }
})

const databaseStatusText = computed(() => {
  if (!systemStatus.value) return 'Desconocido'
  
  const { postgresql_available, tables_exist, fallback_active, total_custom_prompts } = systemStatus.value
  
  if (postgresql_available && tables_exist && !fallback_active) {
    return `✅ PostgreSQL Activo (${total_custom_prompts || 0} prompts personalizados)`
  } else if (postgresql_available && !tables_exist) {
    return '⚠️ PostgreSQL disponible - Tablas no creadas'
  } else if (fallback_active) {
    return `⚠️ Modo Fallback Activo (${systemStatus.value.fallback_used || fallback_active})`
  } else {
    return '❌ Sistema de prompts no disponible'
  }
})

const showMigrationButton = computed(() => {
  if (!systemStatus.value) return false
  return systemStatus.value.postgresql_available && !systemStatus.value.tables_exist
})

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DEL SCRIPT.JS - ENDPOINTS CORREGIDOS
// ============================================================================

/**
 * Carga el estado del sistema - CORREGIDO: usar /api/admin/status como script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadSystemStatus = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    appStore.addToLog('Loading prompts system status', 'info')
    
    // ✅ CORRECCIÓN: Usar el endpoint correcto como en script.js
    const response = await apiRequest('/api/admin/status')
    
    // ✅ CORRECCIÓN: Extraer prompt_system como hace script.js
    systemStatus.value = response.prompt_system || response
    lastUpdated.value = new Date().toISOString()
    
    appStore.addToLog('Prompts system status loaded successfully', 'info')
    
  } catch (error) {
    appStore.addToLog(`Error loading prompts system status: ${error.message}`, 'error')
    error.value = error.message
    systemStatus.value = null
  } finally {
    isLoading.value = false
  }
}

/**
 * Migra a PostgreSQL - MIGRADO: migratePromptsToPostgreSQL() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const migrateToPostgreSQL = async () => {
  if (!confirm('¿Estás seguro de migrar el sistema de prompts a PostgreSQL? Esta operación puede tardar unos minutos.')) {
    return
  }
  
  isMigrating.value = true
  
  try {
    appStore.addToLog('Starting prompts migration to PostgreSQL', 'info')
    
    // ✅ CORRECCIÓN: Usar endpoint correcto como script.js
    const response = await apiRequest('/api/admin/prompts/migrate', {
      method: 'POST',
      body: {
        force: false
      }
    })
    
    showNotification('Migración completada exitosamente', 'success')
    appStore.addToLog('Prompts migration completed successfully', 'info')
    
    // Recargar estado después de la migración
    await loadSystemStatus()
    
  } catch (error) {
    appStore.addToLog(`Error during prompts migration: ${error.message}`, 'error')
    showNotification('Error durante la migración: ' + error.message, 'error')
  } finally {
    isMigrating.value = false
  }
}

/**
 * Actualizar estado - MIGRADO: updateSystemStatusDisplay() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const refreshStatus = async () => {
  await loadSystemStatus()
}

// ============================================================================
// HERRAMIENTAS DEL SISTEMA
// ============================================================================

const repairAllPrompts = async () => {
  if (!confirm('¿Reparar todos los prompts desde el repositorio? Esta operación sobrescribirá prompts corruptos.')) {
    return
  }
  
  isProcessing.value = true
  
  try {
    appStore.addToLog('Starting repair of all prompts', 'info')
    
    const response = await apiRequest('/api/admin/prompts/repair', {
      method: 'POST',
      body: {
        company_id: appStore.currentCompanyId,
        repair_all: true
      }
    })
    
    showNotification(`Reparación completada: ${response.repaired_count || 0} prompts reparados`, 'success')
    
    // Recargar estado
    await loadSystemStatus()
    
  } catch (error) {
    showNotification('Error reparando prompts: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

const validatePrompts = async () => {
  isProcessing.value = true
  
  try {
    const response = await apiRequest('/api/admin/prompts/validate', {
      method: 'POST'
    })
    
    const { valid, invalid, total } = response
    showNotification(`Validación completada: ${valid}/${total} prompts válidos`, valid === total ? 'success' : 'warning')
    
    if (invalid > 0) {
      appStore.addToLog(`Found ${invalid} invalid prompts`, 'warning')
    }
    
  } catch (error) {
    showNotification('Error validando prompts: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

const optimizeDatabase = async () => {
  if (!confirm('¿Optimizar la base de datos? Esta operación puede tardar unos minutos.')) {
    return
  }
  
  isProcessing.value = true
  
  try {
    const response = await apiRequest('/api/admin/prompts/optimize', {
      method: 'POST'
    })
    
    showNotification('Base de datos optimizada exitosamente', 'success')
    
    // Recargar estado
    await loadSystemStatus()
    
  } catch (error) {
    showNotification('Error optimizando base de datos: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

const exportSystemReport = async () => {
  isProcessing.value = true
  
  try {
    const reportData = {
      timestamp: new Date().toISOString(),
      system_status: systemStatus.value,
      company_id: appStore.currentCompanyId,
      user_agent: navigator.userAgent,
      app_version: '1.0.0'
    }
    
    const dataStr = JSON.stringify(reportData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `prompts_system_report_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    showNotification('Reporte exportado exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando reporte', 'error')
  } finally {
    isProcessing.value = false
  }
}

// ============================================================================
// FUNCIONES DE UTILIDADES
// ============================================================================

const getAgentsStatusClass = () => {
  if (!systemStatus.value?.agents_status) return ''
  
  const { active, total } = systemStatus.value.agents_status
  const ratio = active / total
  
  if (ratio === 1) return 'success'
  if (ratio >= 0.8) return 'warning'
  return 'error'
}

const getAgentsStatusText = () => {
  if (!systemStatus.value?.agents_status) return 'N/A'
  
  const { active, total } = systemStatus.value.agents_status
  return `${active}/${total} activos`
}

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatUptime = (uptime) => {
  if (!uptime) return 'N/A'
  
  const days = Math.floor(uptime / (24 * 60 * 60))
  const hours = Math.floor((uptime % (24 * 60 * 60)) / (60 * 60))
  const minutes = Math.floor((uptime % (60 * 60)) / 60)
  
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('PromptsStatus component mounted', 'info')
  
  // Cargar estado inicial
  await loadSystemStatus()
  
  // Configurar actualización automática cada 30 segundos
  refreshInterval.value = setInterval(() => {
    if (!isLoading.value) {
      loadSystemStatus()
    }
  }, 30000)
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  if (typeof window !== 'undefined') {
    window.loadPromptsSystemStatus = loadSystemStatus
    window.migratePromptsToPostgreSQL = migrateToPostgreSQL
    window.updateSystemStatusDisplay = refreshStatus
  }
})

onUnmounted(() => {
  // Limpiar interval
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadPromptsSystemStatus
    delete window.migratePromptsToPostgreSQL
    delete window.updateSystemStatusDisplay
  }
  
  appStore.addToLog('PromptsStatus component unmounted', 'info')
})
</script>

<style scoped>
/* ===== ESTILOS PARA PROMPTS STATUS ===== */

.prompts-status-container {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #007bff;
}

.status-header h3 {
  margin: 0;
  color: #495057;
  font-size: 1.4em;
}

.status-actions {
  display: flex;
  gap: 10px;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #0056b3;
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-section,
.error-section {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.btn-retry {
  padding: 10px 20px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 15px;
}

.status-content {
  display: grid;
  gap: 20px;
}

.status-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.status-card-header {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-card-header h4 {
  margin: 0;
  color: #495057;
  font-size: 1.1em;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 0.9em;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-indicator.success .status-dot {
  background: #28a745;
}

.status-indicator.warning .status-dot {
  background: #ffc107;
}

.status-indicator.error .status-dot {
  background: #dc3545;
}

.status-indicator.unknown .status-dot {
  background: #6c757d;
}

.status-card-body {
  padding: 20px;
}

.status-detail,
.health-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f1f3f4;
}

.status-detail:last-child,
.health-item:last-child {
  border-bottom: none;
}

.detail-label,
.health-label {
  font-weight: 500;
  color: #495057;
}

.detail-value,
.health-value {
  font-weight: 600;
}

.detail-value.success,
.health-value.success {
  color: #28a745;
}

.detail-value.warning,
.health-value.warning {
  color: #ffc107;
}

.detail-value.error,
.health-value.error {
  color: #dc3545;
}

.migration-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #dee2e6;
  text-align: center;
}

.btn-migrate {
  padding: 12px 24px;
  background: #17a2b8;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1em;
  transition: all 0.2s ease;
}

.btn-migrate:hover:not(:disabled) {
  background: #117a8b;
  transform: translateY(-1px);
}

.btn-migrate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.migration-help {
  margin: 10px 0 0 0;
  font-size: 0.85em;
  color: #6c757d;
}

.metrics-grid,
.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.metric-item {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 0.85em;
  color: #6c757d;
  margin-bottom: 5px;
}

.metric-value {
  display: block;
  font-size: 1.2em;
  font-weight: 600;
  color: #495057;
}

.metric-value.error {
  color: #dc3545;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.tool-button {
  padding: 12px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9em;
  transition: all 0.2s ease;
  text-align: center;
}

.tool-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.tool-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.repair-btn {
  background: #fd7e14;
  color: white;
}

.repair-btn:hover:not(:disabled) {
  background: #e8690b;
}

.validate-btn {
  background: #28a745;
  color: white;
}

.validate-btn:hover:not(:disabled) {
  background: #1e7e34;
}

.optimize-btn {
  background: #6f42c1;
  color: white;
}

.optimize-btn:hover:not(:disabled) {
  background: #5a32a3;
}

.export-btn {
  background: #17a2b8;
  color: white;
}

.export-btn:hover:not(:disabled) {
  background: #117a8b;
}

.status-footer {
  margin-top: 20px;
  text-align: center;
  padding-top: 15px;
  border-top: 1px solid #dee2e6;
  color: #6c757d;
}

/* Database status specific styling */
.database-status.success {
  border-left: 4px solid #28a745;
}

.database-status.warning {
  border-left: 4px solid #ffc107;
}

.database-status.error {
  border-left: 4px solid #dc3545;
}

.database-status.unknown {
  border-left: 4px solid #6c757d;
}

/* Responsive design */
@media (max-width: 768px) {
  .prompts-status-container {
    padding: 15px;
  }
  
  .status-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .status-actions {
    justify-content: center;
  }
  
  .metrics-grid,
  .health-grid,
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .status-detail,
  .health-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .status-card-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .status-indicator {
    align-self: flex-end;
  }
}

/* Animation for status updates */
.status-card {
  transition: all 0.3s ease;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>
