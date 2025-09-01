// src/hooks/useLoading.js
import { useState } from 'react';

export const useLoading = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  
  const showLoading = (msg = 'Cargando...') => {
    setMessage(msg);
    setLoading(true);
  };
  
  const hideLoading = () => {
    setLoading(false);
    setMessage('');
  };
  
  return { loading, message, showLoading, hideLoading };
};
