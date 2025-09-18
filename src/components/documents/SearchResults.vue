<template>
  <div class="search-results">
    <!-- Results header -->
    <div class="search-results-header">
      <h4>📋 Resultados de búsqueda ({{ results.length }})</h4>
      <div class="search-actions">
        <button @click="clearResults" class="clear-btn" title="Limpiar resultados">
          ✕ Limpiar
        </button>
        <select v-model="sortBy" @change="handleSortChange" class="sort-select">
          <option value="relevance">📊 Por relevancia</option>
          <option value="date">📅 Por fecha</option>
          <option value="title">📝 Por título</option>
          <option value="type">📄 Por tipo</option>
        </select>
      </div>
    </div>
    
    <!-- Results list -->
    <div class="results-list">
      <div
        v-for="(result, index) in sortedResults"
        :key="result.id || result._id || index"
        class="result-item"
        :class="{ 'result-selected': selectedResultId === result.id }"
        @click="selectResult(result)"
      >
        <!-- Result header -->
        <div class="result-header">
          <div class="result-icon">
            {{ getResultIcon(result.type) }}
          </div>
          <div class="result-title-section">
            <h5 class="result-title" v-html="highlightMatches(result.title)"></h5>
            <div class="result-meta">
              <span class="result-date">
                📅 {{ formatDate(result.created_at) }}
              </span>
              <span v-if="result.type" class="result-type">
                📄 {{ result.type }}
              </span>
              <span v-if="result.relevance" class="result-relevance">
                ⭐ {{ Math.round(result.relevance * 100) }}%
              </span>
            </div>
          </div>
          <div class="result-actions">
            <button
              @click.stop="$emit('view-document', result.id || result._id)"
              class="action-btn view-btn"
              title="Ver documento"
            >
              👁️ Ver
            </button>
            <button
              @click.stop="$emit('delete-document', result.id || result._id)"
              class="action-btn delete-btn"
              title="Eliminar documento"
            >
              🗑️ Eliminar
            </button>
          </div>
        </div>
        
        <!-- Result content preview -->
        <div class="result-content">
          <!-- Highlighted excerpt -->
          <div v-if="result.highlight" class="result-excerpt">
            <strong>Extracto:</strong>
            <span v-html="highlightMatches(result.highlight)"></span>
          </div>
          
          <!-- Content preview -->
          <div v-if="result.content" class="result-preview">
            <strong>Vista previa:</strong>
            <span v-html="highlightMatches(getContentPreview(result.content))"></span>
          </div>
          
          <!-- Matched terms -->
          <div v-if="result.matched_terms && result.matched_terms.length" class="matched-terms">
            <strong>Términos encontrados:</strong>
            <span
              v-for="term in result.matched_terms"
              :key="term"
              class="matched-term"
            >
              {{ term }}
            </span>
          </div>
        </div>
        
        <!-- Result footer with additional info -->
        <div v-if="showAdditionalInfo" class="result-footer">
          <div class="result-stats">
            <span v-if="result.word_count" class="stat">
              📝 {{ result.word_count }} palabras
            </span>
            <span v-if="result.size" class="stat">
              💾 {{ formatFileSize(result.size) }}
            </span>
            <span v-if="result.last_modified" class="stat">
              ✏️ Mod. {{ formatDate(result.last_modified) }}
            </span>
          </div>
          
          <!-- Tags or categories -->
          <div v-if="result.tags && result.tags.length" class="result-tags">
            <span
              v-for="tag in result.tags"
              :key="tag"
              class="tag"
            >
              #{{ tag }}
            </span>
          </div>
        </div>
        
        <!-- Expand/collapse content -->
        <div v-if="result.content && result.content.length > 200" class="result-expand">
          <button
            @click.stop="toggleResultExpanded(result.id)"
            class="expand-btn"
          >
            {{ expandedResults.includes(result.id) ? '▲ Mostrar menos' : '▼ Mostrar más' }}
          </button>
        </div>
        
        <!-- Full content (when expanded) -->
        <div
          v-if="expandedResults.includes(result.id) && result.content"
          class="result-full-content"
        >
          <div class="full-content-header">
            <strong>Contenido completo:</strong>
          </div>
          <pre class="full-content-text" v-html="highlightMatches(result.content)"></pre>
        </div>
      </div>
    </div>
    
    <!-- No results message -->
    <div v-if="results.length === 0" class="no-results">
      <div class="no-results-icon">🔍</div>
      <h4>No se encontraron resultados</h4>
      <p>Intenta con otros términos de búsqueda</p>
    </div>
    
    <!-- Load more button (if applicable) -->
    <div v-if="hasMoreResults" class="load-more-section">
      <button @click="$emit('load-more')" class="load-more-btn" :disabled="loadingMore">
        <span v-if="loadingMore">⏳ Cargando...</span>
        <span v-else>📄 Cargar más resultados</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  },
  searchQuery: {
    type: String,
    default: ''
  },
  showAdditionalInfo: {
    type: Boolean,
    default: true
  },
  hasMoreResults: {
    type: Boolean,
    default: false
  },
  loadingMore: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'view-document',
  'delete-document',
  'clear-results',
  'load-more',
  'result-selected'
])

// ============================================================================
// STORES
// ============================================================================

const appStore = useAppStore()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedResultId = ref(null)
const expandedResults = ref([])
const sortBy = ref('relevance')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const sortedResults = computed(() => {
  const results = [...props.results]
  
  switch (sortBy.value) {
    case 'date':
      return results.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      
    case 'title':
      return results.sort((a, b) => a.title.localeCompare(b.title))
      
    case 'type':
      return results.sort((a, b) => (a.type || '').localeCompare(b.type || ''))
      
    case 'relevance':
    default:
      return results.sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
  }
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Select a result
 */
const selectResult = (result) => {
  selectedResultId.value = result.id || result._id
  emit('result-selected', result)
}

/**
 * Clear search results
 */
const clearResults = () => {
  selectedResultId.value = null
  expandedResults.value = []
  emit('clear-results')
  appStore.addToLog('Search results cleared', 'info')
}

/**
 * Handle sort change
 */
const handleSortChange = () => {
  appStore.addToLog(`Search results sorted by: ${sortBy.value}`, 'info')
}

/**
 * Toggle result expanded state
 */
const toggleResultExpanded = (resultId) => {
  const index = expandedResults.value.indexOf(resultId)
  if (index > -1) {
    expandedResults.value.splice(index, 1)
  } else {
    expandedResults.value.push(resultId)
  }
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Get result icon based on type
 */
const getResultIcon = (type) => {
  const iconMap = {
    'pdf': '📕',
    'word': '📘',
    'txt': '📄',
    'text': '📄',
    'markdown': '📝',
    'md': '📝',
    'json': '🔧',
    'csv': '📊',
    'excel': '📊',
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵'
  }
  
  return iconMap[type?.toLowerCase()] || '📄'
}

/**
 * Get content preview (truncated)
 */
const getContentPreview = (content) => {
  if (!content) return ''
  
  const maxLength = 200
  const cleaned = content.replace(/\s+/g, ' ').trim()
  
  return cleaned.length > maxLength 
    ? cleaned.substring(0, maxLength) + '...'
    : cleaned
}

/**
 * Highlight search matches in text
 */
const highlightMatches = (text) => {
  if (!text || !props.searchQuery) return escapeHTML(text)
  
  // Split search query into terms
  const terms = props.searchQuery
    .toLowerCase()
    .split(/\s+/)
    .filter(term => term.length > 2) // Only highlight terms longer than 2 chars
  
  if (terms.length === 0) return escapeHTML(text)
  
  let highlightedText = escapeHTML(text)
  
  // Highlight each term
  terms.forEach(term => {
    const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi')
    highlightedText = highlightedText.replace(regex, '<mark class="search-highlight">$1</mark>')
  })
  
  return highlightedText
}

/**
 * Escape HTML for security
 */
const escapeHTML = (text) => {
  if (!text) return ''
  
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Escape RegExp special characters
 */
const escapeRegExp = (string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Format file size
 */
const formatFileSize = (bytes) => {
  if (!bytes) return 'Desconocido'
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format date
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Fecha desconocida'
  
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Hoy'
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `Hace ${diffDays} días`
    if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
    
    return date.toLocaleDateString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// WATCHERS
// ============================================================================

// Reset expanded results when search results change
watch(() => props.results, () => {
  expandedResults.value = []
  selectedResultId.value = null
})
</script>

<style scoped>
.search-results {
  width: 100%;
}

.search-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 10px;
}

.search-results-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.search-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.clear-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: var(--danger-color);
  border-color: var(--danger-color);
  color: white;
}

.sort-select {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.85em;
  cursor: pointer;
}

.sort-select:focus {
  outline: none;
  border-color: var(--primary-color);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.result-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.result-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-item.result-selected {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.result-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.result-icon {
  font-size: 1.3em;
  min-width: 28px;
  text-align: center;
}

.result-title-section {
  flex: 1;
  min-width: 0;
}

.result-title {
  margin: 0 0 6px 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  word-wrap: break-word;
}

.result-meta {
  display: flex;
  gap: 12px;
  font-size: 0.8em;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.result-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8em;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.view-btn:hover {
  border-color: var(--info-color);
  color: var(--info-color);
}

.delete-btn:hover {
  border-color: var(--danger-color);
  color: var(--danger-color);
}

.result-content {
  margin-bottom: 12px;
}

.result-excerpt,
.result-preview {
  margin-bottom: 8px;
  font-size: 0.9em;
  line-height: 1.4;
}

.result-excerpt strong,
.result-preview strong {
  color: var(--text-primary);
  margin-right: 6px;
}

.result-excerpt span,
.result-preview span {
  color: var(--text-secondary);
}

.matched-terms {
  font-size: 0.8em;
  margin-top: 8px;
}

.matched-terms strong {
  color: var(--text-primary);
  margin-right: 6px;
}

.matched-term {
  display: inline-block;
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
  padding: 2px 6px;
  border-radius: 12px;
  margin: 2px 4px 2px 0;
  font-size: 0.85em;
  font-weight: 500;
}

.result-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  flex-wrap: wrap;
  gap: 8px;
}

.result-stats {
  display: flex;
  gap: 12px;
  font-size: 0.8em;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.result-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 0.75em;
  border: 1px solid var(--border-color);
}

.result-expand {
  text-align: center;
  margin: 12px 0;
}

.expand-btn {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
}

.expand-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.result-full-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.full-content-header {
  margin-bottom: 8px;
  font-size: 0.9em;
  color: var(--text-primary);
}

.full-content-text {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  font-size: 0.85em;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  color: var(--text-secondary);
}

/* Search highlighting */
:deep(.search-highlight) {
  background: #ffeb3b;
  color: #000;
  padding: 1px 2px;
  border-radius: 2px;
  font-weight: 600;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.no-results-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.no-results h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.no-results p {
  margin: 0;
}

.load-more-section {
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.load-more-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.load-more-btn:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .search-results-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-actions {
    justify-content: space-between;
  }
  
  .result-header {
    flex-direction: column;
    gap: 8px;
  }
  
  .result-actions {
    justify-content: center;
  }
  
  .result-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .result-stats {
    justify-content: center;
  }
  
  .result-meta {
    flex-direction: column;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .result-item {
    padding: 12px;
  }
  
  .action-btn {
    flex: 1;
    text-align: center;
  }
  
  .matched-term {
    margin: 1px 2px;
  }
}
</style>
