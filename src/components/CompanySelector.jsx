// src/components/CompanySelector.jsx
import React from 'react';

const CompanySelector = ({ companies, currentCompanyId, onChange }) => {
  return (
    <div className="flex items-center space-x-4">
      <label htmlFor="company-select" className="text-sm font-medium text-gray-700">
        Empresa:
      </label>
      <select
        id="company-select"
        value={currentCompanyId}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 bg-white"
      >
        <option value="">Seleccionar empresa...</option>
        {Object.values(companies).map((company) => (
          <option key={company.company_id} value={company.company_id}>
            {company.company_name} ({company.company_id})
          </option>
        ))}
      </select>
    </div>
  );
};

export default CompanySelector;

