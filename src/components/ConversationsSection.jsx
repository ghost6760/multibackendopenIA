// src/components/ConversationsSection.jsx - Gestión de conversaciones corregida
import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

const ConversationsSection = ({ currentCompanyId, companies }) => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [expandedConversations, setExpandedConversations] = useState(new Set());

  useEffect(() => {
    if (currentCompanyId) {
      apiService.setCompanyId(currentCompanyId);
      loadConversations();
      loadConversationStats();
    }
  }, [currentCompanyId]);

  const loadConversations = async () => {
    if (!currentCompanyId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🔍 Loading conversations for company:', currentCompanyId);
      const response = await apiService.getConversations();
      
      console.log('💬 Conversations response:', response);
      
      if (response && response.status === 'success') {
        setConversations(response.conversations || []);
      } else if (response && Array.isArray(response)) {
        setConversations(response);
      } else {
        throw new Error(response?.message || 'Formato de respuesta inválido');
      }
      
    } catch (error) {
      console.error('❌ Error loading conversations:', error);
      setError(`Error cargando conversaciones: ${error.message}`);
      setConversations([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadConversationStats = async () => {
    if (!currentCompanyId) return;
    
    try {
      const response = await apiService.getConversationStats();
      console.log('📊 Conversation stats:', response);
      setStats(response);
    } catch (error) {
      console.error('❌ Error loading conversation stats:', error);
      // No mostrar error para stats, no es crítico
    }
  };

  const loadConversationDetails = async (conversationId) => {
    if (!currentCompanyId) return;
    
    try {
      setIsLoading(true);
      console.log('🔍 Loading conversation details:', conversationId);
      
      const response = await apiService.getConversation(conversationId);
      console.log('💬 Conversation details:', response);
      
      if (response && response.status === 'success') {
        setSelectedConversation(response.conversation || response);
      } else {
        setSelectedConversation(response);
      }
      
    } catch (error) {
      console.error('❌ Error loading conversation details:', error);
      setError(`Error cargando detalles de conversación: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteConversation = async (conversationId) => {
    if (!window.confirm('¿Estás seguro de eliminar esta conversación?')) {
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🗑️ Deleting conversation:', conversationId);
      
      const response = await apiService.deleteConversation(conversationId);
      console.log('✅ Delete response:', response);
      
      if (response && response.status === 'success') {
        // Recargar conversaciones
        await loadConversations();
        await loadConversationStats();
        
        // Limpiar conversación seleccionada si era la que se eliminó
        if (selectedConversation && selectedConversation.id === conversationId) {
          setSelectedConversation(null);
        }
        
        alert('✅ Conversación eliminada exitosamente');
      } else {
        throw new Error(response?.message || 'Error eliminando conversación');
      }
      
    } catch (error) {
      console.error('❌ Error deleting conversation:', error);
      setError(`Error eliminando conversación: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleConversationExpansion = (conversationId) => {
    const newExpanded = new Set(expandedConversations);
    if (newExpanded.has(conversationId)) {
      newExpanded.delete(conversationId);
    } else {
      newExpanded.add(conversationId);
    }
    setExpandedConversations(newExpanded);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getMessagePreview = (messages) => {
    if (!messages || messages.length === 0) return 'Sin mensajes';
    const lastMessage = messages[messages.length - 1];
    const text = lastMessage.content || lastMessage.message || lastMessage.text || '';
    return text.length > 100 ? text.substring(0, 100) + '...' : text;
  };

  if (!currentCompanyId) {
    return (
      <div className="bg-white/90 backdrop-blur rounded-lg p-6 text-center">
        <div className="text-gray-500">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-lg font-semibold mb-2">Historial de Conversaciones</h3>
          <p>Selecciona una empresa para ver sus conversaciones</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              💬 Conversaciones de {companies[currentCompanyId]?.company_name}
            </h2>
            <p className="text-gray-600 mt-1">
              Revisa y gestiona las conversaciones del chatbot
            </p>
          </div>
          
          {stats && (
            <div className="bg-green-50 rounded-lg p-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="font-semibold text-green-800">Total Conversaciones</div>
                  <div className="text-green-600">{stats.total_conversations || 0}</div>
                </div>
                <div>
                  <div className="font-semibold text-green-800">Total Mensajes</div>
                  <div className="text-green-600">{stats.total_messages || 0}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <div className="flex">
              <span className="text-red-500 mr-2">❌</span>
              {error}
            </div>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={loadConversations}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            🔄 Actualizar Conversaciones
          </button>
          
          <button
            onClick={() => setSelectedConversation(null)}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            👁️ Vista General
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conversations List */}
        <div className="bg-white/90 backdrop-blur rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">📋 Lista de Conversaciones</h3>

          {isLoading && conversations.length === 0 ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Cargando conversaciones...</p>
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">💬</div>
              <p>No hay conversaciones disponibles</p>
              <p className="text-sm mt-1">Las conversaciones aparecerán aquí cuando los usuarios interactúen con el chatbot</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {conversations.map((conversation) => {
                const conversationId = conversation.id || conversation.conversation_id;
                const isExpanded = expandedConversations.has(conversationId);
                
                return (
                  <div
                    key={conversationId}
                    className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center mb-2">
                          <span className="text-lg mr-2">👤</span>
                          <div>
                            <h4 className="font-medium text-gray-800">
                              {conversation.user_id || 'Usuario Anónimo'}
                            </h4>
                            <p className="text-xs text-gray-500">
                              ID: {conversationId?.toString().slice(-8) || 'N/A'}
                            </p>
                          </div>
                        </div>
                        
                        <div className="text-sm text-gray-600 mb-2">
                          <div>📅 {formatDate(conversation.created_at || conversation.last_message_at)}</div>
                          <div>💬 {conversation.message_count || conversation.messages?.length || 0} mensajes</div>
                        </div>
                        
                        {!isExpanded && (
                          <p className="text-sm text-gray-700 italic">
                            "{getMessagePreview(conversation.messages)}"
                          </p>
                        )}
                        
                        {isExpanded && conversation.messages && (
                          <div className="mt-3 space-y-2 max-h-40 overflow-y-auto bg-gray-50 rounded p-2">
                            {conversation.messages.map((message, index) => (
                              <div key={index} className="text-sm">
                                <div className="font-medium text-xs text-gray-500">
                                  {message.role === 'user' ? '👤 Usuario' : '🤖 Bot'} • 
                                  {formatDate(message.timestamp)}
                                </div>
                                <div className="text-gray-700 ml-4">
                                  {message.content || message.message || message.text}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      <div className="ml-4 flex flex-col space-y-2">
                        <button
                          onClick={() => toggleConversationExpansion(conversationId)}
                          className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                        >
                          {isExpanded ? '👆 Ocultar' : '👇 Ver Más'}
                        </button>
                        
                        <button
                          onClick={() => loadConversationDetails(conversationId)}
                          className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                          disabled={isLoading}
                        >
                          🔍 Detalles
                        </button>
                        
                        <button
                          onClick={() => deleteConversation(conversationId)}
                          disabled={isLoading}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors disabled:opacity-50"
                        >
                          🗑️ Eliminar
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Conversation Details */}
        <div className="bg-white/90 backdrop-blur rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">🔍 Detalles de Conversación</h3>

          {selectedConversation ? (
            <div className="space-y-4">
              {/* Conversation Header */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium text-gray-700">Usuario</div>
                    <div className="text-gray-600">{selectedConversation.user_id || 'Anónimo'}</div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-700">ID Conversación</div>
                    <div className="text-gray-600 font-mono text-xs">
                      {selectedConversation.id || selectedConversation.conversation_id || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-700">Creada</div>
                    <div className="text-gray-600">{formatDate(selectedConversation.created_at)}</div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-700">Mensajes</div>
                    <div className="text-gray-600">
                      {selectedConversation.messages?.length || selectedConversation.message_count || 0}
                    </div>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {selectedConversation.messages && selectedConversation.messages.length > 0 ? (
                  selectedConversation.messages.map((message, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg ${
                        message.role === 'user' || message.sender === 'user'
                          ? 'bg-blue-100 ml-4'
                          : 'bg-gray-100 mr-4'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-sm">
                          {message.role === 'user' || message.sender === 'user' ? '👤 Usuario' : '🤖 Bot'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatDate(message.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-800 whitespace-pre-wrap">
                        {message.content || message.message || message.text}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 text-gray-500">
                    <p>No hay mensajes en esta conversación</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">🔍</div>
              <p>Selecciona una conversación para ver sus detalles</p>
            </div>
          )}
        </div>
      </div>

      {/* Debug Info */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-4">
        <details>
          <summary className="cursor-pointer font-medium text-sm">🔧 Debug Info</summary>
          <div className="mt-2 text-xs space-y-1 text-gray-600">
            <div><strong>Company ID:</strong> {currentCompanyId}</div>
            <div><strong>Conversations Count:</strong> {conversations.length}</div>
            <div><strong>Selected Conversation:</strong> {selectedConversation?.id || 'Ninguna'}</div>
            <div><strong>API Endpoint:</strong> GET /api/conversations</div>
            <div><strong>Loading:</strong> {isLoading ? 'Sí' : 'No'}</div>
            <div><strong>Expanded:</strong> {expandedConversations.size} conversaciones</div>
            <div><strong>Last Error:</strong> {error || 'Ninguno'}</div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default ConversationsSection;
