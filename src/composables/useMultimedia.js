/**
 * useMultimedia.js - Composable para Procesamiento Multimedia
 * MIGRADO DE: script.js funciones processAudio(), processImage(), testMultimediaIntegration(), captureScreen(), toggleVoiceRecording()
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
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
  // ESTADO LOCAL
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
  
  const mediaRecorder = ref(null)
  const recordedChunks = ref([])
  const processingProgress = ref(0)

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
    webrtc: !!window.RTCPeerConnection
  }))

  const recordingDuration = ref(0)
  const recordingInterval = ref(null)

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Procesa archivo de audio - MIGRADO: processAudio() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const processAudio = async (audioFile = null, options = {}) => {
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
  
    try {
      isProcessingAudio.value = true
      processingProgress.value = 0
      audioResults.value = null
  
      addToLog(`Starting audio processing: ${audioFile.name}`, 'info')
      showNotification('Procesando archivo de audio...', 'info')
  
      if (!audioFile.type.startsWith('audio/')) {
        throw new Error('El archivo debe ser de audio')
      }
  
      const maxSize = 50 * 1024 * 1024 // 50MB
      if (audioFile.size > maxSize) {
        throw new Error('El archivo es demasiado grande. Máximo 50MB')
      }
  
      const formData = new FormData()
      formData.append('audio', audioFile)
  
      // user_id (mantener campo exacto)
      const userIdInput = document.getElementById('audioUserId')
      if (userIdInput && userIdInput.value.trim()) {
        formData.append('user_id', userIdInput.value.trim())
      }
  
      // company_id (AHORA incluido para alinear comportamiento con script.js)
      const companyId = getCompanyId()
      if (companyId) {
        formData.append('company_id', companyId)
      }
  
      if (options.language) formData.append('language', options.language)
      if (options.prompt) formData.append('prompt', options.prompt)
  
      processingProgress.value = 25
  
      // ENDPOINT actualizado y misma estructura (POST FormData) — coincide con script.js
      const response = await apiRequest('/api/multimedia/process-voice', {
        method: 'POST',
        body: formData
      })
  
      processingProgress.value = 100
      audioResults.value = response
  
      // actualizar DOM si existe (comportamiento preservado)
      const resultContainer = document.getElementById('audioResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Audio Procesado Exitosamente</h4>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }
  
      addToLog('Audio processing completed successfully', 'success')
      showNotification('Audio procesado exitosamente', 'success')
  
      return response
  
    } catch (error) {
      addToLog(`Audio processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando audio: ${error.message}`, 'error')
  
      const resultContainer = document.getElementById('audioResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al procesar audio</p>
            <p>${error.message}</p>
          </div>
        `
      }
  
      throw error
  
    } finally {
      isProcessingAudio.value = false
      processingProgress.value = 0
    }
  }

  /**
   * Procesa imagen - MIGRADO: processImage() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const processImage = async (imageFile = null, options = {}) => {
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
  
      if (!imageFile.type.startsWith('image/')) {
        throw new Error('El archivo debe ser una imagen')
      }
  
      const maxSize = 20 * 1024 * 1024 // 20MB
      if (imageFile.size > maxSize) {
        throw new Error('La imagen es demasiado grande. Máximo 20MB')
      }
  
      const formData = new FormData()
      formData.append('image', imageFile)
  
      const userIdInput = document.getElementById('imageUserId')
      if (userIdInput && userIdInput.value.trim()) {
        formData.append('user_id', userIdInput.value.trim())
      }
  
      const companyId = getCompanyId()
      if (companyId) {
        formData.append('company_id', companyId)
      }
  
      if (options.analysis_type) formData.append('analysis_type', options.analysis_type)
      if (options.prompt) formData.append('prompt', options.prompt)
  
      processingProgress.value = 25
  
      // ENDPOINT actualizado y misma estructura (POST FormData)
      const response = await apiRequest('/api/multimedia/process-image', {
        method: 'POST',
        body: formData
      })
  
      processingProgress.value = 100
      imageResults.value = response
  
      const resultContainer = document.getElementById('imageResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Imagen Procesada Exitosamente</h4>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }
  
      addToLog('Image processing completed successfully', 'success')
      showNotification('Imagen procesada exitosamente', 'success')
  
      return response
  
    } catch (error) {
      addToLog(`Image processing failed: ${error.message}`, 'error')
      showNotification(`Error procesando imagen: ${error.message}`, 'error')
  
      const resultContainer = document.getElementById('imageResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al procesar imagen</p>
            <p>${error.message}</p>
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
    if (isTestingIntegration.value) {
      showNotification('Ya se está ejecutando un test de integración', 'warning')
      return
    }
  
    try {
      isTestingIntegration.value = true
      integrationResults.value = null
  
      addToLog('Starting multimedia integration test', 'info')
      showNotification('Ejecutando test de integración multimedia...', 'info')
  
      const companyId = getCompanyId()
      const body = companyId ? { company_id: companyId } : {}
  
      // Usamos el mismo endpoint y contract que script.js
      const response = await apiRequest('/api/admin/multimedia/test', {
        method: 'POST',
        body
      })
  
      integrationResults.value = response
  
      const resultContainer = document.getElementById('multimediaTestResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Test de Integración Multimedia</h4>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }
  
      addToLog('Multimedia integration test completed successfully', 'success')
      showNotification('Test de integración completado exitosamente', 'success')
  
      return response
  
    } catch (error) {
      addToLog(`Multimedia integration test failed: ${error.message}`, 'error')
      showNotification(`Error en test de integración: ${error.message}`, 'error')
  
      const resultContainer = document.getElementById('multimediaTestResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en test de integración</p>
            <p>${error.message}</p>
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
  const captureScreen = async () => {
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
        video: { mediaSource: 'screen' },
        audio: false
      })

      const video = document.createElement('video')
      video.srcObject = stream
      video.play()

      video.addEventListener('loadedmetadata', () => {
        const canvas = document.createElement('canvas')
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        const ctx = canvas.getContext('2d')
        ctx.drawImage(video, 0, 0)

        // Convertir a blob
        canvas.toBlob((blob) => {
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

          // PRESERVAR: Mostrar resultado como script.js
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

          // Detener stream
          stream.getTracks().forEach(track => track.stop())
        }, 'image/png')
      })

    } catch (error) {
      addToLog(`Screen capture failed: ${error.message}`, 'error')
      showNotification(`Error capturando pantalla: ${error.message}`, 'error')

      const resultContainer = document.getElementById('screenCaptureResult')
      if (resultContainer) {
        resultContainer.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al capturar pantalla</p>
            <p>${error.message}</p>
          </div>
        `
      }

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
   * Inicia grabación de voz
   */
  const startVoiceRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showNotification('La grabación de voz no está disponible en este navegador', 'error')
      return
    }

    try {
      addToLog('Starting voice recording', 'info')
      showNotification('Iniciando grabación de voz...', 'info')

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
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

        // PRESERVAR: Actualizar botón como script.js
        const recordButton = document.getElementById('recordVoiceButton')
        if (recordButton) {
          recordButton.textContent = '🎤 Grabar Voz'
          recordButton.className = 'btn btn-primary'
        }

        addToLog(`Voice recording completed (${recordingDuration.value}s)`, 'success')
        showNotification(`Grabación completada (${recordingDuration.value}s)`, 'success')

        // Procesar automáticamente el audio grabado
        try {
          const file = new File([blob], `voice_recording_${Date.now()}.webm`, { type: 'audio/webm' })
          await processAudio(file)
        } catch (error) {
          addToLog(`Error processing recorded audio: ${error.message}`, 'error')
        }
      }

      mediaRecorder.value.start()
      isRecording.value = true

      // PRESERVAR: Actualizar botón como script.js
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
   * Detiene grabación de voz
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
    
    // Limpiar contenedores DOM
    const containers = [
      'audioResult', 'imageResult', 'multimediaTestResult',
      'screenCaptureResult'
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
    formatFileSize
  }
}
