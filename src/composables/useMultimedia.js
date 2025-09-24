/**
 * useMultimedia.js - Composable para Procesamiento Multimedia
 * MIGRADO Y ACTUALIZADO desde script.js 
 * PRESERVA: Comportamiento exacto de las funciones originales
 * ENDPOINTS: Idénticos a script.js
 * VALIDACIONES: Exactas como script.js
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
  // ESTADO LOCAL REACTIVO
  // ============================================================================

  const isProcessingAudio = ref(false)
  const isProcessingImage = ref(false)
  const isTestingIntegration = ref(false)
  const isRecording = ref(false)
  const isCapturingScreen = ref(false)
  
  const audioResults = ref(null)
  const imageResults = ref(null)
  const integrationResults = ref(null)
  const screenCaptureResults = ref(null)
  const voiceRecordingResults = ref(null)
  
  // Media recording state
  const mediaRecorder = ref(null)
  const recordedChunks = ref([])
  const processingProgress = ref(0)
  const recordingDuration = ref(0)
  const recordingInterval = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const isAnyProcessing = computed(() => 
    isProcessingAudio.value || 
    isProcessingImage.value || 
    isTestingIntegration.value ||
    isCapturingScreen.value
  )

  const multimediaCapabilities = computed(() => ({
    audio: !!navigator.mediaDevices?.getUserMedia,
    screen: !!navigator.mediaDevices?.getDisplayMedia,
    files: !!window.File && !!window.FileReader,
    webrtc: !!window.RTCPeerConnection,
    webgl: !!window.WebGLRenderingContext
  }))

  // ============================================================================
  // FUNCIONES PRINCIPALES - EXACTAS A SCRIPT.JS (CON MEJORA PARA SOURCE)
  // ============================================================================

  /**
   * Procesa archivo de audio - MIGRADO: processAudio() de script.js
   * PRESERVAR: Comportamiento y endpoints exactos
   *
   * options: { language, prompt, source: 'recorder'|'uploader'|undefined, skipDomUpdate: boolean }
   */
  const processAudio = async (audioFile = null, options = {}) => {
    // Validar empresa seleccionada - PRESERVAR lógica script.js
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    // Si no se pasa archivo, intentar obtenerlo del DOM como en script.js
    if (!audioFile) {
      const fileInput = document.getElementById('audioFile')
      if (!fileInput || !fileInput.files[0]) {
        showNotification('Por favor selecciona un archivo de audio', 'warning')
        return null
      }
      audioFile = fileInput.files[0]
    }

    if (isProcessingAudio.value) {
      showNotification('Ya se está procesando un archivo de audio', 'warning')
      return null
    }

    // decide target container based on options.source
    const source = options.source || null
    const targetContainerId = source === 'recorder' ? 'voiceResult' : 'audioResult'
    const skipDomUpdate = !!options.skipDomUpdate

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
      
      // PRESERVAR: Obtener userId del DOM como script.js (si existe)
      const userIdInput = document.getElementById('audioUserId')
      if (userIdInput && userIdInput.value.trim()) {
        formData.append('user_id', userIdInput.value.trim())
      }

      // Agregar opciones adicionales
      if (options.language) formData.append('language', options.language)
      if (options.prompt) formData.append('prompt', options.prompt)

      processingProgress.value = 25

      // PRESERVAR: Endpoint exacto como script.js CORREGIDO
      // script.js usa '/api/multimedia/process-voice' en la versión corregida
      const response = await apiRequest('/api/multimedia/process-voice', {
        method: 'POST',
        body: formData
      })

      processingProgress.value = 100
      audioResults.value = response

      // PRESERVAR: Actualizar DOM como script.js SI EXISTE,
      // pero ahora targeteado por source (voiceResult vs audioResult), y con opción de skip
      if (!skipDomUpdate) {
        const resultContainer = document.getElementById(targetContainerId)
        if (resultContainer) {
          // MEJORADO: Extraer campos de manera robusta como script.js corregido
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
          
          resultContainer.innerHTML = resultHTML
        }
      }

      addToLog('Audio processing completed successfully', 'success')
      showNotification('Audio procesado exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Audio processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando audio: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js SI EXISTE
      if (!skipDomUpdate) {
        const resultContainer = document.getElementById(targetContainerId)
        if (resultContainer) {
          resultContainer.innerHTML = `
            <div class="result-container result-error">
              <p>❌ Error al procesar audio</p>
              <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
              <p><strong>Empresa:</strong> ${appStore.currentCompanyId}</p>
            </div>
          `
        }
      }

      throw error

    } finally {
      isProcessingAudio.value = false
      processingProgress.value = 0
    }
  }

  /**
   * Procesa imagen - MIGRADO: processImage() de script.js  
   * PRESERVAR: Comportamiento y endpoints exactos
   */
  const processImage = async (imageFile = null, options = {}) => {
    // Validar empresa seleccionada
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    // Si no se pasa archivo, intentar obtenerlo del DOM como en script.js
    if (!imageFile) {
      const fileInput = document.getElementById('imageFile')
      if (!fileInput || !fileInput.files[0]) {
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
      
      // PRESERVAR: Obtener userId del DOM como script.js
      const userIdInput = document.getElementById('imageUserId')
      if (userIdInput && userIdInput.value.trim()) {
        formData.append('user_id', userIdInput.value.trim())
      }

      // Agregar opciones adicionales
      if (options.analysis_type) formData.append('analysis_type', options.analysis_type)
      if (options.prompt) formData.append('prompt', options.prompt)

      processingProgress.value = 25

      // PRESERVAR: Endpoint exacto como script.js CORREGIDO
      // script.js usa '/api/multimedia/process-image' en la versión corregida
      const response = await apiRequest('/api/multimedia/process-image', {
        method: 'POST',
        body: formData
      })

      processingProgress.value = 100
      imageResults.value = response

      // PRESERVAR: Actualizar DOM como script.js SI EXISTE
      const resultContainer = document.getElementById('imageResult')
      if (resultContainer) {
        // MEJORADO: Extraer campos de manera robusta como script.js corregido
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
        
        resultContainer.innerHTML = resultHTML
      }

      addToLog('Image processing completed successfully', 'success')
      showNotification('Imagen procesada exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Image processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando imagen: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js SI EXISTE
      const resultContainer = document.getElementById('imageResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al procesar imagen</p>
            <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
            <p><strong>Empresa:</strong> ${appStore.currentCompanyId}</p>
          </div>
        `
      }

      throw error

    } finally {
      isProcessingImage.value = false
      processingProgress.value = 0
    }
  }

  /**
   * Prueba la integración multimedia - MIGRADO: testMultimediaIntegration() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const testMultimediaIntegration = async () => {
    // Validar empresa seleccionada
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

      // PRESERVAR: Endpoint exacto como script.js  
      // script.js usa '/api/admin/multimedia/test' en testMultimediaIntegration()
      const response = await apiRequest('/api/admin/multimedia/test', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId
        }
      })

      integrationResults.value = response

      // PRESERVAR: Mostrar resultados en DOM como script.js SI EXISTE
      const resultContainer = document.getElementById('multimediaTestResult')
      if (resultContainer) {
        const integration = response.multimedia_integration || {}
        
        resultContainer.innerHTML = `
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
      }

      addToLog('Multimedia integration test completed successfully', 'success')
      showNotification('Test de integración completado exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Multimedia integration test failed: ${error.message}`, 'error')
      showNotification(`Error en test de integración: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js SI EXISTE
      const resultContainer = document.getElementById('multimediaTestResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en test de integración</p>
            <p>${escapeHTML(error.message)}</p>
          </div>
        `
      }

      throw error

    } finally {
      isTestingIntegration.value = false
    }
  }

  /**
   * Captura pantalla - MIGRADO: captureScreen() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
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

      // PRESERVAR: Configuración de captura como script.js
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

      // Detener stream
      stream.getTracks().forEach(track => track.stop())

      // Convertir a blob
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

      // PRESERVAR: Mostrar resultado como script.js SI EXISTE
      const resultContainer = document.getElementById('screenCaptureResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
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
      }

      addToLog('Screen capture completed successfully', 'success')
      showNotification('Pantalla capturada exitosamente', 'success')

      return screenCaptureResults.value

    } catch (error) {
      addToLog(`Screen capture failed: ${error.message}`, 'error')
      showNotification(`Error capturando pantalla: ${error.message}`, 'error')

      const resultContainer = document.getElementById('screenCaptureResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al capturar pantalla</p>
            <p>${escapeHTML(error.message)}</p>
          </div>
        `
      }

      throw error

    } finally {
      isCapturingScreen.value = false
    }
  }

  /**
   * Alterna grabación de voz - MIGRADO: toggleVoiceRecording() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
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
        const blob = new Blob(recordedChunks.value, { type: 'audio/webm' })
        
        voiceRecordingResults.value = {
          blob,
          url: URL.createObjectURL(blob),
          duration: recordingDuration.value,
          timestamp: new Date().toISOString()
        }

        // PRESERVAR: Actualizar botón como script.js SI EXISTE
        const recordButton = document.getElementById('recordVoiceButton')
        if (recordButton) {
          recordButton.textContent = '🎤 Grabar Voz'
          recordButton.className = 'btn btn-primary'
        }

        addToLog(`Voice recording completed (${recordingDuration.value}s)`, 'success')
        showNotification(`Grabación completada (${recordingDuration.value}s)`, 'success')

        // PRESERVAR: Procesamiento automático como script.js
        try {
          const file = new File([blob], `voice_recording_${Date.now()}.webm`, { type: 'audio/webm' })

          // Important: indicate this processing originates from the recorder,
          // so processAudio will target the voiceResult container instead of audioResult
          await processAudio(file, { source: 'recorder' })
        } catch (error) {
          addToLog(`Error processing recorded audio: ${error.message}`, 'error')
        }
      }

      mediaRecorder.value.start()
      isRecording.value = true

      // PRESERVAR: Actualizar botón como script.js SI EXISTE
      const recordButton = document.getElementById('recordVoiceButton')
      if (recordButton) {
        recordButton.textContent = '⏹️ Detener'
        recordButton.className = 'btn btn-danger'
      }

      // Contador de duración
      recordingInterval.value = setInterval(() => {
        recordingDuration.value++
        if (recordButton) {
          recordButton.textContent = `⏹️ Detener (${recordingDuration.value}s)`
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
   * Detiene grabación de voz - MIGRADO de script.js
   */
  const stopVoiceRecording = async () => {
    if (!isRecording.value || !mediaRecorder.value) return

    try {
      mediaRecorder.value.stop()
      mediaRecorder.value.stream.getTracks().forEach(track => track.stop())
      
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
    
    // Limpiar contenedores DOM SI EXISTEN
    const containers = [
      'audioResult', 'imageResult', 'multimediaTestResult',
      'screenCaptureResult', 'voiceResult'
    ]
    
    containers.forEach(id => {
      const container = document.getElementById(id)
      if (container) {
        container.innerHTML = ''
      }
    })

    addToLog('Multimedia results cleared', 'info')
    showNotification('Resultados limpiados', 'info')
  }

  // HELPER: Escape HTML para evitar XSS - PRESERVAR de script.js
  const escapeHTML = (text) => {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
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
    isAnyProcessing,
    processingProgress,
    recordingDuration,
    
    // Resultados
    audioResults,
    imageResults,
    integrationResults,
    screenCaptureResults,
    voiceRecordingResults,
    
    // Capacidades
    multimediaCapabilities,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    processAudio,
    processImage,
    testMultimediaIntegration,
    captureScreen,
    toggleVoiceRecording,

    // Funciones auxiliares
    startVoiceRecording,
    stopVoiceRecording,
    checkMultimediaCapabilities,
    clearResults,
    formatFileSize,
    escapeHTML
  }
}
