<!-- PromptsStatus.vue - CORREGIDO con endpoints exactos del script.js -->
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
            
            <!-- Last Update -->
            <div class="health-item" v-if="systemStatus.last_updated">
              <span class="health-label">Última actualización:</span>
              <span class="health-value">{{ formatDateTime(systemStatus.last_updated) }}</span>
            </div>
            
            <!-- Current Company -->
            <div class="health-item">
              <span class="health-label">Empresa activa:</span>
              <span class="health-value">{{ appStore.currentCompanyId || 'Ninguna' }}</span>
            </div>
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

// ============================================================================
// FUNCIONES PRINCIPALES - ENDPOINT CORREGIDO
// ============================================================================

/**
 * Carga el estado del sistema - ENDPOINT CORREGIDO
 * ORIGINAL SCRIPT.JS: `/api/admin/status` ✅ 
 * ANTES (INCORRECTO): `/api/admin/prompts/status` ❌
 */
const loadSystemStatus = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    appStore.addToLog('Loading prompts system status', 'info')
    
    // ✅ ENDPOINT CORREGIDO - Como en script.js funcional
    const response = await apiRequest('/api/admin/status')
    
    // En script.js original, se busca response.prompt_system
    if (response && response.prompt_system) {
      systemStatus.value = response.prompt_system
    } else {
      // Fallback si viene la respuesta directa
      systemStatus.value = response
    }
    
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
 * Actualizar estado - MIGRADO de script.js
 */
const refreshStatus = async () => {
  await loadSystemStatus()
}

// ============================================================================
// FUNCIONES DE UTILIDADES
// ============================================================================

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
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
  
  // ✅ EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  if (typeof window !== 'undefined') {
    window.loadPromptsSystemStatus = loadSystemStatus
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

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
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
  
  .health-grid {
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
