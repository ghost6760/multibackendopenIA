"""
Unit tests for CompensationOrchestrator

Tests for Saga pattern implementation including compensation/rollback logic.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.workflows.compensation_orchestrator import (
    CompensationOrchestrator,
    Saga,
    SagaAction,
    SagaStatus
)
from app.models.audit_trail import AuditManager


class TestCompensationOrchestrator:
    """Test suite for CompensationOrchestrator"""

    @pytest.fixture
    def audit_manager_mock(self):
        """Mock AuditManager"""
        mock = MagicMock(spec=AuditManager)
        mock.log_action.return_value = MagicMock(audit_id="audit_123")
        mock.mark_success.return_value = True
        mock.mark_failed.return_value = True
        mock.compensate.return_value = True
        return mock

    @pytest.fixture
    def orchestrator(self, audit_manager_mock):
        """Create CompensationOrchestrator with mocked dependencies"""
        with patch('app.workflows.compensation_orchestrator.get_redis') as mock_redis:
            mock_redis.return_value = MagicMock()
            orch = CompensationOrchestrator(
                company_id="test_company",
                audit_manager=audit_manager_mock
            )
            orch.redis = MagicMock()
            return orch

    def test_init(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.company_id == "test_company"
        assert orchestrator.audit_manager is not None
        assert orchestrator.max_retries == 3

    def test_create_saga(self, orchestrator):
        """Test creating a new saga"""
        # Execute
        saga = orchestrator.create_saga(
            user_id="user123",
            saga_name="test_saga"
        )

        # Verify
        assert saga.company_id == "test_company"
        assert saga.user_id == "user123"
        assert saga.saga_name == "test_saga"
        assert saga.status == SagaStatus.PENDING
        assert len(saga.actions) == 0

    def test_add_action_to_saga(self, orchestrator):
        """Test adding action to saga"""
        # Setup
        saga = orchestrator.create_saga("user123", "test_saga")

        # Mock executor and compensator
        def mock_executor():
            return {"success": True, "data": "result"}

        def mock_compensator(result):
            return {"success": True}

        # Execute
        action = orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_event",
            executor=mock_executor,
            compensator=mock_compensator,
            input_params={"event_id": "evt_123"}
        )

        # Verify
        assert action is not None
        assert action.action_type == "booking"
        assert action.action_name == "create_event"
        assert action.executed is False
        assert action.compensator is not None

    def test_execute_saga_success(self, orchestrator, audit_manager_mock):
        """Test successful saga execution"""
        # Setup
        saga = orchestrator.create_saga("user123", "booking_saga")

        # Add actions
        def action1_executor():
            return {"success": True, "event_id": "evt_123"}

        def action2_executor():
            return {"success": True, "email_sent": True}

        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_calendar_event",
            executor=action1_executor
        )

        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="notification",
            action_name="send_confirmation_email",
            executor=action2_executor
        )

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["actions_executed"] == 2
        assert result["actions_compensated"] == 0

    def test_execute_saga_with_failure_and_compensation(self, orchestrator, audit_manager_mock):
        """Test saga execution with failure and automatic compensation"""
        # Setup
        saga = orchestrator.create_saga("user123", "booking_saga")

        # Track compensation
        action1_compensated = {"compensated": False}

        def action1_executor():
            return {"success": True, "event_id": "evt_123"}

        def action1_compensator(result):
            action1_compensated["compensated"] = True
            return {"success": True, "deleted": True}

        def action2_executor():
            # This action fails
            raise Exception("Email service unavailable")

        # Add actions
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_calendar_event",
            executor=action1_executor,
            compensator=action1_compensator
        )

        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="notification",
            action_name="send_confirmation_email",
            executor=action2_executor
        )

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is False
        assert result["status"] == "compensated"
        assert result["actions_executed"] == 1  # Only first action executed
        assert result["actions_compensated"] == 1  # First action compensated
        assert action1_compensated["compensated"] is True

    def test_execute_saga_compensation_in_reverse_order(self, orchestrator):
        """Test that compensation happens in reverse order (LIFO)"""
        # Setup
        saga = orchestrator.create_saga("user123", "multi_step_saga")

        compensation_order = []

        def make_compensator(name):
            def compensator(result):
                compensation_order.append(name)
                return {"success": True}
            return compensator

        # Add 3 actions
        for i in range(1, 4):
            orchestrator.add_action(
                saga_id=saga.saga_id,
                action_type="test",
                action_name=f"action_{i}",
                executor=lambda: {"success": True},
                compensator=make_compensator(f"action_{i}")
            )

        # Add failing action at the end
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="test",
            action_name="action_4_fail",
            executor=lambda: {"success": False, "error": "Intentional failure"}
        )

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify compensation order is reversed (LIFO)
        assert result["success"] is False
        assert compensation_order == ["action_3", "action_2", "action_1"]

    def test_execute_saga_retry_on_transient_failure(self, orchestrator):
        """Test retry mechanism for transient failures"""
        # Setup
        saga = orchestrator.create_saga("user123", "retry_saga")

        call_count = {"count": 0}

        def flaky_executor():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise Exception("Transient error")
            return {"success": True, "data": "final_result"}

        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="api_call",
            action_name="flaky_api",
            executor=flaky_executor
        )

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify - should succeed after retries
        assert result["success"] is True
        assert call_count["count"] == 3

    def test_execute_saga_max_retries_exceeded(self, orchestrator):
        """Test that saga fails after max retries"""
        # Setup
        saga = orchestrator.create_saga("user123", "always_fail_saga")

        call_count = {"count": 0}

        def always_fail_executor():
            call_count["count"] += 1
            raise Exception("Permanent error")

        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="api_call",
            action_name="always_fail",
            executor=always_fail_executor
        )

        orchestrator.max_retries = 3

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify
        assert result["success"] is False
        assert call_count["count"] == orchestrator.max_retries

    def test_execute_saga_with_non_compensable_action(self, orchestrator):
        """Test saga with non-compensable actions"""
        # Setup
        saga = orchestrator.create_saga("user123", "mixed_saga")

        # Action 1: Compensable
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_event",
            executor=lambda: {"success": True},
            compensator=lambda r: {"success": True}
        )

        # Action 2: Non-compensable (no compensator)
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="notification",
            action_name="send_email",
            executor=lambda: {"success": True},
            compensator=None  # Cannot undo sending email
        )

        # Action 3: Fails
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="api_call",
            action_name="failing_action",
            executor=lambda: {"success": False, "error": "Fail"}
        )

        # Execute
        result = orchestrator.execute_saga(saga.saga_id)

        # Verify - should compensate action 1, skip action 2
        assert result["success"] is False
        assert result["actions_compensated"] == 1  # Only action 1 compensated

    def test_get_saga(self, orchestrator):
        """Test retrieving saga by ID"""
        # Setup
        saga = orchestrator.create_saga("user123", "test_saga")

        # Mock Redis get
        import json
        from dataclasses import asdict
        saga_data = asdict(saga)
        # Convert enum to string for serialization
        saga_data["status"] = saga.status.value
        orchestrator.redis.get.return_value = json.dumps(saga_data).encode('utf-8')

        # Execute
        retrieved = orchestrator.get_saga(saga.saga_id)

        # Verify
        assert retrieved is not None
        assert retrieved.saga_id == saga.saga_id

    def test_get_saga_not_found(self, orchestrator):
        """Test retrieving non-existent saga"""
        # Mock Redis get returns None
        orchestrator.redis.get.return_value = None

        # Execute
        saga = orchestrator.get_saga("nonexistent_saga")

        # Verify
        assert saga is None

    def test_compensate_single_action(self, orchestrator):
        """Test compensating a single action"""
        # Setup
        compensated = {"flag": False}

        def compensator(result):
            compensated["flag"] = True
            return {"success": True}

        action = SagaAction(
            action_id="action_1",
            action_type="booking",
            action_name="create_event",
            executor=lambda: {"success": True},
            compensator=compensator,
            executed=True,
            execution_result={"event_id": "evt_123"}
        )

        # Execute
        result = orchestrator._compensate_action(action)

        # Verify
        assert result["success"] is True
        assert compensated["flag"] is True

    def test_compensate_action_without_compensator(self, orchestrator):
        """Test compensating action that has no compensator"""
        action = SagaAction(
            action_id="action_1",
            action_type="notification",
            action_name="send_email",
            executor=lambda: {"success": True},
            compensator=None,  # No compensator
            executed=True
        )

        # Execute
        result = orchestrator._compensate_action(action)

        # Verify - should skip gracefully
        assert result["success"] is False
        assert "no compensator" in result["error"].lower()

    def test_saga_status_transitions(self, orchestrator):
        """Test saga status transitions through lifecycle"""
        # Setup
        saga = orchestrator.create_saga("user123", "status_test_saga")

        # Initial state
        assert saga.status == SagaStatus.PENDING

        # Add and execute successful saga
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="test",
            action_name="test_action",
            executor=lambda: {"success": True}
        )

        result = orchestrator.execute_saga(saga.saga_id)

        # Final state
        assert result["status"] == "completed"

    def test_exponential_backoff_calculation(self, orchestrator):
        """Test exponential backoff for retries"""
        # Retry 0: 2s
        # Retry 1: 4s
        # Retry 2: 8s
        delays = []
        for retry_num in range(3):
            delay = orchestrator.retry_delay * (2 ** retry_num)
            delays.append(delay)

        assert delays[0] == 2.0
        assert delays[1] == 4.0
        assert delays[2] == 8.0


class TestSagaDataclass:
    """Test Saga dataclass"""

    def test_create_minimal_saga(self):
        """Test creating saga with minimal fields"""
        saga = Saga(
            saga_id="saga_1",
            company_id="company_1",
            user_id="user_1",
            saga_name="test_saga"
        )

        assert saga.saga_id == "saga_1"
        assert saga.status == SagaStatus.PENDING
        assert len(saga.actions) == 0

    def test_create_full_saga(self):
        """Test creating saga with all fields"""
        action = SagaAction(
            action_id="action_1",
            action_type="booking",
            action_name="create_event",
            executor=lambda: {},
            compensator=lambda r: {}
        )

        saga = Saga(
            saga_id="saga_2",
            company_id="company_1",
            user_id="user_1",
            saga_name="full_saga",
            status=SagaStatus.IN_PROGRESS,
            actions=[action],
            conversation_id="conv_123"
        )

        assert saga.status == SagaStatus.IN_PROGRESS
        assert len(saga.actions) == 1
        assert saga.conversation_id == "conv_123"


class TestSagaActionDataclass:
    """Test SagaAction dataclass"""

    def test_create_saga_action(self):
        """Test creating saga action"""
        def executor():
            return {"success": True}

        def compensator(result):
            return {"success": True}

        action = SagaAction(
            action_id="action_1",
            action_type="booking",
            action_name="create_event",
            executor=executor,
            compensator=compensator,
            input_params={"date": "2025-01-15"}
        )

        assert action.action_id == "action_1"
        assert action.executed is False
        assert action.compensated is False
        assert action.input_params == {"date": "2025-01-15"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
