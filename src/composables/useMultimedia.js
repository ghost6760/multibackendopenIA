/**
 * useMultimedia.js - Composable para Procesamiento Multimedia
 * MIGRADO Y ACTUALIZADO desde script.js 
 * PRESERVA: Comportamiento exacto de las funciones originales
 * ENDPOINTS: Idénticos a script.js
 * VALIDACIONES: Exactas como script.js
 * CORREGIDO: Referencias DOM seguras y manejo de errores
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useMultimedia = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL REACTIVO - SEPARADO POR FUNCIONALIDAD
  // ============================================================================

  const isProcessingAudio = ref(false)
  const isProcessingImage = ref(false)
  const isTestingIntegration = ref(false)
  const isRecording = ref(false)
  const isCapturingScreen = ref(false)
  
  // SEPARADO: Resultados independientes
  const audioResults = ref(null)              // Solo para AudioProcessor
  const imageResults = ref(null)              // Solo para ImageProcessor
  const integrationResults = ref(null)        // Solo para tests
  const screenCaptureResults = ref(null)      // Solo para ScreenCapture
  const voiceRecordingResults = ref(null)     // Solo para VoiceRecorder
  
  // Media recording state - SOLO PARA GRABACIÓN
  const mediaRecorder = ref(null)
  const recordedChunks = ref([])
  const processingProgress = ref(0)
  const recordingDuration = ref(0)
  const recordingInterval = ref(null)

  // NUEVO: Estado específico para procesamiento de grabación de voz
  const isProcessingVoiceRecording = ref(false)
  const voiceProcessingProgress = ref(0)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const isAnyProcessing = computed(() => 
    isProcessingAudio.value || 
    isProcessingImage.value || 
    isTestingIntegration.value ||
    isCapturingScreen.value ||
    isProcessingVoiceRecording.value
  )

  const multimediaCapabilities = computed(() => ({
    audio: !!navigator.mediaDevices?.getUserMedia,
    screen: !!navigator.mediaDevices?.getDisplayMedia,
    files: !!window.File && !!window.FileReader,
    webrtc: !!window.RTCPeerConnection,
    webgl: !!window.WebGLRenderingContext
  }))

  // ============================================================================
  // HELPERS SEGUROS PARA DOM
  // ============================================================================

  const safeGetElement = (id) => {
    try {
      return document.getElementById(id)
    } catch (error) {
      console.warn(`Element ${id} not found:`, error)
      return null
    }
  }

  const safeUpdateDOM = (elementId, html) => {
    try {
      const element = safeGetElement(elementId)
      if (element) {
        element.innerHTML = html
      }
    } catch (error) {
      console.warn(`Error updating DOM element ${elementId}:`, error)
    }
  }

  const safeGetInputValue = (id) => {
    try {
      const element = safeGetElement(id)
      return element ? element.value.trim() : ''
    } catch (error) {
      console.warn(`Error getting input value ${id}:`, error)
      return ''
    }
  }

  // ============================================================================
  // FUNCIONES PRINCIPALES - EXACTAS A SCRIPT.JS CON MANEJO SEGURO
  // ============================================================================

  /**
   * Procesa archivo de audio - MIGRADO: processAudio() de script.js
   * PRESERVAR: Comportamiento y endpoints exactos
   * SOLO para AudioProcessor - NO para grabaciones de voz
   */
  const processAudio = async (audioFile = null, options = {}) => {
    // Validar empresa seleccionada - PRESERVAR lógica script.js
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    // Si no se pasa archivo, intentar obtenerlo del DOM como en script.js
    if (!audioFile) {
      const fileInput = safeGetElement('audioFile')
      if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        showNotification('Por favor selecciona un archivo de audio', 'warning')
        return null
      }
      audioFile = fileInput.files[0]
    }

    if (isProcessingAudio.value) {
      showNotification('Ya se está procesando un archivo de audio', 'warning')
      return null
    }

    try {
      isProcessingAudio.value = true
      processingProgress.value = 0
      audioResults.value = null

      addToLog(`Starting audio processing: ${audioFile.name}`, 'info')
      showNotification('Procesando archivo de audio...', 'info')

      // PRESERVAR: Validaciones exactas como en script.js
      if (!audioFile.type.startsWith('audio/')) {
        throw new Error('El archivo debe ser de audio')
      }

      // PRESERVAR: Límite de tamaño exacto como script.js
      const maxSize = 50 * 1024 * 1024 // 50MB
      if (audioFile.size > maxSize) {
        throw new Error('El archivo es demasiado grande. Máximo 50MB')
      }

      // Crear FormData - PRESERVAR: Estructura exacta como script.js
      const formData = new FormData()
      formData.append('audio', audioFile)

      // PRESERVAR: Company ID handling exacto
      formData.append('company_id', appStore.currentCompanyId)
      
      // PRESERVAR: Obtener userId del DOM como script.js (SEGURO)
      const userId = safeGetInputValue('audioUserId')
      if (userId) {
        formData.append('user_id', userId)
      }

      // Agregar opciones adicionales
      if (options.language) formData.append('language', options.language)
      if (options.prompt) formData.append('prompt', options.prompt)

      processingProgress.value = 25

      // PRESERVAR: Endpoint exacto como script.js CORREGIDO
      const response = await apiRequest('/api/multimedia/process-voice', {
        method: 'POST',
        body: formData
      })

      processingProgress.value = 100
      audioResults.value = response

      // PRESERVAR: Actualizar DOM como script.js SI EXISTE (SEGURO)
      const transcript = response.transcript || response.transcription || 'Sin transcripción'
      const botResponse = response.bot_response || response.response || response.message || null
      const companyId = response.company_id || appStore.currentCompanyId
      const processingTime = response.processing_time || response.time || null
      
      let resultHTML = `
        <div class="result-container result-success">
          <h4>🎵 Procesamiento de Audio Completado</h4>
          <p><strong>Transcripción:</strong></p>
          <div class="code-block">${escapeHTML(transcript)}</div>
      `
      
      if (botResponse) {
        resultHTML += `
          <p><strong>Respuesta del Bot:</strong></p>
          <div class="code-block">${escapeHTML(botResponse)}</div>
        `
      }
      
      resultHTML += `
          <p><strong>Empresa:</strong> ${companyId}</p>
      `
      
      if (processingTime) {
        resultHTML += `<p><strong>Tiempo:</strong> ${processingTime}ms</p>`
      }
      
      resultHTML += `</div>`
      
      safeUpdateDOM('audioResult', resultHTML)

      addToLog('Audio processing completed successfully', 'success')
      showNotification('Audio procesado exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Audio processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando audio: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js (SEGURO)
      const errorHTML = `
        <div class="result-container result-error">
          <p>❌ Error al procesar audio</p>
          <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
          <p><strong>Empresa:</strong> ${appStore.currentCompanyId}</p>
        </div>
      `
      safeUpdateDOM('audioResult', errorHTML)

      throw error

    } finally {
      isProcessingAudio.value = false
      processingProgress.value = 0
    }
  }

  /**
   * NUEVO: Procesa grabación de voz - INDEPENDIENTE del procesamiento de audio
   * Usa endpoint idéntico pero resultados separados
   */
  const processVoiceRecording = async (voiceBlob, userId, options = {}) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    if (!voiceBlob) {
      showNotification('No hay grabación de voz para procesar', 'warning')
      return null
    }

    if (isProcessingVoiceRecording.value) {
      showNotification('Ya se está procesando una grabación de voz', 'warning')
      return null
    }

    try {
      isProcessingVoiceRecording.value = true
      voiceProcessingProgress.value = 0

      addToLog('Starting voice recording processing', 'info')
      showNotification('Procesando grabación de voz...', 'info')

      // Crear archivo desde blob
      const file = new File([voiceBlob], `voice_recording_${Date.now()}.webm`, { type: 'audio/webm' })

      // Crear FormData igual que processAudio pero para grabación
      const formData = new FormData()
      formData.append('audio', file)
      formData.append('company_id', appStore.currentCompanyId)
      
      if (userId && userId.trim()) {
        formData.append('user_id', userId.trim())
      }

      // Agregar opciones adicionales
      if (options.language) formData.append('language', options.language)
      if (options.prompt) formData.append('prompt', options.prompt)

      voiceProcessingProgress.value = 25

      // MISMO endpoint pero resultados van a voiceRecordingResults
      const response = await apiRequest('/api/multimedia/process-voice', {
        method: 'POST',
        body: formData
      })

      voiceProcessingProgress.value = 100

      // IMPORTANTE: Los resultados van a voiceRecordingResults, NO a audioResults
      // Preservar datos de grabación existentes y agregar datos de procesamiento
      const currentResults = voiceRecordingResults.value || {}
      
      voiceRecordingResults.value = {
        ...currentResults, // Preservar blob, url, duration, timestamp, etc.
        processed: true,
        transcript: response.transcript || response.transcription || 'Sin transcripción',
        bot_response: response.bot_response || response.response || response.message || null,
        company_id: response.company_id || appStore.currentCompanyId,
        processing_time: response.processing_time || response.time || null,
        full_response: response
      }

      addToLog('Voice recording processing completed successfully', 'success')
      showNotification('Grabación de voz procesada exitosamente', 'success')

      return voiceRecordingResults.value

    } catch (error) {
      addToLog(`Voice recording processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando grabación: ${error.message}`, 'error')

      // Actualizar voiceRecordingResults con error
      if (voiceRecordingResults.value) {
        voiceRecordingResults.value.processingError = error.message
      }

      throw error

    } finally {
      isProcessingVoiceRecording.value = false
      voiceProcessingProgress.value = 0
    }
  }

  /**
   * Procesa imagen - MIGRADO: processImage() de script.js  
   * PRESERVAR: Comportamiento y endpoints exactos CON MANEJO SEGURO
   */
  const processImage = async (imageFile = null, options = {}) => {
    // Validar empresa seleccionada
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    // Si no se pasa archivo, intentar obtenerlo del DOM como en script.js
    if (!imageFile) {
      const fileInput = safeGetElement('imageFile')
      if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        showNotification('Por favor selecciona una imagen', 'warning')
        return null
      }
      imageFile = fileInput.files[0]
    }

    if (isProcessingImage.value) {
      showNotification('Ya se está procesando una imagen', 'warning')
      return null
    }

    try {
      isProcessingImage.value = true
      processingProgress.value = 0
      imageResults.value = null

      addToLog(`Starting image processing: ${imageFile.name}`, 'info')
      showNotification('Procesando imagen...', 'info')

      // PRESERVAR: Validaciones exactas como en script.js
      if (!imageFile.type.startsWith('image/')) {
        throw new Error('El archivo debe ser una imagen')
      }

      // PRESERVAR: Límite de tamaño exacto como script.js
      const maxSize = 20 * 1024 * 1024 // 20MB
      if (imageFile.size > maxSize) {
        throw new Error('La imagen es demasiado grande. Máximo 20MB')
      }

      // Crear FormData - PRESERVAR: Estructura exacta como script.js
      const formData = new FormData()
      formData.append('image', imageFile)

      // PRESERVAR: Company ID handling exacto
      formData.append('company_id', appStore.currentCompanyId)
      
      // PRESERVAR: Obtener userId del DOM como script.js (SEGURO)
      const userId = safeGetInputValue('imageUserId')
      if (userId) {
        formData.append('user_id', userId)
      }

      // Agregar opciones adicionales
      if (options.analysis_type) formData.append('analysis_type', options.analysis_type)
      if (options.prompt) formData.append('prompt', options.prompt)

      processingProgress.value = 25

      // PRESERVAR: Endpoint exacto como script.js CORREGIDO
      const response = await apiRequest('/api/multimedia/process-image', {
        method: 'POST',
        body: formData
      })

      processingProgress.value = 100
      imageResults.value = response

      // PRESERVAR: Actualizar DOM como script.js SI EXISTE (SEGURO)
      const analysis = response.analysis || response.description || response.image_analysis || 'Sin análisis'
      const botResponse = response.bot_response || response.response || response.message || null
      const companyId = response.company_id || appStore.currentCompanyId
      const processingTime = response.processing_time || response.time || null
      
      let resultHTML = `
        <div class="result-container result-success">
          <h4>📸 Procesamiento de Imagen Completado</h4>
          <p><strong>Análisis:</strong></p>
          <div class="code-block">${escapeHTML(analysis)}</div>
      `
      
      if (botResponse) {
        resultHTML += `
          <p><strong>Respuesta del Bot:</strong></p>
          <div class="code-block">${escapeHTML(botResponse)}</div>
        `
      }
      
      resultHTML += `
          <p><strong>Empresa:</strong> ${companyId}</p>
      `
      
      if (processingTime) {
        resultHTML += `<p><strong>Tiempo:</strong> ${processingTime}ms</p>`
      }
      
      resultHTML += `</div>`
      
      safeUpdateDOM('imageResult', resultHTML)

      addToLog('Image processing completed successfully', 'success')
      showNotification('Imagen procesada exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Image processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando imagen: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js (SEGURO)
      const errorHTML = `
        <div class="result-container result-error">
          <p>❌ Error al procesar imagen</p>
          <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
          <p><strong>Empresa:</strong> ${appStore.currentCompanyId}</p>
        </div>
      `
      safeUpdateDOM('imageResult', errorHTML)

      throw error

    } finally {
      isProcessingImage.value = false
      processingProgress.value = 0
    }
  }

  /**
   * Prueba la integración multimedia - MIGRADO: testMultimediaIntegration() de script.js
   * PRESERVAR: Comportamiento exacto de la función original CON MANEJO SEGURO
   */
  const testMultimediaIntegration = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    if (isTestingIntegration.value) {
      showNotification('Ya se está ejecutando un test de integración', 'warning')
      return
    }

    try {
      isTestingIntegration.value = true
      integrationResults.value = null

      addToLog('Starting multimedia integration test', 'info')
      showNotification('Ejecutando test de integración multimedia...', 'info')

      const response = await apiRequest('/api/admin/multimedia/test', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId
        }
      })

      integrationResults.value = response

      // PRESERVAR: Actualizar DOM como script.js (SEGURO)
      const integration = response.multimedia_integration || {}
      
      const resultHTML = `
        <div class="result-container result-success">
          <h4>🧪 Test de Integración Multimedia</h4>
          <div class="health-status ${integration.fully_integrated ? 'healthy' : 'warning'}">
            <span class="status-indicator status-${integration.fully_integrated ? 'healthy' : 'warning'}"></span>
            Integración completa: ${integration.fully_integrated ? '✅' : '❌'}
          </div>
          <div class="health-status ${integration.transcribe_audio_from_url ? 'healthy' : 'error'}">
            <span class="status-indicator status-${integration.transcribe_audio_from_url ? 'healthy' : 'error'}"></span>
            Transcripción de audio: ${integration.transcribe_audio_from_url ? '✅' : '❌'}
          </div>
          <div class="health-status ${integration.analyze_image_from_url ? 'healthy' : 'error'}">
            <span class="status-indicator status-${integration.analyze_image_from_url ? 'healthy' : 'error'}"></span>
            Análisis de imagen: ${integration.analyze_image_from_url ? '✅' : '❌'}
          </div>
          <div class="health-status ${integration.process_attachment ? 'healthy' : 'error'}">
            <span class="status-indicator status-${integration.process_attachment ? 'healthy' : 'error'}"></span>
            Procesamiento de archivos: ${integration.process_attachment ? '✅' : '❌'}
          </div>
          <p><strong>OpenAI disponible:</strong> ${response.openai_service_available ? '✅' : '❌'}</p>
          <p><strong>Empresa:</strong> ${response.company_id}</p>
        </div>
      `
      
      safeUpdateDOM('multimediaTestResult', resultHTML)

      addToLog('Multimedia integration test completed successfully', 'success')
      showNotification('Test de integración completado exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Multimedia integration test failed: ${error.message}`, 'error')
      showNotification(`Error en test de integración: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js (SEGURO)
      const errorHTML = `
        <div class="result-container result-error">
          <p>❌ Error en test de integración</p>
          <p>${escapeHTML(error.message)}</p>
        </div>
      `
      safeUpdateDOM('multimediaTestResult', errorHTML)

      throw error

    } finally {
      isTestingIntegration.value = false
    }
  }

  /**
   * Captura pantalla - MIGRADO: captureScreen() de script.js
   * PRESERVAR: Comportamiento exacto de la función original CON MANEJO SEGURO
   */
  const captureScreen = async (options = {}) => {
    if (isCapturingScreen.value) {
      showNotification('Ya se está capturando pantalla', 'warning')
      return
    }

    if (!navigator.mediaDevices?.getDisplayMedia) {
      showNotification('La captura de pantalla no está disponible en este navegador', 'error')
      return
    }

    try {
      isCapturingScreen.value = true
      addToLog('Starting screen capture', 'info')
      showNotification('Iniciando captura de pantalla...', 'info')

      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { 
          mediaSource: 'screen',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      })

      const video = document.createElement('video')
      video.srcObject = stream
      video.play()

      await new Promise(resolve => {
        video.onloadedmetadata = resolve
      })

      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0)

      stream.getTracks().forEach(track => track.stop())

      const blob = await new Promise(resolve => {
        canvas.toBlob(resolve, 'image/png')
      })

      const url = URL.createObjectURL(blob)
      
      screenCaptureResults.value = {
        url,
        blob,
        timestamp: new Date().toISOString(),
        dimensions: {
          width: canvas.width,
          height: canvas.height
        }
      }

      // PRESERVAR: Actualizar DOM como script.js (SEGURO)
      const resultHTML = `
        <div class="result-container result-success">
          <h4>✅ Pantalla Capturada</h4>
          <p>Dimensiones: ${canvas.width}x${canvas.height}px</p>
          <img src="${url}" style="max-width: 300px; border: 1px solid #ccc;" alt="Screen capture">
          <br>
          <button onclick="window.open('${url}')" class="btn btn-primary" style="margin-top: 10px;">
            Ver Pantalla Completa
          </button>
        </div>
      `
      
      safeUpdateDOM('screenCaptureResult', resultHTML)

      addToLog('Screen capture completed successfully', 'success')
      showNotification('Pantalla capturada exitosamente', 'success')

      return screenCaptureResults.value

    } catch (error) {
      addToLog(`Screen capture failed: ${error.message}`, 'error')
      showNotification(`Error capturando pantalla: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js (SEGURO)
      const errorHTML = `
        <div class="result-container result-error">
          <p>❌ Error al capturar pantalla</p>
          <p>${escapeHTML(error.message)}</p>
        </div>
      `
      safeUpdateDOM('screenCaptureResult', errorHTML)

      throw error

    } finally {
      isCapturingScreen.value = false
    }
  }

  /**
   * Alterna grabación de voz - MIGRADO: toggleVoiceRecording() de script.js
   * MODIFICADO: Ya NO procesa automáticamente al finalizar
   */
  const toggleVoiceRecording = async () => {
    if (isRecording.value) {
      await stopVoiceRecording()
    } else {
      await startVoiceRecording()
    }
  }

  /**
   * Inicia grabación de voz - MIGRADO de script.js
   * MODIFICADO: Ya NO procesa automáticamente CON MANEJO SEGURO
   */
  const startVoiceRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showNotification('La grabación de voz no está disponible en este navegador', 'error')
      return
    }

    try {
      addToLog('Starting voice recording', 'info')
      showNotification('Iniciando grabación de voz...', 'info')

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      })
      
      mediaRecorder.value = new MediaRecorder(stream)
      recordedChunks.value = []
      recordingDuration.value = 0

      mediaRecorder.value.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.value.push(event.data)
        }
      }

      mediaRecorder.value.onstop = async () => {
        try {
          const blob = new Blob(recordedChunks.value, { type: 'audio/webm' })
          
          // IMPORTANTE: Los resultados van SOLO a voiceRecordingResults
          voiceRecordingResults.value = {
            blob,
            url: URL.createObjectURL(blob),
            duration: recordingDuration.value,
            timestamp: new Date().toISOString(),
            processed: false // Indica que aún no está procesado
          }

          // PRESERVAR: Actualizar botón como script.js (SEGURO)
          const recordButton = safeGetElement('recordVoiceButton')
          if (recordButton) {
            recordButton.textContent = '🎤 Grabar Voz'
            recordButton.className = 'btn btn-primary'
          }

          addToLog(`Voice recording completed (${recordingDuration.value}s)`, 'success')
          showNotification(`Grabación completada (${recordingDuration.value}s)`, 'success')

          // ELIMINADO: Ya no procesa automáticamente
          // El usuario debe hacer clic en "Procesar con IA" manualmente
        } catch (error) {
          addToLog(`Error in voice recording onstop: ${error.message}`, 'error')
          showNotification(`Error finalizando grabación: ${error.message}`, 'error')
        }
      }

      mediaRecorder.value.start()
      isRecording.value = true

      // PRESERVAR: Actualizar botón como script.js (SEGURO)
      const recordButton = safeGetElement('recordVoiceButton')
      if (recordButton) {
        recordButton.textContent = '⏹️ Detener'
        recordButton.className = 'btn btn-danger'
      }

      // Contador de duración
      recordingInterval.value = setInterval(() => {
        recordingDuration.value++
        const button = safeGetElement('recordVoiceButton')
        if (button) {
          button.textContent = `⏹️ Detener (${recordingDuration.value}s)`
        }
      }, 1000)

      addToLog('Voice recording started', 'success')
      showNotification('Grabación de voz iniciada', 'success')

    } catch (error) {
      addToLog(`Error starting voice recording: ${error.message}`, 'error')
      showNotification(`Error iniciando grabación: ${error.message}`, 'error')
      isRecording.value = false
    }
  }

  /**
   * Detiene grabación de voz - MIGRADO de script.js CON MANEJO SEGURO
   */
  const stopVoiceRecording = async () => {
    if (!isRecording.value || !mediaRecorder.value) return

    try {
      mediaRecorder.value.stop()
      
      // Detener stream de manera segura
      if (mediaRecorder.value.stream) {
        mediaRecorder.value.stream.getTracks().forEach(track => {
          try {
            track.stop()
          } catch (error) {
            console.warn('Error stopping track:', error)
          }
        })
      }
      
      if (recordingInterval.value) {
        clearInterval(recordingInterval.value)
        recordingInterval.value = null
      }

      isRecording.value = false

    } catch (error) {
      addToLog(`Error stopping voice recording: ${error.message}`, 'error')
      showNotification(`Error deteniendo grabación: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const checkMultimediaCapabilities = () => {
    const capabilities = {
      audio: !!navigator.mediaDevices?.getUserMedia,
      screen: !!navigator.mediaDevices?.getDisplayMedia,
      files: !!window.File && !!window.FileReader,
      webrtc: !!window.RTCPeerConnection,
      webgl: !!window.WebGLRenderingContext
    }

    addToLog(`Multimedia capabilities: ${JSON.stringify(capabilities)}`, 'info')
    return capabilities
  }

  const clearResults = () => {
    audioResults.value = null
    imageResults.value = null
    integrationResults.value = null
    screenCaptureResults.value = null
    voiceRecordingResults.value = null
    
    // Limpiar contenedores DOM SI EXISTEN (SEGURO)
    const containers = [
      'audioResult', 'imageResult', 'multimediaTestResult',
      'screenCaptureResult'
    ]
    
    containers.forEach(id => {
      safeUpdateDOM(id, '')
    })

    addToLog('Multimedia results cleared', 'info')
    showNotification('Resultados limpiados', 'info')
  }

  // NUEVO: Limpiar solo resultados de grabación de voz CON MANEJO SEGURO
  const clearVoiceResults = () => {
    try {
      if (voiceRecordingResults.value?.url) {
        URL.revokeObjectURL(voiceRecordingResults.value.url)
      }
      voiceRecordingResults.value = null
      addToLog('Voice recording results cleared', 'info')
    } catch (error) {
      console.warn('Error clearing voice results:', error)
    }
  }

  // HELPER: Escape HTML para evitar XSS - PRESERVAR de script.js
  const escapeHTML = (text) => {
    try {
      const div = document.createElement('div')
      div.textContent = text || ''
      return div.innerHTML
    } catch (error) {
      console.warn('Error escaping HTML:', error)
      return String(text || '').replace(/[&<>"']/g, '')
    }
  }

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    isProcessingAudio,
    isProcessingImage,
    isTestingIntegration,
    isRecording,
    isCapturingScreen,
    isProcessingVoiceRecording,  // NUEVO
    isAnyProcessing,
    processingProgress,
    voiceProcessingProgress,     // NUEVO
    recordingDuration,
    
    // Resultados SEPARADOS
    audioResults,              // Solo AudioProcessor
    imageResults,              // Solo ImageProcessor
    integrationResults,        // Solo tests
    screenCaptureResults,      // Solo ScreenCapture
    voiceRecordingResults,     // Solo VoiceRecorder
    
    // Capacidades
    multimediaCapabilities,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    processAudio,              // Solo para archivos de audio
    processVoiceRecording,     // NUEVO: Solo para grabaciones de voz
    processImage,
    testMultimediaIntegration,
    captureScreen,
    toggleVoiceRecording,

    // Funciones auxiliares
    startVoiceRecording,
    stopVoiceRecording,
    checkMultimediaCapabilities,
    clearResults,
    clearVoiceResults,         // NUEVO
    formatFileSize,
    escapeHTML
  }
}
