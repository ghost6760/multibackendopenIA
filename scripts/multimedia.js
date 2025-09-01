// scripts/multimedia.js - Multimedia Management Module
'use strict';

/**
 * Multimedia Management Module for Multi-Tenant Admin Panel
 * Handles voice recording, image capture, file processing, and multimedia interactions
 */
class MultimediaManager {
    constructor() {
        this.isInitialized = false;
        this.currentCompanyId = null;
        
        // Media recording state
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.cameraStream = null;
        this.isRecording = false;
        
        // Supported formats
        this.audioFormats = window.APP_CONFIG.UPLOAD.allowed_types.audio;
        this.imageFormats = window.APP_CONFIG.UPLOAD.allowed_types.images;
        this.maxFileSize = window.APP_CONFIG.UPLOAD.max_file_size;
        
        this.init = this.init.bind(this);
        this.onCompanyChange = this.onCompanyChange.bind(this);
    }

    /**
     * Initialize Multimedia Manager
     */
    async init() {
        if (this.isInitialized) return;

        try {
            this.setupEventListeners();
            this.checkMediaSupport();
            this.setupFileInputs();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('🎬 Multimedia Manager initialized');
            }
        } catch (error) {
            console.error('❌ Failed to initialize Multimedia Manager:', error);
            throw error;
        }
    }

    /**
     * Handle company change
     */
    onCompanyChange(companyId) {
        this.currentCompanyId = companyId;
        
        // Stop any ongoing recordings
        this.stopVoiceRecording();
        this.closeCameraModal();
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🎬 Multimedia context changed to company:', companyId);
        }
    }

    /**
     * Check media support
     */
    checkMediaSupport() {
        const support = {
            getUserMedia: !!navigator.mediaDevices?.getUserMedia,
            mediaRecorder: !!window.MediaRecorder,
            webRTC: !!window.RTCPeerConnection
        };

        if (!support.getUserMedia) {
            console.warn('⚠️ getUserMedia not supported');
            this.disableMediaFeatures();
        }

        if (!support.mediaRecorder) {
            console.warn('⚠️ MediaRecorder not supported');
            this.disableRecordingFeatures();
        }

        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🎬 Media support:', support);
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Voice recording buttons
        const startVoiceBtn = document.getElementById('startVoiceBtn');
        const stopVoiceBtn = document.getElementById('stopVoiceBtn');
        
        if (startVoiceBtn) {
            startVoiceBtn.addEventListener('click', () => this.startVoiceRecording());
        }
        
        if (stopVoiceBtn) {
            stopVoiceBtn.addEventListener('click', () => this.stopVoiceRecording());
        }

        // Camera capture button
        const captureImageBtn = document.getElementById('captureImageBtn');
        if (captureImageBtn) {
            captureImageBtn.addEventListener('click', () => this.startCameraCapture());
        }

        // Camera modal buttons
        const takePictureBtn = document.getElementById('takePictureBtn');
        const cancelCameraBtn = document.getElementById('cancelCameraBtn');
        const closeCameraBtn = document.getElementById('closeCameraBtn');
        
        if (takePictureBtn) {
            takePictureBtn.addEventListener('click', () => this.takePicture());
        }
        
        if (cancelCameraBtn) {
            cancelCameraBtn.addEventListener('click', () => this.closeCameraModal());
        }
        
        if (closeCameraBtn) {
            closeCameraBtn.addEventListener('click', () => this.closeCameraModal());
        }

        // File inputs
        const voiceFileInput = document.getElementById('voiceFileInput');
        const imageFileInput = document.getElementById('imageFileInput');
        
        if (voiceFileInput) {
            voiceFileInput.addEventListener('change', (e) => this.handleVoiceFile(e));
        }
        
        if (imageFileInput) {
            imageFileInput.addEventListener('change', (e) => this.handleImageFile(e));
        }
    }

    /**
     * Setup file inputs with validation
     */
    setupFileInputs() {
        const voiceFileInput = document.getElementById('voiceFileInput');
        const imageFileInput = document.getElementById('imageFileInput');
        
        if (voiceFileInput) {
            voiceFileInput.accept = this.audioFormats.join(',');
        }
        
        if (imageFileInput) {
            imageFileInput.accept = this.imageFormats.join(',');
        }
    }

    // ==================== VOICE RECORDING ====================

    /**
     * Start voice recording
     */
    async startVoiceRecording() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        if (this.isRecording) {
            window.UI.showToast('⚠️ Ya hay una grabación en curso', 'warning');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            this.isRecording = true;

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
                
                await this.processVoiceMessage(audioFile);
                
                // Clean up stream
                stream.getTracks().forEach(track => track.stop());
                this.isRecording = false;
            };

            this.mediaRecorder.start();
            this.updateRecordingUI(true);
            
            window.UI.showToast('🎙️ Grabación iniciada', 'info');
            
        } catch (error) {
            console.error('❌ Error accessing microphone:', error);
            window.UI.showToast('❌ Error accediendo al micrófono: ' + error.message, 'error');
            this.isRecording = false;
        }
    }

    /**
     * Stop voice recording
     */
    stopVoiceRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            this.updateRecordingUI(false);
            window.UI.showToast('⏹️ Grabación detenida', 'info');
        }
    }

    /**
     * Update recording UI state
     */
    updateRecordingUI(isRecording) {
        const startBtn = document.getElementById('startVoiceBtn');
        const stopBtn = document.getElementById('stopVoiceBtn');
        const recordingStatus = document.getElementById('recordingStatus');

        if (startBtn) {
            startBtn.style.display = isRecording ? 'none' : 'inline-flex';
        }
        
        if (stopBtn) {
            stopBtn.style.display = isRecording ? 'inline-flex' : 'none';
        }
        
        if (recordingStatus) {
            recordingStatus.style.display = isRecording ? 'block' : 'none';
        }
    }

    /**
     * Handle voice file upload
     */
    async handleVoiceFile(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        if (!this.validateAudioFile(file)) return;
        
        await this.processVoiceMessage(file);
        e.target.value = '';
    }

    /**
     * Process voice message
     */
    async processVoiceMessage(audioFile) {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const userId = document.getElementById('testUserId')?.value.trim() || 'test_user';

        try {
            window.UI.showLoading('Procesando audio...');

            const response = await window.API.processVoiceMessage(audioFile, userId);

            if (response.status === 'success') {
                // Display transcript and response in chat
                if (window.ChatTester) {
                    window.ChatTester.addUserMessage(`🎤 ${response.transcript}`);
                    window.ChatTester.addAssistantMessage(response.response);
                    
                    if (response.agent_used) {
                        window.ChatTester.addSystemMessage(`🤖 Agente: ${response.agent_used} | Empresa: ${window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name || this.currentCompanyId}`);
                    }
                }

                window.UI.showToast('✅ Audio procesado correctamente', 'success');
            } else {
                throw new Error(response.message || 'Error procesando audio');
            }

        } catch (error) {
            console.error('❌ Error processing voice:', error);
            window.UI.showToast('❌ Error procesando audio: ' + error.message, 'error');
            
            if (window.ChatTester) {
                window.ChatTester.addErrorMessage('Error procesando audio: ' + error.message);
            }
        } finally {
            window.UI.hideLoading();
        }
    }

    // ==================== CAMERA CAPTURE ====================

    /**
     * Start camera capture
     */
    async startCameraCapture() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            this.cameraStream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            });
            
            const video = document.getElementById('cameraVideo');
            if (video) {
                video.srcObject = this.cameraStream;
            }
            
            // Update company name in modal
            const cameraCompany = document.getElementById('cameraCompany');
            if (cameraCompany) {
                cameraCompany.textContent = window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name || this.currentCompanyId;
            }
            
            const modal = document.getElementById('cameraModal');
            if (modal) {
                modal.style.display = 'flex';
            }
            
            window.UI.showToast('📸 Cámara activada', 'info');
            
        } catch (error) {
            console.error('❌ Error accessing camera:', error);
            window.UI.showToast('❌ Error accediendo a la cámara: ' + error.message, 'error');
        }
    }

    /**
     * Take picture from camera
     */
    async takePicture() {
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('cameraCanvas');
        
        if (!video || !canvas) {
            window.UI.showToast('❌ Error con los elementos de cámara', 'error');
            return;
        }

        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        context.drawImage(video, 0, 0);

        canvas.toBlob(async (blob) => {
            const imageFile = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            await this.processImageMessage(imageFile);
            this.closeCameraModal();
        }, 'image/jpeg', 0.8);
    }

    /**
     * Close camera modal
     */
    closeCameraModal() {
        const modal = document.getElementById('cameraModal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
    }

    /**
     * Handle image file upload
     */
    async handleImageFile(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        if (!this.validateImageFile(file)) return;
        
        await this.processImageMessage(file);
        e.target.value = '';
    }

    /**
     * Process image message
     */
    async processImageMessage(imageFile, question = '¿Qué hay en esta imagen?') {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Analizando imagen...');

            const response = await window.API.processImageMessage(imageFile, question);

            if (response.status === 'success') {
                // Display image analysis in chat
                if (window.ChatTester) {
                    window.ChatTester.addUserMessage(`📸 Imagen subida: ${imageFile.name}`);
                    window.ChatTester.addAssistantMessage(response.analysis || response.response);
                    
                    if (response.agent_used) {
                        window.ChatTester.addSystemMessage(`🤖 Agente: ${response.agent_used} | Análisis de imagen completado`);
                    }
                }

                window.UI.showToast('✅ Imagen analizada correctamente', 'success');
            } else {
                throw new Error(response.message || 'Error analizando imagen');
            }

        } catch (error) {
            console.error('❌ Error processing image:', error);
            window.UI.showToast('❌ Error analizando imagen: ' + error.message, 'error');
            
            if (window.ChatTester) {
                window.ChatTester.addErrorMessage('Error analizando imagen: ' + error.message);
            }
        } finally {
            window.UI.hideLoading();
        }
    }

    // ==================== FILE VALIDATION ====================

    /**
     * Validate audio file
     */
    validateAudioFile(file) {
        if (!file) return false;

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.audioFormats.includes(fileExtension)) {
            window.UI.showToast(`❌ Formato de audio no soportado: ${fileExtension}`, 'error');
            return false;
        }

        // Check file size
        if (file.size > this.maxFileSize) {
            const maxSizeMB = Math.round(this.maxFileSize / 1024 / 1024);
            window.UI.showToast(`❌ Archivo muy grande (máximo ${maxSizeMB}MB)`, 'error');
            return false;
        }

        return true;
    }

    /**
     * Validate image file
     */
    validateImageFile(file) {
        if (!file) return false;

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.imageFormats.includes(fileExtension)) {
            window.UI.showToast(`❌ Formato de imagen no soportado: ${fileExtension}`, 'error');
            return false;
        }

        // Check file size
        if (file.size > this.maxFileSize) {
            const maxSizeMB = Math.round(this.maxFileSize / 1024 / 1024);
            window.UI.showToast(`❌ Archivo muy grande (máximo ${maxSizeMB}MB)`, 'error');
            return false;
        }

        return true;
    }

    // ==================== FEATURE CONTROL ====================

    /**
     * Disable media features if not supported
     */
    disableMediaFeatures() {
        const mediaButtons = [
            'startVoiceBtn',
            'captureImageBtn'
        ];

        mediaButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.disabled = true;
                btn.title = 'Función no soportada en este navegador';
            }
        });

        window.UI.showToast('⚠️ Funciones multimedia limitadas en este navegador', 'warning');
    }

    /**
     * Disable recording features if not supported
     */
    disableRecordingFeatures() {
        const recordingButtons = [
            'startVoiceBtn',
            'stopVoiceBtn'
        ];

        recordingButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.disabled = true;
                btn.title = 'Grabación no soportada en este navegador';
            }
        });
    }

    // ==================== UTILITY FUNCTIONS ====================

    /**
     * Get supported audio formats
     */
    getSupportedAudioFormats() {
        const testRecorder = new MediaRecorder(new MediaStream());
        const supportedFormats = [];

        const formats = ['audio/webm', 'audio/mp4', 'audio/wav'];
        formats.forEach(format => {
            if (MediaRecorder.isTypeSupported(format)) {
                supportedFormats.push(format);
            }
        });

        return supportedFormats;
    }

    /**
     * Get media device info
     */
    async getMediaDevices() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            
            return {
                audio_inputs: devices.filter(d => d.kind === 'audioinput').length,
                video_inputs: devices.filter(d => d.kind === 'videoinput').length,
                audio_outputs: devices.filter(d => d.kind === 'audiooutput').length
            };
        } catch (error) {
            console.error('❌ Error getting media devices:', error);
            return { audio_inputs: 0, video_inputs: 0, audio_outputs: 0 };
        }
    }

    /**
     * Test multimedia functionality
     */
    async testMultimediaSupport() {
        const support = {
            getUserMedia: !!navigator.mediaDevices?.getUserMedia,
            mediaRecorder: !!window.MediaRecorder,
            webRTC: !!window.RTCPeerConnection,
            audio_formats: this.getSupportedAudioFormats(),
            devices: await this.getMediaDevices()
        };

        const content = `
            <div class="multimedia-test-results">
                <h4>🎬 Test de Soporte Multimedia</h4>
                
                <div class="support-grid">
                    <div class="support-item">
                        <div class="support-label">getUserMedia</div>
                        <div class="support-value ${support.getUserMedia ? 'supported' : 'not-supported'}">
                            ${support.getUserMedia ? '✅ Soportado' : '❌ No soportado'}
                        </div>
                    </div>
                    <div class="support-item">
                        <div class="support-label">MediaRecorder</div>
                        <div class="support-value ${support.mediaRecorder ? 'supported' : 'not-supported'}">
                            ${support.mediaRecorder ? '✅ Soportado' : '❌ No soportado'}
                        </div>
                    </div>
                    <div class="support-item">
                        <div class="support-label">WebRTC</div>
                        <div class="support-value ${support.webRTC ? 'supported' : 'not-supported'}">
                            ${support.webRTC ? '✅ Soportado' : '❌ No soportado'}
                        </div>
                    </div>
                </div>

                <div class="devices-info">
                    <h5>Dispositivos Detectados:</h5>
                    <ul>
                        <li>🎤 Entradas de audio: ${support.devices.audio_inputs}</li>
                        <li>📹 Entradas de video: ${support.devices.video_inputs}</li>
                        <li>🔊 Salidas de audio: ${support.devices.audio_outputs}</li>
                    </ul>
                </div>

                <div class="formats-info">
                    <h5>Formatos de Audio Soportados:</h5>
                    <p>${support.audio_formats.join(', ') || 'Ninguno'}</p>
                </div>
            </div>
        `;

        window.UI.showModal('🎬 Test Multimedia', content, {
            maxWidth: '600px'
        });
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopVoiceRecording();
        this.closeCameraModal();
        this.isInitialized = false;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🧹 Multimedia Manager cleaned up');
        }
    }
}

// Create global instance
window.MultimediaManager = new MultimediaManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultimediaManager;
}
