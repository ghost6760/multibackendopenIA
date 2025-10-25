# Tools, Audit Trail & Compensation System - User Guide

## Overview

This guide covers the complete Tools, Audit Trail, and Compensation/Rollback system for the multi-agent platform.

### Components

1. **ToolExecutor** - Unified tool execution with automatic audit logging
2. **AuditManager** - Audit trail system for tracking all critical actions
3. **EmailService** - Multi-provider email service
4. **CompensationOrchestrator** - Saga pattern for compensating transactions

---

## 1. ToolExecutor

### Purpose

ToolExecutor provides a unified interface for executing tools (API calls, notifications, bookings, etc.) with automatic audit trail logging.

### Features

- ✅ Unified tool execution interface
- ✅ Automatic audit trail logging (before/after execution)
- ✅ Multi-tenant support
- ✅ Service injection (dependency injection pattern)
- ✅ Error handling with retry
- ✅ Compensable action tracking

### Basic Usage

```python
from app.workflows.tool_executor import ToolExecutor
from app.models.audit_trail import AuditManager

# Create tool executor
audit_manager = AuditManager(company_id="benova")
tool_executor = ToolExecutor(
    company_id="benova",
    audit_manager=audit_manager
)

# Inject required services
tool_executor.set_vectorstore_service(vectorstore_service)
tool_executor.set_calendar_service(calendar_service)
tool_executor.set_email_service(email_service)

# Execute a tool
result = tool_executor.execute_tool(
    tool_name="knowledge_base",
    parameters={"query": "¿Cuánto cuesta el botox?", "top_k": 3},
    user_id="user_123",
    agent_name="sales_agent",
    conversation_id="conv_456"
)

# Check result
if result["success"]:
    print(f"Tool executed successfully: {result['data']}")
    print(f"Audit ID: {result['audit_id']}")
else:
    print(f"Tool failed: {result['error']}")
```

### Available Tools

| Tool | Description | Compensable | Service Required |
|------|-------------|-------------|------------------|
| `knowledge_base` | RAG search in knowledge base | No | VectorstoreService |
| `google_calendar` | Calendar operations | **Yes** | CalendarIntegrationService |
| `send_email` | Send emails | No | EmailService |
| `send_whatsapp` | Send WhatsApp messages | No | ChatwootService |
| `transcribe_audio` | Audio transcription | No | MultimediaService |
| `analyze_image` | Image analysis (GPT-4 Vision) | No | MultimediaService |
| `text_to_speech` | Convert text to speech | No | MultimediaService |

### Execute Tool Response Format

```python
{
    "success": bool,
    "tool": str,
    "data": Any,
    "error": Optional[str],
    "audit_id": Optional[str]  # Present when audit is enabled
}
```

### Examples

#### Example 1: RAG Search

```python
result = tool_executor.execute_tool(
    tool_name="knowledge_base",
    parameters={
        "query": "¿Qué tratamientos ofrecen para arrugas?",
        "top_k": 5
    },
    user_id="user_maria",
    agent_name="sales_agent"
)

# Result:
# {
#     "success": True,
#     "tool": "knowledge_base",
#     "data": {
#         "query": "¿Qué tratamientos ofrecen para arrugas?",
#         "results": [
#             {"content": "...", "metadata": {...}},
#             ...
#         ],
#         "total_found": 5
#     },
#     "audit_id": "audit_xyz123"
# }
```

#### Example 2: Create Calendar Booking

```python
result = tool_executor.execute_tool(
    tool_name="google_calendar",
    parameters={
        "action": "create_booking",
        "booking_data": {
            "date": "2025-01-20",
            "time": "10:00",
            "treatment": "Botox",
            "customer_name": "María González",
            "customer_email": "maria@example.com"
        }
    },
    user_id="user_maria",
    agent_name="schedule_agent",
    conversation_id="conv_789"
)

# This creates a COMPENSABLE audit entry
# If booking needs to be cancelled, it can be rolled back
```

#### Example 3: Send Email

```python
result = tool_executor.execute_tool(
    tool_name="send_email",
    parameters={
        "to_email": "customer@example.com",
        "subject": "Confirmación de Cita - Benova Clinic",
        "body_html": "<h1>Su cita ha sido confirmada</h1>...",
        "body_text": "Su cita ha sido confirmada..."
    },
    user_id="user_maria",
    agent_name="schedule_agent"
)
```

#### Example 4: Using Email Templates

```python
result = tool_executor.execute_tool(
    tool_name="send_email",
    parameters={
        "to_email": "customer@example.com",
        "template_name": "appointment_confirmation",
        "template_vars": {
            "customer_name": "María González",
            "appointment_date": "20 de Enero, 2025",
            "appointment_time": "10:00 AM",
            "treatment": "Aplicación de Botox"
        }
    },
    user_id="user_maria"
)
```

---

## 2. AuditManager

### Purpose

AuditManager provides a comprehensive audit trail system for logging all critical actions with Redis persistence.

### Features

- ✅ Automatic action logging (pending → success/failed)
- ✅ Multi-tenant isolation (company-specific)
- ✅ Compensation tracking for rollback
- ✅ Duration tracking for performance monitoring
- ✅ Query by user, action type, date range
- ✅ 90-day TTL (configurable)
- ✅ Tagging system for categorization

### Basic Usage

```python
from app.models.audit_trail import AuditManager

# Create audit manager
audit_manager = AuditManager(company_id="benova")

# Log an action
entry = audit_manager.log_action(
    user_id="user_123",
    action_type="booking",
    action_name="google_calendar.create_event",
    input_params={"date": "2025-01-20", "time": "10:00"},
    compensable=True,
    compensation_action="google_calendar.delete_event",
    compensation_params={"event_id": "to_be_filled"},
    agent_name="schedule_agent",
    conversation_id="conv_456",
    tags=["booking", "calendar"]
)

audit_id = entry.audit_id

# Mark as successful
audit_manager.mark_success(
    audit_id=audit_id,
    result={"event_id": "evt_abc123", "status": "confirmed"},
    duration_ms=250.5
)

# Or mark as failed
audit_manager.mark_failed(
    audit_id=audit_id,
    error_message="Calendar API timeout",
    duration_ms=5000
)
```

### Compensation (Rollback)

```python
# Compensate (rollback) a successful action
result = audit_manager.compensate(
    audit_id=audit_id,
    reason="User cancelled appointment"
)

if result:
    print("Action compensated successfully")
    # Status changed to "compensated"
```

### Querying Audit Trail

```python
# Get all actions for a user
user_actions = audit_manager.get_user_actions(
    user_id="user_maria",
    limit=50
)

# Get actions by type
booking_actions = audit_manager.get_actions_by_type(
    action_type="booking",
    limit=100
)

# Get specific entry
entry = audit_manager.get_entry(audit_id="audit_xyz123")
if entry:
    print(f"Status: {entry.status}")
    print(f"Duration: {entry.duration_ms}ms")
    print(f"Compensable: {entry.compensable}")
```

### Action Types

- `booking` - Calendar bookings
- `notification` - Emails, WhatsApp, SMS
- `ticket` - Support tickets
- `rag_search` - Knowledge base searches
- `api_call` - Generic API calls

### Entry Lifecycle

```
pending → success → [compensated]
   ↓
 failed
```

---

## 3. EmailService

### Purpose

Multi-provider email service with template support and automatic retry.

### Features

- ✅ Multiple providers: SMTP, SendGrid, Mailgun
- ✅ Template system with variable substitution
- ✅ Retry with exponential backoff
- ✅ HTML + Text email support
- ✅ CC, BCC, Reply-To support
- ✅ Multi-tenant configuration

### Configuration

```python
from app.services.email_service import EmailService, EmailConfig

# SMTP Configuration
smtp_config = EmailConfig(
    company_id="benova",
    from_email="noreply@benova.com",
    from_name="Benova Clinic",
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_username="your_email@gmail.com",
    smtp_password="your_app_password",
    use_tls=True,
    max_retries=3
)

# SendGrid Configuration
sendgrid_config = EmailConfig(
    company_id="benova",
    from_email="noreply@benova.com",
    from_name="Benova Clinic",
    sendgrid_api_key="SG.your_api_key_here"
)

# Mailgun Configuration
mailgun_config = EmailConfig(
    company_id="benova",
    from_email="noreply@benova.com",
    from_name="Benova Clinic",
    mailgun_api_key="key-your_key_here",
    mailgun_domain="mg.benova.com"
)
```

### Basic Email Sending

```python
email_service = EmailService(config=smtp_config)

result = email_service.send_email(
    to_email="customer@example.com",
    subject="Confirmación de Cita",
    body_html="<h1>Su cita ha sido confirmada</h1><p>Fecha: 20/01/2025</p>",
    body_text="Su cita ha sido confirmada. Fecha: 20/01/2025",
    cc=["admin@benova.com"],
    reply_to="info@benova.com"
)

if result["success"]:
    print(f"Email sent via {result['provider']}")
else:
    print(f"Failed to send email: {result['error']}")
```

### Template-Based Emails

```python
result = email_service.send_template_email(
    to_email="customer@example.com",
    template_name="appointment_confirmation",
    template_vars={
        "customer_name": "María González",
        "appointment_date": "20 de Enero, 2025",
        "appointment_time": "10:00 AM",
        "treatment": "Aplicación de Botox",
        "clinic_name": "Benova Clinic",
        "clinic_phone": "+1 234 567 8900"
    }
)
```

### Available Templates

1. **appointment_confirmation** - Confirm scheduled appointment
   - Required vars: `customer_name`, `appointment_date`, `appointment_time`, `treatment`

2. **appointment_reminder** - Remind about upcoming appointment
   - Required vars: `customer_name`, `appointment_date`, `appointment_time`, `treatment`

---

## 4. CompensationOrchestrator (Saga Pattern)

### Purpose

Implements the Saga pattern for managing compensating transactions with automatic rollback on failures.

### Features

- ✅ Sequential action execution
- ✅ Automatic compensation on failure (LIFO order)
- ✅ Retry with exponential backoff
- ✅ Integration with AuditManager
- ✅ Multi-step workflow support

### Basic Usage

```python
from app.workflows.compensation_orchestrator import CompensationOrchestrator

# Create orchestrator
orchestrator = CompensationOrchestrator(
    company_id="benova",
    audit_manager=audit_manager
)

# Create a saga
saga = orchestrator.create_saga(
    user_id="user_maria",
    saga_name="complete_booking_flow",
    conversation_id="conv_789"
)
```

### Adding Actions to Saga

```python
# Action 1: Create calendar event (compensable)
orchestrator.add_action(
    saga_id=saga.saga_id,
    action_type="booking",
    action_name="create_calendar_event",
    executor=lambda: tool_executor.execute_tool(
        tool_name="google_calendar",
        parameters={
            "action": "create_booking",
            "booking_data": {...}
        },
        user_id="user_maria"
    ),
    compensator=lambda result: tool_executor.execute_tool(
        tool_name="google_calendar",
        parameters={
            "action": "delete_booking",
            "event_id": result["data"]["event_id"]
        },
        user_id="user_maria"
    )
)

# Action 2: Send confirmation email (non-compensable)
orchestrator.add_action(
    saga_id=saga.saga_id,
    action_type="notification",
    action_name="send_confirmation_email",
    executor=lambda: tool_executor.execute_tool(
        tool_name="send_email",
        parameters={
            "to_email": "customer@example.com",
            "template_name": "appointment_confirmation",
            "template_vars": {...}
        },
        user_id="user_maria"
    ),
    compensator=None  # Cannot undo sending email
)
```

### Execute Saga

```python
result = orchestrator.execute_saga(saga.saga_id)

if result["success"]:
    print(f"Saga completed successfully")
    print(f"Actions executed: {result['actions_executed']}")
else:
    print(f"Saga failed and was compensated")
    print(f"Error: {result['error']}")
    print(f"Actions compensated: {result['actions_compensated']}")
```

### Complete Example: Booking Flow

```python
def create_booking_saga(user_id, booking_data, customer_email):
    """
    Create a complete booking saga:
    1. Create calendar event
    2. Send confirmation email
    3. If any step fails, rollback previous steps
    """

    # Create saga
    saga = orchestrator.create_saga(
        user_id=user_id,
        saga_name="complete_booking"
    )

    # Step 1: Create calendar event
    orchestrator.add_action(
        saga_id=saga.saga_id,
        action_type="booking",
        action_name="create_calendar_event",
        executor=lambda: tool_executor.execute_tool(
            tool_name="google_calendar",
            parameters={
                "action": "create_booking",
                "booking_data": booking_data
            },
            user_id=user_id
        ),
        compensator=lambda result: {
            "success": True,
            "message": "Event deleted (compensated)"
        }
    )

    # Step 2: Send confirmation
    orchestrator.add_action(
        saga_id=saga.saga_id,
        action_type="notification",
        action_name="send_email_confirmation",
        executor=lambda: tool_executor.execute_tool(
            tool_name="send_email",
            parameters={
                "to_email": customer_email,
                "template_name": "appointment_confirmation",
                "template_vars": {
                    "customer_name": booking_data["customer_name"],
                    "appointment_date": booking_data["date"],
                    "appointment_time": booking_data["time"],
                    "treatment": booking_data["treatment"]
                }
            },
            user_id=user_id
        )
    )

    # Execute saga
    result = orchestrator.execute_saga(saga.saga_id)
    return result

# Usage
result = create_booking_saga(
    user_id="user_maria",
    booking_data={
        "date": "2025-01-20",
        "time": "10:00",
        "treatment": "Botox",
        "customer_name": "María González"
    },
    customer_email="maria@example.com"
)
```

---

## 5. Integration with StateGraph

The tools are integrated into the StateGraph orchestrator as actionable nodes:

### Tool Nodes in StateGraph

```python
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph

# Create orchestrator with tool executor
orchestrator_graph = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents={
        "sales": sales_agent,
        "schedule": schedule_agent,
        "support": support_agent
    },
    company_id="benova",
    tool_executor=tool_executor  # Inject tool executor
)

# The graph now has tool nodes:
# - execute_booking (after schedule agent confirms appointment)
# - send_notification (after booking is created)
# - create_ticket (if support detects a problem)
```

### Automatic Tool Execution Flow

```
User: "Quiero agendar una cita para botox el 20 de enero a las 10am"
  ↓
Router Agent → Classify intent: "schedule"
  ↓
Schedule Agent → Process request, confirm appointment
  ↓
Conditional Routing → Detects "has_appointment" in shared context
  ↓
execute_booking Tool Node → Creates calendar event (compensable)
  ↓
send_notification Tool Node → Sends confirmation email
  ↓
Response to User: "✅ Su cita ha sido confirmada..."
```

---

## 6. Testing

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_audit_manager.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Test Structure

```
tests/
├── __init__.py
├── unit/
│   ├── test_audit_manager.py
│   ├── test_email_service.py
│   └── test_compensation_orchestrator.py
└── integration/
    └── test_tools_integration.py
```

---

## 7. Best Practices

### 1. Always Use Audit Trail

```python
# ✅ Good: Pass user_id for audit trail
result = tool_executor.execute_tool(
    tool_name="send_email",
    parameters={...},
    user_id="user_123",  # IMPORTANT
    agent_name="schedule_agent"
)

# ❌ Bad: Missing user_id
result = tool_executor.execute_tool(
    tool_name="send_email",
    parameters={...}
)
```

### 2. Use Saga for Multi-Step Operations

```python
# ✅ Good: Use Saga for booking + notification
saga = orchestrator.create_saga(...)
orchestrator.add_action(...)  # Create booking
orchestrator.add_action(...)  # Send email
result = orchestrator.execute_saga(saga.saga_id)

# ❌ Bad: Manual execution without rollback capability
tool_executor.execute_tool("google_calendar", ...)
tool_executor.execute_tool("send_email", ...)
# No way to rollback if email fails!
```

### 3. Add Compensators for Critical Actions

```python
# ✅ Good: Compensable booking
orchestrator.add_action(
    executor=create_booking_lambda,
    compensator=delete_booking_lambda  # Can rollback
)

# ⚠️ Acceptable: Non-compensable notification
orchestrator.add_action(
    executor=send_email_lambda,
    compensator=None  # Cannot undo email
)
```

### 4. Query Audit Trail for Analytics

```python
# Get all bookings for a user
bookings = audit_manager.get_actions_by_type("booking")
successful_bookings = [b for b in bookings if b.status == "success"]

# Calculate average booking time
avg_duration = sum(b.duration_ms for b in successful_bookings) / len(successful_bookings)
print(f"Average booking time: {avg_duration}ms")
```

---

## 8. Troubleshooting

### Issue: Tools not creating audit entries

**Cause**: `user_id` not provided to `execute_tool()`

**Solution**: Always pass `user_id` parameter

```python
result = tool_executor.execute_tool(
    tool_name="...",
    parameters={...},
    user_id="user_123"  # Required for audit
)
```

### Issue: Saga not compensating

**Cause**: Missing compensator function

**Solution**: Add compensator for critical actions

```python
orchestrator.add_action(
    executor=my_executor,
    compensator=my_compensator  # Add this!
)
```

### Issue: Email not sending

**Cause**: EmailService not injected into ToolExecutor

**Solution**: Inject email service

```python
email_service = EmailService(config=email_config)
tool_executor.set_email_service(email_service)
```

---

## 9. Configuration Examples

### Production Configuration (Redis + SendGrid)

```python
from app.models.audit_trail import AuditManager
from app.services.email_service import EmailService, EmailConfig
from app.workflows.tool_executor import ToolExecutor

# Audit Manager with Redis
audit_manager = AuditManager(
    company_id="benova",
    ttl_days=90,
    enabled=True
)

# Email Service with SendGrid
email_config = EmailConfig(
    company_id="benova",
    from_email="noreply@benova.com",
    from_name="Benova Clinic",
    sendgrid_api_key=os.getenv("SENDGRID_API_KEY"),
    max_retries=3,
    retry_delay=2.0
)
email_service = EmailService(config=email_config)

# Tool Executor
tool_executor = ToolExecutor(
    company_id="benova",
    audit_manager=audit_manager
)
tool_executor.set_email_service(email_service)
tool_executor.set_calendar_service(calendar_service)
tool_executor.set_vectorstore_service(vectorstore_service)
```

---

## 10. API Reference

### ToolExecutor Methods

- `execute_tool(tool_name, parameters, user_id=None, agent_name=None, conversation_id=None)` - Execute a tool
- `get_available_tools()` - Get status of all tools
- `get_tool_info(tool_name)` - Get info for specific tool
- `set_vectorstore_service(service)` - Inject RAG service
- `set_calendar_service(service)` - Inject calendar service
- `set_email_service(service)` - Inject email service
- `set_chatwoot_service(service)` - Inject WhatsApp service
- `set_multimedia_service(service)` - Inject multimedia service

### AuditManager Methods

- `log_action(...)` - Log a new action
- `mark_success(audit_id, result, duration_ms)` - Mark action as successful
- `mark_failed(audit_id, error_message, duration_ms)` - Mark action as failed
- `compensate(audit_id, reason)` - Compensate (rollback) an action
- `get_entry(audit_id)` - Get specific audit entry
- `get_user_actions(user_id, limit=100)` - Get user's actions
- `get_actions_by_type(action_type, limit=100)` - Get actions by type

### CompensationOrchestrator Methods

- `create_saga(user_id, saga_name, conversation_id=None)` - Create new saga
- `add_action(saga_id, action_type, action_name, executor, compensator=None, ...)` - Add action to saga
- `execute_saga(saga_id)` - Execute saga with auto-compensation
- `get_saga(saga_id)` - Retrieve saga

---

## Conclusion

This system provides enterprise-grade audit trail, compensation, and tool execution capabilities for the multi-agent platform. All critical actions are logged, compensable, and auditable.

For questions or issues, please refer to the test files for additional examples.
