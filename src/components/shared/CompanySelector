<template>
  <div class="company-selector-wrapper">
    <label for="companySelect" class="company-label">
      🏢 Empresa Activa:
    </label>
    <select
      id="companySelect"
      v-model="selectedCompanyId"
      @change="handleCompanyChange"
      :disabled="isLoading"
      :class="{ 'highlight': shouldHighlight }"
      class="company-select"
    >
      <option value="">Seleccionar empresa...</option>
      <option 
        v-for="company in companies" 
        :key="company.id" 
        :value="company.id"
        :disabled="!company.active"
      >
        {{ company.name }} {{ !company.active ? '(Inactiva)' : '' }}
      </option>
    </select>
    
    <!-- Loading indicator -->
    <div v-if="isLoading" class="loading-spinner">⏳</div>
    
    <!-- Company info display -->
    <div v-if="selectedCompany" class="company-info">
      <small class="company-details">
        <span class="company-status" :class="`status-${selectedCompany.status || 'unknown'}`">
          {{ getStatusIcon(selectedCompany.status) }}
        </span>
        {{ selectedCompany.description || 'Sin descripción' }}
      </small>
    </div>
    
    <!-- Refresh button -->
    <button
      @click="refreshCompanies"
      :disabled="isLoading"
      class="refresh-btn"
      title="Recargar lista de empresas"
    >
      <span v-if="isLoading">⏳</span>
      <span v-else>🔄</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest, apiRequestWithCache } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const companies = ref([])
const isLoading = ref(false)
const shouldHighlight = ref(false)
const lastRefresh = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const selectedCompanyId = computed({
  get() {
    return appStore.currentCompanyId
  },
  set(value) {
    // Usar el setter del store para manejar el cambio
    appStore.setCurrentCompany(value)
  }
})

const selectedCompany = computed(() => {
  if (!selectedCompanyId.value) return null
  return companies.value.find(c => c.id === selectedCompanyId.value)
})

// ============================================================================
// MÉTODOS PRINCIPALES - MIGRADOS DESDE SCRIPT.JS
// ============================================================================

/**
 * Carga la lista de empresas disponibles
 * MIGRADO: loadCompanies() de script.js - PRESERVAR COMPORTAMIENTO EXACTO
 */
const loadCompanies = async () => {
  try {
    // Usar cache si está disponible y es válido
    if (appStore.isCacheValid('companies', 300000)) { // 5 minutos
      const cachedCompanies = appStore.cache.companies
      if (cachedCompanies && Array.isArray(cachedCompanies)) {
        console.log('Using cached companies:', cachedCompanies)
        companies.value = cachedCompanies
        return cachedCompanies
      }
    }
    
    console.log('Loading companies from API...')
    
    // Intentar primero el endpoint /api/companies - PRESERVAR LÓGICA EXACTA
    try {
      const response = await apiRequest('/api/companies')
      console.log('Response from /api/companies:', response)
      
      let companiesData = []
      
      // Verificar si las empresas están directamente en response.companies
      if (response.companies && typeof response.companies === 'object') {
        const companiesObj = response.companies
        
        // Convertir objeto de empresas a array - PRESERVAR LÓGICA EXACTA
        companiesData = Object.keys(companiesObj).map(companyId => {
          const companyData = companiesObj[companyId]
          return {
            id: companyId,
            name: companyData.company_name || companyId,
            description: companyData.description,
            status: companyData.status || 'active',
            active: companyData.active !== false
          }
        })
        
        console.log('Converted companies from /api/companies:', companiesData)
        
      } else if (response.data && response.data.companies) {
        // Fallback: verificar si están en response.data.companies
        companiesData = response.data.companies
      } else if (Array.isArray(response)) {
        // Fallback: respuesta directa como array
        companiesData = response
      } else {
        // Último fallback: empresas por defecto
        console.warn('No companies found in response, using defaults')
        companiesData = getDefaultCompanies()
      }
      
      // Actualizar estado y cache
      companies.value = companiesData
      appStore.updateCache('companies', companiesData)
      
      appStore.addToLog(`Loaded ${companiesData.length} companies successfully`, 'info')
      return companiesData
      
    } catch (apiError) {
      console.error('Error loading companies from API:', apiError)
      
      // Fallback: usar empresas por defecto
      const defaultCompanies = getDefaultCompanies()
      companies.value = defaultCompanies
      
      showNotification('⚠️ Usando empresas por defecto - API no disponible', 'warning')
      appStore.addToLog(`Companies API error, using defaults: ${apiError.message}`, 'warning')
      
      return defaultCompanies
    }
    
  } catch (error) {
    console.error('Error in loadCompanies:', error)
    
    // Último fallback
    const defaultCompanies = getDefaultCompanies()
    companies.value = defaultCompanies
    
    showNotification(`Error cargando empresas: ${error.message}`, 'error')
    appStore.addToLog(`Error loading companies: ${error.message}`, 'error')
    
    return defaultCompanies
  }
}

/**
 * Obtiene las empresas por defecto
 * PRESERVAR: Lista exacta del HTML original
 */
const getDefaultCompanies = () => {
  return [
    { id: 'benova', name: 'Benova', active: true, status: 'active' },
    { id: 'medispa', name: 'MediSpa Elite', active: true, status: 'active' },
    { id: 'dental_clinic', name: 'Clínica Dental Sonríe', active: true, status: 'active' },
    { id: 'spa_wellness', name: 'Wellness Spa & Relax', active: true, status: 'active' }
  ]
}

/**
 * Maneja el cambio de empresa
 * MIGRADO: handleCompanyChange() de script.js
 */
const handleCompanyChange = async (event) => {
  const newCompanyId = event?.target?.value || event
  
  if (newCompanyId === selectedCompanyId.value) {
    return // No hay cambio
  }
  
  const previousCompany = selectedCompanyId.value
  
  try {
    // Validar que la empresa existe
    const company = companies.value.find(c => c.id === newCompanyId)
    
    if (newCompanyId && !company) {
      throw new Error(`Empresa no encontrada: ${newCompanyId}`)
    }
    
    if (newCompanyId && !company.active) {
      throw new Error(`Empresa inactiva: ${company.name}`)
    }
    
    // Actualizar en el store (esto triggereará el computed)
    appStore.setCurrentCompany(newCompanyId)
    
    // Log del cambio
    const logMessage = newCompanyId 
      ? `Company changed: ${previousCompany || 'none'} → ${newCompanyId}`
      : `Company cleared: ${previousCompany} → none`
    
    appStore.addToLog(logMessage, 'info')
    
    // Notificación al usuario
    if (newCompanyId) {
      const companyName = company.name || newCompanyId
      showNotification(`✅ Empresa seleccionada: ${companyName}`, 'success', 3000)
    } else {
      showNotification('ℹ️ Empresa deseleccionada', 'info', 3000)
    }
    
  } catch (error) {
    console.error('Error changing company:', error)
    
    // Revertir selección en caso de error
    selectedCompanyId.value = previousCompany
    
    showNotification(`Error al cambiar empresa: ${error.message}`, 'error')
    appStore.addToLog(`Company change error: ${error.message}`, 'error')
  }
}

/**
 * Refresca la lista de empresas
 */
const refreshCompanies = async () => {
  isLoading.value = true
  lastRefresh.value = Date.now()
  
  try {
    // Limpiar cache para forzar recarga
    appStore.cache.companies = null
    delete appStore.cache.lastUpdate.companies
    
    await loadCompanies()
    
    showNotification('✅ Lista de empresas actualizada', 'success', 2000)
    appStore.addToLog('Companies list refreshed manually', 'info')
    
  } catch (error) {
    console.error('Error refreshing companies:', error)
    showNotification(`Error actualizando empresas: ${error.message}`, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * Actualiza el selector de empresas
 * MIGRADO: updateCompanySelector() de script.js
 */
const updateCompanySelector = () => {
  // Este método ya no es necesario en Vue debido a la reactividad
  // pero mantenemos la referencia para compatibilidad
  console.log('updateCompanySelector called - handled by Vue reactivity')
}

/**
 * Resalta temporalmente el selector
 */
const highlightSelector = () => {
  shouldHighlight.value = true
  
  // Focus en el selector
  nextTick(() => {
    const selectElement = document.getElementById('companySelect')
    if (selectElement) {
      selectElement.focus()
    }
  })
  
  // Quitar highlight después de 2 segundos
  setTimeout(() => {
    shouldHighlight.value = false
  }, 2000)
}

/**
 * Obtiene el ícono del estado de la empresa
 */
const getStatusIcon = (status) => {
  switch (status) {
    case 'active': return '✅'
    case 'inactive': return '❌'
    case 'maintenance': return '🔧'
    case 'warning': return '⚠️'
    default: return '❓'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('CompanySelector mounted', 'info')
  
  // Cargar empresas al montar el componente
  isLoading.value = true
  try {
    await loadCompanies()
    
    // Establecer empresa por defecto si no hay ninguna seleccionada
    if (!selectedCompanyId.value && companies.value.length > 0) {
      const defaultCompany = companies.value.find(c => c.id === appStore.DEFAULT_COMPANY_ID) 
                           || companies.value[0]
      
      if (defaultCompany) {
        await handleCompanyChange(defaultCompany.id)
      }
    }
    
  } finally {
    isLoading.value = false
  }
  
  // Event listeners para compatibilidad
  window.addEventListener('highlightCompanySelector', highlightSelector)
})

onUnmounted(() => {
  window.removeEventListener('highlightCompanySelector', highlightSelector)
})

// ============================================================================
// WATCHERS
// ============================================================================

// Watcher para reaccionar a eventos externos que requieran highlight
watch(() => appStore.activeTab, (newTab, oldTab) => {
  // Si se intenta cambiar a un tab que requiere empresa y no hay empresa seleccionada
  const requiresCompany = ['prompts', 'documents', 'conversations']
  
  if (requiresCompany.includes(newTab) && !selectedCompanyId.value) {
    highlightSelector()
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // Exponer funciones globales - CRÍTICO PARA COMPATIBILIDAD
  window.loadCompanies = loadCompanies
  window.handleCompanyChange = handleCompanyChange
  window.updateCompanySelector = updateCompanySelector
  window.refreshCompanies = refreshCompanies
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadCompanies
    delete window.handleCompanyChange
    delete window.updateCompanySelector
    delete window.refreshCompanies
  }
})
</script>

<style scoped>
.company-selector-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.company-label {
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
}

.company-select {
  background: var(--bg-primary);
  border: 2px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  min-width: 200px;
  transition: all 0.3s ease;
}

.company-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.company-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Highlight animation para llamar atención */
.company-select.highlight {
  animation: pulse-highlight 2s ease-in-out;
  border-color: var(--warning-color);
}

@keyframes pulse-highlight {
  0%, 100% {
    border-color: var(--warning-color);
    box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.2);
  }
  50% {
    border-color: var(--warning-color);
    box-shadow: 0 0 0 6px rgba(255, 193, 7, 0.4);
  }
}

.loading-spinner {
  color: var(--primary-color);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.company-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.company-details {
  color: var(--text-secondary);
  font-size: 0.85em;
  display: flex;
  align-items: center;
  gap: 4px;
}

.company-status {
  font-size: 0.9em;
}

.status-active {
  color: var(--success-color);
}

.status-inactive {
  color: var(--danger-color);
}

.status-maintenance {
  color: var(--warning-color);
}

.status-unknown {
  color: var(--text-muted);
}

.refresh-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .company-selector-wrapper {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .company-select {
    min-width: 100%;
  }
  
  .company-info {
    text-align: center;
  }
}
</style>
