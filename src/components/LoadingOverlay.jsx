// src/components/LoadingOverlay.jsx
import React from 'react';
import { Loader } from 'lucide-react';

const LoadingOverlay = ({ loading, message }) => {
  if (!loading) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 flex flex-col items-center space-y-4 min-w-[200px]">
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-gray-700 text-center">{message}</p>
      </div>
    </div>
  );
};

export default LoadingOverlay;
