-- ============================================================================
-- WORKFLOWS SYSTEM - INCREMENTAL SCHEMA
-- Compatible con postgresql_schema.sql existente
-- ============================================================================

-- Verificar prerequisitos
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'companies') THEN
        RAISE EXCEPTION 'Base schema not found. Run postgresql_schema.sql first';
    END IF;
    RAISE NOTICE '✅ Base schema found - proceeding with workflows tables';
END $$;

-- ============================================================================
-- TABLAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflows (
    id BIGSERIAL PRIMARY KEY,
    workflow_id VARCHAR(150) UNIQUE NOT NULL,
    company_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    workflow_data JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    enabled BOOLEAN DEFAULT true,
    tags TEXT[],
    triggers JSONB DEFAULT '[]'::JSONB,
    variables JSONB DEFAULT '{}'::JSONB,
    start_node_id VARCHAR(100),
    total_nodes INTEGER DEFAULT 0,
    total_edges INTEGER DEFAULT 0,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    modified_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS workflow_versions (
    id BIGSERIAL PRIMARY KEY,
    workflow_pk BIGINT REFERENCES workflows(id) ON DELETE CASCADE,
    workflow_id VARCHAR(150) NOT NULL,
    version INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'ENABLE', 'DISABLE', 'CLONE')),
    workflow_snapshot JSONB NOT NULL,
    changes_summary TEXT,
    changed_fields TEXT[],
    previous_values JSONB,
    new_values JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT,
    change_reason VARCHAR(200),
    change_source VARCHAR(100) DEFAULT 'api',
    ip_address INET,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS workflow_executions (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(150) UNIQUE NOT NULL,
    workflow_id VARCHAR(150) NOT NULL,
    company_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled', 'timeout')),
    context JSONB DEFAULT '{}'::JSONB,
    execution_history JSONB DEFAULT '[]'::JSONB,
    final_output JSONB,
    errors JSONB DEFAULT '[]'::JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms BIGINT,
    triggered_by VARCHAR(100),
    trigger_type VARCHAR(50),
    trigger_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_templates (
    id BIGSERIAL PRIMARY KEY,
    template_id VARCHAR(150) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100) DEFAULT 'general',
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT false,
    business_types TEXT[],
    required_tools TEXT[],
    required_agents TEXT[],
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'admin'
);

CREATE TABLE IF NOT EXISTS workflow_nodes (
    id BIGSERIAL PRIMARY KEY,
    workflow_id VARCHAR(150) NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    node_name VARCHAR(200) NOT NULL,
    node_config JSONB DEFAULT '{}'::JSONB,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_duration_ms BIGINT,
    UNIQUE(workflow_id, node_id)
);

-- ============================================================================
-- CONSTRAINTS (SAFE METHOD)
-- ============================================================================

-- Función helper para constraints seguros
CREATE OR REPLACE FUNCTION add_workflow_constraint_safe(
    p_table TEXT,
    p_constraint TEXT,
    p_definition TEXT
) RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = p_table AND constraint_name = p_constraint
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I %s', p_table, p_constraint, p_definition);
        RAISE NOTICE 'Added constraint: %', p_constraint;
    ELSE
        RAISE NOTICE 'Constraint already exists: %', p_constraint;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Aplicar constraints
SELECT add_workflow_constraint_safe('workflows', 'unique_workflow_per_company', 'UNIQUE (company_id, name)');
SELECT add_workflow_constraint_safe('workflow_versions', 'unique_workflow_version', 'UNIQUE (workflow_id, version)');

-- Limpiar función helper
DROP FUNCTION IF EXISTS add_workflow_constraint_safe(TEXT, TEXT, TEXT);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_workflows_company_id ON workflows(company_id);
CREATE INDEX IF NOT EXISTS idx_workflows_enabled ON workflows(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_workflows_tags ON workflows USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_executions_company_id ON workflow_executions(company_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_versions_workflow_id ON workflow_versions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_templates_category ON workflow_templates(category);
CREATE INDEX IF NOT EXISTS idx_nodes_workflow_id ON workflow_nodes(workflow_id);

-- ============================================================================
-- FUNCIONES Y TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION create_workflow_version()
RETURNS TRIGGER AS $$
DECLARE
    next_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version), 0) + 1 INTO next_version 
    FROM workflow_versions WHERE workflow_id = COALESCE(NEW.workflow_id, OLD.workflow_id);
    
    IF TG_OP = 'INSERT' THEN
        INSERT INTO workflow_versions (workflow_pk, workflow_id, version, action, workflow_snapshot, created_by)
        VALUES (NEW.id, NEW.workflow_id, next_version, 'CREATE', to_jsonb(NEW), NEW.created_by);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO workflow_versions (workflow_pk, workflow_id, version, action, workflow_snapshot, created_by)
        VALUES (NEW.id, NEW.workflow_id, next_version, 'UPDATE', to_jsonb(NEW), NEW.modified_by);
        NEW.version := next_version;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO workflow_versions (workflow_pk, workflow_id, version, action, workflow_snapshot, created_by)
        VALUES (OLD.id, OLD.workflow_id, next_version, 'DELETE', to_jsonb(OLD), OLD.modified_by);
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_workflow_execution_stats(
    p_workflow_id VARCHAR(150),
    p_status VARCHAR(50)
) RETURNS VOID AS $$
BEGIN
    UPDATE workflows 
    SET execution_count = execution_count + 1,
        success_count = success_count + CASE WHEN p_status = 'success' THEN 1 ELSE 0 END,
        failure_count = failure_count + CASE WHEN p_status IN ('failed', 'timeout') THEN 1 ELSE 0 END,
        last_executed_at = CURRENT_TIMESTAMP,
        modified_at = CURRENT_TIMESTAMP
    WHERE workflow_id = p_workflow_id;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_workflow_versioning ON workflows;
CREATE TRIGGER trigger_workflow_versioning
    AFTER INSERT OR UPDATE OR DELETE ON workflows
    FOR EACH ROW EXECUTE FUNCTION create_workflow_version();

-- ============================================================================
-- TEMPLATE POR DEFECTO
-- ============================================================================

INSERT INTO workflow_templates (template_id, name, description, category, template_data, is_public, business_types, required_tools, required_agents)
VALUES (
    'template_sales_basic',
    'Workflow de Ventas Básico',
    'Responde consultas y agenda si hay interés',
    'sales',
    '{"nodes": {"node_1": {"id": "node_1", "type": "trigger", "name": "Trigger", "config": {}, "position": {"x": 100, "y": 100}}}}'::JSONB,
    true,
    ARRAY['healthcare', 'beauty'],
    ARRAY['knowledge_base'],
    ARRAY['sales', 'schedule']
) ON CONFLICT (template_id) DO NOTHING;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_name IN ('workflows', 'workflow_versions', 'workflow_executions', 'workflow_templates', 'workflow_nodes');
    
    IF table_count = 5 THEN
        RAISE NOTICE '✅ Workflows migration SUCCESS: All 5 tables created';
    ELSE
        RAISE WARNING '⚠️ Expected 5 tables, found %', table_count;
    END IF;
END $$;
