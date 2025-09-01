// src/components/TabNavigation.jsx
import React from 'react';
import { MessageSquare, FileText, Settings } from 'lucide-react';

const TabNavigation = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'chat', label: 'Chat Testing', icon: MessageSquare },
    { id: 'documents', label: 'Documentos', icon: FileText },
    { id: 'admin', label: 'Administración', icon: Settings }
  ];

  return (
    <div className="mb-8">
      <nav className="flex space-x-8">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === id
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-white/80 hover:text-white hover:bg-white/10'
            }`}
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default TabNavigation;
