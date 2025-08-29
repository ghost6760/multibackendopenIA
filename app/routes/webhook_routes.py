from flask import Blueprint, request, jsonify, current_app
from app.services.chatwoot_service import MultiCompanyChatwootService
from app.models.conversation import MultiCompanyConversationManager
from app.services.multiagent_system import MultiCompanyAgentSystem
from app.config.company_config import get_company_config_manager
import logging
import json
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Initialize multi-company services
multi_company_chatwoot = MultiCompanyChatwootService()
multi_company_conversations = MultiCompanyConversationManager()
multi_company_agents = MultiCompanyAgentSystem()

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook/chatwoot', methods=['POST'])
def handle_chatwoot_webhook():
    """Handle incoming Chatwoot webhooks with multi-company support"""
    
    start_time = time.time()
    
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.error("No webhook data received")
            return jsonify({
                "status": "error",
                "error": "No data received"
            }), 400
        
        # Extract basic info for logging
        event = webhook_data.get('event', 'unknown')
        message_id = webhook_data.get('id')
        conversation_id = webhook_data.get('conversation', {}).get('id')
        
        logger.info(f"🔄 Webhook received: event={event}, message_id={message_id}, conversation_id={conversation_id}")
        
        # Determine company from webhook data
        company_config_manager = get_company_config_manager()
        company_id = company_config_manager.extract_company_id_from_webhook(webhook_data)
        
        logger.info(f"📋 Processing webhook for company: {company_id}")
        
        # Handle different event types
        if event == "message_created":
            return handle_message_created(webhook_data, company_id, start_time)
        elif event == "conversation_updated":
            return handle_conversation_updated(webhook_data, company_id, start_time)
        else:
            logger.info(f"ℹ️ Ignoring webhook event: {event} for company {company_id}")
            return jsonify({
                "status": "ignored",
                "event": event,
                "company_id": company_id,
                "reason": "Event not handled"
            }), 200
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"❌ Critical error in webhook handler after {processing_time:.2f}s")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "processing_time": round(processing_time, 2)
        }), 500


def handle_message_created(webhook_data: dict, company_id: str, start_time: float) -> tuple:
    """Handle message_created events with multi-company support"""
    
    try:
        # Get company-specific services
        conversation_manager = multi_company_conversations.get_manager_for_company(company_id)
        multiagent_system = multi_company_agents.get_agent_system_for_company(company_id)
        
        # Process the message using multi-company service
        result = multi_company_chatwoot.process_webhook_message(
            webhook_data,
            conversation_manager,
            multiagent_system
        )
        
        processing_time = time.time() - start_time
        
        # Add timing and company info to result
        result.update({
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Determine HTTP status code based on result
        if result.get("status") == "success":
            status_code = 200
            logger.info(f"✅ Message processed successfully for company {company_id} in {processing_time:.2f}s")
        elif result.get("status") == "already_processed":
            status_code = 200
            logger.info(f"🔄 Message already processed for company {company_id}")
        elif result.get("status") == "bot_inactive":
            status_code = 200
            logger.info(f"⏸️ Bot inactive for company {company_id}: {result.get('message', 'Unknown reason')}")
        elif result.get("status") == "non_incoming_message":
            status_code = 200
            logger.info(f"ℹ️ Non-incoming message ignored for company {company_id}")
        else:
            status_code = 500
            logger.error(f"❌ Message processing failed for company {company_id}: {result.get('error', 'Unknown error')}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"❌ Error in handle_message_created for company {company_id} after {processing_time:.2f}s")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "error": str(e),
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


def handle_conversation_updated(webhook_data: dict, company_id: str, start_time: float) -> tuple:
    """Handle conversation_updated events with multi-company support"""
    
    try:
        # Get company-specific Chatwoot service
        chatwoot_service = multi_company_chatwoot.get_service_for_company(company_id)
        
        # Extract conversation data
        conversation_data = webhook_data.get("conversation", {})
        conversation_id = conversation_data.get("id")
        conversation_status = conversation_data.get("status")
        
        if not conversation_id:
            raise ValueError("Missing conversation ID in conversation_updated event")
        
        # Handle the conversation update
        success = chatwoot_service.handle_conversation_updated(conversation_data)
        
        processing_time = time.time() - start_time
        
        result = {
            "status": "success" if success else "error",
            "company_id": company_id,
            "company_name": chatwoot_service.company_config.company_name,
            "conversation_id": conversation_id,
            "conversation_status": conversation_status,
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            logger.info(f"✅ Conversation updated for company {company_id}: {conversation_id} -> {conversation_status}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to handle conversation update for company {company_id}")
            result["error"] = "Failed to process conversation update"
            return jsonify(result), 500
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"❌ Error in handle_conversation_updated for company {company_id} after {processing_time:.2f}s")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "error": str(e),
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@webhook_bp.route('/webhook/status', methods=['GET'])
def webhook_status():
    """Get webhook service status across all companies"""
    
    try:
        # Get global status from multi-company services
        chatwoot_status = multi_company_chatwoot.get_global_status_summary()
        agent_status = multi_company_agents.get_global_health_check()
        conversation_status = multi_company_conversations.get_global_stats()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "chatwoot": chatwoot_status,
                "agents": agent_status,
                "conversations": conversation_status
            },
            "webhook_endpoint": "/webhook/chatwoot",
            "supported_events": ["message_created", "conversation_updated"],
            "multi_company_support": True
        }), 200
        
    except Exception as e:
        logger.exception("Error getting webhook status")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@webhook_bp.route('/webhook/companies', methods=['GET'])
def list_webhook_companies():
    """List all companies configured for webhook processing"""
    
    try:
        company_config_manager = get_company_config_manager()
        all_companies = company_config_manager.get_all_companies()
        
        companies_info = []
        for company_id, config in all_companies.items():
            companies_info.append({
                "company_id": company_id,
                "company_name": config.company_name,
                "industry_type": config.industry_type,
                "services": config.services,
                "redis_prefix": config.redis_prefix,
                "vectorstore_index": config.vectorstore_index,
                "schedule_service_url": config.schedule_service_url
            })
        
        return jsonify({
            "total_companies": len(companies_info),
            "companies": companies_info,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("Error listing webhook companies")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@webhook_bp.route('/webhook/test/<company_id>', methods=['POST'])
def test_webhook_for_company(company_id: str):
    """Test webhook processing for a specific company"""
    
    try:
        # Validate company exists
        company_config_manager = get_company_config_manager()
        company_config = company_config_manager.get_company_config(company_id)
        
        # Create test webhook data
        test_webhook_data = {
            "event": "message_created",
            "id": 999999,
            "message_type": "incoming",
            "content": "Test message from webhook test endpoint",
            "conversation": {
                "id": 999999,
                "status": "open",
                "meta": {
                    "company_id": company_id
                },
                "contact_inbox": {
                    "contact_id": "test_contact_999"
                }
            },
            "attachments": []
        }
        
        # Get company-specific services
        conversation_manager = multi_company_conversations.get_manager_for_company(company_id)
        multiagent_system = multi_company_agents.get_agent_system_for_company(company_id)
        chatwoot_service = multi_company_chatwoot.get_service_for_company(company_id)
        
        # Process test message (but don't actually send to Chatwoot)
        start_time = time.time()
        
        # Simulate processing without sending
        user_id = conversation_manager._create_user_id("test_contact_999")
        ai_response, agent_used = multiagent_system.get_response(
            "Test message from webhook test endpoint",
            user_id,
            conversation_manager
        )
        
        processing_time = time.time() - start_time
        
        return jsonify({
            "status": "test_success",
            "company_id": company_id,
            "company_name": company_config.company_name,
            "test_data": {
                "user_id": user_id,
                "ai_response": ai_response,
                "agent_used": agent_used,
                "processing_time": round(processing_time, 2)
            },
            "services_health": {
                "multiagent_system": multiagent_system.health_check(),
                "chatwoot_service": chatwoot_service.get_status_summary()
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception(f"Error testing webhook for company {company_id}")
        
        return jsonify({
            "status": "test_error",
            "company_id": company_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@webhook_bp.route('/webhook/stats', methods=['GET'])
def webhook_statistics():
    """Get comprehensive webhook statistics across all companies"""
    
    try:
        # Get statistics from all services
        chatwoot_stats = multi_company_chatwoot.get_global_status_summary()
        agent_stats = multi_company_agents.get_global_system_stats()
        conversation_stats = multi_company_conversations.get_global_stats()
        
        # Combine statistics
        combined_stats = {
            "overview": {
                "total_companies": max(
                    chatwoot_stats.get("total_companies", 0),
                    agent_stats.get("total_companies", 0),
                    conversation_stats.get("total_companies", 0)
                ),
                "total_conversations": conversation_stats.get("global_totals", {}).get("conversations", 0),
                "total_messages": conversation_stats.get("global_totals", {}).get("messages", 0),
                "total_agents": agent_stats.get("global_totals", {}).get("total_agents", 0),
                "companies_with_selenium": agent_stats.get("global_totals", {}).get("companies_with_selenium", 0),
                "industries_served": agent_stats.get("global_totals", {}).get("industries_served", [])
            },
            "services": {
                "chatwoot": chatwoot_stats,
                "agents": agent_stats,
                "conversations": conversation_stats
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(combined_stats), 200
        
    except Exception as e:
        logger.exception("Error getting webhook statistics")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@webhook_bp.route('/webhook/health', methods=['GET'])
def webhook_health_check():
    """Comprehensive health check for webhook service"""
    
    try:
        # Check all company services
        health_results = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check multi-company services
        try:
            chatwoot_health = multi_company_chatwoot.get_global_status_summary()
            health_results["components"]["chatwoot"] = {
                "status": "healthy" if chatwoot_health.get("total_companies", 0) > 0 else "warning",
                "details": chatwoot_health
            }
        except Exception as e:
            health_results["components"]["chatwoot"] = {
                "status": "error",
                "error": str(e)
            }
            health_results["overall_status"] = "degraded"
        
        try:
            agent_health = multi_company_agents.get_global_health_check()
            health_results["components"]["agents"] = {
                "status": "healthy" if agent_health.get("global_summary", {}).get("healthy_companies", 0) > 0 else "warning",
                "details": agent_health
            }
        except Exception as e:
            health_results["components"]["agents"] = {
                "status": "error",
                "error": str(e)
            }
            health_results["overall_status"] = "degraded"
        
        try:
            conversation_stats = multi_company_conversations.get_global_stats()
            health_results["components"]["conversations"] = {
                "status": "healthy",
                "details": conversation_stats
            }
        except Exception as e:
            health_results["components"]["conversations"] = {
                "status": "error",
                "error": str(e)
            }
            health_results["overall_status"] = "degraded"
        
        # Determine overall HTTP status
        if health_results["overall_status"] == "healthy":
            status_code = 200
        elif health_results["overall_status"] == "degraded":
            status_code = 207  # Multi-Status
        else:
            status_code = 503  # Service Unavailable
        
        return jsonify(health_results), status_code
        
    except Exception as e:
        logger.exception("Critical error in webhook health check")
        
        return jsonify({
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503


# Error handlers
@webhook_bp.errorhandler(400)
def handle_bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        "status": "error",
        "error": "Bad request",
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }), 400

@webhook_bp.errorhandler(404)
def handle_not_found(error):
    """Handle not found errors"""
    return jsonify({
        "status": "error",
        "error": "Endpoint not found",
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }), 404

@webhook_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors"""
    logger.exception("Internal server error in webhook routes")
    return jsonify({
        "status": "error",
        "error": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }), 500
