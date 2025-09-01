// src/hooks/useToast.js
import { useState } from 'react';

export const useToast = () => {
  const [toasts, setToasts] = useState([]);
  
  const showToast = (message, type = 'info') => {
    const id = Date.now();
    const newToast = { id, message, type };
    setToasts(prev => [...prev, newToast]);
    
    // Auto-remove después de 5 segundos
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 5000);
  };
  
  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };
  
  return { toasts, showToast, removeToast };
};
