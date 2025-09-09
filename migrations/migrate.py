# migrations/migrate.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_schema():
    """Create the complete database schema"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not found")
        raise Exception("DATABASE_URL must be set")
    
    logger.info(f"Connecting to database...")
    
    conn = psycopg2.connect(database_url)
    
    try:
        with conn.cursor() as cursor:
            # 1. Create custom_prompts table
            cursor.execute("""
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
                    modified_by VARCHAR(100) DEFAULT 'admin'
                );
            """)
            logger.info("✅ custom_prompts table created")
            
            # 2. Create unique constraint
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'unique_active_prompt'
                    ) THEN
                        ALTER TABLE custom_prompts 
                        ADD CONSTRAINT unique_active_prompt 
                        UNIQUE (company_id, agent_name) 
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END $$;
            """)
            logger.info("✅ Unique constraint added")
            
            # 3. Create prompt_versions table for audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id BIGSERIAL PRIMARY KEY,
                    prompt_id BIGINT,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    template TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    notes TEXT
                );
            """)
            logger.info("✅ prompt_versions table created")
            
            # 4. Create default_prompts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS default_prompts (
                    id BIGSERIAL PRIMARY KEY,
                    agent_name VARCHAR(100) UNIQUE NOT NULL,
                    template TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ default_prompts table created")
            
            # 5. Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent 
                ON custom_prompts(company_id, agent_name) 
                WHERE is_active = true;
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_custom_prompts_company 
                ON custom_prompts(company_id) 
                WHERE is_active = true;
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id 
                ON prompt_versions(prompt_id);
            """)
            logger.info("✅ Indexes created")
            
            # 6. Insert default prompts
            default_prompts = [
                ('router_agent', '''Eres un clasificador de intenciones para {company_name}. 
Analiza la consulta del usuario y determina el tipo de agente más apropiado.

Tipos de agente disponibles:
- sales: Consultas sobre productos, precios, compras
- support: Problemas técnicos, quejas, ayuda
- emergency: Situaciones urgentes que requieren atención inmediata

Responde ÚNICAMENTE con el tipo de agente (sales/support/emergency).'''),
                
                ('sales_agent', '''Eres un agente de ventas profesional para {company_name}.
Especializado en medicina estética y tratamientos de belleza.

Tu objetivo es:
- Informar sobre productos y servicios
- Guiar hacia la compra
- Resolver dudas comerciales
- Agendar citas de consulta

Mantén un tono profesional, amigable y orientado a resultados.'''),
                
                ('support_agent', '''Eres un especialista en atención al cliente para {company_name}.

Tu función es:
- Resolver consultas generales
- Facilitar navegación y uso de servicios
- Escalar problemas técnicos cuando sea necesario

Sé empático, profesional y orientado a la solución.'''),
                
                ('emergency_agent', '''Eres un agente de emergencias para {company_name}.

PROTOCOLO DE EMERGENCIA:
1. Evalúa la urgencia de la situación
2. Proporciona primeros auxilios básicos si es necesario
3. Recomienda contactar servicios de emergencia si la situación lo requiere
4. Mantén la calma y sé directo

En caso de emergencia médica real, recomienda contactar el 911 inmediatamente.'''),
                
                ('schedule_agent', '''Eres un especialista en agendamiento para {company_name}.

Tu función es:
- Verificar disponibilidad de horarios
- Agendar citas médicas y tratamientos
- Confirmar y modificar citas existentes
- Informar sobre políticas de cancelación

Mantén un tono profesional y eficiente.''')
            ]
            
            for agent_name, template in default_prompts:
                cursor.execute("""
                    INSERT INTO default_prompts (agent_name, template, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (agent_name) DO UPDATE SET
                    template = EXCLUDED.template,
                    updated_at = CURRENT_TIMESTAMP
                """, (agent_name, template, f"Default prompt for {agent_name}"))
            
            logger.info("✅ Default prompts inserted")
            
            # 7. Create trigger function for automatic modified_at update
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_modified_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.modified_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            cursor.execute("""
                DROP TRIGGER IF EXISTS update_custom_prompts_modified_at ON custom_prompts;
                CREATE TRIGGER update_custom_prompts_modified_at
                    BEFORE UPDATE ON custom_prompts
                    FOR EACH ROW
                    EXECUTE FUNCTION update_modified_at();
            """)
            logger.info("✅ Triggers created")
            
            conn.commit()
            logger.info("🎉 Database schema created successfully!")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error creating schema: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_database_schema()
