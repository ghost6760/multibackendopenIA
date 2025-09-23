<template>
  <div class="enterprise-companies-list">
    <!-- Header con estadísticas -->
    <div class="list-header">
      <div class="header-info">
        <h4>📋 Empresas Enterprise Configuradas</h4>
        <div class="stats">
          <span class="total-count">
            Total: <strong id="totalEnterpriseCompanies">{{ companies.length }}</strong>
          </span>
          <span class="active-count">
            Activas: <strong>{{ activeCompaniesCount }}</strong>
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
          {{ isLoading ? 'Cargando...' : 'Recargar Lista' }}
        </button>
        
        <button 
          @click="$emit('create')"
          class="btn btn-primary"
        >
          ➕ Nueva Empresa
        </button>
      </div>
    </div>

    <!-- Estado de carga -->
    <div v-if="isLoading && companies.length === 0" class="loading-state">
      <div class="loading">Cargando empresas enterprise...</div>
    </div>

    <!-- Error state -->
    <div v-if="error && !isLoading" class="enterprise-error">
      <h4>❌ Error al cargar empresas enterprise</h4>
      <p>{{ error }}</p>
      <button @click="$emit('refresh')" class="btn btn-secondary">
        🔄 Reintentar
      </button>
    </div>

    <!-- Lista vacía -->
    <div v-if="!isLoading && companies.length === 0 && !error" class="empty-state">
      <div class="result-container result-info">
        <p>📝 No hay empresas enterprise configuradas</p>
        <p>Utiliza el formulario de arriba para crear la primera empresa.</p>
        <button @click="$emit('create')" class="btn btn-primary">
          ➕ Crear Primera Empresa
        </button>
      </div>
    </div>

    <!-- Lista de empresas -->
    <div v-if="companies.length > 0" class="companies-list" id="enterpriseCompaniesList">
      <div 
        v-for="company in companies" 
        :key="company.company_id || company.id"
        class="company-card"
      >
        <!-- Header de la empresa -->
        <div class="company-header">
          <div class="company-title">
            <h5>{{ company.name || company.company_id }}</h5>
            <span 
              class="status-badge"
              :class="company.is_active ? 'status-success' : 'status-error'"
            >
              {{ company.is_active ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          
          <div class="company-meta">
            <span class="company-environment" :class="`env-${company.environment || 'development'}`">
              {{ (company.environment || 'development').toUpperCase() }}
            </span>
          </div>
        </div>

        <!-- Detalles de la empresa -->
        <div class="company-details">
          <div class="detail-row">
            <strong>ID:</strong> 
            <span>{{ escapeHTML(company.company_id || company.id) }}</span>
          </div>
          
          <div class="detail-row">
            <strong>Tipo:</strong> 
            <span>{{ escapeHTML(company.business_type || 'N/A') }}</span>
          </div>
          
          <div class="detail-row">
            <strong>Plan:</strong> 
            <span>{{ escapeHTML(company.subscription_tier || 'N/A') }}</span>
          </div>
          
          <div class="detail-row">
            <strong>Base URL:</strong> 
            <span class="url-text">{{ company.api_base_url || 'N/A' }}</span>
          </div>
          
          <div class="detail-row">
            <strong>Database:</strong> 
            <span>{{ company.database_type || 'N/A' }}</span>
          </div>
          
          <div v-if="company.services" class="detail-row">
            <strong>Servicios:</strong> 
            <span>{{ escapeHTML(company.services.substring(0, 100)) }}{{ company.services.length > 100 ? '...' : '' }}</span>
          </div>
          
          <div v-if="company.description" class="detail-row">
            <strong>Descripción:</strong> 
            <span>{{ escapeHTML(company.description.substring(0, 150)) }}{{ company.description.length > 150 ? '...' : '' }}</span>
          </div>
        </div>

        <!-- Acciones de la empresa -->
        <div class="company-actions">
          <button 
            @click="$emit('view', company.company_id || company.id)"
            class="btn btn-primary"
            title="Ver detalles completos"
          >
            👁️ Ver
          </button>
          
          <button 
            @click="$emit('edit', company.company_id || company.id)"
            class="btn btn-secondary"
            title="Editar empresa"
          >
            ✏️ Editar
          </button>
          
          <button 
            @click="$emit('test', company.company_id || company.id)"
            class="btn btn-info"
            title="Probar conexión"
          >
            🧪 Test
          </button>
          
          <button 
            v-if="company.is_active"
            @click="$emit('toggle-status', company.company_id || company.id, false)"
            class="btn btn-warning"
            title="Desactivar empresa"
          >
            ⏸️ Desactivar
          </button>
          
          <button 
            v-else
            @click="$emit('toggle-status', company.company_id || company.id, true)"
            class="btn btn-success"
            title="Activar empresa"
          >
            ▶️ Activar
          </button>
        </div>
      </div>
    </div>

    <!-- Footer con información adicional -->
    <div v-if="companies.length > 0" class="list-footer">
      <div class="footer-info">
        <span class="last-sync" v-if="lastSync">
          Última actualización: {{ formatDate(lastSync) }}
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
import { computed } from 'vue'

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
  'migrate'
])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const activeCompaniesCount = computed(() => {
  return props.companies.filter(company => company.is_active).length
})

// ============================================================================
// UTILITY FUNCTIONS (PRESERVAR EXACTAS DEL SCRIPT.JS)
// ============================================================================

/**
 * Escapa HTML para prevenir XSS - MIGRADO: escapeHTML() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const escapeHTML = (text) => {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Formatea fecha para mostrar - Helper function
 */
const formatDate = (timestamp) => {
  if (!timestamp) return 'N/A'
  return new Date(timestamp).toLocaleString('es-ES', {
    year: 'numeric',
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
/* ============================================================================ */
/* ESTILOS DEL COMPONENTE - Siguiendo el estilo actual del proyecto */
/* ============================================================================ */

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

.total-count, .active-count {
  background: #e9ecef;
  padding: 5px 12px;
  border-radius: 15px;
  font-size: 0.9em;
}

.active-count {
  background: #d4edda;
  color: #155724;
}

.list-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* Estados */
.loading-state, .empty-state {
  text-align: center;
  padding: 40px 20px;
}

.loading {
  font-size: 1.1em;
  color: #6c757d;
}

.enterprise-error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 5px;
  padding: 20px;
  margin: 20px 0;
}

.enterprise-error h4 {
  color: #721c24;
  margin: 0 0 10px 0;
}

/* Lista de empresas */
.companies-list {
  display: grid;
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
}

.company-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* Header de empresa */
.company-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.company-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.company-title h5 {
  margin: 0;
  color: #333;
  font-size: 1.1em;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: bold;
  text-transform: uppercase;
}

.status-success {
  background: #d4edda;
  color: #155724;
}

.status-error {
  background: #f8d7da;
  color: #721c24;
}

.company-environment {
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
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-row strong {
  min-width: 100px;
  color: #495057;
  font-size: 0.9em;
}

.detail-row span {
  color: #333;
  font-size: 0.9em;
  word-break: break-word;
}

.url-text {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.85em !important;
}

/* Acciones */
.company-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.company-actions .btn {
  font-size: 0.85em;
  padding: 6px 12px;
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

.footer-info .last-sync {
  color: #6c757d;
  font-size: 0.9em;
}

.footer-actions {
  display: flex;
  gap: 10px;
}

/* Responsive */
@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .company-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .company-actions {
    justify-content: center;
  }
  
  .list-footer {
    flex-direction: column;
    text-align: center;
  }
}
</style>
