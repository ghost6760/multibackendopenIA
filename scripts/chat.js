// scripts/chat.js - Chat Testing Module
'use strict';

/**
 * Chat Testing Module for Multi-Tenant Admin Panel
 * Handles chat message testing, conversation management, and chat interface
 */
class ChatTester {
    constructor() {
        this.messages = [];
        this.conversationId = null;
        this.currentCompanyId = null;
        this.isInitialized = false;
        
        this.init = this.init.bind(this);
        this.onCompanyChange = this.onCompanyChange.bind(this);
    }

    /**
     * Initialize Chat Tester
     */
    async init() {
        if (this.isInitialized) return;

        try {
            this.setupEventListeners();
            this.initializeChatInterface();
            this.setupAutoScroll();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('💬 Chat Tester initialized');
            }
        } catch (error) {
            console.error('❌ Failed to initialize Chat Tester:', error);
            throw error;
        }
    }

    /**
     * Handle company change
     */
    onCompanyChange(companyId) {
        this.currentCompanyId = companyId;
        
        // Clear previous conversation
        this.clearChat();
        
        if (companyId) {
            this.addSystemMessage(`💼 Chat conectado a: ${window.CompanyManager?.getCompany(companyId)?.company_name || companyId}`);
        } else {
            this.addSystemMessage('⚠️ Selecciona una empresa para comenzar a chatear');
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Chat form submission
        const chatForm = document.getElementById('chatTestForm');
        if (chatForm) {
            chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // Enter key to send message
        const messageInput = document.getElementById('testMessage');
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            messageInput.addEventListener('input', () => {
                this.autoResizeTextarea(messageInput);
            });
        }

        // Clear chat button
        const clearBtn = document.getElementById('clearChatBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearChat();
            });
        }

        // Export chat button
        const exportBtn = document.getElementById('exportChatBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportChat();
            });
        }
    }

    /**
     * Initialize chat interface
     */
    initializeChatInterface() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div class="chat-welcome">
                    <div class="welcome-icon">🤖</div>
                    <h4>Bienvenido al Chat de Pruebas</h4>
                    <p>Selecciona una empresa y comienza a probar el chatbot</p>
                </div>
            `;
        }

        // Set default user ID if not set
        const userIdInput = document.getElementById('testUserId');
        if (userIdInput && !userIdInput.value) {
            userIdInput.value = 'test_user_' + Math.random().toString(36).substr(2, 9);
        }
    }

    /**
     * Setup auto-scroll for chat messages
     */
    setupAutoScroll() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            // Create observer to auto-scroll when new messages are added
            const observer = new MutationObserver(() => {
                this.scrollToBottom();
            });

            observer.observe(chatMessages, {
                childList: true,
                subtree: true
            });
        }
    }

    /**
     * Send chat message
     */
    async sendMessage() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const messageInput = document.getElementById('testMessage');
        const userIdInput = document.getElementById('testUserId');
        
        const message = messageInput.value.trim();
        const userId = userIdInput.value.trim() || 'test_user';

        if (!message) {
            window.UI.showToast('❌ Escribe un mensaje', 'error');
            messageInput.focus();
            return;
        }

        try {
            // Display user message immediately
            this.addUserMessage(message);
            
            // Clear input
            messageInput.value = '';
            this.autoResizeTextarea(messageInput);
            
            // Show typing indicator
            this.showTypingIndicator();

            // Send message to API
            const response = await window.API.sendChatMessage(message, userId, this.conversationId);
            
            // Remove typing indicator
            this.hideTypingIndicator();

            if (response.status === 'success') {
                // Display assistant response
                this.addAssistantMessage(response.response);
                
                // Update conversation ID if provided
                if (response.conversation_id) {
                    this.conversationId = response.conversation_id;
                }

                // Show agent info
                if (response.agent_used) {
                    this.addSystemMessage(`🤖 Agente utilizado: ${response.agent_used}`);
                }

                // Show additional info if available
                if (response.sources && response.sources.length > 0) {
                    this.addSystemMessage(`📚 Fuentes consultadas: ${response.sources.length} documentos`);
                }

            } else {
                throw new Error(response.message || 'Error en la respuesta del chat');
            }

        } catch (error) {
            this.hideTypingIndicator();
            console.error('❌ Chat error:', error);
            this.addErrorMessage('Error procesando mensaje: ' + error.message);
            window.UI.showToast('❌ Error en el chat: ' + error.message, 'error');
        }
    }

    /**
     * Add user message to chat
     */
    addUserMessage(message) {
        this.messages.push({
            type: 'user',
            content: message,
            timestamp: new Date()
        });

        this.displayMessage('user', message);
    }

    /**
     * Add assistant message to chat
     */
    addAssistantMessage(message) {
        this.messages.push({
            type: 'assistant',
            content: message,
            timestamp: new Date()
        });

        this.displayMessage('assistant', message);
    }

    /**
     * Add system message to chat
     */
    addSystemMessage(message) {
        this.messages.push({
            type: 'system',
            content: message,
            timestamp: new Date()
        });

        this.displayMessage('system', message);
    }

    /**
     * Add error message to chat
     */
    addErrorMessage(message) {
        this.messages.push({
            type: 'error',
            content: message,
            timestamp: new Date()
        });

        this.displayMessage('error', message);
    }

    /**
     * Display message in chat interface
     */
    displayMessage(type, content) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        // Remove welcome message if exists
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) {
            welcome.remove();
        }

        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${type}`;
        
        // Add timestamp
        const timestamp = new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });

        // Format content based on type
        let formattedContent = content;
        if (type === 'assistant') {
            formattedContent = this.formatAssistantMessage(content);
        }

        messageEl.innerHTML = `
            <div class="message-content">${formattedContent}</div>
            <div class="message-timestamp">${timestamp}</div>
        `;

        chatMessages.appendChild(messageEl);
        
        // Animate in
        setTimeout(() => {
            messageEl.classList.add('message-visible');
        }, 10);
    }

    /**
     * Format assistant message with markdown-like formatting
     */
    formatAssistantMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        const typingEl = document.createElement('div');
        typingEl.className = 'chat-message assistant typing-indicator';
        typingEl.id = 'typingIndicator';
        typingEl.innerHTML = `
            <div class="message-content">
                <div class="typing-animation">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                Escribiendo...
            </div>
        `;

        chatMessages.appendChild(typingEl);
        this.scrollToBottom();
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        const typingEl = document.getElementById('typingIndicator');
        if (typingEl) {
            typingEl.remove();
        }
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    /**
     * Scroll to bottom of chat
     */
    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);
        }
    }

    /**
     * Clear chat messages
     */
    clearChat() {
        this.messages = [];
        this.conversationId = null;
        
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
            this.initializeChatInterface();
        }

        window.UI.showToast('🧹 Chat limpiado', 'info');
    }

    /**
     * Export chat conversation
     */
    exportChat() {
        if (this.messages.length === 0) {
            window.UI.showToast('⚠️ No hay mensajes para exportar', 'warning');
            return;
        }

        const exportData = {
            company_id: this.currentCompanyId,
            company_name: window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name,
            conversation_id: this.conversationId,
            exported_at: new Date().toISOString(),
            messages: this.messages.map(msg => ({
                type: msg.type,
                content: msg.content,
                timestamp: msg.timestamp.toISOString()
            }))
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `chat_conversation_${this.currentCompanyId}_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        window.UI.showToast('✅ Conversación exportada', 'success');
    }

    /**
     * Get conversation statistics
     */
    getConversationStats() {
        return {
            total_messages: this.messages.length,
            user_messages: this.messages.filter(m => m.type === 'user').length,
            assistant_messages: this.messages.filter(m => m.type === 'assistant').length,
            system_messages: this.messages.filter(m => m.type === 'system').length,
            error_messages: this.messages.filter(m => m.type === 'error').length,
            conversation_duration: this.messages.length > 0 ? 
                new Date() - this.messages[0].timestamp : 0,
            conversation_id: this.conversationId,
            company_id: this.currentCompanyId
        };
    }

    /**
     * Show conversation statistics
     */
    showConversationStats() {
        const stats = this.getConversationStats();
        
        if (stats.total_messages === 0) {
            window.UI.showToast('⚠️ No hay mensajes en la conversación', 'warning');
            return;
        }

        const duration = Math.round(stats.conversation_duration / 1000 / 60); // minutes
        
        const content = `
            <div class="conversation-stats">
                <h4>📊 Estadísticas de la Conversación</h4>
                
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Total de Mensajes</div>
                        <div class="stat-value">${stats.total_messages}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Mensajes del Usuario</div>
                        <div class="stat-value">${stats.user_messages}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Respuestas del Asistente</div>
                        <div class="stat-value">${stats.assistant_messages}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Mensajes del Sistema</div>
                        <div class="stat-value">${stats.system_messages}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Errores</div>
                        <div class="stat-value">${stats.error_messages}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Duración</div>
                        <div class="stat-value">${duration} min</div>
                    </div>
                </div>

                ${stats.conversation_id ? `<p><strong>ID de Conversación:</strong> ${stats.conversation_id}</p>` : ''}
                <p><strong>Empresa:</strong> ${window.CompanyManager?.getCompany(stats.company_id)?.company_name || stats.company_id}</p>
            </div>
        `;

        window.UI.showModal('📊 Estadísticas de Conversación', content, {
            maxWidth: '600px'
        });
    }

    /**
     * Test predefined scenarios
     */
    async testScenario(scenario) {
        const scenarios = {
            greeting: '¡Hola! ¿Cómo estás?',
            help: '¿Qué servicios ofrecen?',
            complex: 'Necesito información detallada sobre sus productos y precios',
            appointment: '¿Cómo puedo agendar una cita?',
            technical: 'Tengo un problema técnico, ¿pueden ayudarme?'
        };

        const message = scenarios[scenario];
        if (message) {
            document.getElementById('testMessage').value = message;
            await this.sendMessage();
        }
    }

    /**
     * Get message count
     */
    getMessageCount() {
        return this.messages.length;
    }

    /**
     * Has active conversation
     */
    hasActiveConversation() {
        return this.messages.length > 0 && this.conversationId !== null;
    }

    /**
     * Load conversation from history (if available)
     */
    async loadConversation(conversationId) {
        try {
            window.UI.showLoading('Cargando conversación...');

            // This would call an API endpoint to load conversation history
            // For now, we'll just show a placeholder
            window.UI.showToast('🚧 Función de carga de conversaciones en desarrollo', 'info');

        } catch (error) {
            console.error('❌ Error loading conversation:', error);
            window.UI.showToast('❌ Error cargando conversación: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Save current conversation
     */
    async saveConversation() {
        if (this.messages.length === 0) {
            window.UI.showToast('⚠️ No hay mensajes para guardar', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Guardando conversación...');

            // This would call an API endpoint to save conversation
            // For now, we'll just export to local file
            this.exportChat();

        } catch (error) {
            console.error('❌ Error saving conversation:', error);
            window.UI.showToast('❌ Error guardando conversación: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Reset conversation
     */
    resetConversation() {
        if (this.messages.length === 0) return;

        const confirmed = window.confirm('¿Estás seguro de que quieres reiniciar la conversación? Se perderán todos los mensajes.');
        
        if (confirmed) {
            this.clearChat();
            this.conversationId = null;
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.clearChat();
        this.isInitialized = false;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🧹 Chat Tester cleaned up');
        }
    }
}

// Create global instance
window.ChatTester = new ChatTester();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatTester;
}
