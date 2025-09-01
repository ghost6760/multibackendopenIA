// src/components/ChatMessage.jsx
import React from 'react';
import { User, Bot, Settings, AlertCircle } from 'lucide-react';

const ChatMessage = ({ message }) => {
  const getMessageStyle = () => {
    switch (message.role) {
      case 'user':
        return 'bg-blue-600 text-white ml-auto';
      case 'assistant':
        return 'bg-white text-gray-800 border border-gray-200';
      case 'system':
        return 'bg-yellow-50 text-yellow-800 text-sm border border-yellow-200';
      case 'error':
        return 'bg-red-50 text-red-800 border border-red-200';
      default:
        return 'bg-gray-50 text-gray-600 border border-gray-200';
    }
  };

  const getMessageIcon = () => {
    switch (message.role) {
      case 'user':
        return <User className="h-4 w-4 flex-shrink-0" />;
      case 'assistant':
        return <Bot className="h-4 w-4 flex-shrink-0 text-blue-600" />;
      case 'system':
        return <Settings className="h-3 w-3 flex-shrink-0 text-yellow-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-600" />;
      default:
        return null;
    }
  };

  const getMaxWidth = () => {
    return message.role === 'system' ? 'max-w-full' : 'max-w-3xl';
  };

  return (
    <div className={`${getMaxWidth()} rounded-lg p-3 shadow-sm ${getMessageStyle()}`}>
      <div className="flex items-start space-x-2">
        {getMessageIcon()}
        <div className="flex-1 min-w-0">
          <div className="break-words whitespace-pre-wrap">
            {message.content}
          </div>
          
          {message.agent && message.role === 'assistant' && (
            <div className="text-xs mt-2 opacity-75 flex items-center space-x-1">
              <Bot className="h-3 w-3" />
              <span>Agente: {message.agent}</span>
            </div>
          )}
          
          <div className="text-xs mt-1 opacity-75">
            {message.timestamp.toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
