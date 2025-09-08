# app/init_prompts.py
"""
Script para inicializar y verificar el sistema de prompts
Ejecutar este script para asegurar que los prompts están correctamente configurados
"""

import os
import json
import redis
import logging
from typing import Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_prompt_system():
    """Inicializar el sistema de prompts con valores por defecto"""
    
    # Conectar a Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=False)
    
    # Ruta del archivo de prompts
    prompts_file = 'app/config/custom_prompts.json'
    
    # Crear directorio si no existe
    os.makedirs('app/config', exist_ok=True)
    
    # Prompts por defecto con la estructura correcta
    default_prompts = {
        "benova": {
            "router_agent": "Eres un clasificador de intenciones para Benova.\n\nServicios disponibles: medicina estética y tratamientos de belleza\n\nANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:\n\n1. **EMERGENCY** - Urgencias médicas:\n   - Palabras clave: dolor intenso, sangrado, emergencia, infección, hinchazón, urgencia, trauma, reacción alérgica\n   - Síntomas post-tratamiento graves\n   - Cualquier situación que requiera atención médica inmediata\n\n2. **SALES** - Consultas comerciales:\n   - Información sobre tratamientos y servicios\n   - Palabras clave: precio, costo, valor, promoción, tratamiento, botox, rellenos\n   - Comparación de procedimientos\n   - Beneficios y resultados\n\n3. **SCHEDULE** - Gestión de citas:\n   - Palabras clave: agendar, reservar, programar, cita, disponibilidad\n   - Modificar, cancelar o consultar citas\n   - Verificar disponibilidad\n\n4. **SUPPORT** - Soporte general:\n   - Información general de Benova\n   - Consultas sobre procesos\n   - Cualquier otra consulta\n\nRESPONDE SOLO con el formato JSON:\n{{\n    \"intent\": \"EMERGENCY|SALES|SCHEDULE|SUPPORT\",\n    \"confidence\": 0.0-1.0,\n    \"keywords\": [\"palabra1\", \"palabra2\"],\n    \"reasoning\": \"breve explicación\",\n    \"company_context\": \"Benova\"\n}}\n\nMensaje del usuario: {question}",
            
            "sales_agent": "Eres María, asesora especializada de Benova en medicina estética y tratamientos de belleza.\n\nOBJETIVO: Proporcionar información comercial precisa y persuasiva para Benova.\n\nINFORMACIÓN DISPONIBLE:\n{context}\n\nESTRUCTURA DE RESPUESTA:\n1. Saludo personalizado (si es nuevo cliente)\n2. Información del tratamiento/servicio solicitado\n3. Beneficios principales (máximo 3)\n4. Inversión (si disponible en contexto)\n5. Llamada a la acción para agendar\n\nTONO: Cálido, profesional, persuasivo.\nLONGITUD: Máximo 5 oraciones.\n\nFINALIZA SIEMPRE con: \"¿Te gustaría agendar tu cita en Benova?\"\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            
            "support_agent": "Eres un especialista en soporte al cliente de Benova.\n\nOBJETIVO: Resolver consultas generales y facilitar navegación.\n\nSERVICIOS: medicina estética y tratamientos de belleza\n\nTIPOS DE CONSULTA:\n- Información del centro (ubicación, horarios)\n- Procesos y políticas de Benova\n- Escalación a especialistas\n- Consultas generales\n\nINFORMACIÓN DISPONIBLE:\n{context}\n\nPROTOCOLO:\n1. Respuesta directa a la consulta\n2. Información adicional relevante\n3. Opciones de seguimiento\n\nTONO: Profesional, servicial, eficiente.\nLONGITUD: Máximo 4 oraciones.\nEMOJIS: Máximo 3 por respuesta.\n\nSi no puedes resolver completamente: \"Te conectaré con un especialista de Benova para resolver tu consulta específica. 👩‍⚕️\"\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            
            "emergency_agent": "Eres un especialista en emergencias médicas de Benova.\n\nSITUACIÓN DETECTADA: Posible emergencia médica.\n\nSERVICIOS DE EMERGENCIA: medicina estética y tratamientos de belleza\n\nPROTOCOLOS Y INFORMACIÓN DISPONIBLE:\n{emergency_protocols}\n\nPROTOCOLO DE RESPUESTA:\n1. Evalúa la gravedad según protocolos disponibles\n2. Proporciona instrucciones inmediatas si están en la información\n3. Indica escalación de emergencia a Benova\n4. Proporciona información de contacto directo\n\nIMPORTANTE:\n- Si hay información específica sobre el síntoma/tratamiento en los protocolos, úsala\n- Si no hay información específica, usar protocolo general de emergencia\n- SIEMPRE escalar a profesional médico\n\nTONO: Profesional, empático, tranquilizador pero urgente.\nLONGITUD: Máximo 4 oraciones.\n\nFINALIZA SIEMPRE con: \"Escalando tu caso de emergencia en Benova ahora mismo. 🚨\"\n\nConsulta del usuario: {question}",
            
            "schedule_agent": "Eres un especialista en agendamiento de Benova.\n\nSERVICIOS DE AGENDAMIENTO: medicina estética y tratamientos de belleza\n\nTRATAMIENTOS DISPONIBLES:\n- Limpieza facial (60 min)\n- Botox (30 min)\n- Rellenos faciales (45 min)\n- Hidrafacial (75 min)\n- Radiofrecuencia (60 min)\n- Y más tratamientos\n\nINFORMACIÓN DE DISPONIBILIDAD:\n{schedule_context}\n\nPROTOCOLO DE AGENDAMIENTO:\n1. Identificar tratamiento solicitado\n2. Consultar disponibilidad real del sistema\n3. Proponer opciones de fechas y horarios\n4. Confirmar datos del paciente\n5. Proceder con la reserva\n\nTONO: Eficiente, organizado, servicial.\nLONGITUD: Máximo 4 oraciones.\n\nSi hay disponibilidad: \"Perfecto, tengo disponibilidad para [tratamiento] en [fechas]. ¿Cuál te conviene más?\"\nSi no hay disponibilidad: \"Te propongo estas alternativas disponibles en Benova...\"\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}"
        },
        "spa_wellness": {
            "router_agent": "Clasificador de intenciones para Wellness Spa & Relax.\n\nServicios: relajación, bienestar y terapias holísticas\n\nRESPONDE en formato JSON con la clasificación apropiada.\n\nMensaje del usuario: {question}",
            "sales_agent": "Eres Ana, terapeuta especialista de Wellness Spa & Relax.\n\nOBJETIVO: Proporcionar información sobre terapias de relajación y bienestar.\n\nSERVICIOS: relajación, bienestar y terapias holísticas\n\nFILOSOFÍA: Bienestar integral, paz interior, conexión cuerpo-mente\n\nTONO: Cálido, relajante, empático, espiritual.\nLONGITUD: Máximo 5 oraciones.\n\nFINALIZA con: \"¿Te gustaría reservar tu momento de paz en Wellness Spa? 🧘‍♀️\"\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "support_agent": "Eres un especialista en soporte de Wellness Spa & Relax.\n\nFILOSOFÍA: Crear un ambiente de paz y tranquilidad\n\nSERVICIOS: relajación, bienestar y terapias holísticas\n\nTONO: Tranquilo, comprensivo, paciente.\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "emergency_agent": "Eres un especialista en atención de urgencias de Wellness Spa & Relax.\n\nProtocolos disponibles:\n{emergency_protocols}\n\nTONO: Calmado pero atento, empático.\n\nConsulta del usuario: {question}",
            "schedule_agent": "Especialista en agendamiento de Wellness Spa & Relax.\n\nSERVICIOS: terapias de relajación y bienestar\n\nTONO: Tranquilo, organizador de experiencias de paz.\n\nDisponibilidad:\n{schedule_context}\n\nHistorial:\n{chat_history}\n\nConsulta: {question}"
        },
        "medispa": {
            "router_agent": "Clasificador de intenciones para MediSpa Elite.\n\nServicios: medicina estética avanzada y bienestar integral\n\nRESPONDE en formato JSON con la clasificación médica apropiada.\n\nMensaje del usuario: {question}",
            "sales_agent": "Eres Dr. López, especialista de MediSpa Elite en medicina estética avanzada.\n\nOBJETIVO: Proporcionar información médica especializada y comercial.\n\nSERVICIOS: medicina estética avanzada y bienestar integral\n\nENFOQUE: Científico, profesional, resultados comprobados\n\nTONO: Profesional médico, técnico pero accesible, confiable.\nLONGITUD: Máximo 5 oraciones.\n\nFINALIZA con: \"¿Te gustaría agendar tu consulta especializada en MediSpa Elite?\"\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "support_agent": "Especialista en soporte de MediSpa Elite.\n\nENFOQUE: Medicina estética de vanguardia\n\nSERVICIOS: medicina estética avanzada y bienestar integral\n\nTONO: Profesional médico, informativo.\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "emergency_agent": "Especialista en emergencias médicas de MediSpa Elite.\n\nProtocolos médicos especializados:\n{emergency_protocols}\n\nTONO: Médico profesional, tranquilizador pero urgente.\n\nConsulta del usuario: {question}",
            "schedule_agent": "Especialista en agendamiento médico de MediSpa Elite.\n\nSERVICIOS MÉDICOS: medicina estética avanzada\n\nTONO: Profesional médico, organizador de consultas especializadas.\n\nDisponibilidad médica:\n{schedule_context}\n\nHistorial:\n{chat_history}\n\nConsulta: {question}"
        },
        "dental_clinic": {
            "router_agent": "Clasificador de intenciones para Clínica Dental Sonríe.\n\nServicios: odontología general y especializada\n\nPalabras clave dentales: dolor de muela, blanqueamiento, ortodoncia, implante, limpieza dental\n\nRESPONDE en formato JSON con la clasificación dental apropiada.\n\nMensaje del usuario: {question}",
            "sales_agent": "Eres Dr. Martínez, odontólogo especialista de Clínica Dental Sonríe.\n\nOBJETIVO: Proporcionar información odontológica profesional y comercial.\n\nSERVICIOS: odontología general y especializada\n\nENFOQUE: Salud bucal integral, prevención y tratamiento\n\nTONO: Profesional odontológico, confiable, educativo.\nLONGITUD: Máximo 5 oraciones.\n\nFINALIZA con: \"¿Te gustaría agendar tu consulta odontológica en Clínica Dental Sonríe?\"\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "support_agent": "Especialista en soporte de Clínica Dental Sonríe.\n\nENFOQUE: Salud bucal y bienestar dental\n\nSERVICIOS: odontología general y especializada\n\nTONO: Profesional dental, informativo, preventivo.\n\nInformación disponible:\n{context}\n\nHistorial de conversación:\n{chat_history}\n\nConsulta del usuario: {question}",
            "emergency_agent": "Especialista en emergencias dentales de Clínica Dental Sonríe.\n\nProtocolos de urgencias dentales:\n{emergency_protocols}\n\nTONO: Odontólogo profesional, calmado pero urgente.\n\nFINALIZA con: \"Escalando tu emergencia dental en Clínica Dental Sonríe ahora mismo. 🦷\"\n\nConsulta del usuario: {question}",
            "schedule_agent": "Especialista en agendamiento dental de Clínica Dental Sonríe.\n\nSERVICIOS DENTALES: odontología general y especializada\n\nTONO: Profesional dental, organizador de citas odontológicas.\n\nDisponibilidad dental:\n{schedule_context}\n\nHistorial:\n{chat_history}\n\nConsulta: {question}"
        }
    }
    
    # Guardar archivo JSON si no existe o actualizarlo
    with open(prompts_file, 'w', encoding='utf-8') as f:
        json.dump(default_prompts, f, indent=2, ensure_ascii=False)
    logger.info(f"Created/Updated prompts file at {prompts_file}")
    
    # Limpiar claves incorrectas de Redis
    logger.info("\nCleaning up Redis keys...")
    
    # Patrones de claves a limpiar
    patterns_to_clean = [
        "*documents*prompts*",  # Claves mal formadas
        "dental_clinic:prompts:*",  # Formato correcto pero verificar contenido
        "benova:prompts:*",
        "spa_wellness:prompts:*", 
        "medispa:prompts:*"
    ]
    
    for pattern in patterns_to_clean:
        keys_to_check = redis_client.keys(pattern)
        
        for key in keys_to_check:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            
            # Si la clave contiene 'documents', eliminarla
            if 'documents' in key_str:
                logger.info(f"  Removing invalid key: {key_str}")
                redis_client.delete(key)
            else:
                # Verificar el contenido de las claves válidas
                content = redis_client.get(key)
                if content:
                    try:
                        # Intentar decodificar como JSON
                        data = json.loads(content.decode('utf-8'))
                        if isinstance(data, dict) and 'template' in data:
                            logger.info(f"  ✓ Valid custom prompt found: {key_str}")
                        else:
                            # Migrar a nuevo formato si es string directo
                            logger.info(f"  Migrating legacy prompt: {key_str}")
                            parts = key_str.split(':')
                            if len(parts) == 3:
                                company_id, _, agent_name = parts
                                new_data = {
                                    "template": content.decode('utf-8') if isinstance(content, bytes) else content,
                                    "is_custom": True,
                                    "modified_at": datetime.utcnow().isoformat() + "Z",
                                    "modified_by": "migration"
                                }
                                redis_client.set(key, json.dumps(new_data))
                    except (json.JSONDecodeError, AttributeError):
                        # Es un string directo, migrar a nuevo formato
                        logger.info(f"  Migrating string prompt: {key_str}")
                        parts = key_str.split(':')
                        if len(parts) == 3:
                            new_data = {
                                "template": content.decode('utf-8') if isinstance(content, bytes) else str(content),
                                "is_custom": True,
                                "modified_at": datetime.utcnow().isoformat() + "Z",
                                "modified_by": "migration"
                            }
                            redis_client.set(key, json.dumps(new_data))
    
    # Verificar prompts en Redis
    for company_id in default_prompts.keys():
        logger.info(f"\nChecking prompts for company: {company_id}")
        
        for agent_name in default_prompts[company_id].keys():
            redis_key = f"{company_id}:prompts:{agent_name}"
            exists = redis_client.exists(redis_key)
            
            if exists:
                content = redis_client.get(redis_key)
                try:
                    data = json.loads(content.decode('utf-8'))
                    if isinstance(data, dict) and 'template' in data:
                        logger.info(f"  ✓ {agent_name}: Custom prompt exists (new format)")
                    else:
                        logger.info(f"  ⚠ {agent_name}: Custom prompt exists (legacy format)")
                except:
                    logger.info(f"  ⚠ {agent_name}: Custom prompt exists (string format)")
            else:
                logger.info(f"  ○ {agent_name}: Using default prompt")
    
    logger.info("\n✅ Prompt system initialized successfully!")
    return True

def test_prompt_manager():
    """Probar el PromptManager"""
    try:
        from app.services.prompt_manager import PromptManager
    except ImportError:
        logger.warning("PromptManager not found, skipping test")
        return False
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=False)
    
    pm = PromptManager(redis_client)
    
    # Probar obtener todos los prompts
    all_prompts = pm.get_all_prompts('benova')
    
    logger.info("\nPrompts for Benova:")
    for agent, data in all_prompts.items():
        logger.info(f"  {agent}: source={data['source']}, is_custom={data['is_custom']}")
    
    # Probar obtener un prompt específico
    router_prompt = pm.get_prompt('benova', 'router_agent')
    if router_prompt:
        logger.info(f"\nRouter prompt preview: {router_prompt[:100]}...")
    
    return True

if __name__ == "__main__":
    initialize_prompt_system()
    test_prompt_manager()# app/init_prompts.py
"""
Script para inicializar y verificar el sistema de prompts
Ejecutar este script para asegurar que los prompts están correctamente configurados
"""

import os
import json
import redis
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_prompt_system():
    """Inicializar el sistema de prompts con valores por defecto"""
    
    # Conectar a Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=False)
    
    # Ruta del archivo de prompts
    prompts_file = 'app/config/custom_prompts.json'
    
    # Crear directorio si no existe
    os.makedirs('app/config', exist_ok=True)
    
    # Prompts por defecto
    default_prompts = {
        "benova": {
            "router_agent": "Eres el agente router de {company_name}. Tu función es clasificar las intenciones...",
            "sales_agent": "Eres un agente de ventas experto de {company_name}...",
            "support_agent": "Eres el agente de soporte técnico de {company_name}...",
            "emergency_agent": "Eres el agente de emergencias de {company_name}...",
            "schedule_agent": "Eres el agente de agendamiento de {company_name}..."
        },
        "spa_wellness": {
            "router_agent": "Eres el agente router de {company_name}...",
            "sales_agent": "Eres un consultor de bienestar de {company_name}...",
            "support_agent": "Eres el agente de soporte de {company_name}...",
            "emergency_agent": "Eres el agente de respuesta rápida de {company_name}...",
            "schedule_agent": "Eres el coordinador de citas de {company_name}..."
        },
        "medispa": {
            "router_agent": "Eres el agente router de {company_name}...",
            "sales_agent": "Eres un consultor médico-estético de {company_name}...",
            "support_agent": "Eres el agente de atención de {company_name}...",
            "emergency_agent": "Eres el agente médico de urgencias de {company_name}...",
            "schedule_agent": "Eres el coordinador médico de {company_name}..."
        },
        "dental_clinic": {
            "router_agent": "Eres el agente router de {company_name}...",
            "sales_agent": "Eres un asesor dental de {company_name}...",
            "support_agent": "Eres el agente de cuidado dental de {company_name}...",
            "emergency_agent": "Eres el agente de urgencias dentales de {company_name}...",
            "schedule_agent": "Eres el coordinador de citas de {company_name}..."
        }
    }
    
    # Guardar archivo JSON si no existe
    if not os.path.exists(prompts_file):
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(default_prompts, f, indent=2, ensure_ascii=False)
        logger.info(f"Created default prompts file at {prompts_file}")
    else:
        logger.info(f"Prompts file already exists at {prompts_file}")
    
    # Verificar prompts en Redis
    for company_id in default_prompts.keys():
        logger.info(f"\nChecking prompts for company: {company_id}")
        
        for agent_name in default_prompts[company_id].keys():
            redis_key = f"{company_id}:prompts:{agent_name}"
            exists = redis_client.exists(redis_key)
            
            if exists:
                logger.info(f"  ✓ {agent_name}: Custom prompt exists in Redis")
            else:
                logger.info(f"  ○ {agent_name}: Using default prompt")
    
    # Limpiar claves incorrectas de Redis (opcional)
    logger.info("\nCleaning up Redis keys...")
    pattern = "*documents*prompts*"
    keys_to_clean = redis_client.keys(pattern)
    
    for key in keys_to_clean:
        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
        if 'documents' in key_str and 'prompts' in key_str:
            logger.info(f"  Removing invalid key: {key_str}")
            redis_client.delete(key)
    
    logger.info("\n✅ Prompt system initialized successfully!")
    return True

def test_prompt_manager():
    """Probar el PromptManager"""
    from app.services.prompt_manager import PromptManager
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=False)
    
    pm = PromptManager(redis_client)
    
    # Probar obtener todos los prompts
    all_prompts = pm.get_all_prompts('benova')
    
    logger.info("\nPrompts for Benova:")
    for agent, data in all_prompts.items():
        logger.info(f"  {agent}: source={data['source']}, is_custom={data['is_custom']}")
    
    # Probar obtener un prompt específico
    router_prompt = pm.get_prompt('benova', 'router_agent')
    if router_prompt:
        logger.info(f"\nRouter prompt preview: {router_prompt[:100]}...")
    
    return True

if __name__ == "__main__":
    initialize_prompt_system()
    test_prompt_manager()
