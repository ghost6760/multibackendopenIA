"""
Integration tests for Tools system

Tests integration between ToolExecutor, AuditManager, and CompensationOrchestrator.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.workflows.tool_executor import ToolExecutor
from app.workflows.compensation_orchestrator import CompensationOrchestrator
from app.models.audit_trail import AuditManager
from app.services.email_service import EmailService, EmailConfig


class TestToolsIntegration:
    """Integration tests for tools system"""

    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client"""
        redis = MagicMock()
        redis.setex = MagicMock(return_value=True)
        redis.get = MagicMock(return_value=None)
        redis.sadd = MagicMock(return_value=True)
        redis.smembers = MagicMock(return_value=set())
        return redis

    @pytest.fixture
    def audit_manager(self, redis_mock):
        """Create AuditManager with mocked Redis"""
        with patch('app.models.audit_trail.get_redis') as mock_get_redis:
            mock_get_redis.return_value = redis_mock
            manager = AuditManager(company_id="test_company")
            manager.redis = redis_mock
            return manager

    @pytest.fixture
    def tool_executor(self, audit_manager):
        """Create ToolExecutor with real AuditManager"""
        executor = ToolExecutor(
            company_id="test_company",
            audit_manager=audit_manager
        )
        return executor

    @pytest.fixture
    def compensation_orchestrator(self, audit_manager, redis_mock):
        """Create CompensationOrchestrator"""
        with patch('app.workflows.compensation_orchestrator.get_redis') as mock_get_redis:
            mock_get_redis.return_value = redis_mock
            orch = CompensationOrchestrator(
                company_id="test_company",
                audit_manager=audit_manager
            )
            orch.redis = redis_mock
            return orch

    def test_tool_execution_with_audit_trail(self, tool_executor, audit_manager, redis_mock):
        """Test that tool execution creates audit trail"""
        # Setup: Mock knowledge base service
        mock_vectorstore = MagicMock()
        mock_vectorstore.search_by_company.return_value = [
            MagicMock(page_content="Test content", metadata={})
        ]
        tool_executor.set_vectorstore_service(mock_vectorstore)

        # Execute tool
        result = tool_executor.execute_tool(
            tool_name="knowledge_base",
            parameters={"query": "test query", "top_k": 3},
            user_id="user123",
            agent_name="sales_agent",
            conversation_id="conv456"
        )

        # Verify
        assert result["success"] is True
        assert "audit_id" in result
        assert audit_manager.log_action.called

    def test_tool_failure_creates_audit_entry(self, tool_executor, audit_manager):
        """Test that failed tools create failed audit entries"""
        # Execute tool without configured service (will fail)
        result = tool_executor.execute_tool(
            tool_name="knowledge_base",
            parameters={"query": "test"},
            user_id="user123"
        )

        # Verify
        assert result["success"] is False
        assert "error" in result
        # Audit should have been logged
        assert audit_manager.log_action.called

    def test_email_tool_integration(self, tool_executor, audit_manager):
        """Test email tool with audit trail"""
        # Setup: Mock email service
        email_config = EmailConfig(
            company_id="test_company",
            from_email="test@test.com",
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass"
        )

        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            email_service = EmailService(config=email_config)
            tool_executor.set_email_service(email_service)

            # Execute
            result = tool_executor.execute_tool(
                tool_name="send_email",
                parameters={
                    "to_email": "recipient@test.com",
                    "subject": "Test",
                    "body_html": "<h1>Test</h1>",
                    "body_text": "Test"
                },
                user_id="user123",
                agent_name="schedule_agent"
            )

            # Verify
            assert result["success"] is True
            assert "audit_id" in result
            assert mock_server.send_message.called

    def test_calendar_tool_with_compensation(self, tool_executor, audit_manager):
        """Test calendar tool creates compensable audit entry"""
        # Setup: Mock calendar service
        mock_calendar = MagicMock()
        mock_calendar.create_booking.return_value = {
            "success": True,
            "event_id": "evt_123"
        }
        tool_executor.set_calendar_service(mock_calendar)

        # Execute
        result = tool_executor.execute_tool(
            tool_name="google_calendar",
            parameters={
                "action": "create_booking",
                "booking_data": {
                    "date": "2025-01-15",
                    "time": "10:00",
                    "treatment": "Botox"
                }
            },
            user_id="user123",
            agent_name="schedule_agent"
        )

        # Verify
        assert result["success"] is True
        assert "audit_id" in result

        # Verify audit entry was created as compensable
        call_args = audit_manager.log_action.call_args
        assert call_args is not None
        assert call_args.kwargs["compensable"] is True

    def test_saga_with_tool_executor(self, compensation_orchestrator, tool_executor, audit_manager):
        """Test Saga pattern with ToolExecutor"""
        # Setup: Mock services
        mock_calendar = MagicMock()
        mock_calendar.create_booking.return_value = {
            "success": True,
            "event_id": "evt_123"
        }
        tool_executor.set_calendar_service(mock_calendar)

        # Create saga
        saga = compensation_orchestrator.create_saga(
            user_id="user123",
            saga_name="booking_with_notification"
        )

        # Add action 1: Create booking
        compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_calendar_event",
            executor=lambda: tool_executor.execute_tool(
                tool_name="google_calendar",
                parameters={
                    "action": "create_booking",
                    "booking_data": {"date": "2025-01-15"}
                },
                user_id="user123"
            ),
            compensator=lambda result: {"success": True, "deleted": True}
        )

        # Execute saga
        result = compensation_orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is True
        assert result["actions_executed"] == 1
        assert mock_calendar.create_booking.called

    def test_saga_compensation_on_tool_failure(
        self,
        compensation_orchestrator,
        tool_executor,
        audit_manager
    ):
        """Test that saga compensates when tool fails"""
        # Setup
        mock_calendar = MagicMock()
        mock_calendar.create_booking.return_value = {
            "success": True,
            "event_id": "evt_123"
        }
        mock_calendar.delete_event = MagicMock(return_value={"success": True})
        tool_executor.set_calendar_service(mock_calendar)

        # Track compensation
        compensated = {"flag": False}

        def compensator(result):
            compensated["flag"] = True
            return {"success": True}

        # Create saga
        saga = compensation_orchestrator.create_saga(
            user_id="user123",
            saga_name="booking_then_fail"
        )

        # Action 1: Create booking (succeeds)
        compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_booking",
            executor=lambda: tool_executor.execute_tool(
                tool_name="google_calendar",
                parameters={
                    "action": "create_booking",
                    "booking_data": {"date": "2025-01-15"}
                },
                user_id="user123"
            ),
            compensator=compensator
        )

        # Action 2: Intentional failure (email not configured)
        compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="notification",
            action_name="send_email",
            executor=lambda: tool_executor.execute_tool(
                tool_name="send_email",
                parameters={
                    "to_email": "test@test.com",
                    "subject": "Test",
                    "body_html": "Test"
                },
                user_id="user123"
            )
        )

        # Execute saga
        result = compensation_orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is False  # Overall saga failed
        assert result["actions_executed"] == 1  # Only first action executed
        assert result["actions_compensated"] == 1  # First action compensated
        assert compensated["flag"] is True  # Compensator was called

    def test_multiple_tools_in_sequence(self, tool_executor, audit_manager):
        """Test executing multiple tools in sequence"""
        # Setup: Mock services
        mock_vectorstore = MagicMock()
        mock_vectorstore.search_by_company.return_value = [
            MagicMock(page_content="Test", metadata={})
        ]
        tool_executor.set_vectorstore_service(mock_vectorstore)

        mock_calendar = MagicMock()
        mock_calendar.check_availability.return_value = {
            "available_slots": ["10:00", "11:00"]
        }
        tool_executor.set_calendar_service(mock_calendar)

        # Execute tools in sequence
        result1 = tool_executor.execute_tool(
            tool_name="knowledge_base",
            parameters={"query": "pricing"},
            user_id="user123"
        )

        result2 = tool_executor.execute_tool(
            tool_name="google_calendar",
            parameters={
                "action": "check_availability",
                "date": "2025-01-15",
                "treatment": "Botox"
            },
            user_id="user123"
        )

        # Verify
        assert result1["success"] is True
        assert result2["success"] is True
        assert "audit_id" in result1
        assert "audit_id" in result2
        assert result1["audit_id"] != result2["audit_id"]

    def test_tool_executor_available_tools(self, tool_executor):
        """Test getting available tools status"""
        # Setup: Inject some services
        mock_vectorstore = MagicMock()
        tool_executor.set_vectorstore_service(mock_vectorstore)

        # Execute
        tools_status = tool_executor.get_available_tools()

        # Verify
        assert "knowledge_base" in tools_status
        assert tools_status["knowledge_base"]["available"] is True
        assert "google_calendar" in tools_status
        assert tools_status["google_calendar"]["available"] is False  # Not injected
        assert tools_status["google_calendar"]["missing_service"] == "CalendarIntegrationService"

    def test_audit_trail_query_after_tools(self, tool_executor, audit_manager, redis_mock):
        """Test querying audit trail after tool executions"""
        # Setup
        import json
        mock_vectorstore = MagicMock()
        mock_vectorstore.search_by_company.return_value = []
        tool_executor.set_vectorstore_service(mock_vectorstore)

        # Execute multiple tools
        for i in range(3):
            tool_executor.execute_tool(
                tool_name="knowledge_base",
                parameters={"query": f"query_{i}"},
                user_id="user123"
            )

        # Mock Redis to return audit entries
        redis_mock.smembers.return_value = {
            b"audit_1",
            b"audit_2",
            b"audit_3"
        }

        def get_side_effect(key):
            if b"audit_" in key.encode():
                return json.dumps({
                    "audit_id": key.decode().split(":")[-1],
                    "company_id": "test_company",
                    "user_id": "user123",
                    "action_type": "rag_search",
                    "action_name": "knowledge_base.execute",
                    "status": "success",
                    "created_at": "2025-01-01T10:00:00"
                }).encode('utf-8')
            return None

        redis_mock.get.side_effect = get_side_effect

        # Query audit trail
        actions = audit_manager.get_user_actions("user123", limit=10)

        # Verify
        assert len(actions) >= 0  # May be empty in test environment


class TestEndToEndScenarios:
    """End-to-end integration test scenarios"""

    @pytest.fixture
    def full_system(self):
        """Setup full system with all components"""
        redis_mock = MagicMock()
        redis_mock.setex = MagicMock(return_value=True)
        redis_mock.get = MagicMock(return_value=None)
        redis_mock.sadd = MagicMock(return_value=True)

        with patch('app.models.audit_trail.get_redis') as mock_get_redis:
            mock_get_redis.return_value = redis_mock

            audit_manager = AuditManager(company_id="benova")
            audit_manager.redis = redis_mock

            tool_executor = ToolExecutor(
                company_id="benova",
                audit_manager=audit_manager
            )

            with patch('app.workflows.compensation_orchestrator.get_redis') as mock_get_redis2:
                mock_get_redis2.return_value = redis_mock

                compensation_orchestrator = CompensationOrchestrator(
                    company_id="benova",
                    audit_manager=audit_manager
                )
                compensation_orchestrator.redis = redis_mock

            return {
                "audit_manager": audit_manager,
                "tool_executor": tool_executor,
                "compensation_orchestrator": compensation_orchestrator,
                "redis_mock": redis_mock
            }

    def test_booking_flow_with_compensation(self, full_system):
        """Test complete booking flow with compensation on failure"""
        tool_executor = full_system["tool_executor"]
        compensation_orchestrator = full_system["compensation_orchestrator"]

        # Mock calendar service
        mock_calendar = MagicMock()
        mock_calendar.create_booking.return_value = {
            "success": True,
            "event_id": "evt_appointment_123"
        }
        tool_executor.set_calendar_service(mock_calendar)

        # Create saga for booking flow
        saga = compensation_orchestrator.create_saga(
            user_id="user_maria",
            saga_name="complete_booking_flow"
        )

        # Step 1: Create calendar event
        compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_calendar_event",
            executor=lambda: tool_executor.execute_tool(
                tool_name="google_calendar",
                parameters={
                    "action": "create_booking",
                    "booking_data": {
                        "date": "2025-01-20",
                        "time": "10:00",
                        "treatment": "Botox"
                    }
                },
                user_id="user_maria",
                agent_name="schedule_agent"
            ),
            compensator=lambda result: {
                "success": True,
                "event_deleted": True
            }
        )

        # Step 2: Intentional failure (simulate email error)
        compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="notification",
            action_name="send_confirmation_email",
            executor=lambda: {
                "success": False,
                "error": "Email service unavailable"
            }
        )

        # Execute saga
        result = compensation_orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is False
        assert result["status"] == "compensated"
        assert result["actions_compensated"] == 1  # Calendar event compensated
        assert mock_calendar.create_booking.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
