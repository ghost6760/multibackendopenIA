# app/routes/diagnostic.py - TEMPORAL
# Endpoint interno para diagnóstico del sistema de prompts configurables
# ELIMINAR DESPUÉS DE RESOLVER EL PROBLEMA

from flask import Blueprint, jsonify, request
from app.services.prompt_service import get_prompt_service
from app.config.company_config import get_company_manager, get_company_config
from app.services.multi_agent_factory import get_multi_agent_factory
from app.utils.helpers import create_success_response, create_error_response
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

diagnostic_bp = Blueprint('diagnostic', __name__, url_prefix='/api/diagnostic')

@diagnostic_bp.route('/prompts-system', methods=['GET'])
def diagnose_prompts_system():
    """
    ENDPOINT TEMPORAL: Diagnóstico completo del sistema de prompts configurables
    
    Analiza:
    - Estado de PostgreSQL y tablas
    - Funcionamiento del PromptService  
    - Predicción de qué prompts usarán los agentes
    - Consistencia de company_id
    - Estado de endpoints principales
    
    Usage: GET /api/diagnostic/prompts-system?company_id=benova
    """
    try:
        company_id = request.args.get('company_id', 'benova')
        test_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_company": company_id,
            "postgresql_status": {},
            "prompt_service_status": {},
            "base_agent_simulation": {},
            "company_consistency": {},
            "orchestrator_status": {},
            "final_diagnosis": {},
            "recommendations": []
        }
        
        logger.info(f"🔍 Starting prompts system diagnosis for {company_id}")
        
        # ===== TEST 1: POSTGRESQL STATUS =====
        try:
            prompt_service = get_prompt_service()
            db_status = prompt_service.get_db_status()
            
            results["postgresql_status"] = {
                "postgresql_available": db_status.get('postgresql_available', False),
                "connection_status": db_status.get('connection_status', 'unknown'),
                "tables_exist": db_status.get('tables_exist', False),
                "tables_found": db_status.get('tables_found', []),
                "total_default_prompts": db_status.get('total_default_prompts', 0),
                "total_custom_prompts": db_status.get('total_custom_prompts', 0),
                "fallback_mode": db_status.get('fallback_mode', 'unknown')
            }
            
            logger.info(f"   PostgreSQL Available: {db_status.get('postgresql_available')}")
            logger.info(f"   Tables Exist: {db_status.get('tables_exist')}")
            logger.info(f"   Default Prompts: {db_status.get('total_default_prompts', 0)}")
            
        except Exception as e:
            logger.error(f"PostgreSQL test failed: {e}")
            results["postgresql_status"]["error"] = str(e)
        
        # ===== TEST 2: PROMPT SERVICE STATUS =====
        try:
            prompt_service = get_prompt_service()
            agents_data = prompt_service.get_company_prompts(company_id)
            
            results["prompt_service_status"] = {
                "service_available": True,
                "agents_returned": list(agents_data.keys()),
                "total_agents": len(agents_data),
                "agents_detail": {}
            }
            
            logger.info(f"   PromptService returned {len(agents_data)} agents")
            
            # Analizar cada agente
            for agent_name in test_agents:
                agent_data = agents_data.get(agent_name, {})
                
                agent_detail = {
                    "found": agent_name in agents_data,
                    "source": agent_data.get('source', 'NOT_FOUND'),
                    "has_prompt": bool(agent_data.get('current_prompt')),
                    "is_custom": agent_data.get('is_custom', False),
                    "prompt_preview": agent_data.get('current_prompt', '')[:100] if agent_data.get('current_prompt') else None
                }
                
                results["prompt_service_status"]["agents_detail"][agent_name] = agent_detail
                logger.info(f"   {agent_name}: {agent_detail['source']} (custom: {agent_detail['is_custom']})")
            
        except Exception as e:
            logger.error(f"PromptService test failed: {e}")
            results["prompt_service_status"]["error"] = str(e)
        
        # ===== TEST 3: BASE AGENT SIMULATION =====
        try:
            prompt_service = get_prompt_service()
            agents_data = prompt_service.get_company_prompts(company_id)
            
            results["base_agent_simulation"] = {}
            
            for agent_name in test_agents:
                agent_data = agents_data.get(agent_name, {})
                
                # Simular lógica exacta de BaseAgent._load_custom_prompt_from_postgresql
                would_load_custom = (
                    agent_data.get('is_custom', False) and 
                    agent_data.get('source') in ['custom', 'postgresql_custom'] and
                    agent_data.get('current_prompt')
                )
                
                # Simular lógica de BaseAgent._load_default_prompt_from_postgresql
                would_load_default = (
                    agent_data.get('source') in ['default', 'postgresql_default'] and
                    agent_data.get('current_prompt')
                )
                
                would_use_hardcoded = not (would_load_custom or would_load_default)
                
                predicted_source = "postgresql_custom" if would_load_custom else \
                                 "postgresql_default" if would_load_default else \
                                 "hardcoded_fallback"
                
                simulation_result = {
                    "agent_data_available": bool(agent_data),
                    "would_load_custom": would_load_custom,
                    "would_load_default": would_load_default,
                    "would_use_hardcoded": would_use_hardcoded,
                    "predicted_source": predicted_source,
                    "agent_data_summary": {
                        "source": agent_data.get('source', 'none'),
                        "is_custom": agent_data.get('is_custom', False),
                        "has_prompt": bool(agent_data.get('current_prompt'))
                    }
                }
                
                results["base_agent_simulation"][agent_name] = simulation_result
                
                logger.info(f"   {agent_name}: Will use {predicted_source}")
                
                if would_use_hardcoded:
                    logger.warning(f"      ⚠️  {agent_name} will use hardcoded fallback!")
            
        except Exception as e:
            logger.error(f"BaseAgent simulation failed: {e}")
            results["base_agent_simulation"]["error"] = str(e)
        
        # ===== TEST 4: COMPANY CONSISTENCY =====
        try:
            # Verificar companies_config.json
            config_file = 'companies_config.json'
            companies_in_config = set()
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    companies_in_config = set(config_data.keys())
            
            # Verificar company_config
            company_config = get_company_config(company_id)
            
            # Verificar PromptService
            db_status = results.get("postgresql_status", {})
            
            consistency_issues = []
            
            # Verificar si company_id está en config
            if company_id not in companies_in_config:
                consistency_issues.append(f"{company_id} not in companies_config.json")
            
            # Verificar si hay prompts para company_id
            if db_status.get('total_default_prompts', 0) == 0:
                consistency_issues.append("No default prompts in PostgreSQL")
            
            # Verificar si company_config existe
            if not company_config:
                consistency_issues.append(f"No CompanyConfig found for {company_id}")
            
            results["company_consistency"] = {
                "companies_in_config": list(companies_in_config),
                "test_company_in_config": company_id in companies_in_config,
                "config_file_exists": os.path.exists(config_file),
                "company_config_exists": company_config is not None,
                "consistency_issues": consistency_issues,
                "is_consistent": len(consistency_issues) == 0
            }
            
            logger.info(f"   Config File Exists: {os.path.exists(config_file)}")
            logger.info(f"   Companies in Config: {list(companies_in_config)}")
            logger.info(f"   CompanyConfig exists: {company_config is not None}")
            logger.info(f"   Consistency Issues: {len(consistency_issues)}")
            
        except Exception as e:
            logger.error(f"Company consistency test failed: {e}")
            results["company_consistency"]["error"] = str(e)
        
        # ===== TEST 5: ORCHESTRATOR STATUS =====
        try:
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            if orchestrator:
                agents_available = list(orchestrator.agents.keys())
                
                # Test básico de cada agente
                agents_test = {}
                for agent_key, agent in orchestrator.agents.items():
                    try:
                        # Verificar si el agente tiene prompt_service
                        has_prompt_service = hasattr(agent, 'prompt_service')
                        prompt_service_type = type(agent.prompt_service).__name__ if has_prompt_service else None
                        
                        # Verificar _prompt_source si existe
                        prompt_source = getattr(agent, '_prompt_source', 'unknown')
                        
                        agents_test[agent_key] = {
                            "agent_class": agent.__class__.__name__,
                            "has_prompt_service": has_prompt_service,
                            "prompt_service_type": prompt_service_type,
                            "prompt_source": prompt_source,
                            "has_prompt_template": hasattr(agent, 'prompt_template'),
                            "status": "available"
                        }
                        
                    except Exception as e:
                        agents_test[agent_key] = {
                            "status": "error",
                            "error": str(e)
                        }
                
                results["orchestrator_status"] = {
                    "orchestrator_available": True,
                    "company_id": orchestrator.company_id,
                    "agents_available": agents_available,
                    "total_agents": len(agents_available),
                    "agents_test": agents_test,
                    "vectorstore_connected": orchestrator.vectorstore_service is not None
                }
                
                logger.info(f"   Orchestrator Available: True")
                logger.info(f"   Agents Available: {agents_available}")
                
            else:
                results["orchestrator_status"] = {
                    "orchestrator_available": False,
                    "error": "Could not create orchestrator"
                }
                logger.error("   Orchestrator could not be created")
            
        except Exception as e:
            logger.error(f"Orchestrator test failed: {e}")
            results["orchestrator_status"]["error"] = str(e)
        
        # ===== GENERAR DIAGNÓSTICO FINAL =====
        postgresql_ok = results.get("postgresql_status", {}).get("postgresql_available", False)
        has_default_prompts = results.get("postgresql_status", {}).get("total_default_prompts", 0) > 0
        prompt_service_ok = results.get("prompt_service_status", {}).get("service_available", False)
        orchestrator_ok = results.get("orchestrator_status", {}).get("orchestrator_available", False)
        
        # Analizar si agentes usarán PostgreSQL
        agents_using_postgresql = 0
        agents_using_hardcoded = 0
        
        for agent_name, simulation in results.get("base_agent_simulation", {}).items():
            if isinstance(simulation, dict):
                if simulation.get("predicted_source") in ["postgresql_custom", "postgresql_default"]:
                    agents_using_postgresql += 1
                elif simulation.get("predicted_source") == "hardcoded_fallback":
                    agents_using_hardcoded += 1
        
        # Determinar problema principal
        main_problem = "unknown"
        if not postgresql_ok:
            main_problem = "postgresql_connection_failed"
        elif not has_default_prompts:
            main_problem = "postgresql_empty_needs_migration"
        elif agents_using_hardcoded > 0:
            main_problem = "agents_not_loading_from_postgresql"
        elif not orchestrator_ok:
            main_problem = "orchestrator_not_working"
        elif postgresql_ok and has_default_prompts and agents_using_postgresql > 0:
            main_problem = "system_working_correctly"
        
        # Generar recomendaciones específicas
        recommendations = []
        
        if main_problem == "postgresql_connection_failed":
            recommendations.extend([
                "Check DATABASE_URL environment variable",
                "Verify PostgreSQL server is running",
                "Check network connectivity to database"
            ])
        elif main_problem == "postgresql_empty_needs_migration":
            recommendations.extend([
                "Run migration: POST /api/admin/prompts/migrate",
                "Or execute: python migrate_prompts_to_postgresql.py",
                "Verify default prompts were created successfully"
            ])
        elif main_problem == "agents_not_loading_from_postgresql":
            recommendations.extend([
                "Check BaseAgent._create_prompt_template() implementation",
                "Verify agents call BaseAgent methods correctly",
                "Check PromptService initialization in BaseAgent.__init__",
                "Monitor logs for postgresql_custom/postgresql_default messages"
            ])
        elif main_problem == "system_working_correctly":
            recommendations.extend([
                "System appears to be working correctly",
                "Monitor logs during conversation tests",
                "Test custom prompt creation in Admin Panel"
            ])
        
        # Calcular health score
        health_score = 0
        if postgresql_ok: health_score += 30
        if has_default_prompts: health_score += 25
        if prompt_service_ok: health_score += 15
        if orchestrator_ok: health_score += 20
        if len(test_agents) > 0:
            health_score += int((agents_using_postgresql / len(test_agents)) * 10)
        
        results["final_diagnosis"] = {
            "main_problem": main_problem,
            "postgresql_status": "ok" if postgresql_ok else "failed",
            "has_default_prompts": has_default_prompts,
            "agents_using_postgresql": agents_using_postgresql,
            "agents_using_hardcoded": agents_using_hardcoded,
            "orchestrator_working": orchestrator_ok,
            "system_health_score": min(100, health_score),
            "migration_needed": not has_default_prompts,
            "agents_need_fix": agents_using_hardcoded > 0
        }
        
        results["recommendations"] = recommendations
        
        # Log diagnóstico final
        logger.info(f"🎯 FINAL DIAGNOSIS:")
        logger.info(f"   Main Problem: {main_problem}")
        logger.info(f"   PostgreSQL: {'OK' if postgresql_ok else 'FAILED'}")
        logger.info(f"   Default Prompts: {'YES' if has_default_prompts else 'NO'}")
        logger.info(f"   Agents using PostgreSQL: {agents_using_postgresql}")
        logger.info(f"   Agents using Hardcoded: {agents_using_hardcoded}")
        logger.info(f"   Health Score: {health_score}%")
        
        return create_success_response({
            "diagnosis": results,
            "summary": {
                "main_problem": main_problem,
                "health_score": health_score,
                "migration_needed": not has_default_prompts,
                "recommendations_count": len(recommendations)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in prompts system diagnosis: {e}", exc_info=True)
        return create_error_response(f"Diagnosis failed: {str(e)}", 500)

@diagnostic_bp.route('/test-conversation', methods=['POST'])
def test_conversation_with_diagnosis():
    """
    ENDPOINT TEMPORAL: Test conversation con diagnóstico detallado de prompts
    
    Usage: POST /api/diagnostic/test-conversation
    Body: {"company_id": "benova", "message": "test message"}
    """
    try:
        data = request.get_json() or {}
        company_id = data.get('company_id', 'benova')
        message = data.get('message', 'Test diagnostic message')
        
        logger.info(f"🧪 Testing conversation with prompt diagnosis for {company_id}")
        
        # Hacer test real de conversación
        from app.models.conversation import ConversationManager
        from app.services.multi_agent_factory import get_multi_agent_factory
        
        manager = ConversationManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return create_error_response(f"Orchestrator not available for {company_id}", 503)
        
        # Capturar información ANTES del test
        pre_test_info = {}
        for agent_key, agent in orchestrator.agents.items():
            pre_test_info[agent_key] = {
                "agent_class": agent.__class__.__name__,
                "has_prompt_service": hasattr(agent, 'prompt_service'),
                "prompt_source": getattr(agent, '_prompt_source', 'unknown'),
                "has_prompt_template": hasattr(agent, 'prompt_template')
            }
        
        # Ejecutar test de conversación
        user_id = f"diagnostic_test_{int(datetime.now().timestamp())}"
        response, agent_used = orchestrator.get_response(message, user_id, manager)
        
        # Capturar información DESPUÉS del test
        post_test_info = {}
        for agent_key, agent in orchestrator.agents.items():
            post_test_info[agent_key] = {
                "prompt_source": getattr(agent, '_prompt_source', 'unknown'),
                "was_used": agent_key == agent_used
            }
        
        return create_success_response({
            "test_result": {
                "company_id": company_id,
                "user_message": message,
                "bot_response": response,
                "agent_used": agent_used,
                "response_length": len(response)
            },
            "prompt_diagnosis": {
                "pre_test_agents": pre_test_info,
                "post_test_agents": post_test_info,
                "agent_used_details": post_test_info.get(agent_used, {})
            }
        })
        
    except Exception as e:
        logger.error(f"Error in conversation test with diagnosis: {e}", exc_info=True)
        return create_error_response(f"Conversation test failed: {str(e)}", 500)

@diagnostic_bp.route('/migrate-prompts', methods=['POST'])
def migrate_prompts_now():
    """
    ENDPOINT TEMPORAL: Ejecutar migración de prompts desde el endpoint
    
    Usage: POST /api/diagnostic/migrate-prompts
    """
    try:
        logger.info("🔄 Starting prompt migration from diagnostic endpoint")
        
        prompt_service = get_prompt_service()
        
        # Verificar estado pre-migración
        pre_migration_status = prompt_service.get_db_status()
        
        # Ejecutar migración
        migration_stats = prompt_service.migrate_from_json()
        
        # Verificar estado post-migración
        post_migration_status = prompt_service.get_db_status()
        
        return create_success_response({
            "migration_completed": migration_stats.get('success', False),
            "migration_stats": migration_stats,
            "pre_migration": {
                "default_prompts": pre_migration_status.get('total_default_prompts', 0),
                "custom_prompts": pre_migration_status.get('total_custom_prompts', 0)
            },
            "post_migration": {
                "default_prompts": post_migration_status.get('total_default_prompts', 0),
                "custom_prompts": post_migration_status.get('total_custom_prompts', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in prompt migration: {e}", exc_info=True)
        return create_error_response(f"Migration failed: {str(e)}", 500)
