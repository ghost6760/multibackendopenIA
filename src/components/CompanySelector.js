// src/components/CompanySelector.js - Selector de empresas

import React, { useState } from 'react';

const CompanySelector = ({ companies, selectedCompany, onCompanyChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleCompanySelect = (company) => {
    onCompanyChange(company);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
        <span className="font-medium text-gray-700">
          {selectedCompany ? selectedCompany.company_name : 'Seleccionar Empresa'}
        </span>
        <svg 
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="py-1">
            {companies.map((company) => (
              <button
                key={company.company_id}
                onClick={() => handleCompanySelect(company)}
                className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                  selectedCompany?.company_id === company.company_id 
                    ? 'bg-blue-50 text-blue-600' 
                    : 'text-gray-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{company.company_name}</div>
                    <div className="text-sm text-gray-500">{company.industry}</div>
                  </div>
                  {selectedCompany?.company_id === company.company_id && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        ></div>
      )}
    </div>
  );
};

export default CompanySelector;
