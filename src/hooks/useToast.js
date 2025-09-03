// src/hooks/useToast.js
import { useState } from 'react';

export const useToast = () => {
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    const toast = { id, message, type };
    
    setToasts(prev => [...prev, toast]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const hideToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return { toasts, showToast, hideToast };
};

export default useToast;
