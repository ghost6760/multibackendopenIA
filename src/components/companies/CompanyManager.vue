<!--
  CompanyManager.vue - Gestión de Empresas Enterprise
  MIGRADO DE: script.js funciones createEnterpriseCompany(), editEnterpriseCompany(), loadEnterpriseTab()
  PRESERVAR: Comportamiento exacto de las funciones originales
  COMPATIBILIDAD: 100% con el script.js original
-->

<template>
  <div class="enterprise-section">
    <h3>🏢 Gestión Enterprise de Empresas</h3>
    
    <!-- Estadísticas -->
    <div class="enterprise-stats">
      <div class="stat-card">
        <span class="stat-number">{{ enterpriseStats.total }}</span>
        <span class="stat-label">Empresas Enterprise</span>
      </div>
      <div class="stat-card">
        <span class="stat-number">{{ enterpriseStats.active }}</span>
        <span class="stat-label">Activas</span>
      </div>
      <div class="stat-card">
        <span class="stat-number">{{ enterpriseStats.inactive }}</span>
        <span class="stat-label">Inactivas</span>
      </div>
    </div>
    
    <!-- Verificación API Key -->
    <div v-if="!appStore.adminApiKey" class="warning-message">
      <h3>⚠️ API Key Requerida</h3>
      <p>Se requiere API key para gestionar empresas enterprise</p>
      <button @click="showApiKeyModal" class="btn btn-primary">
        🔑 Configurar API Key
      </button>
    </div>
    
    <!-- Formulario de Creación -->
    <div v-else class="enterprise-create">
      <h4>➕ Crear Nueva Empresa Enterprise</h4>
      <form ref="createForm" class="enterprise-form" @submit.prevent="createEnterpriseCompany">
        <div class="form-grid">
          <div class="form-group">
            <label>ID de empresa (solo minúsculas, números y _):</label>
            <input 
              type="text" 
              v-model="createForm.company_id"
              pattern="[a-z0-9_]+" 
              required 
              placeholder="ej: spa_wellness"
              @input="validateCompanyId"
            >
            <span v-if="validationErrors.company_id" class="validation-error">
              {{ validationErrors.company_id }}
            </span>
          </div>
          
          <div class="form-group">
            <label>Nombre de empresa:</label>
            <input 
              type="text" 
              v-model="createForm.company_name"
              required 
              placeholder="ej: Wellness Spa & Relax"
            >
          </div>
          
          <div class="form-group">
            <label>Tipo de negocio:</label>
            <select v-model="createForm.business_type" required>
              <option value="general">General</option>
              <option value="healthcare">Salud</option>
              <option value="beauty">Belleza</option>
              <option value="dental">Dental</option>
              <option value="spa">Spa & Wellness</option>
              <option value="clinic">Clínica</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Nombre del agente de ventas:</label>
            <input 
              type="text" 
              v-model="createForm.sales_agent_name"
              placeholder="ej: María Asistente"
            >
          </div>
          
          <div class="form-group">
            <label>URL del servicio de citas:</label>
            <input 
              type="url" 
              v-model="createForm.schedule_service_url"
              placeholder="https://calendly.com/tu-empresa"
            >
          </div>
          
          <div class="form-group">
            <label>Zona horaria:</label>
            <select v-model="createForm.timezone">
              <option value="America/Bogota">América/Bogotá (UTC-5)</option>
              <option value="America/Mexico_City">América/Ciudad_México (UTC-6)</option>
              <option value="America/Lima">América/Lima (UTC-5)</option>
              <option value="America/Santiago">América/Santiago (UTC-3)</option>
              <option value="Europe/Madrid">Europa/Madrid (UTC+1)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Moneda:</label>
            <select v-model="createForm.currency">
              <option value="COP">COP (Peso Colombiano)</option>
              <option value="USD">USD (Dólar Americano)</option>
              <option value="EUR">EUR (Euro)</option>
              <option value="MXN">MXN (Peso Mexicano)</option>
              <option value="PEN">PEN (Sol Peruano)</option>
              <option value="CLP">CLP (Peso Chileno)</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Tier de suscripción:</label>
            <select v-model="createForm.subscription_tier" required>
              <option value="basic">Basic</option>
              <option value="premium">Premium</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          
          <div class="form-group full-width">
            <label>Servicios ofrecidos:</label>
            <textarea 
              v-model="createForm.services"
              required 
              rows="3" 
              placeholder="relajación, bienestar y terapias holísticas"
            ></textarea>
          </div>
        </div>
        
        <button 
          type="submit" 
          class="btn btn-primary"
          :disabled="isCreating || !isFormValid"
        >
          <span v-if="isCreating">⏳ Creando...</span>
          <span v-else>➕ Crear Empresa Enterprise</span>
        </button>
      </form>
      
      <!-- Resultado de creación -->
      <div v-if="createResult" class="create-result">
        <div v-if="createResult.success" class="result-container result-success">
          <h4>✅ Empresa Enterprise Creada</h4>
          <p><strong>ID:</strong> {{ createResult.data.company_id }}</p>
          <p><strong>Nombre:</strong> {{ createResult.data.company_name }}</p>
          <p><strong>Arquitectura:</strong> {{ createResult.data.architecture }}</p>
          
          <h5>Estado de Configuración:</h5>
          <div class="setup-status">
            <div 
              v-for="(value, key) in createResult.data.setup_status" 
              :key="key"
              class="status-item"
            >
              <span 
                class="status-indicator"
                :class="{
                  'success': typeof value === 'boolean' && value,
                  'error': typeof value === 'boolean' && !value,
                  'info': typeof value !== 'boolean'
                }"
              ></span>
              {{ key }}: {{ typeof value === 'boolean' ? (value ? '✅' : '❌') : value }}
            </div>
          </div>
          
          <h5>Próximos Pasos:</h5>
          <ol>
            <li v-for="step in createResult.data.next_steps" :key="step">
              {{ step }}
            </li>
          </ol>
        </div>
        
        <div v-else class="result-container result-error">
          <p>❌ Error al crear empresa enterprise</p>
          <p>{{ createResult.error }}</p>
        </div>
      </div>
    </div>
    
    <!-- Herramientas de Administración -->
    <div v-if="appStore.adminApiKey" class="enterprise-admin">
      <h4>🛠️ Herramientas de Administración</h4>
      <div class="admin-tools">
        <button 
          @click="migrateCompaniesToPostgreSQL" 
          class="btn btn-secondary"
          :disabled="isMigrating"
        >
          <span v-if="isMigrating">⏳ Migrando...</span>
          <span v-else>🔄 Migrar desde JSON a PostgreSQL</span>
        </button>
        
        <button 
          @click="reloadEnterpriseCompanies" 
          class="btn btn-info"
          :disabled="isReloading"
        >
          <span v-if="isReloading">⏳ Recargando...</span>
          <span v-else>📋 Recargar Lista</span>
        </button>
        
        <button 
          @click="reloadCompaniesConfig" 
          class="btn btn-warning"
          :disabled="isReloadingConfig"
        >
          <span v-if="isReloadingConfig">⏳ Recargando...</span>
          <span v-else>🔧 Recargar Configuración</span>
        </button>
      </div>
    </div>
    
    <!-- Modal de Edición -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content" style="max-width: 70%; max-height: 80%; overflow-y: auto;" @click.stop>
        <div class="modal-header">
          <h3>✏️ Editar {{ editForm.company_name }}</h3>
          <button @click="closeEditModal" class="modal-close">&times;</button>
        </div>
        
        <form @submit.prevent="saveEnterpriseCompany" class="enterprise-edit-form">
          <div class="form-section">
            <h4>📋 Información Básica</h4>
            <div class="form-grid">
              <div class="form-group">
                <label>Nombre de empresa:</label>
                <input 
                  type="text" 
                  v-model="editForm.company_name" 
                  required
                >
              </div>
              <div class="form-group">
                <label>Tipo de negocio:</label>
                <select v-model="editForm.business_type">
                  <option value="general">General</option>
                  <option value="healthcare">Salud</option>
                  <option value="beauty">Belleza</option>
                  <option value="dental">Dental</option>
                  <option value="spa">Spa & Wellness</option>
                  <option value="clinic">Clínica</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="form-section">
            <h4>🤖 Configuración de Agente</h4>
            <div class="form-grid">
              <div class="form-group">
                <label>Nombre del agente:</label>
                <input 
                  type="text" 
                  v-model="editForm.sales_agent_name"
                >
              </div>
              <div class="form-group">
                <label>Modelo:</label>
                <select v-model="editForm.model_name">
                  <option value="gpt-4o-mini">GPT-4O Mini</option>
                  <option value="gpt-4o">GPT-4O</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="form-section">
            <h4>🌐 Configuración Regional</h4>
            <div class="form-grid">
              <div class="form-group">
                <label>Zona horaria:</label>
                <select v-model="editForm.timezone">
                  <option value="America/Bogota">América/Bogotá (UTC-5)</option>
                  <option value="America/Mexico_City">América/Ciudad_México (UTC-6)</option>
                  <option value="America/Lima">América/Lima (UTC-5)</option>
                  <option value="America/Santiago">América/Santiago (UTC-3)</option>
                  <option value="Europe/Madrid">Europa/Madrid (UTC+1)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>
              <div class="form-group">
                <label>Moneda:</label>
                <select v-model="editForm.currency">
                  <option value="COP">COP (Peso Colombiano)</option>
                  <option value="USD">USD (Dólar Americano)</option>
                  <option value="EUR">EUR (Euro)</option>
                  <option value="MXN">MXN (Peso Mexicano)</option>
                  <option value="PEN">PEN (Sol Peruano)</option>
                  <option value="CLP">CLP (Peso Chileno)</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="form-section">
            <h4>📋 Servicios</h4>
            <div class="form-group full-width">
              <label>Servicios ofrecidos:</label>
              <textarea 
                v-model="editForm.services" 
                rows="4"
                placeholder="Lista de servicios separados por comas"
              ></textarea>
            </div>
          </div>
          
          <div class="modal-footer">
            <button 
              type="button" 
              @click="closeEditModal" 
              class="btn btn-secondary"
            >
              Cancelar
            </button>
            <button 
              type="submit" 
              class="btn btn-primary"
              :disabled="isSaving"
            >
              <span v-if="isSaving">⏳ Guardando...</span>
              <span v-else>💾 Guardar Cambios</span>
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Loading Overlay -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner">⏳ Procesando...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

// ============================================================================
// COMPOSABLES Y STORES
// ============================================================================

const appStore = useAppStore()
const { apiRequest, apiRequestWithKey } = useApiRequest()
const { showNotification } = useNotifications()
const { addToLog } = useSystemLog()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const isLoading = ref(false)
const isCreating = ref(false)
const isMigrating = ref(false)
const isReloading = ref(false)
const isReloadingConfig = ref(false)
const isSaving = ref(false)

const showEditModal = ref(false)
const enterpriseCompanies = ref([])
const createResult = ref(null)
const validationErrors = ref({})

// Formulario de creación - PRESERVAR ESTRUCTURA EXACTA
const createForm = ref({
  company_id: '',
  company_name: '',
  business_type: 'general',
  services: '',
  sales_agent_name: '',
  schedule_service_url: '',
  timezone: 'America/Bogota',
  currency: 'COP',
  subscription_tier: 'basic'
})

// Formulario de edición
const editForm = ref({})
const editingCompanyId = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const enterpriseStats = computed(() => {
  const stats = {
    total: enterpriseCompanies.value.length,
    active: 0,
    inactive: 0
  }
  
  enterpriseCompanies.value.forEach(company => {
    if (company.is_active) {
      stats.active++
    } else {
      stats.inactive++
    }
  })
  
  return stats
})

const isFormValid = computed(() => {
  return createForm.value.company_id && 
         createForm.value.company_name && 
         createForm.value.services &&
         Object.keys(validationErrors.value).length === 0
})

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DE SCRIPT.JS
// ============================================================================

/**
 * Crea una nueva empresa enterprise - MIGRADO: createEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const createEnterpriseCompany = async () => {
  // Validaciones básicas - PRESERVAR LÓGICA EXACTA
  if (!createForm.value.company_id || !createForm.value.company_name || !createForm.value.services) {
    showNotification('Por favor completa los campos obligatorios (ID, Nombre y Servicios)', 'warning')
    return
  }
  
  // Validar formato de company_id - PRESERVAR VALIDACIÓN EXACTA
  if (!/^[a-z0-9_]+$/.test(createForm.value.company_id)) {
    showNotification('El ID de empresa solo puede contener letras minúsculas, números y guiones bajos', 'warning')
    return
  }
  
  try {
    isCreating.value = true
    createResult.value = null
    
    addToLog(`Creating enterprise company: ${createForm.value.company_id}`, 'info')
    
    // PRESERVAR: Llamada API exacta como en script.js
    const response = await apiRequestWithKey('/api/admin/companies/create', {
      method: 'POST',
      body: createForm.value
    })
    
    showNotification(`Empresa enterprise ${createForm.value.company_id} creada exitosamente`, 'success')
    addToLog(`Enterprise company created successfully: ${createForm.value.company_id}`, 'success')
    
    // PRESERVAR: Mostrar resultado como script.js
    createResult.value = {
      success: true,
      data: response
    }
    
    // Limpiar formulario - PRESERVAR COMPORTAMIENTO
    resetCreateForm()
    
    // Recargar lista
    await loadEnterpriseCompanies()
    
  } catch (error) {
    addToLog(`Error creating enterprise company: ${error.message}`, 'error')
    showNotification('Error al crear empresa enterprise: ' + error.message, 'error')
    
    createResult.value = {
      success: false,
      error: error.message
    }
  } finally {
    isCreating.value = false
  }
}

/**
 * Edita una empresa enterprise - MIGRADO: editEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const editEnterpriseCompany = async (companyId) => {
  try {
    addToLog(`Loading company for edit: ${companyId}`, 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`)
    const config = response.configuration
    
    // PRESERVAR: Estructura de editForm como script.js
    editForm.value = {
      company_name: config.company_name || '',
      business_type: config.business_type || 'general',
      sales_agent_name: config.sales_agent_name || '',
      model_name: config.model_name || 'gpt-4o-mini',
      timezone: config.timezone || 'America/Bogota',
      currency: config.currency || 'COP',
      services: config.services || ''
    }
    
    editingCompanyId.value = companyId
    showEditModal.value = true
    
  } catch (error) {
    addToLog(`Error loading company for edit: ${error.message}`, 'error')
    showNotification('Error al cargar empresa: ' + error.message, 'error')
  }
}

/**
 * Guarda cambios de empresa editada - NUEVA FUNCIÓN BASADA EN PATRÓN SCRIPT.JS
 */
const saveEnterpriseCompany = async () => {
  try {
    isSaving.value = true
    
    addToLog(`Saving changes for company: ${editingCompanyId.value}`, 'info')
    
    // Llamada API para guardar cambios
    await apiRequestWithKey(`/api/admin/companies/${editingCompanyId.value}`, {
      method: 'PUT',
      body: editForm.value
    })
    
    showNotification('Empresa actualizada exitosamente', 'success')
    addToLog(`Enterprise company updated: ${editingCompanyId.value}`, 'success')
    
    closeEditModal()
    await loadEnterpriseCompanies()
    
  } catch (error) {
    addToLog(`Error saving company: ${error.message}`, 'error')
    showNotification('Error al guardar empresa: ' + error.message, 'error')
  } finally {
    isSaving.value = false
  }
}

/**
 * Migra empresas de JSON a PostgreSQL - MIGRADO: migrateCompaniesToPostgreSQL() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const migrateCompaniesToPostgreSQL = async () => {
  try {
    isMigrating.value = true
    
    addToLog('Starting companies migration to PostgreSQL', 'info')
    showNotification('Iniciando migración a PostgreSQL...', 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    const response = await apiRequestWithKey('/api/admin/migrate-companies', {
      method: 'POST'
    })
    
    showNotification('Migración completada exitosamente', 'success')
    addToLog(`Migration completed: ${response.migrated_count} companies migrated`, 'success')
    
    // Recargar lista después de migración
    await loadEnterpriseCompanies()
    
  } catch (error) {
    addToLog(`Error in migration: ${error.message}`, 'error')
    showNotification('Error en migración: ' + error.message, 'error')
  } finally {
    isMigrating.value = false
  }
}

/**
 * Recarga configuración de empresas - PRESERVAR FUNCIÓN EXACTA
 */
const reloadCompaniesConfig = async () => {
  try {
    isReloadingConfig.value = true
    
    addToLog('Reloading companies configuration', 'info')
    showNotification('Recargando configuración...', 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    await apiRequestWithKey('/api/admin/reload-companies', {
      method: 'POST'
    })
    
    showNotification('Configuración recargada exitosamente', 'success')
    addToLog('Companies configuration reloaded', 'success')
    
  } catch (error) {
    addToLog(`Error reloading config: ${error.message}`, 'error')
    showNotification('Error recargando configuración: ' + error.message, 'error')
  } finally {
    isReloadingConfig.value = false
  }
}

/**
 * Carga empresas enterprise - MIGRADO: loadEnterpriseCompanies() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadEnterpriseCompanies = async () => {
  try {
    isReloading.value = true
    
    addToLog('Loading enterprise companies', 'info')
    
    // PRESERVAR: Llamada API exacta como script.js
    const response = await apiRequestWithKey('/api/admin/companies', {
      method: 'GET'
    })
    
    enterpriseCompanies.value = response.companies || []
    addToLog(`Enterprise companies loaded: ${enterpriseCompanies.value.length}`, 'success')
    
    // Emitir evento para CompanyList
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent('enterpriseCompaniesLoaded', {
        detail: { companies: enterpriseCompanies.value }
      }))
    }
    
  } catch (error) {
    addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
    showNotification('Error cargando empresas enterprise: ' + error.message, 'error')
  } finally {
    isReloading.value = false
  }
}

const reloadEnterpriseCompanies = loadEnterpriseCompanies

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

/**
 * Validar ID de empresa
 */
const validateCompanyId = () => {
  const companyId = createForm.value.company_id
  
  if (companyId && !/^[a-z0-9_]+$/.test(companyId)) {
    validationErrors.value.company_id = 'Solo minúsculas, números y guiones bajos'
  } else {
    delete validationErrors.value.company_id
  }
}

/**
 * Mostrar modal de API Key - PRESERVAR FUNCIÓN EXACTA
 */
const showApiKeyModal = () => {
  if (typeof window.showApiKeyModal === 'function') {
    window.showApiKeyModal()
  }
}

/**
 * Cerrar modal de edición
 */
const closeEditModal = () => {
  showEditModal.value = false
  editForm.value = {}
  editingCompanyId.value = ''
}

/**
 * Resetear formulario de creación
 */
const resetCreateForm = () => {
  createForm.value = {
    company_id: '',
    company_name: '',
    business_type: 'general',
    services: '',
    sales_agent_name: '',
    schedule_service_url: '',
    timezone: 'America/Bogota',
    currency: 'COP',
    subscription_tier: 'basic'
  }
  validationErrors.value = {}
}

// ============================================================================
// LIFECYCLE Y WRAPPERS DE COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // PRESERVAR: Registrar funciones globales como script.js
  window.createEnterpriseCompany = createEnterpriseCompany
  window.editEnterpriseCompany = editEnterpriseCompany
  window.migrateCompaniesToPostgreSQL = migrateCompaniesToPostgreSQL
  window.reloadCompaniesConfig = reloadCompaniesConfig
  window.loadEnterpriseCompanies = loadEnterpriseCompanies
  
  // Cargar datos iniciales si hay API key
  if (appStore.adminApiKey) {
    loadEnterpriseCompanies()
  }
  
  addToLog('CompanyManager component mounted', 'info')
})

onUnmounted(() => {
  // Limpiar funciones globales
  delete window.createEnterpriseCompany
  delete window.editEnterpriseCompany
  delete window.migrateCompaniesToPostgreSQL
  delete window.reloadCompaniesConfig
  delete window.loadEnterpriseCompanies
})

// ============================================================================
// EXPORTAR FUNCIONES PARA COMPANYLIST
// ============================================================================

defineExpose({
  loadEnterpriseCompanies,
  editEnterpriseCompany,
  enterpriseCompanies
})
</script>

<style scoped>
/* Heredar estilos del CSS principal */
.enterprise-section {
  padding: 20px;
}

.enterprise-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
  min-width: 150px;
  flex: 1;
}

.stat-number {
  display: block;
  font-size: 2em;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 0.9em;
  opacity: 0.9;
}

.enterprise-form .form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.enterprise-form .full-width {
  grid-column: 1 / -1;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.validation-error {
  color: #dc2626;
  font-size: 0.875em;
  margin-top: 4px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-secondary {
  background: linear-gradient(135deg, #6b7280, #4b5563);
  color: white;
}

.btn-info {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: white;
}

.btn-warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.admin-tools {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.create-result {
  margin-top: 20px;
  padding: 20px;
  border-radius: 8px;
}

.result-container {
  padding: 20px;
  border-radius: 8px;
  margin: 15px 0;
}

.result-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.result-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
}

.setup-status {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin: 15px 0;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-indicator.success {
  background: #22c55e;
}

.status-indicator.error {
  background: #ef4444;
}

.status-indicator.info {
  background: #3b82f6;
}

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

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.form-section {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.form-section:last-child {
  border-bottom: none;
}

.form-section h4 {
  margin: 0 0 15px 0;
  color: #374151;
}

.warning-message {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  color: #92400e;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
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

.loading-spinner {
  background: white;
  padding: 20px 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  font-size: 18px;
}

@media (max-width: 768px) {
  .enterprise-stats {
    flex-direction: column;
  }
  
  .enterprise-form .form-grid {
    grid-template-columns: 1fr;
  }
  
  .admin-tools {
    flex-direction: column;
  }
  
  .modal-content {
    width: 95%;
    max-height: 90vh;
    margin: 20px;
  }
}
</style>
