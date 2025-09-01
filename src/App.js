// src/App.js
import React, { useState, useEffect } from 'react';
import { Building, Activity } from 'lucide-react';

// Importar componentes modulares
import CompanySelector from './components/CompanySelector';
import TabNavigation from './components/TabNavigation';
import ChatSection from './components/ChatSection';
import DocumentsSection from './components/DocumentsSection';
import AdminSection from './components/AdminSection';
import LoadingOverlay from './components/LoadingOverlay';
import ToastContainer from './components/ToastContainer';

// Importar modales
import UploadModal from './components/modals/UploadModal';
import ConfigModal from './components/modals/ConfigModal';
import CameraModal from './components/modals/CameraModal';

// Importar hooks personalizados
import { useLoading } from './hooks/useLoading';
import { useToast } from './hooks/useToast';

// Importar servicios
import { companiesService } from './services/companiesService';
import { documentsService } from './services/documentsService';
import { conversationsService } from './services/conversationsService';

const MultiTenantAdmin = () => {
  // Estados principales
  const [companies, setCompanies] = useState({});
  const [currentCompanyId, setCurrentCompanyId] = useState('');
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');

  // Hooks personalizados
  const { loading, message, showLoading, hideLoading } = useLoading();
  const { toasts, showToast, removeToast } = useToast();

  // Estados para modales
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Estados para configuración
  const [googleCalendarUrl, setGoogleCalendarUrl] = useState('');

  // Cargar empresas al inicializar
  useEffect(() => {
    loadCompanies();
  }, []);

  // Cargar datos cuando cambia la empresa
  useEffect(() => {
    if (currentCompanyId) {
      loadDocuments();
      loadConversations();
    }
  }, [currentCompanyId]);

  // Funciones para cargar datos
  const loadCompanies = async () => {
    try {
      showLoading('Cargando empresas...');
      const data = await companiesService.getAll();
      
      setCompanies(data.companies);
      
      // Establecer primera empresa como actual
      const companyIds = Object.keys(data.companies);
      if (companyIds.length > 0 && !currentCompanyId) {
        setCurrentCompanyId(companyIds[0]);
      }
      
      showToast('✅ Empresas cargadas correctamente', 'success');
    } catch (error) {
      showToast('❌ Error cargando empresas: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const loadDocuments = async () => {
    if (!currentCompanyId) return;
    
    try {
      const data = await documentsService.list(currentCompanyId);
      setDocuments(data.documents || []);
    } catch (error) {
      showToast('❌ Error cargando documentos: ' + error.message, 'error');
    }
  };

  const loadConversations = async () => {
    if (!currentCompanyId) return;
    
    try {
      const data = await conversationsService.list(currentCompanyId);
      setConversations(data.conversations || []);
    } catch (error) {
      showToast('❌ Error cargando conversaciones: ' + error.message, 'error');
    }
  };

  // Función para verificar salud del sistema
  const checkSystemHealth = async () => {
    try {
      showLoading('Verificando salud del sistema...');
      
      const response = await fetch('/api/health');
      const data = await response.json();
      
      const healthStatus = data.status === 'healthy' ? '✅ Saludable' : '❌ Con problemas';
      showToast(`Sistema: ${healthStatus}`, data.status === 'healthy' ? 'success' : 'warning');
    } catch (error) {
      showToast('❌ Error verificando salud: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm border-b border-white/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Building className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Multi-Tenant Admin
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <CompanySelector
                companies={companies}
                currentCompanyId={currentCompanyId}
                onCompanyChange={setCurrentCompanyId}
              />
              
              <button
                onClick={checkSystemHealth}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
              >
                <Activity className="h-4 w-4" />
                <span>Health</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navegación por pestañas */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Contenido de las pestañas */}
        {activeTab === 'chat' && (
          <ChatSection
            currentCompanyId={currentCompanyId}
            companies={companies}
            showToast={showToast}
            showLoading={showLoading}
            hideLoading={hideLoading}
            setShowCameraModal={setShowCameraModal}
          />
        )}

        {activeTab === 'documents' && (
          <DocumentsSection
            documents={documents}
            currentCompanyId={currentCompanyId}
            companies={companies}
            loadDocuments={loadDocuments}
            showToast={showToast}
            showLoading={showLoading}
            hideLoading={hideLoading}
            setShowUploadModal={setShowUploadModal}
          />
        )}

        {activeTab === 'admin' && (
          <AdminSection
            currentCompanyId={currentCompanyId}
            companies={companies}
            conversations={conversations}
            setShowConfigModal={setShowConfigModal}
            checkSystemHealth={checkSystemHealth}
            showToast={showToast}
          />
        )}
      </div>

      {/* Modales */}
      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          currentCompanyId={currentCompanyId}
          companies={companies}
          onSuccess={loadDocuments}
          showToast={showToast}
          showLoading={showLoading}
          hideLoading={hideLoading}
        />
      )}

      {showConfigModal && (
        <ConfigModal
          onClose={() => setShowConfigModal(false)}
          currentCompanyId={currentCompanyId}
          googleCalendarUrl={googleCalendarUrl}
          setGoogleCalendarUrl={setGoogleCalendarUrl}
          showToast={showToast}
          showLoading={showLoading}
          hideLoading={hideLoading}
        />
      )}

      {showCameraModal && (
        <CameraModal
          onClose={() => setShowCameraModal(false)}
          currentCompanyId={currentCompanyId}
          companies={companies}
          showToast={showToast}
          showLoading={showLoading}
          hideLoading={hideLoading}
        />
      )}

      {/* Loading overlay */}
      <LoadingOverlay loading={loading} message={message} />

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  );
};

export default MultiTenantAdmin;
