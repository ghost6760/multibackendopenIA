-- ============================================================================
-- POSTGRESQL SCHEMA REFACTORIZADO - MULTI-TENANT SYSTEM WITH STRUCTURED PROMPTS
-- Combina:
-- 1. Sistema de Prompts Configurables con soporte LangGraph (REFACTORED)
-- 2. Sistema de Configuración de Empresas (ENTERPRISE)
-- Compatible con arquitectura multi-tenant y LangGraph
-- ============================================================================

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SECCIÓN 1: SISTEMA DE PROMPTS CONFIGURABLES (REFACTORED FOR LANGGRAPH)
-- ============================================================================

-- TABLA PRINCIPAL DE PROMPTS PERSONALIZADOS
-- REFACTORIZADO: Ahora incluye structured_template y format
CREATE TABLE IF NOT EXISTS custom_prompts (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    
    -- Formato del prompt: 'simple' o 'structured'
    format VARCHAR(20) DEFAULT 'simple' CHECK (format IN ('simple', 'structured')),
    
    -- Template legacy (para backward compatibility)
    template TEXT NOT NULL,
    
    -- Template estructurado (JSONB) para LangGraph
    -- Estructura: {system: str, examples: [], placeholders: {}, meta: {}}
    structured_template JSONB,
    
    -- Control de estado
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    modified_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

-- TABLA DE HISTORIAL Y VERSIONADO DE PROMPTS
-- REFACTORIZADO: Incluye structured_template y format en historial
CREATE TABLE IF NOT EXISTS prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    prompt_id BIGINT,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    
    -- Formato del prompt versionado
    format VARCHAR(20) DEFAULT 'simple',
    
    -- Templates versionados
    template TEXT NOT NULL,
    structured_template JSONB,
    
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'REPAIR')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

-- TABLA DE PROMPTS POR DEFECTO DEL REPOSITORIO (MULTI-TENANT)
-- REFACTORIZADO: Incluye structured_template y format
CREATE TABLE IF NOT EXISTS default_prompts (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    
    -- Formato del prompt: 'simple' o 'structured'
    format VARCHAR(20) DEFAULT 'simple' CHECK (format IN ('simple', 'structured')),
    
    -- Template legacy (para backward compatibility)
    template TEXT NOT NULL,
    
    -- Template estructurado (JSONB) para LangGraph
    structured_template JSONB,
    
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SECCIÓN 2: CONFIGURACIÓN DE EMPRESAS (ENTERPRISE) - SIN CAMBIOS
-- ============================================================================

-- TABLA PRINCIPAL DE CONFIGURACIÓN DE EMPRESAS
CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) UNIQUE NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    business_type VARCHAR(100) DEFAULT 'general',
    services TEXT NOT NULL,
    
    -- Configuración Redis/Vector Store
    redis_prefix VARCHAR(150) NOT NULL,
    vectorstore_index VARCHAR(150) NOT NULL,
    
    -- Configuración de Agentes
    sales_agent_name VARCHAR(200) NOT NULL,
    model_name VARCHAR(100) DEFAULT 'gpt-4o-mini',
    max_tokens INTEGER DEFAULT 1500,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_context_messages INTEGER DEFAULT 10,
    
    -- Configuración de Servicios Externos
    schedule_service_url VARCHAR(300),
    schedule_integration_type VARCHAR(50) DEFAULT 'basic',
    chatwoot_account_id VARCHAR(50),
    
    -- Configuración de Negocio
    treatment_durations JSONB,
    schedule_keywords TEXT[],
    emergency_keywords TEXT[],
    sales_keywords TEXT[],
    required_booking_fields TEXT[],
    
    -- Configuración de Localización
    timezone VARCHAR(50) DEFAULT 'America/Bogota',
    language VARCHAR(10) DEFAULT 'es',
    currency VARCHAR(10) DEFAULT 'COP',
    
    -- Estado y Metadatos
    is_active BOOLEAN DEFAULT true,
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    max_documents INTEGER DEFAULT 1000,
    max_conversations INTEGER DEFAULT 10000,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    modified_by VARCHAR(100) DEFAULT 'admin',
    version INTEGER DEFAULT 1,
    notes TEXT
);

-- TABLA DE HISTORIAL DE CONFIGURACIÓN DE EMPRESAS (VERSIONADO)
CREATE TABLE IF NOT EXISTS company_config_versions (
    id BIGSERIAL PRIMARY KEY,
    company_pk BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    company_id VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'ACTIVATE', 'DEACTIVATE')),
    
    -- Snapshot completo de la configuración
    config_snapshot JSONB NOT NULL,
    changes_summary TEXT,
    
    -- Campos específicos que cambiaron
    changed_fields TEXT[],
    previous_values JSONB,
    new_values JSONB,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT,
    
    -- Metadatos de cambio
    change_reason VARCHAR(200),
    change_source VARCHAR(100) DEFAULT 'admin_panel',
    ip_address INET,
    user_agent TEXT
);

-- TABLA DE CONFIGURACIÓN POR DEFECTO (PLANTILLAS)
CREATE TABLE IF NOT EXISTS company_templates (
    id BIGSERIAL PRIMARY KEY,
    template_name VARCHAR(100) UNIQUE NOT NULL,
    business_type VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Configuración por defecto
    default_config JSONB NOT NULL,
    required_fields TEXT[] NOT NULL,
    optional_fields TEXT[],
    
    -- Metadatos
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TABLA DE CONFIGURACIÓN RUNTIME (NO VERSIONADA)
CREATE TABLE IF NOT EXISTS company_runtime_settings (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) UNIQUE NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- Cache settings
    cache_ttl INTEGER DEFAULT 3600,
    cache_enabled BOOLEAN DEFAULT true,
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    
    -- Feature flags
    features_enabled JSONB DEFAULT '{}'::JSONB,
    
    -- Runtime stats
    last_activity TIMESTAMP WITH TIME ZONE,
    total_conversations INTEGER DEFAULT 0,
    total_documents INTEGER DEFAULT 0,
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Custom prompts constraints
ALTER TABLE custom_prompts 
ADD CONSTRAINT unique_active_prompt UNIQUE (company_id, agent_name);

-- Default prompts constraints
ALTER TABLE default_prompts 
ADD CONSTRAINT unique_default_prompt UNIQUE (company_id, agent_name);

-- ============================================================================
-- INDICES
-- ============================================================================

-- Indices para custom_prompts
CREATE INDEX IF NOT EXISTS idx_custom_prompts_company ON custom_prompts(company_id);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_agent ON custom_prompts(agent_name);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_active ON custom_prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_format ON custom_prompts(format);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_lookup ON custom_prompts(company_id, agent_name, is_active);

-- Indices para default_prompts
CREATE INDEX IF NOT EXISTS idx_default_prompts_company ON default_prompts(company_id);
CREATE INDEX IF NOT EXISTS idx_default_prompts_agent ON default_prompts(agent_name);
CREATE INDEX IF NOT EXISTS idx_default_prompts_format ON default_prompts(format);
CREATE INDEX IF NOT EXISTS idx_default_prompts_lookup ON default_prompts(company_id, agent_name);

-- Indices para prompt_versions
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_company ON prompt_versions(company_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_agent ON prompt_versions(agent_name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_created ON prompt_versions(created_at DESC);

-- Indices para companies
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_companies_business_type ON companies(business_type);
CREATE INDEX IF NOT EXISTS idx_companies_tier ON companies(subscription_tier);

-- Indices para company_config_versions
CREATE INDEX IF NOT EXISTS idx_company_versions_pk ON company_config_versions(company_pk);
CREATE INDEX IF NOT EXISTS idx_company_versions_company_id ON company_config_versions(company_id);
CREATE INDEX IF NOT EXISTS idx_company_versions_created ON company_config_versions(created_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger para versionado automático de prompts
CREATE OR REPLACE FUNCTION create_prompt_version()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO prompt_versions (
        prompt_id,
        company_id,
        agent_name,
        format,
        template,
        structured_template,
        version,
        action,
        created_by,
        notes
    ) VALUES (
        NEW.id,
        NEW.company_id,
        NEW.agent_name,
        NEW.format,
        NEW.template,
        NEW.structured_template,
        NEW.version,
        TG_ARGV[0],
        NEW.modified_by,
        COALESCE(NEW.notes, 'Automatic versioning')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS custom_prompts_version_trigger ON custom_prompts;
CREATE TRIGGER custom_prompts_version_trigger
AFTER INSERT OR UPDATE ON custom_prompts
FOR EACH ROW
EXECUTE FUNCTION create_prompt_version('UPDATE');

-- Trigger para actualizar modified_at automáticamente
CREATE OR REPLACE FUNCTION update_modified_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS custom_prompts_modified_trigger ON custom_prompts;
CREATE TRIGGER custom_prompts_modified_trigger
BEFORE UPDATE ON custom_prompts
FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

DROP TRIGGER IF EXISTS companies_modified_trigger ON companies;
CREATE TRIGGER companies_modified_trigger
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

-- Trigger para versionado de configuración de empresas
CREATE OR REPLACE FUNCTION create_company_config_version()
RETURNS TRIGGER AS $$
DECLARE
    changed_fields_array TEXT[];
    prev_values JSONB;
    new_values JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO company_config_versions (
            company_pk,
            company_id,
            version,
            action,
            config_snapshot,
            changes_summary,
            created_by
        ) VALUES (
            NEW.id,
            NEW.company_id,
            NEW.version,
            'CREATE',
            row_to_json(NEW)::JSONB,
            'Initial configuration created',
            NEW.created_by
        );
    ELSIF TG_OP = 'UPDATE' THEN
        -- Construir array de campos cambiados
        changed_fields_array := ARRAY[]::TEXT[];
        prev_values := '{}'::JSONB;
        new_values := '{}'::JSONB;
        
        IF OLD.company_name IS DISTINCT FROM NEW.company_name THEN
            changed_fields_array := array_append(changed_fields_array, 'company_name');
            prev_values := prev_values || jsonb_build_object('company_name', OLD.company_name);
            new_values := new_values || jsonb_build_object('company_name', NEW.company_name);
        END IF;
        
        IF OLD.services IS DISTINCT FROM NEW.services THEN
            changed_fields_array := array_append(changed_fields_array, 'services');
            prev_values := prev_values || jsonb_build_object('services', OLD.services);
            new_values := new_values || jsonb_build_object('services', NEW.services);
        END IF;
        
        IF OLD.is_active IS DISTINCT FROM NEW.is_active THEN
            changed_fields_array := array_append(changed_fields_array, 'is_active');
            prev_values := prev_values || jsonb_build_object('is_active', OLD.is_active);
            new_values := new_values || jsonb_build_object('is_active', NEW.is_active);
        END IF;
        
        INSERT INTO company_config_versions (
            company_pk,
            company_id,
            version,
            action,
            config_snapshot,
            changed_fields,
            previous_values,
            new_values,
            changes_summary,
            created_by
        ) VALUES (
            NEW.id,
            NEW.company_id,
            NEW.version,
            'UPDATE',
            row_to_json(NEW)::JSONB,
            changed_fields_array,
            prev_values,
            new_values,
            array_to_string(changed_fields_array, ', ') || ' updated',
            NEW.modified_by
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS company_config_version_trigger ON companies;
CREATE TRIGGER company_config_version_trigger
AFTER INSERT OR UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION create_company_config_version();

-- ============================================================================
-- FUNCIONES HELPER
-- ============================================================================

-- Función para obtener prompt con fallback jerárquico
-- REFACTORIZADO: Ahora retorna payload estructurado
CREATE OR REPLACE FUNCTION get_prompt_with_fallback(
    p_company_id VARCHAR(100),
    p_agent_name VARCHAR(100)
)
RETURNS TABLE (
    source VARCHAR(50),
    format VARCHAR(20),
    template TEXT,
    structured_template JSONB,
    version INTEGER,
    modified_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- Nivel 1: Custom prompt activo
    RETURN QUERY
    SELECT 
        'custom'::VARCHAR(50),
        cp.format,
        cp.template,
        cp.structured_template,
        cp.version,
        cp.modified_at
    FROM custom_prompts cp
    WHERE cp.company_id = p_company_id 
      AND cp.agent_name = p_agent_name 
      AND cp.is_active = true
    LIMIT 1;
    
    IF FOUND THEN RETURN; END IF;
    
    -- Nivel 2: Default prompt de la empresa
    RETURN QUERY
    SELECT 
        'default_company'::VARCHAR(50),
        dp.format,
        dp.template,
        dp.structured_template,
        1::INTEGER,
        dp.updated_at
    FROM default_prompts dp
    WHERE dp.company_id = p_company_id 
      AND dp.agent_name = p_agent_name
    LIMIT 1;
    
    IF FOUND THEN RETURN; END IF;
    
    -- Nivel 3: Default genérico (cualquier empresa)
    RETURN QUERY
    SELECT 
        'default_generic'::VARCHAR(50),
        dp.format,
        dp.template,
        dp.structured_template,
        1::INTEGER,
        dp.updated_at
    FROM default_prompts dp
    WHERE dp.agent_name = p_agent_name
    ORDER BY dp.created_at DESC
    LIMIT 1;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Función para reparar prompts desde repositorio
CREATE OR REPLACE FUNCTION repair_prompts_from_repository(
    p_company_id VARCHAR(100) DEFAULT NULL
)
RETURNS TABLE (
    company_id VARCHAR(100),
    agent_name VARCHAR(100),
    action VARCHAR(50),
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_company_id VARCHAR(100);
    v_agent_name VARCHAR(100);
    v_default_record RECORD;
BEGIN
    FOR v_default_record IN 
        SELECT 
            dp.company_id,
            dp.agent_name,
            dp.format,
            dp.template,
            dp.structured_template
        FROM default_prompts dp
        WHERE p_company_id IS NULL OR dp.company_id = p_company_id
    LOOP
        BEGIN
            INSERT INTO custom_prompts (
                company_id,
                agent_name,
                format,
                template,
                structured_template,
                created_by,
                modified_by,
                notes
            ) VALUES (
                v_default_record.company_id,
                v_default_record.agent_name,
                v_default_record.format,
                v_default_record.template,
                v_default_record.structured_template,
                'repair_function',
                'repair_function',
                'Repaired from default_prompts repository'
            )
            ON CONFLICT (company_id, agent_name) DO UPDATE SET
                format = EXCLUDED.format,
                template = EXCLUDED.template,
                structured_template = EXCLUDED.structured_template,
                modified_by = 'repair_function',
                modified_at = CURRENT_TIMESTAMP,
                notes = 'Repaired from default_prompts repository';
            
            RETURN QUERY SELECT 
                v_default_record.company_id,
                v_default_record.agent_name,
                'REPAIR'::VARCHAR(50),
                true,
                'Successfully repaired'::TEXT;
                
        EXCEPTION WHEN OTHERS THEN
            RETURN QUERY SELECT 
                v_default_record.company_id,
                v_default_record.agent_name,
                'REPAIR'::VARCHAR(50),
                false,
                SQLERRM::TEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Función para migrar configuración desde JSON
CREATE OR REPLACE FUNCTION migrate_company_from_json(
    p_company_id VARCHAR(100),
    p_config JSONB
)
RETURNS BOOLEAN AS $$
DECLARE
    v_success BOOLEAN := false;
BEGIN
    INSERT INTO companies (
        company_id,
        company_name,
        business_type,
        services,
        redis_prefix,
        vectorstore_index,
        sales_agent_name,
        model_name,
        max_tokens,
        temperature,
        max_context_messages,
        timezone,
        language,
        currency,
        is_active,
        created_by,
        notes
    ) VALUES (
        p_company_id,
        COALESCE(p_config->>'company_name', p_company_id),
        COALESCE(p_config->>'business_type', 'general'),
        COALESCE(p_config->>'services', 'general services'),
        COALESCE(p_config->>'redis_prefix', p_company_id || ':'),
        COALESCE(p_config->>'vectorstore_index', p_company_id || '_index'),
        COALESCE(p_config->>'sales_agent_name', 'Sales Agent'),
        COALESCE(p_config->>'model_name', 'gpt-4o-mini'),
        COALESCE((p_config->>'max_tokens')::INTEGER, 1500),
        COALESCE((p_config->>'temperature')::DECIMAL, 0.7),
        COALESCE((p_config->>'max_context_messages')::INTEGER, 10),
        COALESCE(p_config->>'timezone', 'America/Bogota'),
        COALESCE(p_config->>'language', 'es'),
        COALESCE(p_config->>'currency', 'COP'),
        COALESCE((p_config->>'is_active')::BOOLEAN, true),
        'json_migration',
        'Migrated from JSON configuration'
    )
    ON CONFLICT (company_id) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        business_type = EXCLUDED.business_type,
        services = EXCLUDED.services,
        modified_at = CURRENT_TIMESTAMP,
        modified_by = 'json_migration',
        notes = 'Updated from JSON configuration';
    
    v_success := true;
    RETURN v_success;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error migrating company %: %', p_company_id, SQLERRM;
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Función helper para obtener configuración con fallback
CREATE OR REPLACE FUNCTION get_company_config_with_fallback(
    p_company_id VARCHAR(100)
)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    -- Intentar obtener de PostgreSQL
    SELECT row_to_json(c)::JSONB INTO v_config
    FROM companies c
    WHERE c.company_id = p_company_id
      AND c.is_active = true;
    
    IF v_config IS NOT NULL THEN
        RETURN v_config;
    END IF;
    
    -- Fallback: retornar configuración vacía con indicador
    RETURN jsonb_build_object(
        'company_id', p_company_id,
        'fallback', true,
        'message', 'Configuration not found in database'
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- ============================================================================

-- Comentarios para prompts
COMMENT ON TABLE custom_prompts IS 'Prompts personalizados con soporte para formato estructurado (LangGraph)';
COMMENT ON TABLE prompt_versions IS 'Historial completo de cambios en prompts con versionado infinito';
COMMENT ON TABLE default_prompts IS 'Prompts por defecto con soporte estructurado para fallback multi-tenant';

COMMENT ON COLUMN custom_prompts.format IS 'Formato del prompt: simple (string) o structured (JSONB)';
COMMENT ON COLUMN custom_prompts.template IS 'Template legacy para backward compatibility';
COMMENT ON COLUMN custom_prompts.structured_template IS 'Template estructurado: {system, examples, placeholders, meta}';

COMMENT ON FUNCTION get_prompt_with_fallback IS 'Obtiene prompt con jerarquía de fallback: custom -> default empresa -> default genérico';
COMMENT ON FUNCTION repair_prompts_from_repository IS 'Repara prompts corruptos restaurando desde repositorio por empresa';

-- Comentarios para empresas
COMMENT ON TABLE companies IS 'Configuración principal de empresas - Source of truth para configuraciones multi-tenant';
COMMENT ON TABLE company_config_versions IS 'Historial completo de cambios en configuración con versionado infinito';
COMMENT ON TABLE company_templates IS 'Plantillas de configuración por tipo de negocio para facilitar setup';
COMMENT ON TABLE company_runtime_settings IS 'Configuración dinámica runtime que puede cambiar frecuentemente';

COMMENT ON FUNCTION get_company_config_with_fallback IS 'Obtiene configuración con fallback automático: PostgreSQL -> defaults';
COMMENT ON FUNCTION migrate_company_from_json IS 'Migra configuración desde JSON hacia PostgreSQL de forma segura';

-- ============================================================================
-- VERIFICACIÓN DEL SCHEMA
-- ============================================================================

-- Verificar que todas las tablas se crearon correctamente
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('custom_prompts', 'prompt_versions', 'default_prompts', 'companies', 'company_config_versions', 'company_templates', 'company_runtime_settings')
ORDER BY tablename;
