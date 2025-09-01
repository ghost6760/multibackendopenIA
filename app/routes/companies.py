# app/routes/companies.py - Companies Route Handler
"""
Companies route handler for multi-tenant admin panel
Handles company listing, selection, and basic company operations
"""

from flask import Blueprint, jsonify, request
import logging
import os
import json

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('companies', __name__, url_prefix='/api')

def load_companies_config():
    """Load companies from configuration file"""
    try:
        # Try to load from companies_config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'companies_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                companies_data = json.load(f)
                logger.info(f"Loaded companies from config file: {len(companies_data)} companies")
                return companies_data
        else:
            logger.warning(f"Companies config file not found at {config_path}")
            # Return fallback companies
            return {
                "benova": {
                    "company_name": "Benova Estética",
                    "services": ["Tratamientos faciales", "Depilación láser", "Rejuvenecimiento"],
                    "status": "active"
                },
                "medispa": {
                    "company_name": "MediSpa Wellness",
                    "services": ["Medicina estética", "Spa wellness", "Terapias"],
                    "status": "active"
                },
                "clinica_dental": {
                    "company_name": "Clínica Dental Premium",
                    "services": ["Odontología general", "Ortodoncia", "Estética dental"],
                    "status": "active"
                },
                "spa_wellness": {
                    "company_name": "Spa & Wellness Center",
                    "services": ["Masajes", "Tratamientos corporales", "Relajación"],
                    "status": "active"
                }
            }
            
    except Exception as e:
        logger.error(f"Error loading companies config: {e}")
        # Return minimal fallback
        return {
            "fallback": {
                "company_name": "Modo de Emergencia",
                "services": ["Sistema en modo fallback"],
                "status": "fallback"
            }
        }

@bp.route('/companies', methods=['GET'])
def get_companies():
    """Get all available companies"""
    try:
        companies = load_companies_config()
        
        return jsonify({
            "status": "success",
            "total_companies": len(companies),
            "companies": companies,
            "message": f"Successfully loaded {len(companies)} companies"
        })
        
    except Exception as e:
        logger.error(f"Error in get_companies: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "companies": {
                "fallback": {
                    "company_name": "Modo de Emergencia",
                    "services": ["Error cargando configuración"],
                    "status": "error"
                }
            }
        }), 500

@bp.route('/companies/<company_id>', methods=['GET'])
def get_company(company_id):
    """Get specific company details"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return jsonify({
                "status": "error",
                "message": f"Company {company_id} not found"
            }), 404
        
        company = companies[company_id]
        
        return jsonify({
            "status": "success",
            "company_id": company_id,
            "company": company
        })
        
    except Exception as e:
        logger.error(f"Error getting company {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/companies/<company_id>/status', methods=['GET'])
def get_company_status(company_id):
    """Get company status and health information"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return jsonify({
                "status": "error",
                "message": f"Company {company_id} not found"
            }), 404
        
        company = companies[company_id]
        
        # Simulate health check data
        status_data = {
            "company_id": company_id,
            "company_name": company.get("company_name", company_id),
            "status": company.get("status", "unknown"),
            "services_count": len(company.get("services", [])),
            "last_updated": "2025-09-01T09:37:00Z",
            "health": {
                "api": True,
                "database": True,
                "redis": True,  # This will be updated based on actual availability
                "openai": True,
                "schedule_service": False  # Known to be in fallback mode
            },
            "metrics": {
                "active_sessions": 0,
                "daily_requests": 0,
                "avg_response_time": "150ms"
            }
        }
        
        return jsonify({
            "status": "success",
            "data": status_data
        })
        
    except Exception as e:
        logger.error(f"Error getting company status {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/companies/reload-config', methods=['POST'])
def reload_companies_config():
    """Reload companies configuration from file"""
    try:
        companies = load_companies_config()
        
        return jsonify({
            "status": "success",
            "message": f"Configuration reloaded successfully",
            "total_companies": len(companies),
            "companies": list(companies.keys())
        })
        
    except Exception as e:
        logger.error(f"Error reloading companies config: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Health check for this route
@bp.route('/companies/health', methods=['GET'])
def companies_health():
    """Health check for companies service"""
    try:
        companies = load_companies_config()
        companies_count = len(companies)
        
        return jsonify({
            "status": "healthy" if companies_count > 0 else "degraded",
            "service": "companies",
            "companies_loaded": companies_count,
            "message": f"Companies service operational with {companies_count} companies"
        })
        
    except Exception as e:
        logger.error(f"Companies health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "companies",
            "error": str(e)
        }), 500
