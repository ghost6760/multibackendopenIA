<!--
  CompanyList.vue - Lista de Empresas Enterprise
  MIGRADO DE: script.js funciones loadEnterpriseCompanies(), viewEnterpriseCompany()
  PRESERVAR: Comportamiento exacto de las funciones originales
  COMPATIBILIDAD: 100% con el script.js original
-->

<template>
  <div class="enterprise-companies">
    <div class="companies-header">
      <h4>📋 Empresas Enterprise Configuradas</h4>
      <div class="header-actions">
        <button 
          @click="refreshCompanies" 
          class="btn btn-refresh"
          :disabled="isLoading"
        >
          <span v-if="isLoading">⏳</span>
          <span v-else">🔄</span>
          {{ isLoading ? 'Cargando...' : 'Actualizar' }}
        </button>
        
        <div class="view-toggle">
          <button 
            @click="viewMode = 'cards'" 
            :class="{ active: viewMode === 'cards' }"
            class="toggle-btn"
          >
            📋 Cards
          </button>
          <button 
            @click="viewMode = 'table'" 
            :class="{ active: viewMode === 'table' }"
            class="toggle-btn"
          >
            📊 Tabla
          </button>
        </div>
      </div>
    </div>
    
    <!-- Filtros y búsqueda -->
    <div class="companies-filters">
      <div class="search-box">
        <input 
          type="text"
          v-model="searchQuery"
          placeholder="🔍 Buscar por nombre o ID..."
          class="search-input"
        >
      </div>
      
      <div class="filter-controls">
        <select v-model="statusFilter" class="filter-select">
          <option value="">Todos los estados</option>
          <option value="active">Solo Activas</option>
          <option value="inactive">Solo Inactivas</option>
        </select>
        
        <select v-model="businessTypeFilter" class="filter-select">
          <option value="">Todos los tipos</option>
          <option value="healthcare">Salud</option>
          <option value="beauty">Belleza</option>
          <option value="dental">Dental</option>
          <option value="spa">Spa & Wellness</option>
          <option value="general">General</option>
        </select>
      </div>
    </div>
    
    <!-- Estados de carga y error -->
    <div v-if="isLoading && companies.length === 0" class="companies-list loading">
      <div class="loading-state">
        <div class="loading-spinner">⏳</div>
        <p>Cargando empresas enterprise...</p>
      </div>
    </div>
    
    <div v-else-if="error" class="companies-list error">
      <div class="error-state">
        <h4>❌ Error al cargar empresas enterprise</h4>
        <p>{{ error }}</p>
        <button @click="refreshCompanies" class="btn btn-primary">
          🔄 Reintentar
        </button>
      </div>
    </div>
    
    <div v-else-if="filteredCompanies.length === 0 && companies.length === 0" class="companies-list empty">
      <div class="empty-state">
        <h4>📁 No hay empresas enterprise configuradas</h4>
        <p>Las empresas aparecerán aquí una vez que sean creadas</p>
      </div>
    </div>
    
    <div v-else-if="filteredCompanies.length === 0" class="companies-list empty">
      <div class="empty-state">
        <h4>🔍 No se encontraron empresas</h4>
        <p>Intenta ajustar los filtros de búsqueda</p>
      </div>
    </div>
    
    <!-- Vista en Cards (por defecto) -->
    <div v-else-if="viewMode === 'cards'" class="companies-list cards">
      <div class="companies-grid">
        <div 
          v-for="company in filteredCompanies" 
          :key="company.company_id"
          class="enterprise-company-card"
          :class="{ 'inactive': !company.is_active }"
        >
          <!-- Header de la card -->
          <div class="company-header">
            <div class="company-title">
              <h4>{{ company.company_name }}</h4>
              <span class="company-id">{{ company.company_id }}</span>
            </div>
            <div class="company-status">
              <span 
                :class="['badge', company.is_active ? 'badge-success' : 'badge-warning']"
              >
                {{ company.is_active ? '✅ Activa' : '⚠️ Inactiva' }}
              </span>
            </div>
          </div>
          
          <!-- Detalles de la empresa -->
          <div class="company-details">
            <div class="detail-row">
              <span class="detail-label">🏢 Tipo:</span>
              <span class="detail-value">{{ formatBusinessType(company.business_type) }}</span>
            </div>
            
            <div v-if="company.subscription_tier" class="detail-row">
              <span class="detail-label">💎 Plan:</span>
              <span class="detail-value">{{ company.subscription_tier.toUpperCase() }}</span>
            </div>
            
            <div v-if="company.timezone" class="detail-row">
              <span class="detail-label">🌍 Zona horaria:</span>
              <span class="detail-value">{{ company.timezone }}</span>
            </div>
            
            <div v-if="company.currency" class="detail-row">
              <span class="detail-label">💰 Moneda:</span>
              <span class="detail-value">{{ company.currency }}</span>
            </div>
            
            <div v-if="company.created_at" class="detail-row">
              <span class="detail-label">📅 Creada:</span>
              <span class="detail-value">{{ formatDate(company.created_at) }}</span>
            </div>
            
            <div v-if="company.last_updated" class="detail-row">
              <span class="detail-label">🔄 Actualizada:</span>
              <span class="detail-value">{{ formatDate(company.last_updated) }}</span>
            </div>
          </div>
          
          <!-- Servicios -->
          <div v-if="company.services" class="company-services">
            <span class="services-label">🎯 Servicios:</span>
            <div class="services-content">
              {{ company.services }}
            </div>
          </div>
          
          <!-- Acciones -->
          <div class="company-actions">
            <button 
              @click="viewCompanyDetails(company.company_id)"
              class="btn btn-info btn-sm"
            >
              👁️ Ver Detalles
            </button>
            
            <button 
              @click="editCompany(company.company_id)"
              class="btn btn-primary btn-sm"
            >
              ✏️ Editar
            </button>
            
            <button 
              @click="toggleCompanyStatus(company.company_id, company.is_active)"
              :class="['btn', 'btn-sm', company.is_active ? 'btn-warning' : 'btn-success']"
            >
              {{ company.is_active ? '⏸️ Desactivar' : '▶️ Activar' }}
            </button>
            
            <button 
              @click="deleteCompany(company.company_id)"
              class="btn btn-danger btn-sm"
            >
              🗑️ Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Vista en Tabla -->
    <div v-else class="companies-list table">
      <div class="table-container">
        <table class="companies-table">
          <thead>
            <tr>
              <th>Estado</th>
              <th>ID</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Plan</th>
              <th>Zona Horaria</th>
              <th>Creada</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="company in filteredCompanies" 
              :key="company.company_id"
              :class="{ 'inactive-row': !company.is_active }"
            >
              <td>
                <span 
                  :class="['badge', company.is_active ? 'badge-success' : 'badge-warning']"
                >
                  {{ company.is_active ? 'Activa' : 'Inactiva' }}
                </span>
              </td>
              <td class="company-id-cell">{{ company.company_id }}</td>
              <td class="company-name-cell">{{ company.company_name }}</td>
              <td>{{ formatBusinessType(company.business_type) }}</td>
              <td>{{ company.subscription_tier?.toUpperCase() || '-' }}</td>
              <td>{{ company.timezone || '-' }}</td>
              <td>{{ formatDate(company.created_at) }}</td>
              <td>
                <div class="table-actions">
                  <button 
                    @click="viewCompanyDetails(company.company_id)"
                    class="btn btn-info btn-xs"
                    title="Ver detalles"
                  >
                    👁️
                  </button>
                  
                  <button 
                    @click="editCompany(company.company_id)"
                    class="btn btn-primary btn-xs"
                    title="Editar"
                  >
                    ✏️
                  </button>
                  
                  <button 
                    @click="toggleCompanyStatus(company.company_id, company.is_active)"
                    :class="['btn', 'btn-xs', company.is_active ? 'btn-warning' : 'btn-success']"
                    :title="company.is_active ? 'Desactivar' : 'Activar'"
                  >
                    {{ company.is_active ? '⏸️' : '▶️' }}
                  </button>
                  
                  <button 
                    @click="deleteCompany(company.company_id)"
                    class="btn btn-danger btn-xs"
                    title="Eliminar"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Modal de detalles de empresa -->
    <div v-if="showDetailsModal" class="modal-overlay" @click="closeDetailsModal">
      <div class="modal-content company-details-modal" @click.stop>
        <div class="modal-header">
          <h3>👁️ Detalles de {{ selectedCompany?.company_name }}</h3>
          <button @click="closeDetailsModal" class="modal-close">&times;</button>
        </div>
        
        <div v-if="selectedCompany" class="modal-body">
          <!-- Información básica -->
          <div class="detail-section">
            <h4>📋 Información Básica</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">ID:</span>
                <span class="detail-value">{{ selectedCompany.company_id }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Nombre:</span>
                <span class="detail-value">{{ selectedCompany.company_name }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Estado:</span>
                <span 
                  :class="['badge', selectedCompany.is_active ? 'badge-success' : 'badge-warning']"
                >
                  {{ selectedCompany.is_active ? '✅ Activa' : '⚠️ Inactiva' }}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Tipo de negocio:</span>
                <span class="detail-value">{{ formatBusinessType(selectedCompany.business_type) }}</span>
              </div>
            </div>
          </div>
          
          <!-- Configuración -->
          <div class="detail-section">
            <h4>⚙️ Configuración</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Plan:</span>
                <span class="detail-value">{{ selectedCompany.subscription_tier?.toUpperCase() || '-' }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Zona horaria:</span>
                <span class="detail-value">{{ selectedCompany.timezone || '-' }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Moneda:</span>
                <span class="detail-value">{{ selectedCompany.currency || '-' }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Agente:</span>
                <span class="detail-value">{{ selectedCompany.sales_agent_name || '-' }}</span>
              </div>
            </div>
          </div>
          
          <!-- Servicios -->
          <div v-if="selectedCompany.services" class="detail-section">
            <h4>🎯 Servicios</h4>
            <div class="services-text">
              {{ selectedCompany.services }}
            </div>
          </div>
          
          <!-- Fechas -->
          <div class="detail-section">
            <h4>📅 Fechas</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Creada:</span>
                <span class="detail-value">{{ formatDate(selectedCompany.created_at) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Última actualización:</span>
                <span class="detail-value">{{ formatDate(selectedCompany.last_updated) }}</span>
              </div>
            </div>
          </div>
          
          <!-- Configuración técnica -->
          <div v-if="companyConfiguration" class="detail-section">
            <h4>🔧 Configuración Técnica</h4>
            <div class="config-details">
              <pre>{{ JSON.stringify(companyConfiguration, null, 2) }}</pre>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeDetailsModal" class="btn btn-secondary">
            Cerrar
          </button>
          <button @click="editCompany(selectedCompany?.company_id)" class="btn btn-primary">
            ✏️ Editar Empresa
          </button>
        </div>
      </div>
    </div>
    
    <!-- Loading overlay para acciones -->
    <div v-if="actionLoading" class="loading-overlay">
      <div class="loading-spinner">⏳ {{ actionLoadingText }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

// ============================================================================
// PROPS Y EMITS
// ============================================================================

const emit = defineEmits(['edit-company', 'company-updated'])

// ============================================================================
// COMPOSABLES Y STORES
// ============================================================================

const appStore = useAppStore()
const { apiRequestWithKey } = useApiRequest()
const { showNotification } = useNotifications()
const { addToLog } = useSystemLog()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const companies = ref([])
const isLoading = ref(false)
const error = ref('')
const viewMode = ref('cards') // 'cards' | 'table'

// Filtros
const searchQuery = ref('')
const statusFilter = ref('')
const businessTypeFilter = ref('')

// Modal de detalles
const showDetailsModal = ref(false)
const selectedCompany = ref(null)
const companyConfiguration = ref(null)

// Loading de acciones
const actionLoading = ref(false)
const actionLoadingText = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const filteredCompanies = computed(() => {
  let filtered = companies.value

  // Filtro por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(company => 
      company.company_name.toLowerCase().includes(query) ||
      company.company_id.toLowerCase().includes(query)
    )
  }

  // Filtro por estado
  if (statusFilter.value) {
    filtered = filtered.filter(company => {
      if (statusFilter.value === 'active') return company.is_active
      if (statusFilter.value === 'inactive') return !company.is_active
      return true
    })
  }

  // Filtro por tipo de negocio
  if (businessTypeFilter.value) {
    filtered = filtered.filter(company => 
      company.business_type === businessTypeFilter.value
    )
  }

  return filtered
})

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DE SCRIPT.JS
// ============================================================================

/**
 * Carga empresas enterprise - MIGRADO: loadEnterpriseCompanies() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadEnterpriseCompanies = async () => {
  try {
    isLoading.value = true
    error.value = ''
    
    addToLog('Loading enterprise companies for list', 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    const response = await apiRequestWithKey('/api/admin/companies', {
      method: 'GET'
    })
    
    companies.value = response.companies || []
    addToLog(`Enterprise companies loaded: ${companies.value.length}`, 'success')
    
  } catch (err) {
    error.value = err.message
    addToLog(`Error loading enterprise companies: ${err.message}`, 'error')
    showNotification('Error cargando empresas enterprise: ' + err.message, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * Ver detalles de empresa - MIGRADO: viewEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const viewCompanyDetails = async (companyId) => {
  try {
    actionLoading.value = true
    actionLoadingText.value = 'Cargando detalles...'
    
    addToLog(`Loading company details: ${companyId}`, 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`)
    
    selectedCompany.value = companies.value.find(c => c.company_id === companyId)
    companyConfiguration.value = response.configuration
    showDetailsModal.value = true
    
    addToLog(`Company details loaded: ${companyId}`, 'success')
    
  } catch (err) {
    addToLog(`Error loading company details: ${err.message}`, 'error')
    showNotification('Error al cargar detalles: ' + err.message, 'error')
  } finally {
    actionLoading.value = false
  }
}

/**
 * Editar empresa - EMITE EVENTO PARA CompanyManager
 */
const editCompany = (companyId) => {
  emit('edit-company', companyId)
  closeDetailsModal()
}

/**
 * Alternar estado de empresa - NUEVA FUNCIÓN BASADA EN PATRÓN SCRIPT.JS
 */
const toggleCompanyStatus = async (companyId, currentStatus) => {
  const action = currentStatus ? 'desactivar' : 'activar'
  
  if (!confirm(`¿Estás seguro de que quieres ${action} la empresa ${companyId}?`)) {
    return
  }
  
  try {
    actionLoading.value = true
    actionLoadingText.value = `${action === 'activar' ? 'Activando' : 'Desactivando'}...`
    
    addToLog(`Toggling company status: ${companyId} to ${!currentStatus}`, 'info')
    
    await apiRequestWithKey(`/api/admin/companies/${companyId}/status`, {
      method: 'PUT',
      body: { is_active: !currentStatus }
    })
    
    showNotification(`Empresa ${currentStatus ? 'desactivada' : 'activada'} exitosamente`, 'success')
    addToLog(`Company status updated: ${companyId}`, 'success')
    
    // Actualizar lista
    await refreshCompanies()
    
  } catch (err) {
    addToLog(`Error toggling company status: ${err.message}`, 'error')
    showNotification(`Error al ${action} empresa: ${err.message}`, 'error')
  } finally {
    actionLoading.value = false
  }
}

/**
 * Eliminar empresa - NUEVA FUNCIÓN BASADA EN PATRÓN SCRIPT.JS
 */
const deleteCompany = async (companyId) => {
  if (!confirm(`¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE la empresa ${companyId}?\n\nEsta acción NO se puede deshacer.`)) {
    return
  }
  
  // Doble confirmación para empresas en producción
  const confirmText = prompt(`Para confirmar, escribe el ID de la empresa: ${companyId}`)
  if (confirmText !== companyId) {
    showNotification('Eliminación cancelada: ID no coincide', 'warning')
    return
  }
  
  try {
    actionLoading.value = true
    actionLoadingText.value = 'Eliminando empresa...'
    
    addToLog(`Deleting company: ${companyId}`, 'warning')
    
    await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
      method: 'DELETE'
    })
    
    showNotification(`Empresa ${companyId} eliminada exitosamente`, 'success')
    addToLog(`Company deleted: ${companyId}`, 'success')
    
    // Actualizar lista
    await refreshCompanies()
    
  } catch (err) {
    addToLog(`Error deleting company: ${err.message}`, 'error')
    showNotification(`Error al eliminar empresa: ${err.message}`, 'error')
  } finally {
    actionLoading.value = false
  }
}

/**
 * Refrescar lista de empresas
 */
const refreshCompanies = async () => {
  await loadEnterpriseCompanies()
  emit('company-updated')
}

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

/**
 * Formatear tipo de negocio
 */
const formatBusinessType = (type) => {
  const types = {
    general: 'General',
    healthcare: 'Salud',
    beauty: 'Belleza',
    dental: 'Dental',
    spa: 'Spa & Wellness',
    clinic: 'Clínica'
  }
  return types[type] || type
}

/**
 * Formatear fecha
 */
const formatDate = (dateString) => {
  if (!dateString) return '-'
  
  try {
    return new Date(dateString).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateString
  }
}

/**
 * Cerrar modal de detalles
 */
const closeDetailsModal = () => {
  showDetailsModal.value = false
  selectedCompany.value = null
  companyConfiguration.value = null
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

/**
 * Escuchar eventos de empresas actualizadas
 */
const handleCompaniesUpdated = (event) => {
  if (event.detail?.companies) {
    companies.value = event.detail.companies
  }
}

// ============================================================================
// LIFECYCLE Y WRAPPERS DE COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // PRESERVAR: Registrar funciones globales como script.js
  window.viewEnterpriseCompany = viewCompanyDetails
  window.loadEnterpriseCompaniesList = loadEnterpriseCompanies
  
  // Escuchar eventos de actualización
  window.addEventListener('enterpriseCompaniesLoaded', handleCompaniesUpdated)
  
  // Cargar datos iniciales
  if (appStore.adminApiKey) {
    loadEnterpriseCompanies()
  }
  
  addToLog('CompanyList component mounted', 'info')
})

onUnmounted(() => {
  // Limpiar funciones globales
  delete window.viewEnterpriseCompany
  delete window.loadEnterpriseCompaniesList
  
  // Remover event listeners
  window.removeEventListener('enterpriseCompaniesLoaded', handleCompaniesUpdated)
})

// Watch para recargar cuando cambie la API key
watch(() => appStore.adminApiKey, (newApiKey) => {
  if (newApiKey) {
    loadEnterpriseCompanies()
  } else {
    companies.value = []
    error.value = ''
  }
})

// ============================================================================
// EXPORTAR FUNCIONES
// ============================================================================

defineExpose({
  loadEnterpriseCompanies,
  refreshCompanies,
  companies
})
</script>

<style scoped>
/* Heredar estilos del CSS principal */
.enterprise-companies {
  margin-top: 30px;
}

.companies-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.companies-header h4 {
  margin: 0;
  color: #374151;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.view-toggle {
  display: flex;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
}

.toggle-btn {
  background: #f9fafb;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: #3b82f6;
  color: white;
}

.toggle-btn:hover:not(.active) {
  background: #e5e7eb;
}

.companies-filters {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.search-box {
  flex: 1;
  min-width: 200px;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.filter-controls {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.companies-list {
  min-height: 200px;
}

/* Estados de carga y error */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 20px;
}

.error-state {
  color: #dc2626;
}

.empty-state {
  color: #6b7280;
}

/* Vista en Cards */
.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.enterprise-company-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  background: white;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.enterprise-company-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.enterprise-company-card.inactive {
  opacity: 0.7;
  background: #f9fafb;
}

.company-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.company-title h4 {
  margin: 0 0 5px 0;
  color: #1f2937;
  font-size: 1.1em;
}

.company-id {
  font-size: 0.85em;
  color: #6b7280;
  font-family: 'Courier New', monospace;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.company-details {
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid #f3f4f6;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 500;
  color: #374151;
  font-size: 0.9em;
}

.detail-value {
  color: #6b7280;
  font-size: 0.9em;
  text-align: right;
}

.company-services {
  margin-bottom: 15px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
}

.services-label {
  font-weight: 500;
  color: #374151;
  font-size: 0.9em;
  display: block;
  margin-bottom: 5px;
}

.services-content {
  color: #6b7280;
  font-size: 0.85em;
  line-height: 1.4;
}

.company-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75em;
  font-weight: 500;
}

.badge-success {
  background: #d1fae5;
  color: #065f46;
}

.badge-warning {
  background: #fef3c7;
  color: #92400e;
}

/* Vista en Tabla */
.table-container {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.companies-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.companies-table th {
  background: #f9fafb;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e2e8f0;
}

.companies-table td {
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.companies-table tr:hover {
  background: #f9fafb;
}

.inactive-row {
  opacity: 0.6;
  background: #f9fafb;
}

.company-id-cell {
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #6b7280;
}

.company-name-cell {
  font-weight: 500;
  color: #1f2937;
}

.table-actions {
  display: flex;
  gap: 5px;
}

/* Botones */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 11px;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

.btn-info {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: white;
}

.btn-success {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.btn-warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.btn-danger {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.btn-secondary {
  background: linear-gradient(135deg, #6b7280, #4b5563);
  color: white;
}

.btn-refresh {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: white;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-height: 90vh;
  overflow-y: auto;
}

.company-details-modal {
  width: 90%;
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-body {
  padding: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.detail-section {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h4 {
  margin: 0 0 15px 0;
  color: #374151;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item .detail-label {
  font-size: 0.875em;
  font-weight: 500;
  color: #6b7280;
}

.detail-item .detail-value {
  font-size: 0.95em;
  color: #1f2937;
}

.services-text {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
  line-height: 1.5;
}

.config-details {
  background: #1f2937;
  color: #f9fafb;
  padding: 15px;
  border-radius: 6px;
  overflow-x: auto;
}

.config-details pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  line-height: 1.4;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.loading-overlay .loading-spinner {
  background: white;
  padding: 20px 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  font-size: 18px;
}

/* Responsive */
@media (max-width: 768px) {
  .companies-grid {
    grid-template-columns: 1fr;
  }
  
  .companies-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: space-between;
  }
  
  .companies-filters {
    flex-direction: column;
  }
  
  .filter-controls {
    flex-direction: column;
  }
  
  .company-header {
    flex-direction: column;
    gap: 10px;
  }
  
  .company-actions {
    justify-content: center;
  }
  
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .table-container {
    font-size: 0.875em;
  }
  
  .companies-table th,
  .companies-table td {
    padding: 8px;
  }
}
</style>
