<template>
  <div class="enterprise-companies-list">
    <!-- Header con estadísticas y herramientas -->
    <div class="list-header">
      <div class="header-info">
        <h4>📋 Empresas Enterprise Configuradas</h4>
        <div class="stats">
          <span class="total-count">
            Total: <strong>{{ companies.length }}</strong>
          </span>
          <span class="active-count">
            Activas: <strong>{{ activeCompaniesCount }}</strong>
          </span>
          <span class="inactive-count" v-if="inactiveCompaniesCount > 0">
            Inactivas: <strong>{{ inactiveCompaniesCount }}</strong>
          </span>
        </div>
      </div>
      
      <div class="list-actions">
        <button 
          @click="$emit('refresh')" 
          :disabled="isLoading"
          class="btn btn-info"
          title="Recargar lista de empresas"
        >
          <span v-if="isLoading">🔄</span>
          <span v-else>📋</span>
          {{ isLoading ? 'Cargando...' : 'Recargar Lista' }}
        </button>
        
        <button 
          @click="$emit('create')"
          class="btn btn-primary"
          title="Crear nueva empresa enterprise"
        >
          ➕ Nueva Empresa
        </button>

        <button 
          @click="$emit('export', 'json')"
          class="btn btn-secondary"
          title="Exportar empresas en formato JSON"
        >
          📤 Exportar
        </button>
      </div>
    </div>

    <!-- Filtros y búsqueda -->
    <div class="list-filters">
      <div class="search-section">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Buscar por nombre, ID o tipo de negocio..."
          class="search-input"
        />
        <select v-model="statusFilter" class="filter-select">
          <option value="">Todos los estados</option>
          <option value="active">Solo activas</option>
          <option value="inactive">Solo inactivas</option>
        </select>
        <select v-model="businessTypeFilter" class="filter-select">
          <option value="">Todos los tipos</option>
          <option value="spa">SPA & Wellness</option>
          <option value="healthcare">Salud</option>
          <option value="beauty">Belleza</option>
          <option value="dental">Dental</option>
          <option value="retail">Retail</option>
          <option value="technology">Tecnología</option>
          <option value="consulting">Consultoría</option>
          <option value="general">General</option>
        </select>
        <button 
          v-if="hasActiveFilters" 
          @click="clearFilters"
          class="btn btn-outline-small"
          title="Limpiar filtros"
        >
          🗑️ Limpiar
        </button>
      </div>
    </div>

    <!-- Estado de carga -->
    <div v-if="isLoading && companies.length === 0" class="loading-state">
      <div class="loading-spinner">🔄</div>
      <p>Cargando empresas enterprise...</p>
    </div>

    <!-- Error state -->
    <div v-if="error && !isLoading" class="enterprise-error">
      <div class="result-container result-error">
        <h4>❌ Error al cargar empresas enterprise</h4>
        <p>{{ error }}</p>
        <button @click="$emit('refresh')" class="btn btn-secondary">
          🔄 Reintentar
        </button>
      </div>
    </div>

    <!-- Lista vacía -->
    <div v-if="!isLoading && companies.length === 0 && !error" class="empty-state">
      <div class="result-container result-info">
        <div class="empty-icon">🏢</div>
        <h4>No hay empresas enterprise configuradas</h4>
        <p>Utiliza el botón "Nueva Empresa" para crear la primera empresa enterprise.</p>
        <button @click="$emit('create')" class="btn btn-primary">
          ➕ Crear Primera Empresa
        </button>
      </div>
    </div>

    <!-- Lista filtrada vacía -->
    <div v-if="!isLoading && companies.length > 0 && filteredCompanies.length === 0" class="empty-filtered-state">
      <div class="result-container result-warning">
        <div class="empty-icon">🔍</div>
        <h4>No se encontraron empresas</h4>
        <p>No hay empresas que coincidan con los filtros aplicados.</p>
        <button @click="clearFilters" class="btn btn-secondary">
          🗑️ Limpiar Filtros
        </button>
      </div>
    </div>

    <!-- Grid de empresas -->
    <div v-if="filteredCompanies.length > 0" class="companies-grid">
      <div 
        v-for="company in paginatedCompanies" 
        :key="company.company_id"
        class="company-card"
        :class="{ 
          'company-inactive': !company.is_active,
          'company-error': company.status === 'error'
        }"
      >
        <!-- Header de la empresa -->
        <div class="company-header">
          <div class="company-title">
            <h5>{{ company.company_name || company.company_id }}</h5>
            <div class="company-badges">
              <span 
                class="status-badge"
                :class="getStatusClass(company.is_active, company.status)"
              >
                {{ getStatusText(company.is_active, company.status) }}
              </span>
              <span 
                v-if="company.business_type" 
                class="business-type-badge"
                :class="`business-${company.business_type}`"
              >
                {{ formatBusinessType(company.business_type) }}
              </span>
              <span 
                v-if="company.environment" 
                class="environment-badge" 
                :class="`env-${company.environment}`"
              >
                {{ company.environment.toUpperCase() }}
              </span>
            </div>
          </div>
          
          <div class="company-actions">
            <button 
              @click="$emit('view', company.company_id)" 
              class="btn btn-xs btn-info"
              title="Ver detalles completos"
            >
              👁️ Ver
            </button>
            <button 
              @click="$emit('edit', company.company_id)" 
              class="btn btn-xs btn-primary"
              title="Editar empresa"
            >
              ✏️ Editar
            </button>
            <button 
              @click="$emit('test', company.company_id)" 
              class="btn btn-xs btn-success"
              title="Probar conexión"
            >
              🧪 Test
            </button>
          </div>
        </div>

        <!-- Detalles de la empresa -->
        <div class="company-details">
          <div class="detail-row">
            <strong>ID:</strong> 
            <span class="company-id">{{ company.company_id }}</span>
          </div>
          
          <div class="detail-row" v-if="company.sales_agent_name">
            <strong>Agente:</strong> 
            <span>{{ company.sales_agent_name }}</span>
          </div>
          
          <div class="detail-row" v-if="company.subscription_tier">
            <strong>Plan:</strong> 
            <span class="plan-badge" :class="`plan-${company.subscription_tier}`">
              {{ company.subscription_tier.toUpperCase() }}
            </span>
          </div>
          
          <div class="detail-row" v-if="company.api_base_url">
            <strong>API Base:</strong> 
            <span class="url-text">{{ truncateUrl(company.api_base_url) }}</span>
          </div>
          
          <div class="detail-row" v-if="company.database_type">
            <strong>Database:</strong> 
            <span>{{ company.database_type.toUpperCase() }}</span>
          </div>
          
          <div v-if="company.services" class="detail-row">
            <strong>Servicios:</strong> 
            <span class="services-preview">{{ truncateText(company.services, 80) }}</span>
          </div>
          
          <div v-if="company.description" class="detail-row">
            <strong>Descripción:</strong> 
            <span>{{ truncateText(company.description, 100) }}</span>
          </div>

          <!-- Información técnica adicional -->
          <div class="technical-info">
            <div class="tech-item" v-if="company.timezone">
              <span class="tech-label">⏰</span>
              <span class="tech-value">{{ company.timezone }}</span>
            </div>
            <div class="tech-item" v-if="company.currency">
              <span class="tech-label">💰</span>
              <span class="tech-value">{{ company.currency }}</span>
            </div>
            <div class="tech-item" v-if="company.schedule_service_url">
              <span class="tech-label">📅</span>
              <span class="tech-value">Agenda configurada</span>
            </div>
          </div>
        </div>

        <!-- Footer con información de tiempo -->
        <div class="company-footer">
          <div class="time-info">
            <span v-if="company.created_at" class="created-time">
              Creada: {{ formatDate(company.created_at) }}
            </span>
            <span v-if="company.updated_at || company.last_modified" class="updated-time">
              Actualizada: {{ formatDate(company.updated_at || company.last_modified) }}
            </span>
          </div>
          
          <!-- Acciones adicionales -->
          <div class="additional-actions">
            <button 
              v-if="company.is_active"
              @click="$emit('toggle-status', company.company_id, false)"
              class="btn btn-xs btn-warning"
              title="Desactivar empresa"
            >
              ⏸️
            </button>
            <button 
              v-else
              @click="$emit('toggle-status', company.company_id, true)"
              class="btn btn-xs btn-success"
              title="Activar empresa"
            >
              ▶️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="filteredCompanies.length > itemsPerPage" class="pagination">
      <button 
        @click="currentPage = Math.max(1, currentPage - 1)"
        :disabled="currentPage === 1"
        class="btn btn-outline-small"
      >
        ⬅️ Anterior
      </button>
      
      <span class="pagination-info">
        Página {{ currentPage }} de {{ totalPages }} 
        ({{ filteredCompanies.length }} empresas)
      </span>
      
      <button 
        @click="currentPage = Math.min(totalPages, currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="btn btn-outline-small"
      >
        Siguiente ➡️
      </button>
    </div>

    <!-- Footer con información adicional -->
    <div v-if="companies.length > 0" class="list-footer">
      <div class="footer-info">
        <span class="last-sync" v-if="lastSync">
          Última actualización: {{ formatDate(lastSync) }}
        </span>
        <span class="filter-info" v-if="hasActiveFilters">
          Mostrando {{ filteredCompanies.length }} de {{ companies.length }} empresas
        </span>
      </div>
      
      <div class="footer-actions">
        <button 
          @click="$emit('migrate')"
          class="btn btn-secondary"
          title="Migrar desde JSON a PostgreSQL"
        >
          🔄 Migrar a PostgreSQL
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  companies: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  lastSync: {
    type: Number,
    default: null
  }
})

const emit = defineEmits([
  'refresh',
  'create', 
  'view',
  'edit',
  'test',
  'toggle-status',
  'migrate',
  'export'
])

// ============================================================================
// REACTIVE DATA
// ============================================================================

const searchQuery = ref('')
const statusFilter = ref('')
const businessTypeFilter = ref('')
const currentPage = ref(1)
const itemsPerPage = 6

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const activeCompaniesCount = computed(() => {
  return props.companies.filter(company => company.is_active !== false).length
})

const inactiveCompaniesCount = computed(() => {
  return props.companies.filter(company => company.is_active === false).length
})

const hasActiveFilters = computed(() => {
  return searchQuery.value.trim() || statusFilter.value || businessTypeFilter.value
})

const filteredCompanies = computed(() => {
  let filtered = [...props.companies]
  
  // Filtro de búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(company =>
      (company.company_name || '').toLowerCase().includes(query) ||
      (company.company_id || '').toLowerCase().includes(query) ||
      (company.business_type || '').toLowerCase().includes(query) ||
      (company.description || '').toLowerCase().includes(query) ||
      (company.services || '').toLowerCase().includes(query)
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
    }
  }
  
  // Filtro de tipo de negocio
  if (businessTypeFilter.value) {
    filtered = filtered.filter(company => company.business_type === businessTypeFilter.value)
  }
  
  // Ordenar por nombre
  return filtered.sort((a, b) => 
    (a.company_name || a.company_id).localeCompare(b.company_name || b.company_id)
  )
})

const totalPages = computed(() => {
  return Math.ceil(filteredCompanies.value.length / itemsPerPage)
})

const paginatedCompanies = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredCompanies.value.slice(start, end)
})

// ============================================================================
// WATCHERS
// ============================================================================

// Reset página cuando cambian los filtros
watch([searchQuery, statusFilter, businessTypeFilter], () => {
  currentPage.value = 1
})

// ============================================================================
// METHODS
// ============================================================================

const clearFilters = () => {
  searchQuery.value = ''
  statusFilter.value = ''
  businessTypeFilter.value = ''
  currentPage.value = 1
}

const getStatusClass = (isActive, status) => {
  if (status === 'error') return 'status-error'
  if (isActive === false) return 'status-inactive'
  return 'status-success'
}

const getStatusText = (isActive, status) => {
  if (status === 'error') return '❌ Error'
  if (isActive === false) return '⏸️ Inactiva'
  return '✅ Activa'
}

const formatBusinessType = (type) => {
  const types = {
    spa: 'SPA',
    healthcare: 'Salud', 
    beauty: 'Belleza',
    dental: 'Dental',
    retail: 'Retail',
    technology: 'Tech',
    consulting: 'Consultoría',
    general: 'General'
  }
  return types[type] || type.toUpperCase()
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

const truncateUrl = (url) => {
  if (!url) return ''
  try {
    const urlObj = new URL(url)
    return urlObj.hostname + (urlObj.pathname !== '/' ? urlObj.pathname : '')
  } catch {
    return truncateText(url, 30)
  }
}

const formatDate = (timestamp) => {
  if (!timestamp) return 'N/A'
  
  try {
    const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date(timestamp)
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short', 
      day: 'numeric'
    })
  } catch {
    return 'Fecha inválida'
  }
}
</script>

<style scoped>
.enterprise-companies-list {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

/* Header */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.header-info h4 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 1.2em;
}

.stats {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.total-count, .active-count, .inactive-count {
  background: #e9ecef;
  padding: 5px 12px;
  border-radius: 15px;
  font-size: 0.9em;
}

.active-count {
  background: #d4edda;
  color: #155724;
}

.inactive-count {
  background: #f8d7da;
  color: #721c24;
}

.list-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* Filtros */
.list-filters {
  margin-bottom: 20px;
}

.search-section {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 250px;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.9em;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: white;
  font-size: 0.9em;
}

/* Estados */
.loading-state, .empty-state, .empty-filtered-state {
  text-align: center;
  padding: 40px 20px;
}

.loading-spinner {
  font-size: 2em;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 15px;
  opacity: 0.6;
}

.enterprise-error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 5px;
  padding: 20px;
  margin: 20px 0;
}

/* Grid de empresas */
.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.company-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.company-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.company-card.company-inactive {
  opacity: 0.7;
  border-left: 4px solid #ffc107;
}

.company-card.company-error {
  border-left: 4px solid #dc3545;
}

/* Header de empresa */
.company-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  gap: 10px;
}

.company-title h5 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 1.1em;
}

.company-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.status-badge, .business-type-badge, .environment-badge, .plan-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: bold;
  text-transform: uppercase;
}

.status-success {
  background: #d4edda;
  color: #155724;
}

.status-inactive {
  background: #fff3cd;
  color: #856404;
}

.status-error {
  background: #f8d7da;
  color: #721c24;
}

.business-type-badge {
  background: #e2e3e5;
  color: #495057;
}

.business-spa {
  background: #d1ecf1;
  color: #0c5460;
}

.business-healthcare {
  background: #d4edda;
  color: #155724;
}

.business-beauty {
  background: #f8d7da;
  color: #721c24;
}

.environment-badge {
  background: #e9ecef;
  color: #495057;
}

.env-development {
  background: #fff3cd;
  color: #856404;
}

.env-staging {
  background: #cce5ff;
  color: #0066cc;
}

.env-production {
  background: #d4edda;
  color: #155724;
}

.company-actions {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

/* Detalles */
.company-details {
  flex: 1;
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}

.detail-row strong {
  min-width: 80px;
  color: #495057;
  font-size: 0.9em;
  flex-shrink: 0;
}

.detail-row span {
  color: #333;
  font-size: 0.9em;
  word-break: break-word;
  flex: 1;
}

.company-id {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.85em !important;
}

.url-text {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.85em !important;
}

.services-preview {
  font-style: italic;
  color: #6c757d !important;
}

.plan-badge {
  display: inline-block;
  margin-top: 2px;
}

.plan-basic {
  background: #fff3cd;
  color: #856404;
}

.plan-premium {
  background: #cce5ff;
  color: #0066cc;
}

.plan-enterprise {
  background: #d4edda;
  color: #155724;
}

/* Información técnica */
.technical-info {
  display: flex;
  gap: 15px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.tech-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8em;
  color: #6c757d;
}

.tech-label {
  font-size: 1em;
}

.tech-value {
  font-weight: 500;
}

/* Footer de empresa */
.company-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #eee;
  margin-top: auto;
}

.time-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.8em;
  color: #6c757d;
}

.additional-actions {
  display: flex;
  gap: 5px;
}

/* Paginación */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin: 30px 0;
  padding: 20px;
  background: white;
  border-radius: 8px;
}

.pagination-info {
  font-size: 0.9em;
  color: #6c757d;
}

/* Footer */
.list-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #dee2e6;
  flex-wrap: wrap;
  gap: 15px;
}

.footer-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.footer-info span {
  color: #6c757d;
  font-size: 0.9em;
}

.filter-info {
  font-weight: 500;
  color: #495057 !important;
}

.footer-actions {
  display: flex;
  gap: 10px;
}

/* Botones */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 0.8em;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #138496;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #1e7e34;
}

.btn-warning {
  background: #ffc107;
  color: #212529;
}

.btn-warning:hover:not(:disabled) {
  background: #e0a800;
}

.btn-outline-small {
  background: transparent;
  color: #6c757d;
  border: 1px solid #6c757d;
  padding: 4px 8px;
  font-size: 0.8em;
}

.btn-outline-small:hover:not(:disabled) {
  background: #6c757d;
  color: white;
}

/* Result containers */
.result-container {
  padding: 20px;
  border-radius: 6px;
  border-left: 4px solid;
}

.result-success {
  background: #d4edda;
  border-left-color: #28a745;
  color: #155724;
}

.result-error {
  background: #f8d7da;
  border-left-color: #dc3545;
  color: #721c24;
}

.result-info {
  background: #d1ecf1;
  border-left-color: #17a2b8;
  color: #0c5460;
}

.result-warning {
  background: #fff3cd;
  border-left-color: #ffc107;
  color: #856404;
}

/* Responsive */
@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-section {
    flex-direction: column;
  }
  
  .search-input {
    min-width: auto;
  }
  
  .companies-grid {
    grid-template-columns: 1fr;
  }
  
  .company-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .company-actions {
    justify-content: center;
    margin-top: 10px;
  }
  
  .list-footer {
    flex-direction: column;
    text-align: center;
  }
  
  .pagination {
    flex-direction: column;
    gap: 10px;
  }
  
  .technical-info {
    justify-content: center;
  }
  
  .company-footer {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .time-info {
    text-align: center;
  }
  
  .additional-actions {
    justify-content: center;
  }
}
</style>
