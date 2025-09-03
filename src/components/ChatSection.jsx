// src/components/ChatSection.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Settings, Trash2, MessageSquare, AlertCircle, CheckCircle, Bot, User } from 'lucide-react';

const ChatSection = ({ currentCompanyId, companies, addToast }) => {
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [testUserId, setTestUserId] = useState('test_user');
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  useEffect(() => {
    // Generar nuevo conversation_id cuando cambie la empresa
    setConversationId(`${testUserId}_${currentCompanyId}_${Date.now()}`);
    setChatMessages([]);
  }, [currentCompanyId, testUserId]);

  const clearChat = () => {
    setChatMessages([]);
    setConversationId(`${testUserId}_${currentCompanyId}_${Date.now()}`);
    addToast('Chat limpiado', 'success');
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    // Agregar mensaje del usuario inmediatamente
    const userMessageObj = {
      id: Date.now(),
      type: 'user',
      content: userMessage,
      timestamp: new Date().toLocaleTimeString(),
      user_id: testUserId
    };

    setChatMessages(prev => [...prev, userMessageObj]);

    try {
      console.log('Sending message:', {
        message: userMessage,
        company_id: currentCompanyId,
        user_id: testUserId,
        conversation_id: conversationId
      });

      const response = await fetch('/api/conversations/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Company-ID': currentCompanyId
        },
        body: JSON.stringify({
          message: userMessage,
          company_id: currentCompanyId,
          user_id: testUserId,
          conversation_id: conversationId
        })
      });

      console.log('Response status:', response.status);
      const responseData = await response.json();
      console.log('Response data:', responseData);

      if (!response.ok) {
        throw new Error(responseData.message || `HTTP ${response.status}`);
      }

      // Agregar respuesta del bot
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: responseData.data?.response || responseData.response || 'Sin respuesta',
        timestamp: new Date().toLocaleTimeString(),
        agent_type: responseData.data?.agent_type || responseData.agent_type || 'unknown',
        metadata: responseData.data?.metadata || responseData.metadata || {}
      };

      setChatMessages(prev => [...prev, botMessage]);
      
      addToast(`Mensaje procesado por ${botMessage.agent_type}`, 'success');

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Agregar mensaje de error
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toLocaleTimeString()
      };

      setChatMessages(prev => [...prev, errorMessage]);
      addToast(`Error enviando mensaje: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getMessageIcon = (type, agentType) => {
    switch (type) {
      case 'user':
        return <User className="h-4 w-4 text-blue-600" />;
      case 'bot':
        return <Bot className="h-4 w-4 text-green-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <MessageSquare className="h-4 w-4 text-gray-600" />;
    }
  };

  const getMessageStyles = (type) => {
    switch (type) {
      case 'user':
        return 'bg-blue-50 border-blue-200 ml-8';
      case 'bot':
        return 'bg-green-50 border-green-200 mr-8';
      case 'error':
        return 'bg-red-50 border-red-200 mr-8';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  if (!currentCompanyId || !companies[currentCompanyId]) {
    return (
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-8 text-center">
        <AlertCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700 mb-2">
          No hay empresa seleccionada
        </h3>
        <p className="text-gray-500">
          Selecciona una empresa válida para comenzar las pruebas de chat.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Configuración del chat */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Settings className="h-5 w-5 mr-2" />
          Configuración de Pruebas
        </h3>
        
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Usuario de Prueba
              </label>
              <input
                type="text"
                value={testUserId}
                onChange={(e) => setTestUserId(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="test_user"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Empresa Actual
              </label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-gray-700">
                {companies[currentCompanyId]?.company_name || currentCompanyId}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={clearChat}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm flex items-center space-x-1"
            >
              <Trash2 className="h-4 w-4" />
              <span>Limpiar Chat</span>
            </button>
            <div className="text-sm text-gray-500">
              {chatMessages.length} mensajes
            </div>
          </div>
        </div>
      </div>

      {/* Chat interface */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl overflow-hidden shadow-lg">
        {/* Messages area */}
        <div className="h-96 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {chatMessages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium">¡Comienza una conversación!</p>
              <p className="text-sm">
                Escribe un mensaje para probar el sistema de chatbot de {companies[currentCompanyId]?.company_name}
              </p>
            </div>
          ) : (
            chatMessages.map((message) => (
              <div
                key={message.id}
                className={`p-4 rounded-lg border ${getMessageStyles(message.type)}`}
              >
                <div className="flex items-start space-x-3">
                  {getMessageIcon(message.type, message.agent_type)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {message.type === 'user' ? `Usuario (${message.user_id})` : 
                         message.type === 'bot' ? `Bot (${message.agent_type || 'AI'})` : 
                         'Sistema'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {message.timestamp}
                      </span>
                    </div>
                    <div className="text-gray-800 whitespace-pre-wrap">
                      {message.content}
                    </div>
                    {message.metadata && Object.keys(message.metadata).length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <details>
                          <summary className="cursor-pointer">Metadatos</summary>
                          <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-auto">
                            {JSON.stringify(message.metadata, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="bg-gray-100 p-4 rounded-lg border mr-8">
              <div className="flex items-center space-x-3">
                <Bot className="h-4 w-4 text-gray-600" />
                <div>
                  <div className="text-sm font-medium text-gray-700">Bot está escribiendo...</div>
                  <div className="flex space-x-1 mt-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="p-4 bg-white border-t">
          <div className="flex space-x-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={`Escribe tu mensaje para ${companies[currentCompanyId]?.company_name}...`}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              <Send className="h-4 w-4" />
              <span>{isLoading ? 'Enviando...' : 'Enviar'}</span>
            </button>
          </div>
          
          {/* Quick test buttons */}
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => setInputMessage('Hola, ¿cómo estás?')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              disabled={isLoading}
            >
              Saludo
            </button>
            <button
              onClick={() => setInputMessage('¿Qué servicios ofrecen?')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              disabled={isLoading}
            >
              Servicios
            </button>
            <button
              onClick={() => setInputMessage('Quiero agendar una cita')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              disabled={isLoading}
            >
              Cita
            </button>
            <button
              onClick={() => setInputMessage('¿Cuáles son sus precios?')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              disabled={isLoading}
            >
              Precios
            </button>
          </div>
        </div>
      </div>

      {/* Debug info */}
      <div className="bg-white/90 rounded-lg p-4 text-xs text-gray-600">
        <details>
          <summary className="cursor-pointer font-medium">Debug Info</summary>
          <div className="mt-2 space-y-1">
            <div><strong>Company ID:</strong> {currentCompanyId}</div>
            <div><strong>User ID:</strong> {testUserId}</div>
            <div><strong>Conversation ID:</strong> {conversationId}</div>
            <div><strong>Messages Count:</strong> {chatMessages.length}</div>
            <div><strong>API Endpoint:</strong> /api/conversations/message</div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default ChatSection;
