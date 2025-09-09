-- ============================================================================
-- POSTGRESQL SCHEMA MIGRATION - MULTI-TENANT PROMPTS SYSTEM
-- Migración de custom_prompts.json a PostgreSQL con fallbacks y versionado
-- ============================================================================

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLA PRINCIPAL DE PROMPTS PERSONALIZADOS
-- ============================================================================
CREATE TABLE custom_prompts (
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
    notes TEXT,
    
    -- Constraint único para un prompt activo por empresa/agente
    CONSTRAINT unique_active_prompt UNIQUE (company_id, agent_name)
    DEFERRABLE INITIALLY DEFERRED
);

-- ============================================================================
-- TABLA DE HISTORIAL Y VERSIONADO
-- ============================================================================
CREATE TABLE prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    prompt_id BIGINT REFERENCES custom_prompts(id) ON DELETE CASCADE,
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'REPAIR')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT,
    
    -- Índice único para version por prompt
    CONSTRAINT unique_prompt_version UNIQUE (prompt_id, version)
);

-- ============================================================================
-- TABLA DE PROMPTS POR DEFECTO DEL REPOSITORIO
-- ============================================================================
CREATE TABLE default_prompts (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    template TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_agent_name CHECK (agent_name IN ('router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent'))
);

-- ============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================================================

-- Índices principales para consultas frecuentes
CREATE INDEX idx_custom_prompts_company_agent ON custom_prompts(company_id, agent_name);
CREATE INDEX idx_custom_prompts_active ON custom_prompts(is_active) WHERE is_active = true;
CREATE INDEX idx_custom_prompts_modified_at ON custom_prompts(modified_at DESC);

-- Índices para versionado
CREATE INDEX idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
CREATE INDEX idx_prompt_versions_company_agent ON prompt_versions(company_id, agent_name);
CREATE INDEX idx_prompt_versions_created_at ON prompt_versions(created_at DESC);

-- Índices para prompts por defecto
CREATE INDEX idx_default_prompts_agent ON default_prompts(agent_name);
CREATE INDEX idx_default_prompts_category ON default_prompts(category);

-- ============================================================================
-- FUNCIÓN PARA TRIGGER DE VERSIONADO AUTOMÁTICO
-- ============================================================================
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

-- ============================================================================
-- TRIGGERS PARA VERSIONADO AUTOMÁTICO
-- ============================================================================
CREATE TRIGGER trigger_custom_prompts_versioning
    BEFORE INSERT OR UPDATE OR DELETE ON custom_prompts
    FOR EACH ROW
    EXECUTE FUNCTION create_prompt_version();

-- ============================================================================
-- FUNCIÓN PARA OBTENER PROMPT CON FALLBACK
-- ============================================================================
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
    
    -- 2. Fallback a prompt por defecto
    RETURN QUERY
    SELECT 
        dp.template,
        'default'::VARCHAR(50) as source,
        false as is_custom,
        1 as version,
        dp.updated_at as modified_at
    FROM default_prompts dp
    WHERE dp.agent_name = p_agent_name;
    
    -- Si no se encontró nada, retornar prompt hardcodeado
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            ('Prompt por defecto para ' || p_agent_name || '. Sistema en recuperación.')::TEXT as template,
            'hardcoded'::VARCHAR(50) as source,
            false as is_custom,
            0 as version,
            CURRENT_TIMESTAMP as modified_at;
    END IF;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCIÓN PARA REPARAR PROMPTS DESDE REPOSITORIO
-- ============================================================================
CREATE OR REPLACE FUNCTION repair_prompts_from_repository(
    p_company_id VARCHAR(100) DEFAULT NULL,
    p_agent_name VARCHAR(100) DEFAULT NULL,
    p_repair_user VARCHAR(100) DEFAULT 'system_repair'
) RETURNS TABLE (
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
        -- Verificar que existe en default_prompts
        IF EXISTS (SELECT 1 FROM default_prompts WHERE agent_name = p_agent_name) THEN
            -- Actualizar o insertar prompt personalizado
            INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
            SELECT 
                p_company_id, 
                dp.agent_name, 
                dp.template,
                p_repair_user,
                p_repair_user,
                'Repaired from repository'
            FROM default_prompts dp 
            WHERE dp.agent_name = p_agent_name
            ON CONFLICT (company_id, agent_name) 
            DO UPDATE SET 
                template = EXCLUDED.template,
                modified_by = p_repair_user,
                modified_at = CURRENT_TIMESTAMP,
                notes = 'Repaired from repository',
                is_active = true;
            
            RETURN QUERY SELECT p_agent_name, 'REPAIR'::VARCHAR(50), true, 'Agent repaired successfully'::TEXT;
        ELSE
            RETURN QUERY SELECT p_agent_name, 'ERROR'::VARCHAR(50), false, 'Agent not found in repository'::TEXT;
        END IF;
    ELSE
        -- Reparar todos los agentes
        FOR agent_record IN (SELECT dp.agent_name, dp.template FROM default_prompts dp) LOOP
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
                RETURN QUERY SELECT agent_record.agent_name, 'REPAIR'::VARCHAR(50), true, 'Bulk repair successful'::TEXT;
                
            EXCEPTION WHEN OTHERS THEN
                RETURN QUERY SELECT agent_record.agent_name, 'ERROR'::VARCHAR(50), false, SQLERRM;
            END;
        END LOOP;
    END IF;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- POBLAR PROMPTS POR DEFECTO
-- ============================================================================
INSERT INTO default_prompts (agent_name, template, description, category) VALUES
('router_agent', 
'Eres un asistente especializado en clasificar intenciones de usuarios. Analiza el mensaje y determina si es: VENTAS, SOPORTE, EMERGENCIA, AGENDAMIENTO, o DISPONIBILIDAD. Responde solo con la categoría en mayúsculas.',
'Clasificador de intenciones principal del sistema',
'routing'),

('sales_agent',
'Eres un especialista en ventas para servicios médicos y estéticos. Proporciona información comercial precisa, destacando beneficios y promoviendo la reserva de citas. Mantén un tono profesional y persuasivo.',
'Agente comercial especializado en conversión',
'commercial'),

('support_agent',
'Eres un asistente de soporte técnico amigable y eficiente. Ayuda a resolver dudas generales, problemas técnicos y proporciona información sobre servicios. Mantén un tono servicial y profesional.',
'Soporte general y atención al cliente',
'support'),

('emergency_agent',
'Eres un asistente para situaciones de emergencia médica. Proporciona información de primeros auxilios básicos, recomienda buscar atención médica inmediata cuando sea necesario, y ofrece números de emergencia. NUNCA des diagnósticos médicos.',
'Asistencia en emergencias médicas',
'emergency'),

('schedule_agent',
'Eres un asistente especializado en agendamiento de citas. Ayuda a los usuarios a programar, modificar o cancelar citas médicas. Proporciona información sobre disponibilidad y confirma los detalles de las citas.',
'Gestión de citas y programación',
'scheduling'),

('availability_agent',
'Eres un asistente que proporciona información sobre disponibilidad de servicios, horarios de atención, y disponibilidad de profesionales. Ofrece alternativas cuando no hay disponibilidad inmediata.',
'Consulta de disponibilidad y horarios',
'availability');

-- ============================================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- ============================================================================

COMMENT ON TABLE custom_prompts IS 'Almacena prompts personalizados por empresa y agente con versionado';
COMMENT ON TABLE prompt_versions IS 'Historial completo de cambios en prompts con versionado infinito';
COMMENT ON TABLE default_prompts IS 'Prompts por defecto del repositorio para fallback';

COMMENT ON FUNCTION get_prompt_with_fallback IS 'Obtiene prompt con jerarquía de fallback: custom -> default -> hardcoded';
COMMENT ON FUNCTION repair_prompts_from_repository IS 'Repara prompts corruptos restaurando desde repositorio';

-- ============================================================================
-- VERIFICACIÓN DEL SCHEMA
-- ============================================================================

-- Verificar que las tablas se crearon correctamente
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('custom_prompts', 'prompt_versions', 'default_prompts');

-- Verificar que los índices se crearon
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('custom_prompts', 'prompt_versions', 'default_prompts');

-- Verificar que las funciones se crearon
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines 
WHERE routine_name IN ('get_prompt_with_fallback', 'repair_prompts_from_repository', 'create_prompt_version');

-- Verificar datos por defecto
SELECT agent_name, LEFT(template, 100) as template_preview FROM default_prompts ORDER BY agent_name;
