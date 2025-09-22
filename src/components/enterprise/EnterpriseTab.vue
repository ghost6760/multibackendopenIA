<template>
  <div class="enterprise-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏢 Gestión Enterprise</h2>
      <p class="tab-subtitle">
        Administración avanzada de empresas y configuraciones multi-tenant
      </p>
    </div>

    <!-- Verificación de API Key -->
    <div v-if="!hasValidApiKey" class="api-key-required">
      <div class="warning-card">
        <div class="warning-icon">🔑</div>
        <h3>API Key Requerida</h3>
        <p>
          Las funciones enterprise requieren una API key válida para acceder a las 
          operaciones administrativas avanzadas.
        </p>
        <button @click="requestApiKey" class="btn btn-primary">
          🔑 Configurar API Key
        </button>
      </div>
    </div>

    <!-- Contenido principal (cuando hay API key válida) -->
    <div v-else class="enterprise-content">
      <!-- Panel de estado -->
      <div class="enterprise-status">
        <div class="status-cards">
          <div class="status-card">
            <div class="card-icon">🏢</div>
            <div class="card-content">
              <h4>Total Empresas</h4>
              <div class="card-value">{{ companiesCount }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">✅</div>
            <div class="card-content">
              <h4>Empresas Activas</h4>
              <div class="card-value success">{{ activeCompaniesCount }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">⚠️</div>
            <div class="card-content">
              <h4>Con Problemas</h4>
              <div class="card-value warning">{{ companiesWithIssues }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">🔄</div>
            <div class="card-content">
              <h4>Última Sincronización</h4>
              <div class="card-value">{{ formatDateTime(lastUpdateTime) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Herramientas enterprise -->
      <div class="enterprise-tools">
        <div class="tools-header">
          <h3>🔧 Herramientas Enterprise</h3>
          <div class="tools-actions">
            <button @click="loadEnterpriseCompanies" class="btn btn-secondary" :disabled="isLoading">
              <span v-if="isLoading">⏳ Cargando...</span>
              <span v-else">🔄 Actualizar</span>
            </button>
            <button @click="showCreateCompanyModal" class="btn btn-primary">
              ➕ Nueva Empresa
            </button>
          </div>
        </div>
        
        <div class="tools-grid">
          <button 
            @click="migrateCompaniesToPostgreSQL"
            class="tool-button"
            :disabled="isMigrating"
          >
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Migrar a PostgreSQL</div>
              <div class="tool-description">Migrar todas las empresas al sistema PostgreSQL</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button @click="syncAllCompanies" class="tool-button" :disabled="isSyncing">
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Sincronizar Todo</div>
              <div class="tool-description">Sincronizar configuraciones de todas las empresas</div>
            </div>
            <div v-if="isSyncing" class="tool-loading">⏳</div>
          </button>
          
          <button @click="exportCompaniesData" class="tool-button">
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar Datos</div>
              <div class="tool-description">Exportar configuraciones de todas las empresas</div>
            </div>
          </button>
          
          <button @click="runHealthCheckAll" class="tool-button" :disabled="isRunningHealthCheck">
            <div class="tool-icon">🏥</div>
            <div class="tool-content">
              <div class="tool-title">Health Check Global</div>
              <div class="tool-description">Verificar el estado de todas las empresas</div>
            </div>
            <div v-if="isRunningHealthCheck" class="tool-loading">⏳</div>
          </button>
        </div>
      </div>

      <!-- Lista de empresas -->
      <div class="companies-section">
        <div class="section-header">
          <h3>📋 Empresas Enterprise</h3>
          <div class="search-filters">
            <input
              type="text"
              v-model="searchQuery"
              placeholder="Buscar empresas..."
              class="search-input"
            />
            <select v-model="statusFilter" class="filter-select">
              <option value="">Todos los estados</option>
              <option value="active">Activas</option>
              <option value="inactive">Inactivas</option>
              <option value="error">Con errores</option>
            </select>
          </div>
        </div>
        
        <div v-if="filteredCompanies.length === 0" class="empty-state">
          <div class="empty-icon">🏢</div>
          <h4>No se encontraron empresas</h4>
          <p>No hay empresas que coincidan con los filtros seleccionados.</p>
        </div>
        
        <div v-else class="companies-grid">
          <div 
            v-for="company in filteredCompanies"
            :key="company.company_id || company.id"
            class="company-card"
            :class="{ 
              'company-inactive': !company.is_active,
              'company-error': company.status === 'error'
            }"
          >
            <div class="company-header">
              <div class="company-info">
                <h4>{{ company.company_name || company.name || company.company_id || company.id }}</h4>
                <div class="company-badges">
                  <span :class="['badge', 'badge-status', getStatusClass(company.status)]">
                    {{ getStatusText(company.status) }}
                  </span>
                  <span v-if="company.environment" class="badge badge-env">
                    {{ company.environment }}
                  </span>
                </div>
              </div>
              
              <div class="company-actions">
                <button @click="viewEnterpriseCompany(company.company_id || company.id)" class="btn btn-xs btn-info">
                  👁️ Ver
                </button>
                <button @click="editEnterpriseCompany(company.company_id || company.id)" class="btn btn-xs btn-primary">
                  ✏️ Editar
                </button>
                <button @click="testEnterpriseCompany(company.company_id || company.id)" class="btn btn-xs btn-success">
                  🧪 Test
                </button>
              </div>
            </div>
            
            <div class="company-content">
              <div class="company-description">
                {{ company.description || 'Sin descripción disponible' }}
              </div>
              
              <div class="company-config">
                <div class="config-item">
                  <span class="config-label">API Base:</span>
                  <span class="config-value">{{ company.api_base_url || 'N/A' }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Base de datos:</span>
                  <span class="config-value">{{ company.database_type || 'N/A' }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Última actividad:</span>
                  <span class="config-value">{{ formatDateTime(company.last_activity || company.last_modified) }}</span>
                </div>
              </div>
              
              <div v-if="company.health_status" class="health-summary">
                <div class="health-item" v-for="(status, service) in company.health_status" :key="service">
                  <span class="service-name">{{ service }}:</span>
                  <span :class="['health-status', status.toLowerCase()]">{{ status }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de creación/edición de empresa -->
    <div v-if="showCompanyModal" class="company-modal" @click="closeCompanyModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>{{ isEditMode ? '✏️ Editar Empresa' : '➕ Nueva Empresa' }}</h4>
          <button @click="closeCompanyModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="handleSaveCompany" class="company-form">
            <div class="form-grid">
              <div class="form-group">
                <label for="companyId">ID de la empresa *:</label>
                <input
                  id="companyId"
                  type="text"
                  v-model="localCompanyForm.company_id"
                  :disabled="isEditMode"
                  required
                  placeholder="ej: mi-empresa"
                />
              </div>
              
              <div class="form-group">
                <label for="companyName">Nombre *:</label>
                <input
                  id="companyName"
                  type="text"
                  v-model="localCompanyForm.company_name"
                  required
                  placeholder="Nombre de la empresa"
                />
              </div>
              
              <div class="form-group full-width">
                <label for="companyDescription">Descripción:</label>
                <textarea
                  id="companyDescription"
                  v-model="localCompanyForm.description"
                  placeholder="Descripción de la empresa"
                  rows="3"
                ></textarea>
              </div>
              
              <div class="form-group">
                <label for="apiBaseUrl">API Base URL:</label>
                <input
                  id="apiBaseUrl"
                  type="url"
                  v-model="localCompanyForm.api_base_url"
                  placeholder="https://api.empresa.com"
                />
              </div>
              
              <div class="form-group">
                <label for="databaseType">Tipo de base de datos:</label>
                <select id="databaseType" v-model="localCompanyForm.database_type">
                  <option value="">Seleccionar...</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                  <option value="mongodb">MongoDB</option>
                </select>
              </div>
              
              <div class="form-group">
                <label for="environment">Entorno:</label>
                <select id="environment" v-model="localCompanyForm.environment">
                  <option value="development">Desarrollo</option>
                  <option value="staging">Staging</option>
                  <option value="production">Producción</option>
                </select>
              </div>
              
              <div class="form-group">
                <label>
                  <input type="checkbox" v-model="localCompanyForm.is_active" />
                  Empresa activa
                </label>
              </div>
              
              <div class="form-group full-width">
                <label for="services">Servicios JSON:</label>
                <textarea
                  id="services"
                  v-model="localCompanyForm.servicesJson"
                  placeholder='{"service1": {"enabled": true}, "service2": {"enabled": false}}'
                  rows="6"
                  class="json-textarea"
                ></textarea>
                <div class="textarea-footer">
                  <span :class="['json-status', isValidServicesJSON ? 'valid' : 'invalid']">
                    {{ isValidServicesJSON ? '✅ JSON válido' : '❌ JSON inválido' }}
                  </span>
                </div>
              </div>
              
              <div class="form-group full-width">
                <label for="configuration">Configuración JSON:</label>
                <textarea
                  id="configuration"
                  v-model="localCompanyForm.configurationJson"
                  placeholder='{"key": "value"}'
                  rows="8"
                  class="json-textarea"
                ></textarea>
                <div class="textarea-footer">
                  <span :class="['json-status', isValidConfigJSON ? 'valid' : 'invalid']">
                    {{ isValidConfigJSON ? '✅ JSON válido' : '❌ JSON inválido' }}
                  </span>
                </div>
              </div>
              
              <div class="form-group full-width">
                <label for="notes">Notas:</label>
                <textarea
                  id="notes"
                  v-model="localCompanyForm.notes"
                  placeholder="Notas adicionales sobre la empresa"
                  rows="3"
                ></textarea>
              </div>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <div class="modal-actions">
            <button 
              type="submit" 
              @click="handleSaveCompany" 
              class="btn btn-primary" 
              :disabled="isSaving || !isValidForm"
            >
              <span v-if="isSaving">⏳ Guardando...</span>
              <span v-else>💾 {{ isEditMode ? 'Actualizar' : 'Crear' }} Empresa</span>
            </button>
            <button @click="closeCompanyModal" class="btn btn-secondary">
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de vista detallada -->
    <div v-if="selectedCompany && showViewModal" class="company-modal" @click="closeViewModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>👁️ Detalles: {{ selectedCompany.company_name || selectedCompany.name || selectedCompany.company_id || selectedCompany.id }}</h4>
          <button @click="closeViewModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <div class="company-details">
            <div class="details-section">
              <h5>📊 Información General</h5>
              <div class="details-grid">
                <div class="detail-item">
                  <strong>ID:</strong> {{ selectedCompany.company_id || selectedCompany.id }}
                </div>
                <div class="detail-item">
                  <strong>Nombre:</strong> {{ selectedCompany.company_name || selectedCompany.name }}
                </div>
                <div class="detail-item">
                  <strong>Estado:</strong> 
                  <span :class="['status-badge', getStatusClass(selectedCompany.status)]">
                    {{ getStatusText(selectedCompany.status) }}
                  </span>
                </div>
                <div class="detail-item">
                  <strong>Entorno:</strong> {{ selectedCompany.environment || 'N/A' }}
                </div>
                <div class="detail-item">
                  <strong>Creado:</strong> {{ formatDateTime(selectedCompany.created_at) }}
                </div>
                <div class="detail-item">
                  <strong>Actualizado:</strong> {{ formatDateTime(selectedCompany.updated_at || selectedCompany.last_modified) }}
                </div>
              </div>
            </div>
            
            <div v-if="selectedCompany.services" class="details-section">
              <h5>⚙️ Servicios</h5>
              <pre class="config-json">{{ formatJSON(selectedCompany.services) }}</pre>
            </div>
            
            <div v-if="selectedCompany.configuration" class="details-section">
              <h5>🔧 Configuración</h5>
              <pre class="config-json">{{ formatJSON(parseJSON(selectedCompany.configuration)) }}</pre>
            </div>
            
            <div v-if="selectedCompany.health_status" class="details-section">
              <h5>🏥 Estado de Salud</h5>
              <div class="health-grid">
                <div 
                  v-for="(status, service) in selectedCompany.health_status" 
                  :key="service"
                  class="health-item-detailed"
                >
                  <div class="health-service">{{ service }}</div>
                  <div :class="['health-status-detailed', status.toLowerCase()]">{{ status }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <div class="modal-actions">
            <button @click="editEnterpriseCompany(selectedCompany.company_id || selectedCompany.id)" class="btn btn-primary">
              ✏️ Editar
            </button>
            <button @click="testEnterpriseCompany(selectedCompany.company_id || selectedCompany.id)" class="btn btn-success">
              🧪 Probar Conexión
            </button>
            <button @click="closeViewModal" class="btn btn-secondary">
              ❌ Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Contenedor de resultados (para compatibilidad con useEnterprise) -->
    <div id="enterpriseResults" style="margin-top: 20px;"></div>
    <div id="enterpriseCompaniesTable" style="margin-top: 20px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useEnterprise } from '@/composables/useEnterprise' // ✅ IMPORTAR EL COMPOSABLE
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS
// ============================================================================
const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================
const appStore = useAppStore()
const { showNotification } = useNotifications()

// ✅ USAR EL COMPOSABLE useEnterprise EN LUGAR DE REIMPLEMENTAR
const {
  // Estado reactivo del composable
  enterpriseCompanies,
  selectedCompany,
  isLoading,
  isCreating,
  isUpdating,
  isTesting,
  isMigrating,
  companyForm,
  testResults,
  migrationResults,
  lastUpdateTime,

  // Computed properties del composable
  companiesCount,
  hasCompanies,
  activeCompanies,
  companyOptions,
  isFormValid,
  isAnyProcessing,

  // Funciones principales del composable
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  editEnterpriseCompany,
  saveEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,

  // Funciones auxiliares del composable
  getCompanyById,
  exportCompanies,
  clearCompanyForm,
  populateCompanyForm
} = useEnterprise()

// ============================================================================
// ESTADO LOCAL ADICIONAL (Solo UI, no lógica de negocio)
// ============================================================================
const showCompanyModal = ref(false)
const showViewModal = ref(false)
const isEditMode = ref(false)
const isSaving = ref(false)
const isSyncing = ref(false)
const isRunningHealthCheck = ref(false)

// Filtros de UI
const searchQuery = ref('')
const statusFilter = ref('')

// Formulario local para el modal (mapea a companyForm del composable)
const localCompanyForm = ref({
  company_id: '',
  company_name: '',
  description: '',
  api_base_url: '',
  database_type: '',
  environment: 'development',
  is_active: true,
  servicesJson: '',
  configurationJson: '',
  notes: ''
})

// ============================================================================
// COMPUTED PROPERTIES LOCALES
// ============================================================================
const hasValidApiKey = computed(() => !!appStore.adminApiKey)

const activeCompaniesCount = computed(() => {
  return enterpriseCompanies.value.filter(company => 
    company.is_active !== false && company.status !== 'inactive'
  ).length
})

const companiesWithIssues = computed(() => {
  return enterpriseCompanies.value.filter(company => 
    company.status === 'error' || company.status === 'warning'
  ).length
})

const filteredCompanies = computed(() => {
  let filtered = [...enterpriseCompanies.value]
  
  // Filtro de búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(company =>
      (company.company_name || company.name || '').toLowerCase().includes(query) ||
      (company.company_id || company.id || '').toLowerCase().includes(query) ||
      (company.description || '').toLowerCase().includes(query)
    )
  }
  
  // Filtro de estado
  if (statusFilter.value) {
    switch (statusFilter.value) {
      case 'active':
        filtered = filtered.filter(company => company.is_active !== false)
        break
      case 'inactive':
        filtered = filtered.filter(company => company.is_active === false)
        break
      case 'error':
        filtered = filtered.filter(company => company.status === 'error')
        break
    }
  }
  
  return filtered.sort((a, b) => 
    (a.company_name || a.name || a.company_id || a.id).localeCompare(
      b.company_name || b.name || b.company_id || b.id
    )
  )
})

const isValidServicesJSON = computed(() => {
  if (!localCompanyForm.value.servicesJson.trim()) return true
  
  try {
    JSON.parse(localCompanyForm.value.servicesJson)
    return true
  } catch (error) {
    return false
  }
})

const isValidConfigJSON = computed(() => {
  if (!localCompanyForm.value.configurationJson.trim()) return true
  
  try {
    JSON.parse(localCompanyForm.value.configurationJson)
    return true
  } catch (error) {
    return false
  }
})

const isValidForm = computed(() => {
  return localCompanyForm.value.company_id.trim() &&
         localCompanyForm.value.company_name.trim() &&
         isValidServicesJSON.value &&
         isValidConfigJSON.value
})

// ============================================================================
// FUNCIONES DE UI (No lógica de negocio)
// ============================================================================
const showCreateCompanyModal = () => {
  clearLocalForm()
  isEditMode.value = false
  showCompanyModal.value = true
}

const closeCompanyModal = () => {
  showCompanyModal.value = false
  isEditMode.value = false
  clearLocalForm()
}

const closeViewModal = () => {
  showViewModal.value = false
}

const clearLocalForm = () => {
  localCompanyForm.value = {
    company_id: '',
    company_name: '',
    description: '',
    api_base_url: '',
    database_type: '',
    environment: 'development',
    is_active: true,
    servicesJson: '',
    configurationJson: '',
    notes: ''
  }
}

const populateLocalForm = (company) => {
  localCompanyForm.value = {
    company_id: company.company_id || company.id || '',
    company_name: company.company_name || company.name || '',
    description: company.description || '',
    api_base_url: company.api_base_url || '',
    database_type: company.database_type || '',
    environment: company.environment || 'development',
    is_active: company.is_active !== false,
    servicesJson: company.services ? JSON.stringify(company.services, null, 2) : '',
    configurationJson: company.configuration ? 
      (typeof company.configuration === 'string' ? 
        company.configuration : JSON.stringify(company.configuration, null, 2)) : '',
    notes: company.notes || ''
  }
}

// ============================================================================
// FUNCIONES BRIDGE (Conectan UI con composable)
// ============================================================================
const handleSaveCompany = async () => {
  if (!isValidForm.value) return
  
  isSaving.value = true
  
  try {
    // Convertir formulario local al formato esperado por el composable
    const companyData = {
      company_id: localCompanyForm.value.company_id,
      company_name: localCompanyForm.value.company_name,
      description: localCompanyForm.value.description,
      api_base_url: localCompanyForm.value.api_base_url,
      database_type: localCompanyForm.value.database_type,
      environment: localCompanyForm.value.environment,
      is_active: localCompanyForm.value.is_active,
      services: localCompanyForm.value.servicesJson ? 
        JSON.parse(localCompanyForm.value.servicesJson) : {},
      configuration: localCompanyForm.value.configurationJson ? 
        JSON.parse(localCompanyForm.value.configurationJson) : {},
      notes: localCompanyForm.value.notes
    }
    
    if (isEditMode.value) {
      await saveEnterpriseCompany(companyData.company_id, companyData)
    } else {
      await createEnterpriseCompany(companyData)
    }
    
    closeCompanyModal()
    
  } catch (error) {
    // Error ya manejado en el composable
  } finally {
    isSaving.value = false
  }
}

// Override de editEnterpriseCompany para manejar el modal
const handleEditCompany = async (companyId) => {
  try {
    // Primero llamar al composable para cargar los datos
    await viewEnterpriseCompany(companyId)
    
    if (selectedCompany.value) {
      populateLocalForm(selectedCompany.value)
      isEditMode.value = true
      showCompanyModal.value = true
      showViewModal.value = false
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

// Override de viewEnterpriseCompany para manejar el modal
const handleViewCompany = async (companyId) => {
  try {
    await viewEnterpriseCompany(companyId)
    if (selectedCompany.value) {
      showViewModal.value = true
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

// ============================================================================
// FUNCIONES AUXILIARES LOCALES
// ============================================================================
const syncAllCompanies = async () => {
  isSyncing.value = true
  
  try {
    showNotification('Sincronizando todas las empresas...', 'info')
    
    // Recargar empresas (simula sincronización)
    await loadEnterpriseCompanies()
    
    showNotification('Sincronización completada', 'success')
    
  } catch (error) {
    showNotification(`Error en sincronización: ${error.message}`, 'error')
  } finally {
    isSyncing.value = false
  }
}

const exportCompaniesData = () => {
  exportCompanies('json')
}

const runHealthCheckAll = async () => {
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check en todas las empresas...', 'info')
    
    // Simular health check en todas las empresas
    const healthPromises = enterpriseCompanies.value.map(company => 
      testEnterpriseCompany(company.company_id || company.id)
    )
    
    await Promise.allSettled(healthPromises)
    
    showNotification('Health check completado', 'success')
    
  } catch (error) {
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

const requestApiKey = () => {
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

// ============================================================================
// FUNCIONES DE FORMATO (UTILIDADES)
// ============================================================================
const getStatusClass = (status) => {
  switch (status) {
    case 'active':
    case 'online':
    case 'success':
      return 'status-success'
    case 'inactive':
    case 'offline':
      return 'status-inactive'
    case 'error':
    case 'failed':
      return 'status-error'
    case 'warning':
      return 'status-warning'
    default:
      return 'status-unknown'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'active': return 'Activa'
    case 'inactive': return 'Inactiva'
    case 'error': return 'Error'
    case 'warning': return 'Advertencia'
    case 'online': return 'En línea'
    case 'offline': return 'Fuera de línea'
    default: return status || 'Desconocido'
  }
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return 'N/A'
  
  try {
    const date = typeof dateTime === 'number' ? new Date(dateTime) : new Date(dateTime)
    return date.toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

const parseJSON = (jsonString) => {
  try {
    return typeof jsonString === 'string' ? JSON.parse(jsonString) : jsonString
  } catch (error) {
    return jsonString
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================
onMounted(async () => {
  appStore.addToLog('EnterpriseTab component mounted', 'info')
  
  if (hasValidApiKey.value) {
    await loadEnterpriseCompanies()
  }
  
  // ✅ EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.loadEnterpriseCompanies = loadEnterpriseCompanies
  window.createEnterpriseCompany = createEnterpriseCompany
  window.viewEnterpriseCompany = handleViewCompany  // Usar versión con modal
  window.editEnterpriseCompany = handleEditCompany  // Usar versión con modal
  window.saveEnterpriseCompany = saveEnterpriseCompany
  window.testEnterpriseCompany = testEnterpriseCompany
  window.migrateCompaniesToPostgreSQL = migrateCompaniesToPostgreSQL
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadEnterpriseCompanies
    delete window.createEnterpriseCompany
    delete window.viewEnterpriseCompany
    delete window.editEnterpriseCompany
    delete window.saveEnterpriseCompany
    delete window.testEnterpriseCompany
    delete window.migrateCompaniesToPostgreSQL
  }
  
  appStore.addToLog('EnterpriseTab component unmounted', 'info')
})

// ============================================================================
// WATCHERS
// ============================================================================
watch(() => appStore.adminApiKey, (newApiKey) => {
  if (newApiKey && hasValidApiKey.value) {
    loadEnterpriseCompanies()
  } else {
    // empresas se limpian automáticamente en el composable
  }
})

// ============================================================================
// TEMPLATE REFS PARA FUNCIONES DE VIEW/EDIT
// ============================================================================
// Reemplazar las llamadas directas en el template
const wrappedViewCompany = (companyId) => handleViewCompany(companyId)
const wrappedEditCompany = (companyId) => handleEditCompany(companyId)

// Exponer las funciones wrapeadas al template
defineExpose({
  viewEnterpriseCompany: wrappedViewCompany,
  editEnterpriseCompany: wrappedEditCompany
})
</script>

<style scoped>
/* ✅ MANTENER TODOS LOS ESTILOS ORIGINALES */
.enterprise-tab {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-header {
  margin-bottom: 30px;
  text-align: center;
}

.tab-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tab-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.api-key-required {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.warning-card {
  background: var(--bg-primary);
  border: 2px solid var(--warning-color);
  border-radius: var(--radius-lg);
  padding: 40px;
  text-align: center;
  max-width: 500px;
  box-shadow: var(--shadow-md);
}

.warning-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.warning-card h3 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.warning-card p {
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 25px;
}

.enterprise-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.enterprise-status {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.card-icon {
  font-size: 2rem;
  width: 50px;
  text-align: center;
}

.card-content h4 {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0 0 5px 0;
  font-weight: 500;
}

.card-value {
  color: var(--text-primary);
  font-size: 1.5rem;
  font-weight: 600;
}

.card-value.success {
  color: var(--success-color);
}

.card-value.warning {
  color: var(--warning-color);
}

.enterprise-tools {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tools-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.tools-actions {
  display: flex;
  gap: 10px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.tool-button {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-normal);
  text-align: left;
}

.tool-button:hover:not(:disabled) {
  background: var(--bg-tertiary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tool-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tool-icon {
  font-size: 1.5rem;
  width: 40px;
  text-align: center;
}

.tool-content {
  flex: 1;
}

.tool-title {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.tool-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.tool-loading {
  font-size: 1.2rem;
}

.companies-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.section-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.search-filters {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  min-width: 200px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 15px;
  opacity: 0.6;
}

.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.company-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.company-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.company-card.company-inactive {
  opacity: 0.7;
  border-left: 4px solid var(--text-muted);
}

.company-card.company-error {
  border-left: 4px solid var(--error-color);
}

.company-header {
  padding: 15px;
  border-bottom: 1px solid var(--border-light);
}

.company-info h4 {
  color: var(--text-primary);
  margin: 0 0 8px 0;
  font-size: 1.1rem;
}

.company-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.badge {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
}

.badge-status {
  font-weight: 600;
}

.badge-env {
  background: var(--info-color);
  color: white;
}

.company-actions {
  display: flex;
  gap: 5px;
}

.company-content {
  padding: 15px;
}

.company-description {
  color: var(--text-secondary);
  margin-bottom: 15px;
  font-style: italic;
}

.company-config {
  margin-bottom: 15px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.config-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.config-value {
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
}

.health-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.8rem;
}

.service-name {
  color: var(--text-secondary);
}

.health-status {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  text-transform: uppercase;
}

.health-status.active,
.health-status.online,
.health-status.success {
  background: var(--success-color);
  color: white;
}

.health-status.error,
.health-status.failed {
  background: var(--error-color);
  color: white;
}

.health-status.warning {
  background: var(--warning-color);
  color: white;
}

.status-success {
  background: var(--success-color);
  color: white;
}

.status-error {
  background: var(--error-color);
  color: white;
}

.status-warning {
  background: var(--warning-color);
  color: white;
}

.status-inactive {
  background: var(--text-muted);
  color: white;
}

.status-unknown {
  background: var(--text-secondary);
  color: white;
}

.company-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-content.large {
  max-width: 1000px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.close-button {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.company-form {
  width: 100%;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-group input,
.form-group textarea,
.form-group select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.json-textarea {
  font-family: monospace;
  resize: vertical;
  min-height: 120px;
}

.textarea-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 5px;
}

.json-status {
  font-size: 0.8rem;
  font-weight: 500;
}

.json-status.valid {
  color: var(--success-color);
}

.json-status.invalid {
  color: var(--error-color);
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.company-details {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.details-section h5 {
  color: var(--text-primary);
  margin-bottom: 15px;
  font-size: 1.1rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.detail-item strong {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.status-badge {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  display: inline-block;
  margin-top: 2px;
}

.config-json {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow-x: auto;
  font-size: 0.9rem;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.health-item-detailed {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.health-service {
  font-weight: 500;
  color: var(--text-primary);
}

.health-status-detailed {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
}

.health-status-detailed.active,
.health-status-detailed.online,
.health-status-detailed.success {
  background: var(--success-color);
  color: white;
}

.health-status-detailed.error,
.health-status-detailed.failed {
  background: var(--error-color);
  color: white;
}

.health-status-detailed.warning {
  background: var(--warning-color);
  color: white;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-success {
  background: var(--success-color);
  color: white;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 0.8rem;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-filters {
    flex-direction: column;
  }
  
  .search-input {
    min-width: auto;
  }
  
  .companies-grid {
    grid-template-columns: 1fr;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .status-cards {
    grid-template-columns: 1fr;
  }
  
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
    max-height: calc(100vh - 20px);
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .details-grid {
    grid-template-columns: 1fr;
  }
  
  .health-grid {
    grid-template-columns: 1fr;
  }
  
  .tools-actions {
    flex-direction: column;
  }
}
</style>
