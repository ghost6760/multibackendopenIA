# PromptsTab.vue
<template>
  <div class="prompts-tab" v-if="isActive">
    <!-- Header del Tab -->
    <div class="tab-header">
      <h2>🤖 Sistema de Prompts</h2>
      <p class="tab-description">
        Gestiona y personaliza los prompts de los agentes IA para {{ currentCompanyName }}
      </p>
    </div>

    <!-- Estado del Sistema (Comentado temporalmente para debug) -->
    <!-- <PromptsStatus 
      @status-loaded="handleStatusLoaded"
      @migration-complete="handleMigrationComplete"
    /> -->

    <!-- Main Prompts Section -->
    <div class="prompts-main-section">
      
      <!-- Company Info Bar -->
      <div class="company-bar">
        <div class="company-info">
          <span class="company-label">📢 Empresa Activa:</span>
          <span class="company-name">{{ currentCompanyName || currentCompanyId || 'No seleccionada' }}</span>
        </div>
        <div class="actions-bar">
          <button @click="loadPrompts" class="btn-refresh" :disabled="isLoadingPrompts">
            <span v-if="isLoadingPrompts">⏳ Cargando...</span>
            <span v-else>🔄 Recargar Todos</span>
          </button>
          <button @click="repairAllPrompts" class="btn-repair-all" :disabled="isProcessing">
            🔧 Reparar Todos
          </button>
          <button @click="exportPrompts" class="btn-export">
            💾 Exportar
          </button>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-section">
        <p>⚠️ {{ error }}</p>
      </div>

      <!-- Prompts Grid - Los 5 Agentes -->
      <div v-if="hasPrompts" class="prompts-grid">
        
        <!-- Lead Capture Agent -->
        <div class="agent-card" v-if="agents.leadCaptureAgent">
          <div class="agent-header">
            <h3>📥 Lead Capture Agent</h3>
            <span :class="['status-badge', agents.leadCaptureAgent.is_custom ? 'custom' : 'default']">
              {{ agents.leadCaptureAgent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-leadCaptureAgent`"
              v-model="agents.leadCaptureAgent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Lead Capture Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.leadCaptureAgent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.leadCaptureAgent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.leadCaptureAgent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('leadCaptureAgent')"
              class="btn-update"
              :disabled="isProcessing || !agents.leadCaptureAgent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('leadCaptureAgent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.leadCaptureAgent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('leadCaptureAgent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.leadCaptureAgent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Information Agent -->
        <div class="agent-card" v-if="agents.informationAgent">
          <div class="agent-header">
            <h3>ℹ️ Information Agent</h3>
            <span :class="['status-badge', agents.informationAgent.is_custom ? 'custom' : 'default']">
              {{ agents.informationAgent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-informationAgent`"
              v-model="agents.informationAgent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Information Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.informationAgent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.informationAgent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.informationAgent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('informationAgent')"
              class="btn-update"
              :disabled="isProcessing || !agents.informationAgent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('informationAgent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.informationAgent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('informationAgent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.informationAgent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Appointment Agent -->
        <div class="agent-card" v-if="agents.appointmentAgent">
          <div class="agent-header">
            <h3>📅 Appointment Agent</h3>
            <span :class="['status-badge', agents.appointmentAgent.is_custom ? 'custom' : 'default']">
              {{ agents.appointmentAgent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-appointmentAgent`"
              v-model="agents.appointmentAgent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Appointment Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.appointmentAgent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.appointmentAgent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.appointmentAgent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('appointmentAgent')"
              class="btn-update"
              :disabled="isProcessing || !agents.appointmentAgent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('appointmentAgent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.appointmentAgent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('appointmentAgent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.appointmentAgent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Reschedule Agent -->
        <div class="agent-card" v-if="agents.rescheduleAgent">
          <div class="agent-header">
            <h3>🔄 Reschedule Agent</h3>
            <span :class="['status-badge', agents.rescheduleAgent.is_custom ? 'custom' : 'default']">
              {{ agents.rescheduleAgent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-rescheduleAgent`"
              v-model="agents.rescheduleAgent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Reschedule Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.rescheduleAgent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.rescheduleAgent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.rescheduleAgent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('rescheduleAgent')"
              class="btn-update"
              :disabled="isProcessing || !agents.rescheduleAgent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('rescheduleAgent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.rescheduleAgent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('rescheduleAgent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.rescheduleAgent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Routing Agent -->
        <div class="agent-card" v-if="agents.routingAgent">
          <div class="agent-header">
            <h3>🚦 Routing Agent</h3>
            <span :class="['status-badge', agents.routingAgent.is_custom ? 'custom' : 'default']">
              {{ agents.routingAgent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-routingAgent`"
              v-model="agents.routingAgent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Routing Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.routingAgent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.routingAgent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.routingAgent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('routingAgent')"
              class="btn-update"
              :disabled="isProcessing || !agents.routingAgent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('routingAgent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.routingAgent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('routingAgent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.routingAgent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

      </div>

      <!-- No Prompts State -->
      <div v-else-if="!isLoadingPrompts" class="no-prompts-section">
        <h3>📭 No hay prompts disponibles</h3>
        <p>Selecciona una empresa y haz clic en "Recargar Todos" para ver los prompts.</p>
      </div>

    </div>

    <!-- Loading State -->
    <div v-if="isLoadingPrompts" class="loading-section">
      <div class="loading-spinner"></div>
      <p>Cargando prompts del sistema...</p>
    </div>

  </div>
</template>

<script>
export default {
  name: 'PromptsTab',
  props: {
    isActive: {
      type: Boolean,
      default: false
    },
    
    // Método para debug manual
    async debugPrompts() {
      console.log('=== DEBUG PROMPTS ===')
      console.log('1. Current Company ID:', this.currentCompanyId)
      console.log('2. Current Agents State:', JSON.stringify(this.agents, null, 2))
      console.log('3. Has Prompts?:', this.hasPrompts)
      console.log('4. Is Loading?:', this.isLoadingPrompts)
      console.log('5. Error?:', this.error)
      
      // Hacer petición manual para ver respuesta raw
      try {
        const response = await fetch(`/api/admin/prompts?company_id=${this.currentCompanyId}`)
        const data = await response.json()
        console.log('6. RAW API Response:', data)
        
        // Analizar estructura
        if (data.agents) {
          console.log('7. Agent Keys in Response:', Object.keys(data.agents))
          console.log('8. Agent Values:')
          Object.entries(data.agents).forEach(([key, value]) => {
            console.log(`   ${key}:`, value ? 'Has content' : 'Empty', 
                       value?.current_prompt ? `(${value.current_prompt.substring(0, 50)}...)` : '')
          })
        }
        
        return data
      } catch (err) {
        console.error('Debug Error:', err)
        return null
      }
    }
  },
  data() {
    return {
      isLoading: false,
      isLoadingPrompts: false,
      isProcessing: false,
      error: null,
      agents: {
        leadCaptureAgent: null,
        informationAgent: null,
        appointmentAgent: null,
        rescheduleAgent: null,
        routingAgent: null
      }
    }
  },
  computed: {
    currentCompanyId() {
      // Obtener desde window.currentCompanyId o localStorage
      return window.currentCompanyId || localStorage.getItem('currentCompanyId') || 'dental_clinic'
    },
    currentCompanyName() {
      return window.currentCompanyName || this.currentCompanyId
    },
    hasPrompts() {
      return Object.keys(this.agents).some(key => this.agents[key] !== null)
    }
  },
  watch: {
    isActive(newVal) {
      if (newVal && !this.hasPrompts) {
        this.loadPrompts()
      }
    }
  },
  mounted() {
    console.log('PromptsTab mounted')
    if (this.isActive) {
      this.loadPrompts()
    }
    
    // Exponer funciones globales
    window.loadCurrentPrompts = () => this.loadPrompts()
    window.updatePrompt = (agentName) => this.updatePrompt(agentName)
    window.resetPrompt = (agentName) => this.resetPrompt(agentName)
    window.debugPrompts = () => this.debugPrompts()
    
    // Exponer instancia para debug
    window.PromptsTabInstance = this
  },
  methods: {
    async loadPrompts() {
      if (!this.currentCompanyId) {
        this.error = 'Por favor selecciona una empresa primero'
        return
      }

      try {
        this.isLoadingPrompts = true
        this.error = null
        
        console.log(`Loading prompts for company: ${this.currentCompanyId}`)
        
        // Hacer la petición directamente
        const response = await fetch(`/api/admin/prompts?company_id=${this.currentCompanyId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-Company-ID': this.currentCompanyId
          }
        })
        
        const data = await response.json()
        console.log('Prompts response:', data)
        console.log('Agents detail:', JSON.stringify(data.agents, null, 2))
        
        if (data && data.agents) {
          // DEBUG: Ver exactamente qué agentes vienen
          console.log('Available agents in response:')
          Object.keys(data.agents).forEach(key => {
            console.log(`- ${key}:`, data.agents[key] ? 'Has data' : 'Empty')
          })
          
          // Asignar los agentes recibidos
          this.agents = {
            leadCaptureAgent: data.agents.leadCaptureAgent || null,
            informationAgent: data.agents.informationAgent || null,
            appointmentAgent: data.agents.appointmentAgent || null,
            rescheduleAgent: data.agents.rescheduleAgent || null,
            routingAgent: data.agents.routingAgent || null
          }
          
          // DEBUG: Ver estado después de asignar
          console.log('Assigned agents:', this.agents)
          console.log('Has prompts?', this.hasPrompts)
          console.log('hasPrompts calculation test:')
          Object.keys(this.agents).forEach(key => {
            console.log(`  ${key} !== null?`, this.agents[key] !== null)
          })
          console.log(`Loaded ${Object.keys(data.agents).length} prompts`)
          
          // Forzar actualización de la vista
          this.$forceUpdate()
        } else {
          this.error = 'No se recibieron prompts del servidor'
        }
        
      } catch (err) {
        this.error = `Error cargando prompts: ${err.message}`
        console.error('Error loading prompts:', err)
      } finally {
        this.isLoadingPrompts = false
      }
    },
    
    async updatePrompt(agentName) {
      if (!this.currentCompanyId) {
        alert('Por favor selecciona una empresa primero')
        return
      }

      const promptContent = this.agents[agentName]?.current_prompt
      if (!promptContent || !promptContent.trim()) {
        alert('El prompt no puede estar vacío')
        return
      }

      try {
        this.isProcessing = true
        
        console.log(`Updating prompt for ${agentName}`)
        
        const response = await fetch(`/api/admin/prompts/${agentName}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-Company-ID': this.currentCompanyId
          },
          body: JSON.stringify({
            company_id: this.currentCompanyId,
            prompt_template: promptContent
          })
        })
        
        const data = await response.json()
        
        if (response.ok) {
          // Actualizar el estado local
          if (this.agents[agentName]) {
            this.agents[agentName].is_custom = true
            this.agents[agentName].last_modified = new Date().toISOString()
          }
          
          alert(`Prompt de ${agentName} actualizado exitosamente`)
        } else {
          throw new Error(data.error || 'Error actualizando prompt')
        }
        
      } catch (err) {
        alert(`Error actualizando prompt: ${err.message}`)
        console.error('Error updating prompt:', err)
      } finally {
        this.isProcessing = false
      }
    },
    
    async resetPrompt(agentName) {
      if (!this.currentCompanyId) {
        alert('Por favor selecciona una empresa primero')
        return
      }

      if (!confirm(`¿Estás seguro de restaurar el prompt de ${agentName} a su valor por defecto?`)) {
        return
      }

      try {
        this.isProcessing = true
        
        console.log(`Resetting prompt for ${agentName}`)
        
        const response = await fetch(`/api/admin/prompts/${agentName}?company_id=${this.currentCompanyId}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'X-Company-ID': this.currentCompanyId
          }
        })
        
        if (response.ok) {
          // Recargar los prompts para obtener el valor por defecto
          await this.loadPrompts()
          alert(`Prompt de ${agentName} restaurado exitosamente`)
        } else {
          const data = await response.json()
          throw new Error(data.error || 'Error reseteando prompt')
        }
        
      } catch (err) {
        alert(`Error reseteando prompt: ${err.message}`)
        console.error('Error resetting prompt:', err)
      } finally {
        this.isProcessing = false
      }
    },
    
    previewPrompt(agentName) {
      const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
      
      if (!testMessage) return
      
      // Por ahora, mostrar el prompt en un alert
      const promptContent = this.agents[agentName]?.current_prompt || ''
      const preview = `=== PREVIEW DE ${agentName} ===\n\nMensaje de prueba: ${testMessage}\n\nPrompt actual:\n${promptContent.substring(0, 500)}...`
      
      alert(preview)
    },
    
    async repairAllPrompts() {
      if (!confirm('¿Reparar todos los prompts desde el repositorio?')) {
        return
      }

      try {
        this.isProcessing = true
        
        const response = await fetch('/api/admin/prompts/repair', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Company-ID': this.currentCompanyId
          },
          body: JSON.stringify({
            company_id: this.currentCompanyId,
            agents: Object.keys(this.agents)
          })
        })
        
        if (response.ok) {
          alert('Prompts reparados exitosamente')
          await this.loadPrompts()
        }
        
      } catch (err) {
        alert(`Error reparando prompts: ${err.message}`)
      } finally {
        this.isProcessing = false
      }
    },
    
    exportPrompts() {
      try {
        const exportData = {
          company_id: this.currentCompanyId,
          company_name: this.currentCompanyName,
          timestamp: new Date().toISOString(),
          agents: this.agents
        }
        
        const dataStr = JSON.stringify(exportData, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        
        const link = document.createElement('a')
        link.href = URL.createObjectURL(dataBlob)
        link.download = `prompts_${this.currentCompanyId}_${Date.now()}.json`
        link.click()
        
        alert('Prompts exportados exitosamente')
      } catch (err) {
        alert('Error exportando prompts')
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      try {
        return new Date(dateString).toLocaleDateString()
      } catch {
        return 'Fecha inválida'
      }
    },
    
    handleStatusLoaded(status) {
      console.log('Status loaded:', status)
      if (status?.postgresql_available && status?.tables_exist) {
        this.loadPrompts()
      }
    },
    
    handleMigrationComplete() {
      this.loadPrompts()
    }
  }
}
</script>

<style scoped>
.prompts-tab {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-header {
  text-align: center;
  margin-bottom: 30px;
}

.tab-header h2 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 2em;
}

.tab-description {
  color: #6c757d;
  font-size: 1.1em;
  margin: 0;
}

.prompts-main-section {
  margin-top: 20px;
}

.company-bar {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-label {
  font-weight: 600;
  color: #495057;
}

.company-name {
  color: #007bff;
  font-weight: bold;
  font-size: 1.1em;
}

.actions-bar {
  display: flex;
  gap: 10px;
}

.actions-bar button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-refresh {
  background: #28a745;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background: #218838;
}

.btn-repair-all {
  background: #fd7e14;
  color: white;
}

.btn-repair-all:hover:not(:disabled) {
  background: #e8690b;
}

.btn-export {
  background: #17a2b8;
  color: white;
}

.btn-export:hover:not(:disabled) {
  background: #117a8b;
}

.error-section {
  background: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

/* Prompts Grid */
.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.agent-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.agent-header {
  background: #f8f9fa;
  padding: 15px;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #495057;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 600;
}

.status-badge.custom {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.status-badge.default {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.agent-body {
  padding: 15px;
}

.prompt-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  transition: border-color 0.2s;
}

.prompt-textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
}

.prompt-info {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 0.85em;
  color: #6c757d;
}

.agent-actions {
  padding: 15px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
  display: flex;
  gap: 10px;
}

.agent-actions button {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9em;
  transition: all 0.2s;
}

.btn-update {
  background: #007bff;
  color: white;
}

.btn-update:hover:not(:disabled) {
  background: #0056b3;
}

.btn-reset {
  background: #6c757d;
  color: white;
}

.btn-reset:hover:not(:disabled) {
  background: #545b62;
}

.btn-preview {
  background: #17a2b8;
  color: white;
}

.btn-preview:hover:not(:disabled) {
  background: #117a8b;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-prompts-section {
  text-align: center;
  padding: 60px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #dee2e6;
}

.loading-section {
  text-align: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .prompts-grid {
    grid-template-columns: 1fr;
  }
  
  .company-bar {
    flex-direction: column;
    gap: 15px;
  }
  
  .actions-bar {
    width: 100%;
    flex-direction: column;
  }
  
  .actions-bar button {
    width: 100%;
  }
}
</style>
