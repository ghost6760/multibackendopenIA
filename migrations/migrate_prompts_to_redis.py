#!/usr/bin/env python3
"""
Script de migración de prompts desde archivo JSON a Redis
Ejecutar una sola vez para migrar datos existentes
"""

import os
import sys
import json
import logging
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.prompt_redis_manager import get_prompt_redis_manager
from app.services.redis_service import get_redis_client
from app.config.company_manager import get_company_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_prompts_to_redis():
    """Migrar todos los prompts desde custom_prompts.json a Redis"""
    
    print("=" * 60)
    print("MIGRACIÓN DE PROMPTS A REDIS")
    print("=" * 60)
    
    try:
        # Inicializar managers
        prompt_manager = get_prompt_redis_manager()
        company_manager = get_company_manager()
        redis_client = get_redis_client()
        
        # Verificar conexión a Redis
        redis_client.ping()
        print("✅ Conexión a Redis establecida")
        
        # Buscar archivo de prompts
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            print("⚠️  No se encontró custom_prompts.json - No hay nada que migrar")
            return
        
        print(f"📄 Archivo encontrado: {custom_prompts_file}")
        
        # Cargar prompts desde archivo
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        print(f"📊 Empresas encontradas: {len(custom_prompts)}")
        
        # Estadísticas
        total_prompts = 0
        migrated_prompts = 0
        errors = []
        
        # Migrar cada empresa
        for company_id, company_prompts in custom_prompts.items():
            print(f"\n🏢 Procesando empresa: {company_id}")
            
            # Validar que la empresa existe
            if not company_manager.validate_company_id(company_id):
                print(f"  ⚠️  Empresa {company_id} no está configurada - Saltando")
                continue
            
            # Migrar cada agente
            for agent_name, agent_data in company_prompts.items():
                total_prompts += 1
                
                try:
                    # Solo migrar si tiene prompt personalizado
                    if agent_data.get('is_custom') and agent_data.get('template'):
                        success = prompt_manager.save_custom_prompt(
                            company_id=company_id,
                            agent_name=agent_name,
                            prompt_template=agent_data['template'],
                            modified_by=agent_data.get('modified_by', 'migration')
                        )
                        
                        if success:
                            migrated_prompts += 1
                            print(f"  ✅ {agent_name}: Migrado exitosamente")
                        else:
                            errors.append(f"{company_id}/{agent_name}: Error al guardar")
                            print(f"  ❌ {agent_name}: Error al migrar")
                    else:
                        print(f"  ⏭️  {agent_name}: No tiene prompt personalizado")
                        
                except Exception as e:
                    errors.append(f"{company_id}/{agent_name}: {str(e)}")
                    print(f"  ❌ {agent_name}: Error - {str(e)}")
        
        # Crear backup del archivo original
        if migrated_prompts > 0:
            backup_file = custom_prompts_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(custom_prompts_file, backup_file)
            print(f"\n💾 Archivo original respaldado en: {backup_file}")
            
            # Crear nuevo archivo vacío con estructura básica
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            print(f"📝 Archivo custom_prompts.json recreado vacío")
        
        # Resumen
        print("\n" + "=" * 60)
        print("RESUMEN DE MIGRACIÓN")
        print("=" * 60)
        print(f"📊 Total de prompts procesados: {total_prompts}")
        print(f"✅ Prompts migrados exitosamente: {migrated_prompts}")
        print(f"❌ Errores encontrados: {len(errors)}")
        
        if errors:
            print("\n⚠️  Errores detallados:")
            for error in errors:
                print(f"  - {error}")
        
        # Verificar migración
        print("\n🔍 Verificando migración...")
        redis_keys = redis_client.keys("*:prompts:*")
        print(f"📦 Prompts en Redis: {len(redis_keys)}")
        
        if len(redis_keys) > 0:
            print("✅ Migración completada exitosamente")
        else:
            print("⚠️  No se encontraron prompts en Redis después de la migración")
        
    except Exception as e:
        print(f"\n❌ Error crítico durante la migración: {str(e)}")
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)

def verify_redis_prompts():
    """Verificar y listar todos los prompts en Redis"""
    
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE PROMPTS EN REDIS")
    print("=" * 60)
    
    try:
        redis_client = get_redis_client()
        prompt_manager = get_prompt_redis_manager()
        company_manager = get_company_manager()
        
        # Obtener todas las empresas configuradas
        companies = company_manager.get_all_company_ids()
        
        for company_id in companies:
            print(f"\n🏢 Empresa: {company_id}")
            
            # Obtener todos los prompts de la empresa
            prompts = prompt_manager.get_all_prompts(company_id)
            
            if prompts:
                for agent_name, prompt_data in prompts.items():
                    if prompt_data.get('is_custom'):
                        print(f"  ✅ {agent_name}:")
                        print(f"     - Personalizado: Sí")
                        print(f"     - Modificado: {prompt_data.get('modified_at', 'N/A')}")
                        print(f"     - Por: {prompt_data.get('modified_by', 'N/A')}")
                    else:
                        print(f"  📝 {agent_name}: Usando prompt por defecto")
            else:
                print("  ⚠️  No hay prompts configurados")
        
        # Estadísticas generales
        print("\n" + "=" * 60)
        print("ESTADÍSTICAS GENERALES")
        print("=" * 60)
        
        all_keys = redis_client.keys("*:prompts:*")
        default_keys = redis_client.keys("default_prompts:*")
        
        print(f"📊 Total de keys de prompts: {len(all_keys)}")
        print(f"📝 Prompts por defecto guardados: {len(default_keys)}")
        print(f"🏢 Empresas con prompts: {len(set([k.split(':')[0] for k in all_keys if ':' in k]))}")
        
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {str(e)}")
        logger.error(f"Verification failed: {e}", exc_info=True)

def cleanup_redis_prompts():
    """Limpiar todos los prompts de Redis (usar con cuidado)"""
    
    print("\n" + "=" * 60)
    print("⚠️  LIMPIEZA DE PROMPTS EN REDIS")
    print("=" * 60)
    
    response = input("¿Estás seguro de que quieres eliminar TODOS los prompts de Redis? (si/no): ")
    
    if response.lower() != 'si':
        print("Operación cancelada")
        return
    
    try:
        redis_client = get_redis_client()
        
        # Buscar todas las keys de prompts
        prompt_keys = redis_client.keys("*:prompts:*")
        default_keys = redis_client.keys("default_prompts:*")
        version_keys = redis_client.keys("prompts_version:*")
        
        total_keys = len(prompt_keys) + len(default_keys) + len(version_keys)
        
        if total_keys == 0:
            print("No hay prompts en Redis para eliminar")
            return
        
        print(f"\n🗑️  Eliminando {total_keys} keys...")
        
        # Eliminar keys
        deleted = 0
        for key in prompt_keys + default_keys + version_keys:
            redis_client.delete(key)
            deleted += 1
        
        print(f"✅ {deleted} keys eliminadas exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante la limpieza: {str(e)}")
        logger.error(f"Cleanup failed: {e}", exc_info=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestión de prompts en Redis")
    parser.add_argument(
        'action',
        choices=['migrate', 'verify', 'cleanup'],
        help='Acción a ejecutar'
    )
    
    args = parser.parse_args()
    
    if args.action == 'migrate':
        migrate_prompts_to_redis()
    elif args.action == 'verify':
        verify_redis_prompts()
    elif args.action == 'cleanup':
        cleanup_redis_prompts()
    
    print("\n✨ Proceso completado")
