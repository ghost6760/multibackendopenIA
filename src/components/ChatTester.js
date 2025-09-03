// src/components/ChatTester.js - Interfaz para probar el sistema de chat

import React, { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const ChatTester = ({ company }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [userId] = useState('test-user-' + Date.now());
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (company) {
      // Mensaje de bienvenida
      setMessages([{
        type: 'system',
        content: `Conectado al sistema de chat de ${company.company_name}. Puedes empezar a hacer preguntas.`,
        timestamp: new Date()
      }]);
    }
  }, [company]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || sending) return;

    const userMessage = {
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setSending(true);

    try {
      const response = await apiService.sendMessage(userMessage.content, null, userId);
      
      const assistantMessage = {
        type: 'assistant',
        content: response.response || 'Sin respuesta',
        agent_used: response.agent_used,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setSending(false);
    }
  };

  const clearChat = () => {
    setMessages([{
      type: 'system',
      content: `Chat reiniciado para ${company.company_name}`,
      timestamp: new Date()
    }]);
  };

  const getMessageStyle = (type) => {
    switch (type) {
      case 'user':
        return 'bg-blue-600 text-white ml-auto max-w-xs lg:max-w-md';
      case 'assistant':
        return 'bg-gray-100 text-gray-900 mr-auto max-w-xs lg:max-w-md';
      case 'system':
        return 'bg-yellow-50 text-yellow-800 mx-auto max-w-md text-center';
      case 'error':
        return 'bg-red-50 text-red-800 mx-auto max-w-md';
      default:
        return 'bg-gray-100 text-gray-900';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Test de Chat
            </h2>
            <p className="text-gray-600 mt-1">
              Prueba el sistema de chat de {company?.company_name}
            </p>
          </div>
          <button
            onClick={clearChat}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Limpiar Chat
          </button>
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-lg shadow flex flex-col h-96">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div key={index} className="flex">
              <div className={`rounded-lg p-3 ${getMessageStyle(message.type)}`}>
                <div className="text-sm">
                  {message.content}
                </div>
                {message.agent_used && (
                  <div className="text-xs mt-1 opacity-70">
                    Agente: {message.agent_used}
                  </div>
                )}
                <div className="text-xs mt-1 opacity-70">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          
          {sending && (
            <div className="flex">
              <div className="bg-gray-100 text-gray-900 mr-auto max-w-xs lg:max-w-md rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <LoadingSpinner size="small" />
                  <span className="text-sm">Escribiendo...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSendMessage} className="flex space-x-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Escribe tu mensaje..."
              disabled={sending}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || sending}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {sending ? <LoadingSpinner size="small" /> : 'Enviar'}
            </button>
          </form>
        </div>
      </div>

      {/* Ejemplos de Preguntas */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Preguntas de Ejemplo
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            "¿Qué servicios ofrecen?",
            "¿Cuáles son sus horarios de atención?",
            "Quiero agendar una cita",
            "¿Tienen disponibilidad para mañana?",
            "¿Cuáles son sus precios?",
            "¿Dónde están ubicados?"
          ].map((question, index) => (
            <button
              key={index}
              onClick={() => setInputMessage(question)}
              className="text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="text-sm text-gray-700">{question}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-800">
              Información del Chat
            </h4>
            <div className="mt-2 text-sm text-blue-700 space-y-1">
              <p>• Usuario de prueba: {userId}</p>
              <p>• Empresa: {company?.company_name}</p>
              <p>• Mensajes en esta sesión: {messages.filter(m => m.type !== 'system').length}</p>
              <p>• El sistema utiliza múltiples agentes especializados</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatTester;
