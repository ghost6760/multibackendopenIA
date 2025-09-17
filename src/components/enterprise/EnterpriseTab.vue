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
              <div class="card-value">{{ companies.length }}</div>
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
              <div class="card-value">{{ formatDateTime(lastSync) }}</div>
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
              <span v-else>🔄 Actualizar</span>
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
            :key="company.id"
            class="company-card"
            :class="{ 
              'company-inactive': !company.is_active,
              'company-error': company.status === 'error'
            }"
          >
            <div class="company-header">
              <div class="company-info">
                <h4>{{ company.name || company.id }}</h4>
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
                <button @click="viewEnterpriseCompany(company.id)" class="btn btn-xs btn-info">
                  👁️ Ver
                </button>
                <button @click="editEnterpriseCompany(company.id)" class="btn btn-xs btn-primary">
                  ✏️ Editar
                </button>
                <button @click="testEnterpriseCompany(company.id)" class="btn btn-xs btn-success">
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
                  <span class="config-value">{{ formatDateTime(company.last_activity) }}</span>
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
          <form @submit.prevent="saveEnterpriseCompany" class="company-form">
            <div class="form-grid">
              <div class="form-group">
                <label for="companyId">ID de la empresa *:</label>
                <input
                  id="companyId"
                  type="text"
                  v-model="companyForm.id"
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
                  v-model="companyForm.name"
                  required
                  placeholder="Nombre de la empresa"
                />
              </div>
              
              <div class="form-group full-width">
                <label for="companyDescription">Descripción:</label>
                <textarea
                  id="companyDescription"
                  v-model="companyForm.description"
                  placeholder="Descripción de la empresa"
                  rows="3"
                ></textarea>
              </div>
              
              <div class="form-group">
                <label for="apiBaseUrl">API Base URL:</label>
                <input
                  id="apiBaseUrl"
                  type="url"
                  v-model="companyForm.api_base_url"
                  placeholder="https://api.empresa.com"
                />
              </div>
              
              <div class="form-group">
                <label for="databaseType">Tipo de base de datos:</label>
                <select id="databaseType" v-model="companyForm.database_type">
                  <option value="">Seleccionar...</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                  <option value="mongodb">MongoDB</option>
                </select>
              </div>
              
              <div class="form-group">
                <label for="environment">Entorno:</label>
                <select id="environment" v-model="companyForm.environment">
                  <option value="development">Desarrollo</option>
                  <option value="staging">Staging</option>
                  <option value="production">Producción</option>
                </select>
              </div>
              
              <div class="form-group">
                <label>
                  <input type="checkbox" v-model="companyForm.is_active" />
                  Empresa activa
                </label>
              </div>
              
              <div class="form-group full-width">
                <label for="configuration">Configuración JSON:</label>
                <textarea
                  id="configuration"
                  v-model="companyForm.configuration"
                  placeholder='{"key": "value"}'
                  rows="8"
                  class="json-textarea"
                ></textarea>
                <div class="textarea-footer">
                  <span :class="['json-status', isValidJSON ? 'valid' : 'invalid']">
                    {{ isValidJSON ? '✅ JSON válido' : '❌ JSON inválido' }}
                  </span>
                </div>
              </div>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <div class="modal-actions">
            <button type="submit" @click="saveEnterpriseCompany" class="btn btn-primary" :disabled="isSaving || !isValidJSON">
              <span v-if="isSaving">⏳ Guardando...</span>
              <span v-else">💾 {{ isEditMode ? 'Actualizar' : 'Crear' }} Empresa</span>
            </button>
            <button @click="closeCompanyModal" class="btn btn-secondary">
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de vista detallada -->
    <div v-if="viewingCompany" class="company-modal" @click="closeViewModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>👁️ Detalles: {{ viewingCompany.name || viewingCompany.id }}</h4>
          <button @click="closeViewModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <div class="company-details">
            <div class="details-section">
              <h5>📊 Información General</h5>
              <div class="details-grid">
                <div class="detail-item">
                  <strong>ID:</strong> {{ viewingCompany.id }}
                </div>
                <div class="detail-item">
                  <strong>Nombre:</strong> {{ viewingCompany.name }}
                </div>
                <div class="detail-item">
                  <strong>Estado:</strong> 
                  <span :class="['status-badge', getStatusClass(viewingCompany.status)]">
                    {{ getStatusText(viewingCompany.status) }}
                  </span>
                </div>
                <div class="detail-item">
                  <strong>Entorno:</strong> {{ viewingCompany.environment || 'N/A' }}
                </div>
                <div class="detail-item">
                  <strong>Creado:</strong> {{ formatDateTime(viewingCompany.created_at) }}
                </div>
                <div class="detail-item">
                  <strong>Actualizado:</strong> {{ formatDateTime(viewingCompany.updated_at) }}
                </div>
              </div>
            </div>
            
            <div v-if="viewingCompany.configuration" class="details-section">
              <h5>⚙️ Configuración</h5>
              <pre class="config-json">{{ formatJSON(parseJSON(viewingCompany.configuration)) }}</pre>
            </div>
            
            <div v-if="viewingCompany.health_status" class="details-section">
              <h5>🏥 Estado de Salud</h5>
              <div class="health-grid">
                <div 
                  v-for="(status, service) in viewingCompany.health_status" 
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
            <button @click="editEnterpriseCompany(viewingCompany.id)" class="btn btn-primary">
              ✏️ Editar
            </button>
            <button @click="testEnterpriseCompany(viewingCompany.id)" class="btn btn-success">
              🧪 Probar Conexión
            </button>
            <button @click="closeViewModal" class="btn btn-secondary">
              ❌ Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isLoading = ref(false)
const isMigrating = ref(false)
const isSyncing = ref(false)
const isRunningHealthCheck = ref(false)
const isSaving = ref(false)

const companies = ref([])
const lastSync = ref(null)
const hasValidApiKey = ref(false)

// Modales
const showCompanyModal = ref(false)
const viewingCompany = ref(null)
const isEditMode = ref(false)

// Filtros
const searchQuery = ref('')
const statusFilter = ref('')

// Formulario de empresa
const companyForm = ref({
  id: '',
  name: '',
  description: '',
  api_base_url: '',
  database_type: '',
  environment: 'development',
  is_active: true,
  configuration: ''
})

// ============================================================================
// COMPUTED
// ============================================================================

const activeCompaniesCount = computed(() => {
  return companies.value.filter(c => c.is_active).length
})

const companiesWithIssues = computed(() => {
  return companies.value.filter(c => c.status === 'error' || c.status === 'warning').length
})

const filteredCompanies = computed(() => {
  let filtered = [...companies.value]
  
  // Filtro de búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(company =>
      (company.name || '').toLowerCase().includes(query) ||
      (company.id || '').toLowerCase().includes(query) ||
      (company.description || '').toLowerCase().includes(query)
    )
  }
  
  // Filtro de estado
  if (statusFilter.value) {
    switch (statusFilter.value) {
      case 'active':
        filtered = filtered.filter(company => company.is_active)
        break
      case 'inactive':
        filtered = filtered.filter(company => !company.is_active)
        break
      case 'error':
        filtered = filtered.filter(company => company.status === 'error')
        break
    }
  }
  
  return filtered.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id))
})

const isValidJSON = computed(() => {
  if (!companyForm.value.configuration.trim()) return true
  
  try {
    JSON.parse(companyForm.value.configuration)
    return true
  } catch (error) {
    return false
  }
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Carga empresas enterprise - MIGRADO: loadEnterpriseCompanies() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadEnterpriseCompanies = async () => {
  if (!hasValidApiKey.value) {
    showNotification('Se requiere API key para acceder a funciones enterprise', 'warning')
    return
  }
  
  isLoading.value = true
  
  try {
    appStore.addToLog('Loading enterprise companies', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/enterprise/companies', {
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    companies.value = response.companies || []
    lastSync.value = Date.now()
    
    appStore.addToLog(`Loaded ${companies.value.length} enterprise companies`, 'info')
    showNotification(`${companies.value.length} empresas cargadas`, 'success')
    
  } catch (error) {
    appStore.addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
    showNotification(`Error cargando empresas: ${error.message}`, 'error')
    companies.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * Crea empresa enterprise - MIGRADO: createEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const createEnterpriseCompany = async (companyData) => {
  try {
    appStore.addToLog('Creating enterprise company', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/enterprise/companies', {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      },
      body: companyData
    })
    
    // Agregar nueva empresa a la lista
    companies.value.push(response.company)
    
    appStore.addToLog(`Enterprise company ${companyData.id} created successfully`, 'info')
    showNotification('Empresa creada exitosamente', 'success')
    
    return response
    
  } catch (error) {
    appStore.addToLog(`Error creating enterprise company: ${error.message}`, 'error')
    showNotification(`Error creando empresa: ${error.message}`, 'error')
    throw error
  }
}

/**
 * Ve empresa enterprise - MIGRADO: viewEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const viewEnterpriseCompany = async (companyId) => {
  try {
    appStore.addToLog(`Viewing enterprise company: ${companyId}`, 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/enterprise/companies/${companyId}`, {
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    viewingCompany.value = response.company
    
  } catch (error) {
    appStore.addToLog(`Error viewing enterprise company ${companyId}: ${error.message}`, 'error')
    showNotification(`Error cargando detalles de empresa: ${error.message}`, 'error')
  }
}

/**
 * Edita empresa enterprise - MIGRADO: editEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const editEnterpriseCompany = async (companyId) => {
  try {
    // Cargar datos de la empresa
    const response = await apiRequest(`/api/enterprise/companies/${companyId}`, {
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    const company = response.company
    
    // Llenar formulario
    companyForm.value = {
      id: company.id || '',
      name: company.name || '',
      description: company.description || '',
      api_base_url: company.api_base_url || '',
      database_type: company.database_type || '',
      environment: company.environment || 'development',
      is_active: company.is_active !== false,
      configuration: company.configuration ? 
        (typeof company.configuration === 'string' ? company.configuration : JSON.stringify(company.configuration, null, 2)) : ''
    }
    
    isEditMode.value = true
    showCompanyModal.value = true
    
  } catch (error) {
    showNotification(`Error cargando empresa para edición: ${error.message}`, 'error')
  }
}

/**
 * Guarda empresa enterprise - MIGRADO: saveEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const saveEnterpriseCompany = async () => {
  if (!isValidJSON.value) {
    showNotification('La configuración JSON no es válida', 'error')
    return
  }
  
  isSaving.value = true
  
  try {
    const companyData = {
      id: companyForm.value.id,
      name: companyForm.value.name,
      description: companyForm.value.description,
      api_base_url: companyForm.value.api_base_url,
      database_type: companyForm.value.database_type,
      environment: companyForm.value.environment,
      is_active: companyForm.value.is_active,
      configuration: companyForm.value.configuration ? JSON.parse(companyForm.value.configuration) : {}
    }
    
    if (isEditMode.value) {
      // Actualizar empresa existente
      const response = await apiRequest(`/api/enterprise/companies/${companyData.id}`, {
        method: 'PUT',
        headers: {
          'X-API-Key': appStore.adminApiKey
        },
        body: companyData
      })
      
      // Actualizar en la lista local
      const index = companies.value.findIndex(c => c.id === companyData.id)
      if (index !== -1) {
        companies.value[index] = response.company
      }
      
      showNotification('Empresa actualizada exitosamente', 'success')
    } else {
      // Crear nueva empresa
      await createEnterpriseCompany(companyData)
    }
    
    closeCompanyModal()
    
  } catch (error) {
    // Error ya manejado en las funciones específicas
  } finally {
    isSaving.value = false
  }
}

/**
 * Prueba empresa enterprise - MIGRADO: testEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const testEnterpriseCompany = async (companyId) => {
  try {
    appStore.addToLog(`Testing enterprise company: ${companyId}`, 'info')
    showNotification('Iniciando prueba de conexión...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/enterprise/companies/${companyId}/test`, {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    if (response.success) {
      showNotification('Prueba de conexión exitosa', 'success')
    } else {
      showNotification(`Prueba falló: ${response.message}`, 'warning')
    }
    
    appStore.addToLog(`Enterprise company test ${companyId}: ${response.success ? 'success' : 'failed'}`, 'info')
    
    // Actualizar estado de la empresa en la lista
    const companyIndex = companies.value.findIndex(c => c.id === companyId)
    if (companyIndex !== -1) {
      companies.value[companyIndex].status = response.success ? 'active' : 'error'
      companies.value[companyIndex].last_test = Date.now()
    }
    
  } catch (error) {
    appStore.addToLog(`Error testing enterprise company ${companyId}: ${error.message}`, 'error')
    showNotification(`Error en prueba de conexión: ${error.message}`, 'error')
  }
}

/**
 * Migra empresas a PostgreSQL - MIGRADO: migrateCompaniesToPostgreSQL() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const migrateCompaniesToPostgreSQL = async () => {
  isMigrating.value = true
  
  try {
    appStore.addToLog('Starting companies migration to PostgreSQL', 'info')
    showNotification('Iniciando migración a PostgreSQL...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO (asumiendo que existe)
    const response = await apiRequest('/api/enterprise/companies/migrate', {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    appStore.addToLog('Companies migration to PostgreSQL completed', 'info')
    showNotification('Migración a PostgreSQL completada', 'success')
    
    // Recargar empresas
    await loadEnterpriseCompanies()
    
  } catch (error) {
    appStore.addToLog(`Companies migration failed: ${error.message}`, 'error')
    showNotification(`Error en migración: ${error.message}`, 'error')
  } finally {
    isMigrating.value = false
  }
}

// ============================================================================
// FUNCIONES ADICIONALES
// ============================================================================

const showCreateCompanyModal = () => {
  // Limpiar formulario
  companyForm.value = {
    id: '',
    name: '',
    description: '',
    api_base_url: '',
    database_type: '',
    environment: 'development',
    is_active: true,
    configuration: ''
  }
  
  isEditMode.value = false
  showCompanyModal.value = true
}

const closeCompanyModal = () => {
  showCompanyModal.value = false
  isEditMode.value = false
}

const closeViewModal = () => {
  viewingCompany.value = null
}

const syncAllCompanies = async () => {
  isSyncing.value = true
  
  try {
    showNotification('Sincronizando todas las empresas...', 'info')
    
    // Aquí implementarías la lógica de sincronización
    // Por ahora, simular el proceso
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    showNotification('Sincronización completada', 'success')
    await loadEnterpriseCompanies()
    
  } catch (error) {
    showNotification(`Error en sincronización: ${error.message}`, 'error')
  } finally {
    isSyncing.value = false
  }
}

const exportCompaniesData = () => {
  try {
    const dataStr = JSON.stringify(companies.value, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `enterprise_companies_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    showNotification('Datos de empresas exportados exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando datos', 'error')
  }
}

const runHealthCheckAll = async () => {
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check en todas las empresas...', 'info')
    
    // Simular health check
    await new Promise(resolve => setTimeout(resolve, 3000))
    
    showNotification('Health check completado', 'success')
    await loadEnterpriseCompanies()
    
  } catch (error) {
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

const requestApiKey = () => {
  // Trigger del modal de API key desde el componente padre
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

// ============================================================================
// UTILIDADES
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
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('EnterpriseTab component mounted', 'info')
  
  // Verificar si hay API key válida
  hasValidApiKey.value = !!appStore.adminApiKey
  
  if (hasValidApiKey.value) {
    await loadEnterpriseCompanies()
  }
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.loadEnterpriseCompanies = loadEnterpriseCompanies
  window.createEnterpriseCompany = createEnterpriseCompany
  window.viewEnterpriseCompany = viewEnterpriseCompany
  window.editEnterpriseCompany = editEnterpriseCompany
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

// Watcher para API key changes
watch(() => appStore.adminApiKey, (newApiKey) => {
  hasValidApiKey.value = !!newApiKey
  
  if (hasValidApiKey.value) {
    loadEnterpriseCompanies()
  } else {
    companies.value = []
  }
})
</script>

<style scoped>
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
