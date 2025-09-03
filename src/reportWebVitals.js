// src/reportWebVitals.js - Reportar métricas de rendimiento web

const reportWebVitals = (onPerfEntry) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    }).catch((error) => {
      // Web vitals no es crítico, solo log del error
      console.warn('⚠️ No se pudieron cargar las métricas web vitals:', error);
    });
  }
};

export default reportWebVitals;
