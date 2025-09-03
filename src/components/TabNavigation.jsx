import React from 'react';

const TabNavigation = ({ activeTab, tabs, onTabChange }) => {
  return (
    <nav className="flex space-x-8 border-b">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
            activeTab === tab.id
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <span className="flex items-center space-x-2">
            <span>{tab.icon}</span>
            <span>{tab.name}</span>
          </span>
        </button>
      ))}
    </nav>
  );
};

export default TabNavigation;

