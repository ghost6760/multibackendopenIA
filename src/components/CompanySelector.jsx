// src/components/CompanySelector.jsx
import React from 'react';

const CompanySelector = ({ companies, selectedCompany, onCompanyChange }) => {
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <label style={{ 
        display: 'block', 
        fontSize: '0.875rem', 
        fontWeight: '500', 
        color: 'white', 
        marginBottom: '0.5rem' 
      }}>
        Seleccionar Empresa:
      </label>
      <select 
        value={selectedCompany?.company_id || ''} 
        onChange={(e) => {
          console.log('Company selected:', e.target.value);
          console.log('Available companies:', companies); // NUEVO: Ver estructura real
          console.log('First company structure:', companies[0]); // NUEVO: Ver primer objeto
          console.log('Companies length:', companies.length); // NUEVO: Verificar cantidad
          const company = companies.find(c => c.company_id === e.target.value);
          console.log('Found company:', company);
          if (company) {
            onCompanyChange(company); // Pasar el objeto completo
          }
        }}
        style={{
          display: 'block',
          width: '100%',
          padding: '0.75rem',
          border: '1px solid #d1d5db',
          borderRadius: '0.375rem',
          background: 'white',
          fontSize: '1rem'
        }}
      >
        <option value="">Seleccionar empresa...</option>
        {companies.map((company, index) => (
          <option key={company.company_id || index} value={company.company_id}>
            {company.company_name || `Empresa ${index + 1}`}
          </option>
        ))}
      </select>
    </div>
  );
};

export default CompanySelector;

