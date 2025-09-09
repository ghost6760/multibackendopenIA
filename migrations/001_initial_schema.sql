-- ============================================================================
-- SCHEMA PARA GESTIÓN DE PROMPTS PERSONALIZADOS
-- Base de datos: PostgreSQL 14+
-- ============================================================================

-- Tabla principal para prompts personalizados
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
    
    -- Constraint único para evitar duplicados activos
    CONSTRAINT unique_active_prompt UNIQUE (company_id, agent_name, is_active) 
    WHERE is_active = true
);

-- Tabla para historial de versiones (auditoría)
CREATE TABLE prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    prompt_id BIGINT REFERENCES custom_prompts(id),
    company_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE', 'RESTORE'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

-- Tabla para prompts por defecto (fallback)
CREATE TABLE default_prompts (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    template TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Índice principal para búsquedas rápidas
CREATE INDEX idx_custom_prompts_company_agent 
ON custom_prompts(company_id, agent_name) 
WHERE is_active = true;

-- Índice para búsquedas por empresa
CREATE INDEX idx_custom_prompts_company 
ON custom_prompts(company_id) 
WHERE is_active = true;

-- Índice para auditoría
CREATE INDEX idx_prompt_versions_prompt_id 
ON prompt_versions(prompt_id);

-- Índice para búsquedas por fecha
CREATE INDEX idx_custom_prompts_modified_at 
ON custom_prompts(modified_at DESC);

-- ============================================================================
-- TRIGGERS PARA AUDITORÍA AUTOMÁTICA
-- ============================================================================

-- Función para actualizar modified_at automáticamente
CREATE OR REPLACE FUNCTION update_modified_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar modified_at en custom_prompts
CREATE TRIGGER update_custom_prompts_modified_at
    BEFORE UPDATE ON custom_prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at();

-- Función para crear versión automáticamente
CREATE OR REPLACE FUNCTION create_prompt_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo crear versión si el template cambió
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.template IS DISTINCT FROM NEW.template) THEN
        INSERT INTO prompt_versions (
            prompt_id, company_id, agent_name, template, version, 
            action, created_by, notes
        ) VALUES (
            NEW.id, NEW.company_id, NEW.agent_name, NEW.template, NEW.version,
            CASE TG_OP 
                WHEN 'INSERT' THEN 'CREATE'
                WHEN 'UPDATE' THEN 'UPDATE'
            END,
            NEW.modified_by,
            CASE TG_OP 
                WHEN 'INSERT' THEN 'Prompt creado'
                WHEN 'UPDATE' THEN 'Prompt actualizado'
            END
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para versiones automáticas
CREATE TRIGGER create_prompt_version_trigger
    AFTER INSERT OR UPDATE ON custom_prompts
    FOR EACH ROW
    EXECUTE FUNCTION create_prompt_version();

-- ============================================================================
-- DATOS INICIALES - PROMPTS POR DEFECTO
-- ============================================================================

INSERT INTO default_prompts (agent_name, template, description) VALUES
('router_agent', 
'Eres un clasificador de intenciones para {company_name}. 
Analiza la consulta del usuario y determina el tipo de agente más apropiado.

Tipos de agente disponibles:
- sales: Consultas sobre productos, precios, compras
- support: Problemas técnicos, quejas, ayuda
- emergency: Situaciones urgentes que requieren atención inmediata

Responde ÚNICAMENTE con el tipo de agente (sales/support/emergency).', 
'Prompt por defecto para Router Agent'),

('sales_agent', 
'Eres un agente de ventas profesional para {company_name}.
Especializado en medicina estética y tratamientos de belleza.

Tu objetivo es:
- Informar sobre productos y servicios
- Guiar hacia la compra
- Resolver dudas comerciales
- Agendar citas de consulta

Mantén un tono profesional, amigable y orientado a resultados.', 
'Prompt por defecto para Sales Agent'),

('support_agent', 
'Eres un especialista en atención al cliente para {company_name}.

Tu función es:
- Resolver consultas generales
- Facilitar navegación y uso de servicios
- Escalar problemas técnicos cuando sea necesario

Sé empático, profesional y orientado a la solución.', 
'Prompt por defecto para Support Agent'),

('emergency_agent', 
'Eres un agente de emergencias para {company_name}.

PROTOCOLO DE EMERGENCIA:
1. Evalúa la urgencia de la situación
2. Proporciona primeros auxilios básicos si es necesario
3. Recomienda contactar servicios de emergencia si la situación lo requiere
4. Mantén la calma y sé directo

En caso de emergencia médica real, recomienda contactar el 911 inmediatamente.', 
'Prompt por defecto para Emergency Agent');

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista para obtener prompts activos con fallback a default
CREATE VIEW active_prompts AS
SELECT 
    COALESCE(cp.company_id, 'default') as company_id,
    COALESCE(cp.agent_name, dp.agent_name) as agent_name,
    COALESCE(cp.template, dp.template) as template,
    CASE WHEN cp.id IS NOT NULL THEN true ELSE false END as is_custom,
    cp.version,
    cp.modified_at,
    cp.modified_by
FROM default_prompts dp
LEFT JOIN custom_prompts cp ON dp.agent_name = cp.agent_name 
    AND cp.is_active = true;

-- Vista para estadísticas de uso
CREATE VIEW prompt_stats AS
SELECT 
    company_id,
    COUNT(*) as total_custom_prompts,
    COUNT(CASE WHEN created_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_changes,
    MAX(modified_at) as last_modification
FROM custom_prompts 
WHERE is_active = true
GROUP BY company_id;
