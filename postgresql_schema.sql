-- ============================================================================
-- POSTGRESQL SCHEMA COMBINADO - MULTI-TENANT SYSTEM
-- Combina:
-- 1. Sistema de Prompts Configurables (ORIGINAL)
-- 2. Sistema de Configuración de Empresas (ENTERPRISE)
-- Compatible con arquitectura multi-tenant existente
-- ============================================================================

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SECCIÓN 1: SISTEMA DE PROMPTS CONFIGURABLES (ORIGINAL)
-- ============================================================================

-- TABLA PRINCIPAL DE PROMPTS PERSONALIZADOS
CREATE TABLE IF NOT EXISTS custom_prompts (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    modified_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

-- TABLA DE HISTORIAL Y VERSIONADO DE PROMPTS
CREATE TABLE IF NOT EXISTS prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    prompt_id BIGINT,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'REPAIR')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

-- TABLA DE PROMPTS POR DEFECTO DEL REPOSITORIO (MULTI-TENANT)
CREATE TABLE IF NOT EXISTS default_prompts (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SECCIÓN 2: CONFIGURACIÓN DE EMPRESAS (ENTERPRISE)
-- ============================================================================

-- TABLA PRINCIPAL DE CONFIGURACIÓN DE EMPRESAS
CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) UNIQUE NOT NULL,           -- ID único de empresa
    company_name VARCHAR(200) NOT NULL,                -- Nombre de empresa
    business_type VARCHAR(100) DEFAULT 'general',      -- Tipo de negocio
    services TEXT NOT NULL,                            -- Servicios que ofrece
    
    -- Configuración Redis/Vector Store
    redis_prefix VARCHAR(150) NOT NULL,                -- Prefijo Redis único
    vectorstore_index VARCHAR(150) NOT NULL,           -- Índice vectorstore
    
    -- Configuración de Agentes
    sales_agent_name VARCHAR(200) NOT NULL,            -- Nombre del agente de ventas
    model_name VARCHAR(100) DEFAULT 'gpt-4o-mini',     -- Modelo OpenAI
    max_tokens INTEGER DEFAULT 1500,                   -- Tokens máximos
    temperature DECIMAL(3,2) DEFAULT 0.7,              -- Temperatura del modelo
    max_context_messages INTEGER DEFAULT 10,           -- Contexto máximo
    
    -- Configuración de Servicios Externos
    schedule_service_url VARCHAR(300),                 -- URL servicio agendamiento
    schedule_integration_type VARCHAR(50) DEFAULT 'basic', -- Tipo integración
    chatwoot_account_id VARCHAR(50),                   -- ID cuenta Chatwoot
    
    -- Configuración de Negocio
    treatment_durations JSONB,                         -- Duraciones tratamientos
    schedule_keywords TEXT[],                          -- Keywords agendamiento
    emergency_keywords TEXT[],                         -- Keywords emergencia
    sales_keywords TEXT[],                             -- Keywords ventas
    required_booking_fields TEXT[],                    -- Campos requeridos reserva
    
    -- Configuración de Localización
    timezone VARCHAR(50) DEFAULT 'America/Bogota',     -- Zona horaria
    language VARCHAR(10) DEFAULT 'es',                 -- Idioma principal
    currency VARCHAR(10) DEFAULT 'COP',                -- Moneda
    
    -- Estado y Metadatos
    is_active BOOLEAN DEFAULT true,                    -- Empresa activa
    subscription_tier VARCHAR(50) DEFAULT 'basic',     -- Tier de suscripción
    max_documents INTEGER DEFAULT 1000,                -- Límite documentos
    max_conversations INTEGER DEFAULT 10000,           -- Límite conversaciones
    
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
    config_snapshot JSONB NOT NULL,                   -- Todo el state en JSON
    changes_summary TEXT,                              -- Resumen de cambios
    
    -- Campos específicos que cambiaron (para facilitar queries)
    changed_fields TEXT[],                             -- Lista de campos modificados
    previous_values JSONB,                             -- Valores anteriores
    new_values JSONB,                                  -- Valores nuevos
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT,
    
    -- Metadatos de cambio
    change_reason VARCHAR(200),                        -- Razón del cambio
    change_source VARCHAR(100) DEFAULT 'admin_panel',  -- Origen del cambio
    ip_address INET,                                   -- IP quien hizo el cambio
    user_agent TEXT                                    -- User agent del cambio
);

-- TABLA DE CONFIGURACIÓN POR DEFECTO (PLANTILLAS)
CREATE TABLE IF NOT EXISTS company_templates (
    id BIGSERIAL PRIMARY KEY,
    template_name VARCHAR(100) UNIQUE NOT NULL,        -- Nombre plantilla
    business_type VARCHAR(100) NOT NULL,               -- Tipo de negocio
    display_name VARCHAR(200) NOT NULL,                -- Nombre para mostrar
    description TEXT,                                  -- Descripción plantilla
    
    -- Configuración por defecto
    default_config JSONB NOT NULL,                     -- Configuración base
    required_fields TEXT[] NOT NULL,                   -- Campos obligatorios
    optional_fields TEXT[],                            -- Campos opcionales
    
    -- Metadatos
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin'
);

-- TABLA DE CONFIGURACIÓN DINÁMICA (RUNTIME SETTINGS)
CREATE TABLE IF NOT EXISTS company_runtime_settings (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) REFERENCES companies(company_id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,                -- Clave del setting
    setting_value TEXT,                               -- Valor como texto
    setting_type VARCHAR(50) DEFAULT 'string',        -- Tipo: string, number, boolean, json
    setting_category VARCHAR(100) DEFAULT 'general',  -- Categoría del setting
    
    -- Metadatos
    is_encrypted BOOLEAN DEFAULT false,               -- Si está encriptado
    last_accessed TIMESTAMP WITH TIME ZONE,          -- Último acceso
    access_count INTEGER DEFAULT 0,                  -- Contador de accesos
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    modified_by VARCHAR(100) DEFAULT 'admin',
    
    UNIQUE(company_id, setting_key)
);

-- ============================================================================
-- CONSTRAINTS Y HELPER FUNCTIONS
-- ============================================================================

-- Función helper para crear constraints solo si no existen
CREATE OR REPLACE FUNCTION create_constraint_if_not_exists(
    p_table_name TEXT,
    p_constraint_name TEXT,
    p_constraint_definition TEXT
) RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = p_table_name AND constraint_name = p_constraint_name
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I %s', 
                      p_table_name, p_constraint_name, p_constraint_definition);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- CONSTRAINTS PARA PROMPTS (ORIGINAL)
SELECT create_constraint_if_not_exists(
    'custom_prompts', 
    'unique_active_prompt', 
    'UNIQUE (company_id, agent_name)'
);

SELECT create_constraint_if_not_exists(
    'default_prompts', 
    'unique_company_agent', 
    'UNIQUE (company_id, agent_name)'
);

SELECT create_constraint_if_not_exists(
    'prompt_versions', 
    'unique_prompt_version', 
    'UNIQUE (prompt_id, version)'
);

-- Foreign key constraint para prompt_versions
SELECT create_constraint_if_not_exists(
    'prompt_versions', 
    'fk_prompt_versions_prompt_id', 
    'FOREIGN KEY (prompt_id) REFERENCES custom_prompts(id) ON DELETE CASCADE'
);

-- Check constraints para validaciones de prompts
SELECT create_constraint_if_not_exists(
    'default_prompts', 
    'valid_agent_name', 
    'CHECK (agent_name IN (''router_agent'', ''sales_agent'', ''support_agent'', ''emergency_agent'', ''schedule_agent'', ''availability_agent''))'
);

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- ÍNDICES PARA PROMPTS (ORIGINAL)
CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent ON custom_prompts(company_id, agent_name);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_active ON custom_prompts(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_custom_prompts_modified_at ON custom_prompts(modified_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_company_agent ON prompt_versions(company_id, agent_name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_created_at ON prompt_versions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_default_prompts_company_agent ON default_prompts(company_id, agent_name);
CREATE INDEX IF NOT EXISTS idx_default_prompts_agent ON default_prompts(agent_name);
CREATE INDEX IF NOT EXISTS idx_default_prompts_category ON default_prompts(category);

-- ÍNDICES PARA CONFIGURACIÓN DE EMPRESAS
CREATE INDEX IF NOT EXISTS idx_companies_company_id ON companies(company_id);
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_companies_business_type ON companies(business_type);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at);

CREATE INDEX IF NOT EXISTS idx_config_versions_company_id ON company_config_versions(company_id);
CREATE INDEX IF NOT EXISTS idx_config_versions_version ON company_config_versions(version);
CREATE INDEX IF NOT EXISTS idx_config_versions_action ON company_config_versions(action);
CREATE INDEX IF NOT EXISTS idx_config_versions_created_at ON company_config_versions(created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_settings_company_id ON company_runtime_settings(company_id);
CREATE INDEX IF NOT EXISTS idx_runtime_settings_key ON company_runtime_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_runtime_settings_category ON company_runtime_settings(setting_category);

-- ============================================================================
-- FUNCIONES Y TRIGGERS PARA PROMPTS (ORIGINAL - SIN CAMBIOS)
-- ============================================================================

-- FUNCIÓN PARA TRIGGER DE VERSIONADO AUTOMÁTICO DE PROMPTS
CREATE OR REPLACE FUNCTION create_prompt_version()
RETURNS TRIGGER AS $$
DECLARE
    next_version INTEGER;
    action_type VARCHAR(50);
BEGIN
    -- Determinar el tipo de acción
    IF TG_OP = 'INSERT' THEN
        action_type := 'CREATE';
        next_version := 1;
    ELSIF TG_OP = 'UPDATE' THEN
        action_type := 'UPDATE';
        -- Obtener la siguiente versión
        SELECT COALESCE(MAX(version), 0) + 1 
        INTO next_version 
        FROM prompt_versions 
        WHERE prompt_id = NEW.id;
        
        -- Actualizar el número de versión en la tabla principal
        NEW.version := next_version;
        NEW.modified_at := CURRENT_TIMESTAMP;
    ELSIF TG_OP = 'DELETE' THEN
        action_type := 'DELETE';
        -- Para DELETE, usar OLD en lugar de NEW
        SELECT COALESCE(MAX(version), 0) + 1 
        INTO next_version 
        FROM prompt_versions 
        WHERE prompt_id = OLD.id;
        
        -- Insertar registro de eliminación
        INSERT INTO prompt_versions (
            prompt_id, company_id, agent_name, template, 
            version, action, created_by, notes
        ) VALUES (
            OLD.id, OLD.company_id, OLD.agent_name, OLD.template,
            next_version, action_type, OLD.modified_by, 'Prompt deleted'
        );
        
        RETURN OLD;
    END IF;
    
    -- Insertar en historial para INSERT y UPDATE
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        INSERT INTO prompt_versions (
            prompt_id, company_id, agent_name, template, 
            version, action, created_by, notes
        ) VALUES (
            NEW.id, NEW.company_id, NEW.agent_name, NEW.template,
            next_version, action_type, NEW.modified_by, 
            CASE 
                WHEN action_type = 'CREATE' THEN 'Initial prompt creation'
                ELSE 'Prompt updated'
            END
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- FUNCIÓN PARA OBTENER PROMPT CON FALLBACK (ORIGINAL - SIN CAMBIOS)
CREATE OR REPLACE FUNCTION get_prompt_with_fallback(
    p_company_id VARCHAR(100),
    p_agent_name VARCHAR(100)
) RETURNS TABLE (
    template TEXT,
    source VARCHAR(50),
    is_custom BOOLEAN,
    version INTEGER,
    modified_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- 1. Intentar obtener prompt personalizado activo
    RETURN QUERY
    SELECT 
        cp.template,
        'custom'::VARCHAR(50) as source,
        true as is_custom,
        cp.version,
        cp.modified_at
    FROM custom_prompts cp
    WHERE cp.company_id = p_company_id 
      AND cp.agent_name = p_agent_name 
      AND cp.is_active = true;
    
    -- Si se encontró un prompt personalizado, retornar
    IF FOUND THEN
        RETURN;
    END IF;
    
    -- 2. Fallback a prompt por defecto de la empresa
    RETURN QUERY
    SELECT 
        dp.template,
        'default'::VARCHAR(50) as source,
        false as is_custom,
        1 as version,
        dp.updated_at as modified_at
    FROM default_prompts dp
    WHERE dp.company_id = p_company_id 
      AND dp.agent_name = p_agent_name;
    
    -- 3. Si no hay prompt específico de empresa, usar prompt genérico
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            dp.template,
            'default_generic'::VARCHAR(50) as source,
            false as is_custom,
            1 as version,
            dp.updated_at as modified_at
        FROM default_prompts dp
        WHERE dp.company_id = 'benova'  -- Empresa base como fallback
          AND dp.agent_name = p_agent_name;
    END IF;
    
    -- 4. Si aún no se encontró nada, retornar prompt hardcodeado
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            ('Prompt por defecto para ' || p_agent_name || ' de ' || p_company_id || '. Sistema en recuperación.')::TEXT as template,
            'hardcoded'::VARCHAR(50) as source,
            false as is_custom,
            0 as version,
            CURRENT_TIMESTAMP as modified_at;
    END IF;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- FUNCIÓN PARA REPARAR PROMPTS DESDE REPOSITORIO (ORIGINAL - SIN CAMBIOS)
CREATE OR REPLACE FUNCTION repair_prompts_from_repository(
    p_company_id VARCHAR(100),
    p_agent_name VARCHAR(100) DEFAULT NULL,
    p_repair_user VARCHAR(100) DEFAULT 'system_repair'
) RETURNS TABLE (
    company_id VARCHAR(100),
    agent_name VARCHAR(100),
    action VARCHAR(50),
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    agent_record RECORD;
    repair_count INTEGER := 0;
BEGIN
    -- Si se especifica un agente específico
    IF p_agent_name IS NOT NULL THEN
        -- Verificar que existe en default_prompts para esta empresa
        IF EXISTS (SELECT 1 FROM default_prompts WHERE company_id = p_company_id AND agent_name = p_agent_name) THEN
            -- Actualizar o insertar prompt personalizado
            INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
            SELECT 
                dp.company_id, 
                dp.agent_name, 
                dp.template,
                p_repair_user,
                p_repair_user,
                'Repaired from repository'
            FROM default_prompts dp 
            WHERE dp.company_id = p_company_id AND dp.agent_name = p_agent_name
            ON CONFLICT (company_id, agent_name) 
            DO UPDATE SET 
                template = EXCLUDED.template,
                modified_by = p_repair_user,
                modified_at = CURRENT_TIMESTAMP,
                notes = 'Repaired from repository',
                is_active = true;
            
            RETURN QUERY SELECT p_company_id, p_agent_name, 'REPAIR'::VARCHAR(50), true, 'Agent repaired successfully'::TEXT;
        ELSE
            RETURN QUERY SELECT p_company_id, p_agent_name, 'ERROR'::VARCHAR(50), false, 'Agent not found in repository'::TEXT;
        END IF;
    ELSE
        -- Reparar todos los agentes de la empresa
        FOR agent_record IN (SELECT dp.agent_name, dp.template FROM default_prompts dp WHERE dp.company_id = p_company_id) LOOP
            BEGIN
                INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                VALUES (
                    p_company_id, 
                    agent_record.agent_name, 
                    agent_record.template,
                    p_repair_user,
                    p_repair_user,
                    'Repaired from repository - bulk repair'
                )
                ON CONFLICT (company_id, agent_name) 
                DO UPDATE SET 
                    template = EXCLUDED.template,
                    modified_by = p_repair_user,
                    modified_at = CURRENT_TIMESTAMP,
                    notes = 'Repaired from repository - bulk repair',
                    is_active = true;
                
                repair_count := repair_count + 1;
                RETURN QUERY SELECT p_company_id, agent_record.agent_name, 'REPAIR'::VARCHAR(50), true, 'Bulk repair successful'::TEXT;
                
            EXCEPTION WHEN OTHERS THEN
                RETURN QUERY SELECT p_company_id, agent_record.agent_name, 'ERROR'::VARCHAR(50), false, SQLERRM;
            END;
        END LOOP;
    END IF;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCIONES Y TRIGGERS PARA CONFIGURACIÓN DE EMPRESAS
-- ============================================================================

-- FUNCIÓN PARA TRIGGER DE VERSIONADO AUTOMÁTICO DE CONFIGURACIÓN DE EMPRESAS
CREATE OR REPLACE FUNCTION create_company_config_version()
RETURNS TRIGGER AS $$
DECLARE
    next_version INTEGER;
    config_json JSONB;
    changed_fields_array TEXT[];
    previous_vals JSONB;
    new_vals JSONB;
BEGIN
    -- Obtener siguiente versión
    SELECT COALESCE(MAX(version), 0) + 1 
    INTO next_version 
    FROM company_config_versions 
    WHERE company_id = COALESCE(NEW.company_id, OLD.company_id);
    
    -- Preparar datos según operación
    IF TG_OP = 'DELETE' THEN
        config_json := to_jsonb(OLD);
        
        INSERT INTO company_config_versions (
            company_pk, company_id, version, action, config_snapshot,
            changes_summary, created_by, notes
        ) VALUES (
            OLD.id, OLD.company_id, next_version, 'DELETE', config_json,
            'Company configuration deleted', OLD.modified_by, 'Company deleted'
        );
        
        RETURN OLD;
        
    ELSIF TG_OP = 'INSERT' THEN
        config_json := to_jsonb(NEW);
        
        INSERT INTO company_config_versions (
            company_pk, company_id, version, action, config_snapshot,
            changes_summary, created_by, notes
        ) VALUES (
            NEW.id, NEW.company_id, next_version, 'CREATE', config_json,
            'Initial company configuration created', NEW.created_by, 'Company created'
        );
        
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Detectar campos que cambiaron
        changed_fields_array := ARRAY[]::TEXT[];
        previous_vals := '{}'::JSONB;
        new_vals := '{}'::JSONB;
        
        -- Comparar campos uno por uno
        IF OLD.company_name != NEW.company_name THEN
            changed_fields_array := array_append(changed_fields_array, 'company_name');
            previous_vals := previous_vals || jsonb_build_object('company_name', OLD.company_name);
            new_vals := new_vals || jsonb_build_object('company_name', NEW.company_name);
        END IF;
        
        IF OLD.services != NEW.services THEN
            changed_fields_array := array_append(changed_fields_array, 'services');
            previous_vals := previous_vals || jsonb_build_object('services', OLD.services);
            new_vals := new_vals || jsonb_build_object('services', NEW.services);
        END IF;
        
        IF OLD.sales_agent_name != NEW.sales_agent_name THEN
            changed_fields_array := array_append(changed_fields_array, 'sales_agent_name');
            previous_vals := previous_vals || jsonb_build_object('sales_agent_name', OLD.sales_agent_name);
            new_vals := new_vals || jsonb_build_object('sales_agent_name', NEW.sales_agent_name);
        END IF;
        
        -- Solo crear versión si hay cambios reales
        IF array_length(changed_fields_array, 1) > 0 THEN
            config_json := to_jsonb(NEW);
            
            INSERT INTO company_config_versions (
                company_pk, company_id, version, action, config_snapshot,
                changed_fields, previous_values, new_values,
                changes_summary, created_by, notes
            ) VALUES (
                NEW.id, NEW.company_id, next_version, 'UPDATE', config_json,
                changed_fields_array, previous_vals, new_vals,
                'Configuration updated: ' || array_to_string(changed_fields_array, ', '),
                NEW.modified_by, 'Configuration modified'
            );
        END IF;
        
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- FUNCIÓN PARA OBTENER CONFIGURACIÓN DE EMPRESA CON FALLBACK
CREATE OR REPLACE FUNCTION get_company_config_with_fallback(
    p_company_id VARCHAR(100)
) RETURNS TABLE (
    config JSONB,
    source VARCHAR(50),
    is_from_db BOOLEAN,
    version INTEGER,
    last_modified TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- 1. Intentar obtener de PostgreSQL
    RETURN QUERY
    SELECT 
        to_jsonb(c.*) as config,
        'postgresql'::VARCHAR(50) as source,
        true as is_from_db,
        c.version,
        c.modified_at as last_modified
    FROM companies c
    WHERE c.company_id = p_company_id 
      AND c.is_active = true;
    
    -- Si se encontró en DB, retornar
    IF FOUND THEN
        RETURN;
    END IF;
    
    -- 2. Si no se encuentra, indicar que debe usar fallback
    RETURN QUERY
    SELECT 
        '{}'::JSONB as config,
        'fallback_needed'::VARCHAR(50) as source,
        false as is_from_db,
        0 as version,
        NULL::TIMESTAMP WITH TIME ZONE as last_modified;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- FUNCIÓN PARA MIGRAR EMPRESA DESDE JSON
CREATE OR REPLACE FUNCTION migrate_company_from_json(
    p_company_id VARCHAR(100),
    p_json_config JSONB,
    p_created_by VARCHAR(100) DEFAULT 'migration'
) RETURNS BOOLEAN AS $$
DECLARE
    config_record RECORD;
BEGIN
    -- Extraer valores del JSON con defaults seguros
    SELECT 
        p_company_id as company_id,
        COALESCE(p_json_config->>'company_name', p_company_id) as company_name,
        COALESCE(p_json_config->>'business_type', 'general') as business_type,
        COALESCE(p_json_config->>'services', 'servicios generales') as services,
        COALESCE(p_json_config->>'redis_prefix', p_company_id || ':') as redis_prefix,
        COALESCE(p_json_config->>'vectorstore_index', p_company_id || '_documents') as vectorstore_index,
        COALESCE(p_json_config->>'sales_agent_name', 'Asistente de ' || COALESCE(p_json_config->>'company_name', p_company_id)) as sales_agent_name,
        COALESCE(p_json_config->>'model_name', 'gpt-4o-mini') as model_name,
        COALESCE((p_json_config->>'max_tokens')::INTEGER, 1500) as max_tokens,
        COALESCE((p_json_config->>'temperature')::DECIMAL, 0.7) as temperature,
        COALESCE(p_json_config->>'schedule_service_url', 'http://127.0.0.1:4040') as schedule_service_url
    INTO config_record;
    
    -- Insertar en tabla companies
    INSERT INTO companies (
        company_id, company_name, business_type, services,
        redis_prefix, vectorstore_index, sales_agent_name,
        model_name, max_tokens, temperature, schedule_service_url,
        created_by, modified_by, notes
    ) VALUES (
        config_record.company_id, config_record.company_name, config_record.business_type, config_record.services,
        config_record.redis_prefix, config_record.vectorstore_index, config_record.sales_agent_name,
        config_record.model_name, config_record.max_tokens, config_record.temperature, config_record.schedule_service_url,
        p_created_by, p_created_by, 'Migrated from JSON configuration'
    ) ON CONFLICT (company_id) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        services = EXCLUDED.services,
        modified_at = CURRENT_TIMESTAMP,
        modified_by = p_created_by,
        notes = 'Updated from JSON migration';
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS PARA VERSIONADO AUTOMÁTICO
-- ============================================================================

-- TRIGGER PARA PROMPTS (ORIGINAL)
DROP TRIGGER IF EXISTS trigger_custom_prompts_versioning ON custom_prompts;
CREATE TRIGGER trigger_custom_prompts_versioning
    BEFORE INSERT OR UPDATE OR DELETE ON custom_prompts
    FOR EACH ROW
    EXECUTE FUNCTION create_prompt_version();

-- TRIGGER PARA CONFIGURACIÓN DE EMPRESAS
DROP TRIGGER IF EXISTS trigger_company_config_versioning ON companies;
CREATE TRIGGER trigger_company_config_versioning
    AFTER INSERT OR UPDATE OR DELETE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION create_company_config_version();

-- ============================================================================
-- POBLAR DATOS POR DEFECTO
-- ============================================================================

-- PROMPTS POR DEFECTO PARA TODAS LAS EMPRESAS (ORIGINAL)
WITH base_templates AS (
    SELECT 'router_agent' as agent_name, 
           'Eres un asistente especializado en clasificar intenciones de usuarios. Analiza el mensaje y determina si es: VENTAS, SOPORTE, EMERGENCIA, AGENDAMIENTO, o DISPONIBILIDAD. Responde solo con la categoría en mayúsculas.' as template,
           'Clasificador de intenciones principal del sistema' as description,
           'routing' as category
    UNION ALL
    SELECT 'sales_agent',
           'Eres un especialista en ventas para servicios médicos y estéticos. Proporciona información comercial precisa, destacando beneficios y promoviendo la reserva de citas. Mantén un tono profesional y persuasivo.',
           'Agente comercial especializado en conversión',
           'commercial'
    UNION ALL
    SELECT 'support_agent',
           'Eres un asistente de soporte técnico amigable y eficiente. Ayuda a resolver dudas generales, problemas técnicos y proporciona información sobre servicios. Mantén un tono servicial y profesional.',
           'Soporte general y atención al cliente',
           'support'
    UNION ALL
    SELECT 'emergency_agent',
           'Eres un asistente para situaciones de emergencia médica. Proporciona información de primeros auxilios básicos, recomienda buscar atención médica inmediata cuando sea necesario, y ofrece números de emergencia. NUNCA des diagnósticos médicos.',
           'Asistencia en emergencias médicas',
           'emergency'
    UNION ALL
    SELECT 'schedule_agent',
           'Eres un asistente especializado en agendamiento de citas. Ayuda a los usuarios a programar, modificar o cancelar citas médicas. Proporciona información sobre disponibilidad y confirma los detalles de las citas.',
           'Gestión de citas y programación',
           'scheduling'
    UNION ALL
    SELECT 'availability_agent',
           'Eres un asistente que proporciona información sobre disponibilidad de servicios, horarios de atención, y disponibilidad de profesionales. Ofrece alternativas cuando no hay disponibilidad inmediata.',
           'Consulta de disponibilidad y horarios',
           'availability'
),
companies_for_prompts AS (
    SELECT unnest(ARRAY['benova', 'spa_wellness', 'medispa', 'dental_clinic']) as company_id
)
INSERT INTO default_prompts (company_id, agent_name, template, description, category)
SELECT 
    c.company_id,
    bt.agent_name,
    bt.template,
    bt.description,
    bt.category
FROM companies_for_prompts c
CROSS JOIN base_templates bt
ON CONFLICT (company_id, agent_name) DO UPDATE SET
    template = EXCLUDED.template,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    updated_at = CURRENT_TIMESTAMP;

-- PLANTILLAS DE CONFIGURACIÓN POR DEFECTO
INSERT INTO company_templates (template_name, business_type, display_name, description, default_config, required_fields) VALUES
('medical_clinic', 'healthcare', 'Clínica Médica', 'Plantilla para clínicas médicas generales', 
 '{"business_type": "healthcare", "timezone": "America/Bogota", "language": "es", "currency": "COP", "treatment_durations": {"consulta_general": 30, "procedimiento_basico": 60}, "emergency_keywords": ["dolor", "sangrado", "emergencia"], "schedule_keywords": ["agendar", "cita", "reservar"]}'::JSONB,
 ARRAY['company_name', 'services', 'sales_agent_name']),
 
('dental_clinic', 'healthcare', 'Clínica Dental', 'Plantilla para clínicas dentales',
 '{"business_type": "healthcare", "timezone": "America/Bogota", "language": "es", "currency": "COP", "treatment_durations": {"consulta_dental": 45, "implante": 120, "limpieza": 60}, "emergency_keywords": ["dolor_dental", "sangrado_encia", "emergencia_dental"], "schedule_keywords": ["agendar", "cita", "reservar"]}'::JSONB,
 ARRAY['company_name', 'services', 'sales_agent_name']),
 
('beauty_spa', 'beauty', 'Spa de Belleza', 'Plantilla para spas y centros de belleza',
 '{"business_type": "beauty", "timezone": "America/Bogota", "language": "es", "currency": "COP", "treatment_durations": {"facial": 90, "masaje": 60, "tratamiento_corporal": 120}, "sales_keywords": ["precio", "promocion", "tratamiento"], "schedule_keywords": ["agendar", "reservar", "programar"]}'::JSONB,
 ARRAY['company_name', 'services', 'sales_agent_name'])
ON CONFLICT (template_name) DO NOTHING;

-- ============================================================================
-- LIMPIEZA DE FUNCIONES HELPER
-- ============================================================================
DROP FUNCTION IF EXISTS create_constraint_if_not_exists(TEXT, TEXT, TEXT);

-- ============================================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- ============================================================================

-- Comentarios para prompts (original)
COMMENT ON TABLE custom_prompts IS 'Almacena prompts personalizados por empresa y agente con versionado';
COMMENT ON TABLE prompt_versions IS 'Historial completo de cambios en prompts con versionado infinito';
COMMENT ON TABLE default_prompts IS 'Prompts por defecto del repositorio para fallback multi-tenant';

COMMENT ON FUNCTION get_prompt_with_fallback IS 'Obtiene prompt con jerarquía de fallback: custom -> default empresa -> default genérico -> hardcoded';
COMMENT ON FUNCTION repair_prompts_from_repository IS 'Repara prompts corruptos restaurando desde repositorio por empresa';
COMMENT ON FUNCTION create_prompt_version IS 'Trigger function para versionado automático de prompts';

-- Comentarios para configuración de empresas
COMMENT ON TABLE companies IS 'Configuración principal de empresas - Source of truth para configuraciones multi-tenant';
COMMENT ON TABLE company_config_versions IS 'Historial completo de cambios en configuración con versionado infinito';
COMMENT ON TABLE company_templates IS 'Plantillas de configuración por tipo de negocio para facilitar setup';
COMMENT ON TABLE company_runtime_settings IS 'Configuración dinámica runtime que puede cambiar frecuentemente';

COMMENT ON FUNCTION get_company_config_with_fallback IS 'Obtiene configuración con fallback automático: PostgreSQL -> JSON -> defaults';
COMMENT ON FUNCTION migrate_company_from_json IS 'Migra configuración desde JSON hacia PostgreSQL de forma segura';
COMMENT ON FUNCTION create_company_config_version IS 'Trigger function para versionado automático de configuración de empresas';

-- ============================================================================
-- VERIFICACIÓN DEL SCHEMA COMBINADO
-- ============================================================================

-- Verificar que todas las tablas se crearon correctamente
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('custom_prompts', 'prompt_versions', 'default_prompts', 'companies', 'company_config_versions', 'company_templates', 'company_runtime_settings')
ORDER BY tablename;

-- Verificar que todos los constraints se crearon
SELECT 
    constraint_name,
    table_name,
    constraint_type
FROM information_schema.table_constraints 
WHERE table_name IN ('custom_prompts', 'prompt_versions', 'default_prompts', 'companies', 'company_config_versions', 'company_templates', 'company_runtime_settings')
ORDER BY table_name, constraint_name;

-- Verificar que todos los índices se crearon
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('custom_prompts', 'prompt_versions', 'default_prompts', 'companies', 'company_config_versions', 'company_templates', 'company_runtime_settings')
ORDER BY tablename, indexname;

-- Verificar que todas las funciones se crearon
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines 
WHERE routine_name IN ('get_prompt_with_fallback', 'repair_prompts_from_repository', 'create_prompt_version', 'get_company_config_with_fallback', 'migrate_company_from_json', 'create_company_config_version')
ORDER BY routine_name;

-- Verificar datos por defecto poblados
SELECT 
    'Prompts' as data_type,
    company_id, 
    agent_name, 
    LEFT(template, 50) as content_preview,
    category
FROM default_prompts 
ORDER BY company_id, agent_name

UNION ALL

SELECT 
    'Templates' as data_type,
    template_name as company_id,
    business_type as agent_name,
    LEFT(display_name, 50) as content_preview,
    'template' as category
FROM company_templates 
ORDER BY template_name;
