#!/usr/bin/env python3
"""
SCRIPT TEMPORAL DE DIAGNÓSTICO - SISTEMA DE PROMPTS CONFIGURABLES
==================================================================

Este script diagnostica automáticamente el origen de prompts en:
- Conversation Tester
- Webhook Chatwoot  
- Admin Panel
- BaseAgent initialization
- PostgreSQL vs JSON vs Hardcoded

USO:
    python diagnose_prompts_system.py
    
ELIMINAR DESPUÉS DE COMPLETAR LA MIGRACIÓN
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configurar logging para el diagnóstico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class PromptsSystemDiagnostic:
    """Diagnóstico completo del sistema de prompts configurables"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_company_id = "benova"
        self.test_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "test_company": self.test_company_id,
            "postgresql_status": {},
            "prompt_service_status": {},
            "base_agent_simulation": {},
            "conversation_tester": {},
            "webhook_simulation": {},
            "admin_panel": {},
            "company_consistency": {},
            "final_diagnosis": {},
            "recommendations": []
        }
    
    def run_complete_diagnosis(self) -> Dict[str, Any]:
        """Ejecutar diagnóstico completo del sistema"""
        logger.info("=" * 60)
        logger.info("INICIANDO DIAGNÓSTICO DEL SISTEMA DE PROMPTS CONFIGURABLES")
        logger.info("=" * 60)
        
        try:
            # 1. Verificar PostgreSQL y tablas
            self._test_postgresql_status()
            
            # 2. Testar PromptService directamente
            self._test_prompt_service()
            
            # 3. Simular BaseAgent loading
            self._simulate_base_agent_loading()
            
            # 4. Testar Conversation Tester (endpoint)
            self._test_conversation_tester()
            
            # 5. Simular Webhook
            self._test_webhook_simulation()
            
            # 6. Testar Admin Panel
            self._test_admin_panel()
            
            # 7. Verificar consistencia company_id
            self._test_company_consistency()
            
            # 8. Generar diagnóstico final
            self._generate_final_diagnosis()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error crítico en diagnóstico: {e}")
            self.results["critical_error"] = str(e)
            return self.results
    
    def _test_postgresql_status(self):
        """Test 1: Verificar estado de PostgreSQL"""
        logger.info("\n1. TESTING POSTGRESQL STATUS")
        logger.info("-" * 30)
        
        try:
            # Agregar path del proyecto
            sys.path.insert(0, '.')
            
            from app.services.prompt_service import get_prompt_service
            
            prompt_service = get_prompt_service()
            db_status = prompt_service.get_db_status()
            
            self.results["postgresql_status"] = {
                "postgresql_available": db_status.get('postgresql_available', False),
                "connection_status": db_status.get('connection_status', 'unknown'),
                "tables_exist": db_status.get('tables_exist', False),
                "tables_found": db_status.get('tables_found', []),
                "total_default_prompts": db_status.get('total_default_prompts', 0),
                "total_custom_prompts": db_status.get('total_custom_prompts', 0),
                "fallback_mode": db_status.get('fallback_mode', 'unknown')
            }
            
            # Log results
            logger.info(f"   PostgreSQL Available: {db_status.get('postgresql_available')}")
            logger.info(f"   Tables Exist: {db_status.get('tables_exist')}")
            logger.info(f"   Default Prompts: {db_status.get('total_default_prompts', 0)}")
            logger.info(f"   Custom Prompts: {db_status.get('total_custom_prompts', 0)}")
            
            if db_status.get('total_default_prompts', 0) == 0:
                logger.warning("   ⚠️  NO DEFAULT PROMPTS FOUND - This is likely the problem!")
                self.results["recommendations"].append("Run migration to populate default prompts")
            
        except Exception as e:
            logger.error(f"   ❌ PostgreSQL test failed: {e}")
            self.results["postgresql_status"]["error"] = str(e)
    
    def _test_prompt_service(self):
        """Test 2: Testar PromptService directamente"""
        logger.info("\n2. TESTING PROMPT SERVICE")
        logger.info("-" * 30)
        
        try:
            from app.services.prompt_service import get_prompt_service
            
            prompt_service = get_prompt_service()
            
            # Obtener prompts para benova
            agents_data = prompt_service.get_company_prompts(self.test_company_id)
            
            self.results["prompt_service_status"] = {
                "service_available": True,
                "agents_returned": list(agents_data.keys()),
                "total_agents": len(agents_data),
                "agents_detail": {}
            }
            
            logger.info(f"   Service Available: True")
            logger.info(f"   Agents Returned: {list(agents_data.keys())}")
            
            # Analizar cada agente
            for agent_name in self.test_agents:
                agent_data = agents_data.get(agent_name, {})
                
                agent_detail = {
                    "found": agent_name in agents_data,
                    "source": agent_data.get('source', 'NOT_FOUND'),
                    "has_prompt": bool(agent_data.get('current_prompt')),
                    "is_custom": agent_data.get('is_custom', False),
                    "prompt_preview": agent_data.get('current_prompt', '')[:100] if agent_data.get('current_prompt') else None
                }
                
                self.results["prompt_service_status"]["agents_detail"][agent_name] = agent_detail
                logger.info(f"   {agent_name}: {agent_detail['source']} (custom: {agent_detail['is_custom']})")
            
        except Exception as e:
            logger.error(f"   ❌ PromptService test failed: {e}")
            self.results["prompt_service_status"]["error"] = str(e)
    
    def _simulate_base_agent_loading(self):
        """Test 3: Simular carga de prompts como BaseAgent"""
        logger.info("\n3. SIMULATING BASE AGENT LOADING")
        logger.info("-" * 30)
        
        try:
            from app.services.prompt_service import get_prompt_service
            
            prompt_service = get_prompt_service()
            agents_data = prompt_service.get_company_prompts(self.test_company_id)
            
            self.results["base_agent_simulation"] = {}
            
            for agent_name in self.test_agents:
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
                    "agent_data": agent_data
                }
                
                self.results["base_agent_simulation"][agent_name] = simulation_result
                
                logger.info(f"   {agent_name}: Will use {predicted_source}")
                
                if would_use_hardcoded:
                    logger.warning(f"      ⚠️  {agent_name} will use hardcoded fallback!")
            
        except Exception as e:
            logger.error(f"   ❌ BaseAgent simulation failed: {e}")
            self.results["base_agent_simulation"]["error"] = str(e)
    
    def _test_conversation_tester(self):
        """Test 4: Testar Conversation Tester endpoint"""
        logger.info("\n4. TESTING CONVERSATION TESTER")
        logger.info("-" * 30)
        
        try:
            url = f"{self.base_url}/api/conversations/diagnostic_user/test"
            params = {"company_id": self.test_company_id}
            data = {"message": "Test diagnostic - ¿cuánto cuesta un tratamiento?"}
            
            response = requests.post(url, json=data, params=params, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                self.results["conversation_tester"] = {
                    "endpoint_working": True,
                    "status_code": response.status_code,
                    "response_data": response_data.get("data", {}),
                    "agent_used": response_data.get("data", {}).get("agent_used"),
                    "bot_response_length": len(response_data.get("data", {}).get("bot_response", "")),
                    "company_id_returned": response_data.get("data", {}).get("company_id")
                }
                
                logger.info(f"   Endpoint Working: True")
                logger.info(f"   Agent Used: {response_data.get('data', {}).get('agent_used')}")
                logger.info(f"   Response Length: {len(response_data.get('data', {}).get('bot_response', ''))}")
                
            else:
                self.results["conversation_tester"] = {
                    "endpoint_working": False,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                logger.error(f"   ❌ Endpoint failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"   ❌ Conversation Tester test failed: {e}")
            self.results["conversation_tester"]["error"] = str(e)
    
    def _test_webhook_simulation(self):
        """Test 5: Simular webhook de Chatwoot"""
        logger.info("\n5. TESTING WEBHOOK SIMULATION")
        logger.info("-" * 30)
        
        try:
            url = f"{self.base_url}/api/webhook/test"
            webhook_data = {
                "event": "message_created",
                "message_type": "incoming",
                "content": "Test webhook - ¿tienen descuentos?",
                "conversation": {
                    "id": 99999,
                    "account_id": "7",  # Maps to benova
                    "status": "open"
                },
                "sender": {"id": 88888}
            }
            
            response = requests.post(url, json=webhook_data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                self.results["webhook_simulation"] = {
                    "endpoint_working": True,
                    "status_code": response.status_code,
                    "company_id_detected": response_data.get("company_id"),
                    "response_data": response_data
                }
                
                logger.info(f"   Endpoint Working: True")
                logger.info(f"   Company ID Detected: {response_data.get('company_id')}")
                
            else:
                self.results["webhook_simulation"] = {
                    "endpoint_working": False,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                logger.error(f"   ❌ Webhook test failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"   ❌ Webhook simulation failed: {e}")
            self.results["webhook_simulation"]["error"] = str(e)
    
    def _test_admin_panel(self):
        """Test 6: Testar Admin Panel endpoints"""
        logger.info("\n6. TESTING ADMIN PANEL")
        logger.info("-" * 30)
        
        try:
            # Test get prompts
            url = f"{self.base_url}/api/admin/prompts"
            params = {"company_id": self.test_company_id}
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                response_data = response.json()
                agents_data = response_data.get("data", {}).get("agents", {})
                
                self.results["admin_panel"] = {
                    "get_prompts_working": True,
                    "status_code": response.status_code,
                    "agents_returned": list(agents_data.keys()),
                    "total_agents": len(agents_data),
                    "agents_with_custom": len([a for a in agents_data.values() if a.get("is_custom")]),
                    "response_data": response_data.get("data", {})
                }
                
                logger.info(f"   Get Prompts Working: True")
                logger.info(f"   Agents Returned: {list(agents_data.keys())}")
                logger.info(f"   Custom Prompts: {len([a for a in agents_data.values() if a.get('is_custom')])}")
                
            else:
                self.results["admin_panel"] = {
                    "get_prompts_working": False,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                logger.error(f"   ❌ Admin panel test failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"   ❌ Admin panel test failed: {e}")
            self.results["admin_panel"]["error"] = str(e)
    
    def _test_company_consistency(self):
        """Test 7: Verificar consistencia de company_id"""
        logger.info("\n7. TESTING COMPANY CONSISTENCY")
        logger.info("-" * 30)
        
        try:
            # Verificar companies_config.json
            config_file = 'companies_config.json'
            companies_in_config = set()
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    companies_in_config = set(config_data.keys())
            
            # Verificar PromptService
            from app.services.prompt_service import get_prompt_service
            
            prompt_service = get_prompt_service()
            db_status = prompt_service.get_db_status()
            
            # Simular query de empresas en PostgreSQL
            companies_in_db = set()
            if db_status.get('postgresql_available'):
                # Esto requeriría una query directa, por ahora asumir benova
                companies_in_db.add(self.test_company_id)
            
            consistency_issues = []
            
            # Verificar si benova está en config
            if self.test_company_id not in companies_in_config:
                consistency_issues.append(f"{self.test_company_id} not in companies_config.json")
            
            # Verificar si hay prompts para benova
            if db_status.get('total_default_prompts', 0) == 0:
                consistency_issues.append("No default prompts in PostgreSQL")
            
            self.results["company_consistency"] = {
                "companies_in_config": list(companies_in_config),
                "companies_in_db": list(companies_in_db),
                "test_company_in_config": self.test_company_id in companies_in_config,
                "config_file_exists": os.path.exists(config_file),
                "consistency_issues": consistency_issues,
                "is_consistent": len(consistency_issues) == 0
            }
            
            logger.info(f"   Config File Exists: {os.path.exists(config_file)}")
            logger.info(f"   Companies in Config: {list(companies_in_config)}")
            logger.info(f"   Test Company in Config: {self.test_company_id in companies_in_config}")
            logger.info(f"   Consistency Issues: {len(consistency_issues)}")
            
            for issue in consistency_issues:
                logger.warning(f"      ⚠️  {issue}")
            
        except Exception as e:
            logger.error(f"   ❌ Company consistency test failed: {e}")
            self.results["company_consistency"]["error"] = str(e)
    
    def _generate_final_diagnosis(self):
        """Generar diagnóstico final y recomendaciones"""
        logger.info("\n8. GENERATING FINAL DIAGNOSIS")
        logger.info("-" * 30)
        
        # Analizar resultados
        postgresql_ok = self.results.get("postgresql_status", {}).get("postgresql_available", False)
        has_default_prompts = self.results.get("postgresql_status", {}).get("total_default_prompts", 0) > 0
        prompt_service_ok = self.results.get("prompt_service_status", {}).get("service_available", False)
        conversation_tester_ok = self.results.get("conversation_tester", {}).get("endpoint_working", False)
        webhook_ok = self.results.get("webhook_simulation", {}).get("endpoint_working", False)
        admin_panel_ok = self.results.get("admin_panel", {}).get("get_prompts_working", False)
        
        # Analizar si agentes usarán PostgreSQL
        agents_using_postgresql = 0
        agents_using_hardcoded = 0
        
        for agent_name, simulation in self.results.get("base_agent_simulation", {}).items():
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
        elif not conversation_tester_ok:
            main_problem = "conversation_tester_not_working"
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
                "Run: python migrate_prompts_to_postgresql.py",
                "Or via API: POST /api/admin/prompts/migrate",
                "Verify migration completed successfully"
            ])
        elif main_problem == "agents_not_loading_from_postgresql":
            recommendations.extend([
                "Check BaseAgent._create_prompt_template() implementation",
                "Verify agents call BaseAgent methods correctly",
                "Check PromptService initialization in BaseAgent.__init__"
            ])
        elif main_problem == "system_working_correctly":
            recommendations.extend([
                "System appears to be working correctly",
                "Monitor logs for postgresql_custom/postgresql_default messages",
                "Consider removing JSON fallbacks if no longer needed"
            ])
        
        self.results["final_diagnosis"] = {
            "main_problem": main_problem,
            "postgresql_status": "ok" if postgresql_ok else "failed",
            "has_default_prompts": has_default_prompts,
            "agents_using_postgresql": agents_using_postgresql,
            "agents_using_hardcoded": agents_using_hardcoded,
            "endpoints_working": {
                "conversation_tester": conversation_tester_ok,
                "webhook": webhook_ok,
                "admin_panel": admin_panel_ok
            },
            "system_health_score": self._calculate_health_score(),
            "migration_needed": not has_default_prompts,
            "agents_need_fix": agents_using_hardcoded > 0
        }
        
        self.results["recommendations"].extend(recommendations)
        
        # Log diagnóstico final
        logger.info(f"   Main Problem: {main_problem}")
        logger.info(f"   PostgreSQL: {'OK' if postgresql_ok else 'FAILED'}")
        logger.info(f"   Default Prompts: {'YES' if has_default_prompts else 'NO'}")
        logger.info(f"   Agents using PostgreSQL: {agents_using_postgresql}")
        logger.info(f"   Agents using Hardcoded: {agents_using_hardcoded}")
        logger.info(f"   Health Score: {self._calculate_health_score()}%")
    
    def _calculate_health_score(self) -> int:
        """Calcular score de salud del sistema (0-100)"""
        score = 0
        
        # PostgreSQL disponible (30 puntos)
        if self.results.get("postgresql_status", {}).get("postgresql_available"):
            score += 30
        
        # Tiene prompts por defecto (25 puntos)
        if self.results.get("postgresql_status", {}).get("total_default_prompts", 0) > 0:
            score += 25
        
        # PromptService funciona (15 puntos)
        if self.results.get("prompt_service_status", {}).get("service_available"):
            score += 15
        
        # Endpoints funcionan (20 puntos total)
        endpoints_working = 0
        if self.results.get("conversation_tester", {}).get("endpoint_working"):
            endpoints_working += 1
        if self.results.get("webhook_simulation", {}).get("endpoint_working"):
            endpoints_working += 1
        if self.results.get("admin_panel", {}).get("get_prompts_working"):
            endpoints_working += 1
        
        score += int((endpoints_working / 3) * 20)
        
        # Agentes usan PostgreSQL (10 puntos)
        total_agents = len(self.test_agents)
        agents_using_postgresql = sum(1 for simulation in self.results.get("base_agent_simulation", {}).values() 
                                     if isinstance(simulation, dict) and 
                                     simulation.get("predicted_source") in ["postgresql_custom", "postgresql_default"])
        
        if total_agents > 0:
            score += int((agents_using_postgresql / total_agents) * 10)
        
        return min(100, score)
    
    def save_results(self, filename: str = None):
        """Guardar resultados del diagnóstico"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompts_diagnosis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n📄 Results saved to: {filename}")
        return filename
    
    def print_summary(self):
        """Imprimir resumen ejecutivo"""
        logger.info("\n" + "=" * 60)
        logger.info("RESUMEN EJECUTIVO DEL DIAGNÓSTICO")
        logger.info("=" * 60)
        
        diagnosis = self.results.get("final_diagnosis", {})
        
        logger.info(f"Problema Principal: {diagnosis.get('main_problem', 'unknown')}")
        logger.info(f"PostgreSQL: {'✅ OK' if diagnosis.get('postgresql_status') == 'ok' else '❌ FAILED'}")
        logger.info(f"Prompts por Defecto: {'✅ YES' if diagnosis.get('has_default_prompts') else '❌ NO'}")
        logger.info(f"Agentes usando PostgreSQL: {diagnosis.get('agents_using_postgresql', 0)}/{len(self.test_agents)}")
        logger.info(f"Score de Salud: {diagnosis.get('system_health_score', 0)}%")
        
        logger.info(f"\nRECOMENDACIONES:")
        for i, rec in enumerate(self.results.get("recommendations", []), 1):
            logger.info(f"  {i}. {rec}")
        
        if diagnosis.get("migration_needed"):
            logger.warning("\n⚠️  ACCIÓN REQUERIDA: Ejecutar migración de prompts")
        elif diagnosis.get("system_health_score", 0) >= 80:
            logger.info("\n✅ Sistema funcionando correctamente")
        else:
            logger.warning(f"\n⚠️  Sistema requiere atención (Score: {diagnosis.get('system_health_score', 0)}%)")


def main():
    """Función principal del diagnóstico"""
    print("🔍 DIAGNÓSTICO DEL SISTEMA DE PROMPTS CONFIGURABLES")
    print("=" * 60)
    
    # Verificar si el servidor está corriendo
    diagnostic = PromptsSystemDiagnostic()
    
    try:
        response = requests.get(f"{diagnostic.base_url}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Servidor no responde correctamente: {response.status_code}")
    except Exception:
        print("⚠️  No se puede conectar al servidor. ¿Está corriendo en localhost:5000?")
        print("   Continuando con tests que no requieren servidor...")
    
    # Ejecutar diagnóstico completo
    results = diagnostic.run_complete_diagnosis()
    
    # Mostrar resumen
    diagnostic.print_summary()
    
    # Guardar resultados
    filename = diagnostic.save_results()
    
    # Mostrar next steps
    diagnosis = results.get("final_diagnosis", {})
    
    print(f"\n📋 PRÓXIMOS PASOS:")
    if diagnosis.get("migration_needed"):
        print("   1. Ejecutar: python migrate_prompts_to_postgresql.py")
        print("   2. Re-ejecutar este diagnóstico")
        print("   3. Verificar logs de agentes en conversation tester")
    elif diagnosis.get("system_health_score", 0) >= 80:
        print("   1. Monitorear logs para 'postgresql_custom' y 'postgresql_default'")
        print("   2. Testear prompts personalizados en Admin Panel")
        print("   3. Considerar eliminar fallbacks JSON si no se necesitan")
    else:
        print("   1. Revisar recomendaciones específicas arriba")
        print("   2. Aplicar correcciones")
        print("   3. Re-ejecutar diagnóstico")
    
    print(f"\nResultados completos en: {filename}")
    
    return results


if __name__ == "__main__":
    main()
