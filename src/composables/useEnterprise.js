/**
 * useEnterprise.js - Composable para Funciones Enterprise - CORREGIDO
 * MIGRADO DE: script.js funciones loadEnterpriseCompanies(), createEnterpriseCompany(), editEnterpriseCompany(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 * 🔧 CORRECCIÓN: Manejo correcto del formato de respuesta de la API
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useEnterprise = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const enterpriseCompanies = ref([])
  const selectedCompany = ref(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const isUpdating = ref(false)
  const isTesting = ref(false)
  const isMigrating = ref(false)
  
  const companyForm = ref({
    company_id: '',
    company_name: '',
    services: {},
    configuration: {},
    notes: ''
  })
  
  const testResults = ref({})
  const migrationResults = ref(null)
  const lastUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const companiesCount = computed(() => enterpriseCompanies.value.length)

  const hasCompanies = computed(() => enterpriseCompanies.value.length > 0)

  const activeCompanies = computed(() => {
    return enterpriseCompanies.value.filter(company => 
      company.status !== 'disabled' && company.status !== 'inactive'
    )
  })

  const companyOptions = computed(() => {
    return enterpriseCompanies.value.map(company => ({
      value: company.company_id,
      label: `${company.company_name || company.company_id} (${company.company_id})`,
      status: company.status || 'unknown',
      disabled: company.status === 'disabled'
    }))
  })

  const isFormValid = computed(() => {
    return companyForm.value.company_id.trim() &&
           companyForm.value.company_name.trim() &&
           Object.keys(companyForm.value.services).length > 0
  })

  const isAnyProcessing = computed(() => 
    isLoading.value || isCreating.value || isUpdating.value || isTesting.value || isMigrating.value
  )

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS - CORREGIDAS
  // ============================================================================

  /**
   * Carga empresas enterprise - MIGRADO: loadEnterpriseCompanies() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto del formato de respuesta API
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadEnterpriseCompanies = async () => {
    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      // PRESERVAR: Llamada API exacta como script.js con API key
      const response = await apiRequest('/api/admin/companies', {
        method: 'GET',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      console.log('✅ Enterprise companies response:', response) // DEBUG para verificar formato

      // 🔧 CORRECCIÓN CRÍTICA: La API devuelve {companies: Array}, no Array directo
      if (response && response.companies && Array.isArray(response.companies)) {
        enterpriseCompanies.value = response.companies
        lastUpdateTime.value = new Date().toISOString()

        // PRESERVAR: Actualizar cache como script.js
        appStore.cache.enterpriseCompanies = response.companies
        appStore.cache.lastUpdate.enterpriseCompanies = Date.now()

        // PRESERVAR: Actualizar tabla en DOM como script.js
        updateEnterpriseCompaniesTable(response.companies)

        addToLog(`Enterprise companies loaded successfully (${response.companies.length} companies)`, 'success')
        showNotification(`${response.companies.length} empresas enterprise cargadas`, 'success')
        
      } else {
        // 🔧 CORRECCIÓN: Mensaje de error más específico
        console.error('Invalid response format:', response)
        throw new Error(`Invalid response format: expected object with companies array, got ${typeof response}`)
      }

      return response.companies

    } catch (error) {
      addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
      showNotification('Error cargando empresas enterprise: ' + error.message, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al cargar empresas enterprise</p>
            <p>${error.message}</p>
            <p><strong>Formato recibido:</strong> ${typeof response}</p>
            <p><strong>API Key configurada:</strong> ${appStore.adminApiKey ? 'SÍ' : 'NO'}</p>
          </div>
        `
      }

      // Limpiar estado en caso de error
      enterpriseCompanies.value = []
      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * Crea nueva empresa enterprise - MIGRADO: createEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto de respuesta de creación
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const createEnterpriseCompany = async (companyData = null) => {
    // Si no se pasan datos, obtenerlos del formulario DOM como script.js
    if (!companyData) {
      companyData = getCompanyDataFromForm()
      if (!companyData) return false
    }

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // PRESERVAR: Validaciones como script.js
      if (!companyData.company_id || !companyData.company_name) {
        throw new Error('company_id y company_name son requeridos')
      }

      // PRESERVAR: Request exacto como script.js con API key
      const response = await apiRequest('/api/admin/companies', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: companyData
      })

      // 🔧 CORRECCIÓN: Manejo correcto de respuesta de creación
      let newCompany = response
      if (response.company) {
        newCompany = response.company
      } else if (response.data) {
        newCompany = response.data
      }

      // Actualizar lista local
      enterpriseCompanies.value.push(newCompany)

      // PRESERVAR: Mostrar resultado como script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Empresa Enterprise Creada</h4>
            <p><strong>ID:</strong> ${newCompany.company_id}</p>
            <p><strong>Nombre:</strong> ${newCompany.company_name}</p>
            <div class="json-container">
              <pre>${JSON.stringify(newCompany, null, 2)}</pre>
            </div>
          </div>
        `
      }

      // Limpiar formulario
      clearCompanyForm()

      addToLog(`Enterprise company created successfully: ${newCompany.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')

      // Recargar lista
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      addToLog(`Error creating enterprise company: ${error.message}`, 'error')
      showNotification('Error creando empresa enterprise: ' + error.message, 'error')

      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al crear empresa enterprise</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return false

    } finally {
      isCreating.value = false
    }
  }

  /**
   * Ver detalles de empresa enterprise - MIGRADO: viewEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto de respuesta de empresa individual
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/companies/${companyId}`, {
        method: 'GET',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      // 🔧 CORRECCIÓN: Manejo correcto de respuesta de empresa individual
      let companyData = response
      if (response.company) {
        companyData = response.company
      } else if (response.data) {
        companyData = response.data
      }

      selectedCompany.value = companyData

      // PRESERVAR: Mostrar detalles en modal como script.js
      showCompanyDetailsModal(companyData)

      addToLog(`Enterprise company details loaded: ${companyId}`, 'success')
      
      return companyData

    } catch (error) {
      addToLog(`Error viewing enterprise company: ${error.message}`, 'error')
      showNotification('Error viendo empresa enterprise: ' + error.message, 'error')
      return null
    }
  }

  /**
   * Edita empresa enterprise - MIGRADO: editEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto de carga de datos para edición
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const editEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return
    }

    try {
      addToLog(`Loading company for edit: ${companyId}`, 'info')

      // Cargar datos de la empresa
      const company = await viewEnterpriseCompany(companyId)
      if (!company) return

      // PRESERVAR: Llenar formulario como script.js
      populateCompanyForm(company)

      // PRESERVAR: Mostrar formulario de edición como script.js
      showEditCompanyForm(company)

    } catch (error) {
      addToLog(`Error loading company for edit: ${error.message}`, 'error')
      showNotification('Error cargando empresa para editar: ' + error.message, 'error')
    }
  }

  /**
   * Guarda cambios de empresa enterprise - MIGRADO: saveEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto de respuesta de actualización
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const saveEnterpriseCompany = async (companyId, companyData = null) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return false
    }

    // Si no se pasan datos, obtenerlos del formulario
    if (!companyData) {
      companyData = getCompanyDataFromForm()
      if (!companyData) return false
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/companies/${companyId}`, {
        method: 'PUT',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: companyData
      })

      // 🔧 CORRECCIÓN: Manejo correcto de respuesta de actualización
      let updatedCompany = response
      if (response.company) {
        updatedCompany = response.company
      } else if (response.data) {
        updatedCompany = response.data
      }

      // Actualizar en lista local
      const index = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (index !== -1) {
        enterpriseCompanies.value[index] = updatedCompany
      }

      // PRESERVAR: Mostrar resultado como script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Empresa Enterprise Actualizada</h4>
            <p><strong>ID:</strong> ${updatedCompany.company_id}</p>
            <p><strong>Nombre:</strong> ${updatedCompany.company_name}</p>
            <div class="json-container">
              <pre>${JSON.stringify(updatedCompany, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      // Recargar lista
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      addToLog(`Error updating enterprise company: ${error.message}`, 'error')
      showNotification('Error actualizando empresa enterprise: ' + error.message, 'error')

      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al actualizar empresa enterprise</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return false

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * Prueba empresa enterprise - MIGRADO: testEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Manejo correcto de respuesta de test
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const testEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      isTesting.value = true
      addToLog(`Testing enterprise company: ${companyId}`, 'info')
      showNotification('Probando empresa enterprise...', 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/companies/${companyId}/test`, {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      testResults.value[companyId] = {
        ...response,
        timestamp: new Date().toISOString()
      }

      // PRESERVAR: Mostrar resultado como script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        const isSuccess = response.status === 'success' || response.overall_status === 'success'
        const resultClass = isSuccess ? 'result-success' : 'result-error'
        const resultIcon = isSuccess ? '✅' : '❌'
        
        resultsContainer.innerHTML = `
          <div class="result-container ${resultClass}">
            <h4>${resultIcon} Test de Empresa Enterprise</h4>
            <p><strong>Empresa:</strong> ${companyId}</p>
            <p><strong>Estado:</strong> ${response.status || response.overall_status}</p>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      const isSuccess = response.status === 'success' || response.overall_status === 'success'
      const message = isSuccess ? 
        'Test de empresa enterprise completado exitosamente' : 
        'Test de empresa enterprise completado con errores'
      
      addToLog(`Enterprise company test completed: ${companyId}`, isSuccess ? 'success' : 'warning')
      showNotification(message, isSuccess ? 'success' : 'warning')

      return response

    } catch (error) {
      addToLog(`Error testing enterprise company: ${error.message}`, 'error')
      showNotification('Error probando empresa enterprise: ' + error.message, 'error')

      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al probar empresa enterprise</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return null

    } finally {
      isTesting.value = false
    }
  }

  /**
   * Migra empresas a PostgreSQL - MIGRADO: migrateCompaniesToPostgreSQL() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const migrateCompaniesToPostgreSQL = async () => {
    if (!confirm('¿Estás seguro de migrar las empresas a PostgreSQL? Esta operación puede tomar tiempo.')) {
      return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      // PRESERVAR: Request como script.js
      const response = await apiRequest('/api/enterprise/companies/migrate', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: {
          target: 'postgresql'
        }
      })

      migrationResults.value = response

      // PRESERVAR: Mostrar resultado como script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Migración de Empresas Completada</h4>
            <p><strong>Empresas migradas:</strong> ${response.migrated_count || 'N/A'}</p>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // Recargar empresas después de la migración
      await loadEnterpriseCompanies()

      return true

    } catch (error) {
      addToLog(`Error migrating companies: ${error.message}`, 'error')
      showNotification('Error en migración de empresas: ' + error.message, 'error')

      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en migración de empresas</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return false

    } finally {
      isMigrating.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES DOM (PRESERVAR COMPATIBILIDAD)
  // ============================================================================

  /**
   * Actualiza tabla de empresas en DOM - PRESERVAR: Como script.js
   */
  const updateEnterpriseCompaniesTable = (companies) => {
    const tableContainer = document.getElementById('enterpriseCompaniesTable')
    if (!tableContainer) return

    if (companies.length === 0) {
      tableContainer.innerHTML = '<p>No hay empresas enterprise configuradas.</p>'
      return
    }

    let tableHtml = `
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Estado</th>
            <th>Servicios</th>
            <th>Última Modificación</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
    `

    companies.forEach(company => {
      const servicesCount = Object.keys(company.services || {}).length
      const lastModified = company.last_modified ? 
        new Date(company.last_modified).toLocaleDateString() : 'N/A'
      
      tableHtml += `
        <tr>
          <td>${company.company_id}</td>
          <td>${company.company_name || 'N/A'}</td>
          <td><span class="status-${company.status || 'unknown'}">${company.status || 'Unknown'}</span></td>
          <td>${servicesCount} servicios</td>
          <td>${lastModified}</td>
          <td>
            <button onclick="viewEnterpriseCompany('${company.company_id}')" class="btn btn-info btn-small">Ver</button>
            <button onclick="editEnterpriseCompany('${company.company_id}')" class="btn btn-primary btn-small">Editar</button>
            <button onclick="testEnterpriseCompany('${company.company_id}')" class="btn btn-secondary btn-small">Test</button>
          </td>
        </tr>
      `
    })

    tableHtml += `
        </tbody>
      </table>
    `

    tableContainer.innerHTML = tableHtml
  }

  /**
   * Obtiene datos del formulario DOM - PRESERVAR: Como script.js
   */
  const getCompanyDataFromForm = () => {
    const companyIdInput = document.getElementById('enterpriseCompanyId')
    const companyNameInput = document.getElementById('enterpriseCompanyName')
    const servicesInput = document.getElementById('enterpriseServices')
    const notesInput = document.getElementById('enterpriseNotes')

    if (!companyIdInput || !companyNameInput) {
      showNotification('Formulario de empresa no encontrado', 'error')
      return null
    }

    try {
      const services = servicesInput?.value ? JSON.parse(servicesInput.value) : {}
      
      return {
        company_id: companyIdInput.value.trim(),
        company_name: companyNameInput.value.trim(),
        services,
        notes: notesInput?.value || ''
      }
    } catch (error) {
      showNotification('Error en formato de servicios JSON: ' + error.message, 'error')
      return null
    }
  }

  /**
   * Llena formulario con datos de empresa
   */
  const populateCompanyForm = (company) => {
    const companyIdInput = document.getElementById('enterpriseCompanyId')
    const companyNameInput = document.getElementById('enterpriseCompanyName')
    const servicesInput = document.getElementById('enterpriseServices')
    const notesInput = document.getElementById('enterpriseNotes')

    if (companyIdInput) companyIdInput.value = company.company_id || ''
    if (companyNameInput) companyNameInput.value = company.company_name || ''
    if (servicesInput) servicesInput.value = JSON.stringify(company.services || {}, null, 2)
    if (notesInput) notesInput.value = company.notes || ''

    companyForm.value = {
      company_id: company.company_id || '',
      company_name: company.company_name || '',
      services: company.services || {},
      configuration: company.configuration || {},
      notes: company.notes || ''
    }
  }

  /**
   * Limpia formulario de empresa
   */
  const clearCompanyForm = () => {
    const inputs = ['enterpriseCompanyId', 'enterpriseCompanyName', 'enterpriseServices', 'enterpriseNotes']
    inputs.forEach(inputId => {
      const input = document.getElementById(inputId)
      if (input) input.value = ''
    })

    companyForm.value = {
      company_id: '',
      company_name: '',
      services: {},
      configuration: {},
      notes: ''
    }
  }

  /**
   * Muestra modal de detalles de empresa
   */
  const showCompanyDetailsModal = (company) => {
    const modalHtml = `
      <div id="companyDetailsModal" class="modal" style="display: block;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Detalles de Empresa Enterprise</h3>
            <span class="close" onclick="closeModal()">&times;</span>
          </div>
          <div class="modal-body">
            <div class="json-container">
              <pre>${JSON.stringify(company, null, 2)}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button onclick="editEnterpriseCompany('${company.company_id}')" class="btn btn-primary">Editar</button>
            <button onclick="testEnterpriseCompany('${company.company_id}')" class="btn btn-secondary">Test</button>
            <button onclick="closeModal()" class="btn btn-secondary">Cerrar</button>
          </div>
        </div>
      </div>
    `

    // Remover modal existente
    const existingModal = document.getElementById('companyDetailsModal')
    if (existingModal) existingModal.remove()

    // Agregar nuevo modal
    document.body.insertAdjacentHTML('beforeend', modalHtml)
  }

  /**
   * Muestra formulario de edición
   */
  const showEditCompanyForm = (company) => {
    const editSection = document.getElementById('enterpriseEditSection')
    if (editSection) {
      editSection.style.display = 'block'
      editSection.scrollIntoView({ behavior: 'smooth' })
    }
  }

  // ============================================================================
  // FUNCIONES DE UTILIDADES
  // ============================================================================

  const getCompanyById = (companyId) => {
    return enterpriseCompanies.value.find(c => c.company_id === companyId) || null
  }

  const exportCompanies = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        companies: enterpriseCompanies.value,
        total_count: enterpriseCompanies.value.length
      }

      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      } else if (format === 'csv') {
        const headers = 'Company_ID,Company_Name,Status,Services_Count,Last_Modified,Notes\n'
        content = headers + enterpriseCompanies.value.map(company => 
          `"${company.company_id}","${company.company_name || ''}","${company.status || ''}","${Object.keys(company.services || {}).length}","${company.last_modified || ''}","${(company.notes || '').replace(/"/g, '""')}"`
        ).join('\n')
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `enterprise_companies_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`Enterprise companies exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Empresas enterprise exportadas en formato ${format.toUpperCase()}`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting companies: ${error.message}`, 'error')
      showNotification(`Error exportando empresas: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
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

    // Computed properties
    companiesCount,
    hasCompanies,
    activeCompanies,
    companyOptions,
    isFormValid,
    isAnyProcessing,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    viewEnterpriseCompany,
    editEnterpriseCompany,
    saveEnterpriseCompany,
    testEnterpriseCompany,
    migrateCompaniesToPostgreSQL,

    // Funciones auxiliares
    getCompanyById,
    exportCompanies,
    clearCompanyForm,
    populateCompanyForm,
    updateEnterpriseCompaniesTable
  }
}
