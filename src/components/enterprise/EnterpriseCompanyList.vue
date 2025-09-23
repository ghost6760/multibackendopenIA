<template>
  <div class="enterprise-companies-list">
    <!-- Header con estadísticas y acciones -->
    <div class="list-header">
      <div class="header-info">
        <h4>📋 Empresas Enterprise PostgreSQL</h4>
        <div class="stats">
          <span class="total-count">
            Total: <strong>{{ companies.length }}</strong>
          </span>
          <span class="active-count">
            Activas: <strong>{{ activeCompaniesCount }}</strong>
          </span>
          <span class="last-sync" v-if="lastSync">
            Actualizado: {{ formatDate(lastSync) }}
          </span>
        </div>
      </div>
      
      <div class="list-actions">
        <button 
          @click="$emit('refresh')" 
          :disabled="isLoading"
          class="btn btn-info"
        >
          <span v-if="isLoading">🔄</span>
          <span v-else>📋</span>
          {{ isLoading ? 'Cargando...' : 'Recargar' }}
        </button>
        
        <button 
          @click="$emit('create')"
          class="btn btn-primary"
        >
          ➕ Nueva Empresa
        </button>
      </div>
    </div>

    <!-- Filtros de búsqueda -->
    <div class="search-filters" v-if="companies.length > 0">
      <input
        type="text"
        v-model="searchQuery"
        placeholder="Buscar por ID, nombre o tipo..."
        class="search-input"
      />
      <select v-model="statusFilter" class="filter-select">
        <option value="">Todos los estados</option>
        <option value="active">Activas</option>
        <option value="inactive">Inactivas</option>
        <option value="error">Con errores</option>
      </select>
      <select v-model="typeFilter" class="filter-select">
        <option value="">Todos los tipos</option>
        <option value="healthcare">Salud</option>
        <option value="beauty">Belleza</option>
        <option value="dental">Dental</option>
        <option value="spa">SPA & Wellness</option>
        <option value="general">General</option>
      </select>
    </div>

    <!-- Estado de carga -->
    <div v-if="isLoading && companies.length === 0" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Cargando empresas enterprise desde PostgreSQL...</p>
    </div>

    <!-- Error state -->
    <div v-if="error && !isLoading" class="enterprise-error">
      <div class="result-container result-error">
        <h4>❌ Error al cargar empresas enterprise</h4>
        <p>{{ error }}</p>
        <div class="error-details">
          <p><strong>Posibles causas:</strong></p>
          <ul>
            <li>API Key administrativa no configurada</li>
            <li>PostgreSQL no disponible</li>
            <li>Permisos insuficientes</li>
          </ul>
        </div>
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
        <p>PostgreSQL está listo pero no hay empresas creadas aún.</p>
        <div class="empty-actions">
          <button @click="$emit('create')" class="btn btn-primary">
            ➕ Crear Primera Empresa
          </button>
          <button @click="$emit('migrate')" class="btn btn-secondary">
            🔄 Migrar desde JSON
          </button>
        </div>
      </div>
    </div>

    <!-- Lista de empresas filtrada -->
    <div v-if="filteredCompanies.length > 0" class="companies-grid">
      <div 
        v-for="company in filteredCompanies"
        :key="company.company_id || company.id"
        class="company-card"
        :class="{ 
          'company-inactive': !company.is_active,
          'company-error': company.status === 'error',
          'company-warning': company.status === 'warning'
        }"
      >
        <!-- Header de la empresa -->
        <div class="company-header">
          <div class="company-info">
            <h5>{{ company.company_name || company.name || company.company_id || company.id }}</h5>
            <div class="company-badges">
              <span :class="['badge', 'badge-status', getStatusClass(company)]">
                {{ getStatusText(company) }}
              </span>
              <span v-if="company.business_type" class="badge badge-type">
                {{ formatBusinessType(company.business_type) }}
              </span>
              <span v-if="company.subscription_tier" class="badge badge-tier" :class="`tier-${company.subscription_tier}`">
                {{ company.subscription_tier.toUpperCase() }}
              </span>
            </div>
          </div>
          
          <div class="company-meta">
            <span v-if="company.environment" class="environment-badge" :class="`env-${company.environment}`">
              {{ company.environment.toUpperCase() }}
            </span>
          </div>
        </div>

        <!-- Detalles de la empresa -->
        <div class="company-details">
          <div class="detail-row">
            <strong>ID:</strong> 
            <span class="company-id">{{ company.company_id || company.id }}</span>
          </div>
          
          <div class="detail-row" v-if="company.sales_agent_name">
            <strong>Agente:</strong> 
            <span>{{ company.sales_agent_name }}</span>
          </div>
          
          <div class="detail-row" v-if="company.model_name">
            <strong>Modelo:</strong> 
            <span class="model-badge">{{ company.model_name }}</span>
          </div>
          
          <div class="detail-row" v-if="company.timezone">
            <strong>Zona horaria:</strong> 
            <span>{{ company.timezone }}</span>
          </div>
          
          <div class="detail-row" v-if="company.currency">
            <strong>Moneda:</strong> 
            <span>{{ company.currency }}</span>
          </div>

          <div class="detail-row" v-if="company.schedule_service_url">
            <strong>Servicio de agenda:</strong> 
            <span class="url-text">{{ truncateUrl(company.schedule_service_url) }}</span>
          </div>
          
          <div v-if="company.services" class="detail-row services-row">
            <strong>Servicios:</strong> 
            <span class="services-text">{{ truncateText(company.services, 100) }}</span>
          </div>
        </div>

        <!-- Información técnica -->
        <div class="company-tech" v-if="showTechnicalInfo(company)">
          <div class="tech-item" v-if="company.api_base_url">
            <span class="tech-label">API:</span>
            <span class="tech-value url-text">{{ truncateUrl(company.api_base_url) }}</span>
          </div>
          <div class="tech-item" v-if="company.database_type">
            <span class="tech-label">DB:</span>
            <span class="tech-value">{{ company.database_type }}</span>
          </div>
          <div class="tech-item" v-if="company.version">
            <span class="tech-label">Ver:</span>
            <span class="tech-value">{{ company.version }}</span>
          </div>
        </div>

        <!-- Acciones de la empresa -->
        <div class="company-actions">
          <button 
            @click="$emit('view', company.company_id || company.id)"
            class="btn btn-primary btn-sm"
            title="Ver detalles completos"
          >
            👁️ Ver
          </button>
          
          <button 
            @click="$emit('edit', company.company_id || company.id)"
            class="btn btn-secondary btn-sm"
            title="Editar configuración"
          >
            ✏️ Editar
          </button>
          
          <button 
            @click="$emit('test', company.company_id || company.id)"
            class="btn btn-info btn-sm"
            title="Probar funcionamiento"
          >
            🧪 Test
          </button>
          
          <button 
            v-if="company.is_active"
            @click="$emit('toggle-status', company.company_id || company.id, false)"
            class="btn btn-warning btn-sm"
            title="Desactivar empresa"
          >
            ⏸️
          </button>
          
          <button 
            v-else
            @click="$emit('toggle-status', company.company_id || company.id, true)"
            class="btn btn-success btn-sm"
            title="Activar empresa"
          >
            ▶️
          </button>
        </div>
      </div>
    </div>

    <!-- Paginación (si hay muchas empresas) -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        @click="currentPage = Math.max(1, currentPage - 1)"
        :disabled="currentPage === 1"
        class="btn btn-secondary btn-sm"
      >
        ← Anterior
      </button>
      
      <span class="page-info">
        Página {{ currentPage }} de {{ totalPages }} ({{ filteredCompanies.length }} empresas)
      </span>
      
      <button 
        @click="currentPage = Math.min(totalPages, currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="btn btn-secondary btn-sm"
      >
        Siguiente →
      </button>
    </div>

    <!-- Footer con herramientas adicionales -->
    <div v-if="companies.length > 0" class="list-footer">
      <div class="footer-info">
        <span class="companies-summary">
          {{ companies.length }} empresas enterprise en PostgreSQL
        </span>
      </div>
      
      <div class="footer-actions">
        <button 
          @click="exportToCSV"
          class="btn btn-outline btn-sm"
          title="Exportar a CSV"
        >
          📄 CSV
        </button>
        
        <button 
          @click="exportToJSON"
          class="btn btn-outline btn-sm"
          title="Exportar a JSON"
        >
          📋 JSON
        </button>
        
        <button 
          @click="$emit('migrate')"
          class="btn btn-secondary btn-sm"
          title="Migrar desde JSON a PostgreSQL"
        >
          🔄 Migrar JSON
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
    type: [Number, String],
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
  'migrate'
])

// ============================================================================
// ESTADO LOCAL (Solo para filtros y paginación)
// ============================================================================

const searchQuery = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const currentPage = ref(1)
const itemsPerPage = 12

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const activeCompaniesCount = computed(() => {
  return props.companies.filter(company => company.is_active !== false).length
})

/**
 * Lista filtrada por búsqueda, estado y tipo
 */
const filteredCompanies = computed(() => {
  let filtered = [...props.companies]
  
  // Filtro de búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(company =>
      (company.company_name || company.name || '').toLowerCase().includes(query) ||
      (company.company_id || company.id || '').toLowerCase().includes(query) ||
      (company.business_type || '').toLowerCase().includes(query) ||
      (company.services || '').toLowerCase().includes(query) ||
      (company.sales_agent_name || '').toLowerCase().includes(query)
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
  
  // Filtro de tipo de negocio
  if (typeFilter.value) {
    filtered = filtered.filter(company => company.business_type === typeFilter.value)
  }
  
  // Ordenar por nombre
  return filtered.sort((a, b) => 
    (a.company_name || a.name || a.company_id || a.id).localeCompare(
      b.company_name || b.name || b.company_id || b.id
    )
  )
})

/**
 * Paginación
 */
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

// Resetear página cuando cambian los filtros
watch([searchQuery, statusFilter, typeFilter], () => {
  currentPage.value = 1
})

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

/**
 * Obtener clase CSS para el estado de la empresa
 */
const getStatusClass = (company) => {
  if (!company.is_active) return 'status-inactive'
  if (company.status === 'error') return 'status-error'
  if (company.status === 'warning') return 'status-warning'
  return 'status-active'
}

/**
 * Obtener texto del estado
 */
const getStatusText = (company) => {
  if (!company.is_active) return 'Inactiva'
  if (company.status === 'error') return 'Error'
  if (company.status === 'warning') return 'Advertencia'
  return 'Activa'
}

/**
 * Formatear tipo de negocio
 */
const formatBusinessType = (type) => {
  const types = {
    healthcare: 'Salud',
    beauty: 'Belleza',
    dental: 'Dental',
    spa: 'SPA',
    general: 'General'
  }
  return types[type] || type
}

/**
 * Truncar texto largo
 */
const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

/**
 * Truncar URL para mostrar
 */
const truncateUrl = (url) => {
  if (!url) return ''
  try {
    const urlObj = new URL(url)
    return `${urlObj.hostname}${urlObj.pathname}`
  } catch {
    return truncateText(url, 30)
  }
}

/**
 * Mostrar información técnica si está disponible
 */
const showTechnicalInfo = (company) => {
  return company.api_base_url || company.database_type || company.version
}

/**
 * Formatear fecha para mostrar
 */
const formatDate = (timestamp) => {
  if (!timestamp) return 'N/A'
  
  try {
    const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date(timestamp)
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return 'Fecha inválida'
  }
}

/**
 * Exportar a CSV
 */
const exportToCSV = () => {
  const headers = ['ID', 'Nombre', 'Tipo', 'Estado', 'Agente', 'Modelo', 'Zona Horaria', 'Moneda', 'Servicios']
  const csvContent = [
    headers.join(','),
    ...filteredCompanies.value.map(company => [
      company.company_id || company.id,
      `"${(company.company_name || company.name || '').replace(/"/g, '""')}"`,
      company.business_type || '',
      company.is_active ? 'Activa' : 'Inactiva',
      `"${(company.sales_agent_name || '').replace(/"/g, '""')}"`,
      company.model_name || '',
      company.timezone || '',
      company.currency || '',
      `"${(company.services || '').replace(/"/g, '""')}"`
    ].join(','))
  ].join('\n')
  
  downloadFile(csvContent, 'empresas_enterprise.csv', 'text/csv')
}

/**
 * Exportar a JSON
 */
const exportToJSON = () => {
  const jsonContent = JSON.stringify({
    export_date: new Date().toISOString(),
    total_companies: filteredCompanies.value.length,
    companies: filteredCompanies.value
  }, null, 2)
  
  downloadFile(jsonContent, 'empresas_enterprise.json', 'application/json')
}

/**
 * Descargar archivo
 */
const downloadFile = (content, filename, mimeType) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
/* Lista principal */
.enterprise-companies-list {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Header */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex-wrap: wrap;
  gap: 15px;
}

.header-info h4 {
  margin: 0 0 10px 0;
  font-size: 1.3em;
}

.stats {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 0.9em;
}

.total-count, .active-count, .last-sync {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.list-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* Filtros */
.search-filters {
  display: flex;
  gap: 15px;
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
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
  min-width: 150px;
}

/* Estados */
.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  opacity: 0.6;
}

.empty-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}

.enterprise-error {
  padding: 20px;
}

.error-details {
  margin: 15px 0;
  text-align: left;
}

.error-details ul {
  margin: 10px 0;
  padding-left: 20px;
}

/* Grid de empresas */
.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  padding: 20px;
}

.company-card {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.company-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.company-card.company-inactive {
  opacity: 0.7;
  border-left: 4px solid #6c757d;
}

.company-card.company-error {
  border-left: 4px solid #dc3545;
}

.company-card.company-warning {
  border-left: 4px solid #ffc107;
}

/* Header de empresa */
.company-header {
  padding: 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
}

.company-info h5 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 1.1em;
  word-break: break-word;
}

.company-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-status.status-active {
  background: #d4edda;
  color: #155724;
}

.badge-status.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.badge-status.status-error {
  background: #f8d7da;
  color: #721c24;
}

.badge-status.status-warning {
  background: #fff3cd;
  color: #856404;
}

.badge-type {
  background: #cce5ff;
  color: #0066cc;
}

.badge-tier {
  font-weight: bold;
}

.tier-basic {
  background: #e2e3e5;
  color: #383d41;
}

.tier-premium {
  background: #fff3cd;
  color: #856404;
}

.tier-enterprise {
  background: #d4edda;
  color: #155724;
}

.environment-badge {
  padding: 3px 8px;
  border-radius: 8px;
  font-size: 0.75em;
  font-weight: bold;
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

/* Detalles */
.company-details {
  padding: 15px;
}

.detail-row {
  display: flex;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.detail-row strong {
  min-width: 80px;
  color: #495057;
  font-size: 0.85em;
  font-weight: 600;
}

.detail-row span {
  color: #333;
  font-size: 0.85em;
  word-break: break-word;
  flex: 1;
}

.company-id {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.8em !important;
}

.model-badge {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.8em !important;
}

.url-text {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.8em !important;
  word-break: break-all;
}

.services-row {
  flex-direction: column;
  align-items: flex-start;
}

.services-text {
  font-style: italic;
  color: #6c757d;
  margin-top: 5px;
}

/* Información técnica */
.company-tech {
  padding: 10px 15px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.tech-item {
  display: flex;
  gap: 5px;
  font-size: 0.8em;
}

.tech-label {
  font-weight: 600;
  color: #6c757d;
}

.tech-value {
  color: #333;
}

/* Acciones */
.company-actions {
  display: flex;
  gap: 5px;
  padding: 15px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  flex-wrap: wrap;
  justify-content: center;
}

/* Paginación */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
}

.page-info {
  font-size: 0.9em;
  color: #6c757d;
}

/* Footer */
.list-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
  flex-wrap: wrap;
  gap: 15px;
}

.companies-summary {
  color: #6c757d;
  font-size: 0.9em;
}

.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Botones */
.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-warning {
  background: #ffc107;
  color: #212529;
}

.btn-outline {
  background: transparent;
  color: #6c757d;
  border: 1px solid #6c757d;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 0.8em;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Responsive */
@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-filters {
    flex-direction: column;
  }
  
  .companies-grid {
    grid-template-columns: 1fr;
    padding: 15px;
  }
  
  .company-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .detail-row {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .detail-row strong {
    min-width: auto;
  }
  
  .company-actions {
    justify-content: stretch;
  }
  
  .company-actions .btn {
    flex: 1;
    justify-content: center;
  }
  
  .pagination {
    flex-direction: column;
    gap: 10px;
  }
  
  .list-footer {
    flex-direction: column;
    text-align: center;
  }
}

/* Utilidad - Container de resultados */
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
</style>
