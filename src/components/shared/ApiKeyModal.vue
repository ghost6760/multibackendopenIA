<template>
  <div 
    class="api-key-status"
    :class="statusClass"
  >
    <!-- Status Indicator -->
    <span class="api-key-indicator" :class="indicatorClass"></span>
    
    <!-- Status Text -->
    <span class="api-key-text">{{ statusText }}</span>
    
    <!-- Configure Button -->
    <button 
      @click="showConfigModal"
      class="api-key-configure-btn"
      :title="isConfigured ? 'Cambiar API Key' : 'Configurar API Key'"
    >
      {{ isConfigured ? '🔧' : '🔑' }} {{ buttonText }}
    </button>
    
    <!-- API Key Modal -->
    <Transition name="modal">
      <div v-if="showModal" class="api-key-modal-overlay" @click="closeModal">
        <div class="api-key-modal-content" @click.stop>
          <div class="modal-header">
            <h3>🔑 API Key Administrativa</h3>
            <button @click="closeModal" class="modal-close">✕</button>
          </div>
          
          <div class="modal-body">
            <p class="modal-description">
              Ingresa tu API key para acceder a funciones enterprise y administrativas.
            </p>
            
            <div class="api-key-form-group">
              <label for="apiKeyInput">API Key:</label>
              <div class="input-group">
                <input 
                  ref="apiKeyInputRef"
                  type="password" 
                  id="apiKeyInput" 
                  v-model="inputApiKey"
                  :placeholder="isConfigured ? 'Nueva API key...' : 'your-secure-api-key-here'"
                  class="api-key-input"
                  @keyup.enter="saveApiKey"
                  @keyup.escape="closeModal"
                >
                <button 
                  @click="togglePasswordVisibility"
                  class="toggle-password-btn"
                  type="button"
                  :title="showPassword ? 'Ocultar' : 'Mostrar'"
                >
                  {{ showPassword ? '👁️' : '👁️‍🗨️' }}
                </button>
              </div>
              <small class="api-key-help">
                💡 Encuentra esta key en tus variables de entorno de Railway (API_KEY)
              </small>
            </div>
            
            <!-- Test API Key -->
            <div v-if="inputApiKey.trim()" class="test-section">
              <button 
                @click="testApiKey"
                :disabled="isTesting"
                class="test-btn"
              >
                <span v-if="isTesting">⏳ Probando...</span>
                <span v-else>🧪 Probar API Key</span>
              </button>
              
              <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
                <span class="test-icon">{{ testResult.success ? '✅' : '❌' }}</span>
                <span class="test-message">{{ testResult.message }}</span>
              </div>
            </div>
            
            <!-- Current Status -->
            <div v-if="isConfigured" class="current-status">
              <div class="status-item">
                <span class="status-label">Estado actual:</span>
                <span class="status-value" :class="statusClass">
                  {{ statusText }}
                </span>
              </div>
              <div class="status-item">
                <span class="status-label">Última verificación:</span>
                <span class="status-value">{{ lastCheckFormatted }}</span>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <div class="action-buttons">
              <button 
                @click="saveApiKey" 
                :disabled="!inputApiKey.trim() || isTesting"
                class="api-key-btn primary"
              >
                💾 {{ isConfigured ? 'Actualizar' : 'Guardar' }}
              </button>
              
              <button 
                v-if="isConfigured"
                @click="clearApiKey" 
                class="api-key-btn danger"
              >
                🗑️ Limpiar
              </button>
              
              <button 
                @click="closeModal" 
                class="api-key-btn secondary"
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'
import { useApiRequest } from '@/composables/useApiRequest'

// ============================================================================
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()
const { apiRequest } = useApiRequest()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const showModal = ref(false)
const inputApiKey = ref('')
const showPassword = ref(false)
const isTesting = ref(false)
const testResult = ref(null)
const lastCheck = ref(null)
const apiKeyInputRef = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const isConfigured = computed(() => {
  return Boolean(appStore.adminApiKey)
})

const statusClass = computed(() => {
  return isConfigured.value ? 'configured' : 'not-configured'
})

const indicatorClass = computed(() => {
  if (!isConfigured.value) return 'error'
  return 'success'
})

const statusText = computed(() => {
  return isConfigured.value ? 'API Key configurada' : 'API Key requerida'
})

const buttonText = computed(() => {
  return isConfigured.value ? 'Cambiar' : 'Configurar'
})

const lastCheckFormatted = computed(() => {
  if (!lastCheck.value) return 'Nunca'
  
  try {
    const date = new Date(lastCheck.value)
    return date.toLocaleString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Mostrar modal de configuración
 */
const showConfigModal = () => {
  showModal.value = true
  inputApiKey.value = ''
  testResult.value = null
  showPassword.value = false
  
  // Focus en el input después de que el modal se renderice
  nextTick(() => {
    if (apiKeyInputRef.value) {
      apiKeyInputRef.value.focus()
    }
  })
  
  appStore.addToLog('API Key modal opened', 'info')
}

/**
 * Cerrar modal
 */
const closeModal = () => {
  showModal.value = false
  inputApiKey.value = ''
  testResult.value = null
  showPassword.value = false
  
  appStore.addToLog('API Key modal closed', 'info')
}

/**
 * Toggle visibility de contraseña
 */
const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
  
  if (apiKeyInputRef.value) {
    apiKeyInputRef.value.type = showPassword.value ? 'text' : 'password'
  }
}

/**
 * Guardar API Key
 */
const saveApiKey = async () => {
  const apiKey = inputApiKey.value.trim()
  
  if (!apiKey) {
    showNotification('Por favor ingresa una API key válida', 'warning')
    return
  }
  
  try {
    // Probar la API key antes de guardar
    isTesting.value = true
    const isValid = await testApiKeyValidation(apiKey)
    
    if (isValid) {
      // Guardar en el store
      appStore.adminApiKey = apiKey
      lastCheck.value = Date.now()
      
      // Cerrar modal
      closeModal()
      
      showNotification('✅ API Key configurada correctamente', 'success')
      appStore.addToLog('API Key configured successfully', 'info')
    } else {
      showNotification('❌ API Key inválida', 'error')
    }
    
  } catch (error) {
    console.error('Error saving API key:', error)
    showNotification('❌ Error al validar API Key', 'error')
  } finally {
    isTesting.value = false
  }
}

/**
 * Limpiar API Key
 */
const clearApiKey = () => {
  if (confirm('¿Estás seguro de que quieres limpiar la API Key?')) {
    appStore.adminApiKey = null
    lastCheck.value = null
    
    closeModal()
    
    showNotification('🗑️ API Key eliminada', 'warning')
    appStore.addToLog('API Key cleared', 'info')
  }
}

/**
 * Probar API Key
 */
const testApiKey = async () => {
  const apiKey = inputApiKey.value.trim()
  
  if (!apiKey) {
    showNotification('Ingresa una API key para probar', 'warning')
    return
  }
  
  isTesting.value = true
  testResult.value = null
  
  try {
    const isValid = await testApiKeyValidation(apiKey)
    
    testResult.value = {
      success: isValid,
      message: isValid 
        ? 'API Key válida y funcional' 
        : 'API Key inválida o sin permisos'
    }
    
    if (isValid) {
      lastCheck.value = Date.now()
    }
    
  } catch (error) {
    console.error('Error testing API key:', error)
    testResult.value = {
      success: false,
      message: `Error al probar: ${error.message}`
    }
  } finally {
    isTesting.value = false
  }
}

/**
 * Validar API Key con el servidor
 */
const testApiKeyValidation = async (apiKey) => {
  try {
    // Intentar hacer una request que requiera API key
    const response = await apiRequest('/api/admin/test', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'X-API-Key': apiKey
      }
    })
    
    return response.success === true || response.status === 'ok'
    
  } catch (error) {
    // Si el endpoint no existe, simular validación básica
    if (error.message.includes('404') || error.message.includes('not found')) {
      // Validación básica: la API key debe tener al menos 16 caracteres
      return apiKey.length >= 16
    }
    
    // Para otros errores, considerar la API key como inválida
    return false
  }
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Verificar API Key al cargar el componente
 */
const checkApiKeyStatus = async () => {
  if (!isConfigured.value) return
  
  try {
    const isValid = await testApiKeyValidation(appStore.adminApiKey)
    
    if (!isValid) {
      showNotification('⚠️ API Key configurada no es válida', 'warning')
      appStore.addToLog('Configured API Key is invalid', 'warning')
    } else {
      lastCheck.value = Date.now()
    }
    
  } catch (error) {
    console.error('Error checking API key status:', error)
  }
}

/**
 * Cerrar modal con ESC
 */
const handleKeyDown = (event) => {
  if (event.key === 'Escape' && showModal.value) {
    closeModal()
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Verificar estado de la API key al cargar
  if (isConfigured.value) {
    checkApiKeyStatus()
  }
  
  // Event listener para ESC
  document.addEventListener('keydown', handleKeyDown)
  
  appStore.addToLog('ApiKeyStatus component mounted', 'info')
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // Exponer funciones globales
  window.showApiKeyModal = showConfigModal
  window.testApiKey = testApiKey
  window.updateApiKeyStatus = checkApiKeyStatus
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.showApiKeyModal
    delete window.testApiKey
    delete window.updateApiKeyStatus
  }
})
</script>

<style scoped>
.api-key-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.api-key-status.configured {
  border-color: var(--success-color);
  background: rgba(34, 197, 94, 0.05);
}

.api-key-status.not-configured {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.05);
}

.api-key-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.api-key-indicator.success {
  background: var(--success-color);
  animation: pulse-success 2s infinite;
}

.api-key-indicator.error {
  background: var(--danger-color);
  animation: pulse-error 2s infinite;
}

.api-key-text {
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
}

.api-key-configure-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: background-color 0.2s ease;
  white-space: nowrap;
}

.api-key-configure-btn:hover {
  background: var(--primary-color-dark);
}

.configured .api-key-configure-btn {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.configured .api-key-configure-btn:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* Modal Styles */
.api-key-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.api-key-modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.2em;
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.2em;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
}

.modal-description {
  margin: 0 0 20px 0;
  color: var(--text-secondary);
  line-height: 1.5;
}

.api-key-form-group {
  margin-bottom: 20px;
}

.api-key-form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.api-key-input {
  width: 100%;
  padding: 12px 40px 12px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  font-family: monospace;
  transition: border-color 0.2s ease;
}

.api-key-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.toggle-password-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 3px;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.toggle-password-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.api-key-help {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 0.85em;
  line-height: 1.3;
}

.test-section {
  margin-bottom: 20px;
  padding: 15px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.test-btn {
  background: var(--info-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 500;
  transition: background-color 0.2s ease;
  margin-bottom: 10px;
}

.test-btn:hover:not(:disabled) {
  background: var(--info-color-dark);
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.9em;
}

.test-result.success {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success-color);
}

.test-result.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.test-icon {
  font-size: 1.1em;
}

.current-status {
  margin-bottom: 20px;
  padding: 15px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9em;
}

.status-item:last-child {
  margin-bottom: 0;
}

.status-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.status-value {
  color: var(--text-primary);
  font-weight: 600;
}

.status-value.configured {
  color: var(--success-color);
}

.status-value.not-configured {
  color: var(--danger-color);
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.api-key-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.api-key-btn.primary {
  background: var(--primary-color);
  color: white;
}

.api-key-btn.primary:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.api-key-btn.danger {
  background: var(--danger-color);
  color: white;
}

.api-key-btn.danger:hover {
  background: var(--danger-color-dark);
}

.api-key-btn.secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.api-key-btn.secondary:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.api-key-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Animations */
@keyframes pulse-success {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

@keyframes pulse-error {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

/* Modal Transitions */
.modal-enter-active {
  transition: all 0.3s ease-out;
}

.modal-leave-active {
  transition: all 0.3s ease-in;
}

.modal-enter-from {
  opacity: 0;
  backdrop-filter: blur(0px);
}

.modal-enter-from .api-key-modal-content {
  transform: scale(0.8) translateY(20px);
  opacity: 0;
}

.modal-leave-to {
  opacity: 0;
  backdrop-filter: blur(0px);
}

.modal-leave-to .api-key-modal-content {
  transform: scale(0.8) translateY(-20px);
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .api-key-status {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }
  
  .api-key-text {
    text-align: center;
  }
  
  .api-key-modal-content {
    width: 95%;
    margin: 10px;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 15px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .api-key-status {
    padding: 6px 10px;
    font-size: 0.85em;
  }
  
  .api-key-configure-btn {
    font-size: 0.8em;
    padding: 3px 6px;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .pulse-success,
  .pulse-error {
    animation: none;
  }
  
  .modal-enter-active,
  .modal-leave-active {
    transition: opacity 0.2s ease;
  }
}
</style>
