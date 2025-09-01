// src/components/ToastContainer.jsx
import React from 'react';
import { CheckCircle, X, AlertTriangle, Info } from 'lucide-react';

const Toast = ({ toast, onClose }) => {
  const getToastStyles = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-green-600 text-white border-green-600';
      case 'error':
        return 'bg-red-600 text-white border-red-600';
      case 'warning':
        return 'bg-yellow-600 text-white border-yellow-600';
      default:
        return 'bg-blue-600 text-white border-blue-600';
    }
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="h-5 w-5" />;
      case 'error':
        return <X className="h-5 w-5" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <Info className="h-5 w-5" />;
    }
  };

  return (
    <div className={`flex items-center space-x-3 px-4 py-3 rounded-lg shadow-lg border ${getToastStyles()} transition-all duration-300 cursor-pointer hover:opacity-90`}
         onClick={onClose}>
      {getIcon()}
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        className="hover:bg-white/10 rounded-full p-1 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

const ToastContainer = ({ toasts, removeToast }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          toast={toast}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
};

export default ToastContainer;
