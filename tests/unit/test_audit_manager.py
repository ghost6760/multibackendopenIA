"""
Unit tests for AuditManager

Tests for audit trail functionality including logging actions,
marking success/failure, compensation tracking, and querying.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from app.models.audit_trail import AuditManager, AuditEntry


class TestAuditManager:
    """Test suite for AuditManager"""

    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client for testing"""
        redis = MagicMock()
        redis.setex = MagicMock(return_value=True)
        redis.get = MagicMock(return_value=None)
        redis.sadd = MagicMock(return_value=True)
        redis.smembers = MagicMock(return_value=set())
        redis.delete = MagicMock(return_value=True)
        return redis

    @pytest.fixture
    def audit_manager(self, redis_mock):
        """Create AuditManager with mocked Redis"""
        with patch('app.models.audit_trail.get_redis') as mock_get_redis:
            mock_get_redis.return_value = redis_mock
            manager = AuditManager(company_id="test_company")
            manager.redis = redis_mock
            return manager

    def test_init(self, audit_manager):
        """Test AuditManager initialization"""
        assert audit_manager.company_id == "test_company"
        assert audit_manager.ttl_days == 90
        assert audit_manager.enabled is True

    def test_log_action_basic(self, audit_manager, redis_mock):
        """Test logging a basic action"""
        # Execute
        entry = audit_manager.log_action(
            user_id="user123",
            action_type="api_call",
            action_name="test.action"
        )

        # Verify
        assert entry.company_id == "test_company"
        assert entry.user_id == "user123"
        assert entry.action_type == "api_call"
        assert entry.action_name == "test.action"
        assert entry.status == "pending"
        assert entry.compensable is False

        # Verify Redis was called
        assert redis_mock.setex.called

    def test_log_action_with_compensation(self, audit_manager, redis_mock):
        """Test logging a compensable action"""
        # Execute
        entry = audit_manager.log_action(
            user_id="user123",
            action_type="booking",
            action_name="google_calendar.create_event",
            compensable=True,
            compensation_action="google_calendar.delete_event",
            compensation_params={"event_id": "evt_123"}
        )

        # Verify
        assert entry.compensable is True
        assert entry.compensation_action == "google_calendar.delete_event"
        assert entry.compensation_params == {"event_id": "evt_123"}

    def test_log_action_with_metadata(self, audit_manager, redis_mock):
        """Test logging action with full metadata"""
        # Execute
        entry = audit_manager.log_action(
            user_id="user456",
            action_type="notification",
            action_name="email.send_confirmation",
            input_params={"to": "test@example.com", "subject": "Test"},
            agent_name="schedule_agent",
            conversation_id="conv_789",
            tags=["email", "booking"]
        )

        # Verify
        assert entry.input_params == {"to": "test@example.com", "subject": "Test"}
        assert entry.agent_name == "schedule_agent"
        assert entry.conversation_id == "conv_789"
        assert entry.tags == ["email", "booking"]

    def test_mark_success(self, audit_manager, redis_mock):
        """Test marking action as successful"""
        # Setup: Create entry first
        import json
        audit_id = "audit_123"
        entry_data = {
            "audit_id": audit_id,
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "api_call",
            "action_name": "test.action",
            "status": "pending"
        }
        redis_mock.get.return_value = json.dumps(entry_data).encode('utf-8')

        # Execute
        result = audit_manager.mark_success(
            audit_id=audit_id,
            result={"data": "success"},
            duration_ms=150.5
        )

        # Verify
        assert result is True
        assert redis_mock.setex.called

    def test_mark_failed(self, audit_manager, redis_mock):
        """Test marking action as failed"""
        # Setup
        import json
        audit_id = "audit_456"
        entry_data = {
            "audit_id": audit_id,
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "api_call",
            "action_name": "test.action",
            "status": "pending"
        }
        redis_mock.get.return_value = json.dumps(entry_data).encode('utf-8')

        # Execute
        result = audit_manager.mark_failed(
            audit_id=audit_id,
            error_message="Connection timeout",
            duration_ms=5000
        )

        # Verify
        assert result is True
        assert redis_mock.setex.called

    def test_compensate_action(self, audit_manager, redis_mock):
        """Test compensating (rolling back) an action"""
        # Setup: Create successful compensable action
        import json
        audit_id = "audit_comp_123"
        entry_data = {
            "audit_id": audit_id,
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "booking",
            "action_name": "google_calendar.create_event",
            "status": "success",
            "compensable": True,
            "compensation_action": "google_calendar.delete_event",
            "compensation_params": {"event_id": "evt_456"}
        }
        redis_mock.get.return_value = json.dumps(entry_data).encode('utf-8')

        # Execute
        result = audit_manager.compensate(
            audit_id=audit_id,
            reason="User cancelled appointment"
        )

        # Verify
        assert result is True
        assert redis_mock.setex.called

    def test_compensate_non_compensable_action(self, audit_manager, redis_mock):
        """Test trying to compensate non-compensable action"""
        # Setup: Create non-compensable action
        import json
        audit_id = "audit_noncomp_123"
        entry_data = {
            "audit_id": audit_id,
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "notification",
            "action_name": "email.send",
            "status": "success",
            "compensable": False
        }
        redis_mock.get.return_value = json.dumps(entry_data).encode('utf-8')

        # Execute
        result = audit_manager.compensate(
            audit_id=audit_id,
            reason="Test"
        )

        # Verify - should fail gracefully
        assert result is False

    def test_get_entry(self, audit_manager, redis_mock):
        """Test retrieving audit entry"""
        # Setup
        import json
        audit_id = "audit_get_123"
        entry_data = {
            "audit_id": audit_id,
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "api_call",
            "action_name": "test.action",
            "status": "success"
        }
        redis_mock.get.return_value = json.dumps(entry_data).encode('utf-8')

        # Execute
        entry = audit_manager.get_entry(audit_id)

        # Verify
        assert entry is not None
        assert entry.audit_id == audit_id
        assert entry.status == "success"

    def test_get_entry_not_found(self, audit_manager, redis_mock):
        """Test retrieving non-existent entry"""
        # Setup
        redis_mock.get.return_value = None

        # Execute
        entry = audit_manager.get_entry("nonexistent")

        # Verify
        assert entry is None

    def test_get_user_actions(self, audit_manager, redis_mock):
        """Test retrieving user actions"""
        # Setup
        import json
        redis_mock.smembers.return_value = {
            b"audit_1",
            b"audit_2"
        }

        entry1_data = {
            "audit_id": "audit_1",
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "api_call",
            "action_name": "test.action1",
            "status": "success",
            "created_at": datetime.now().isoformat()
        }
        entry2_data = {
            "audit_id": "audit_2",
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "api_call",
            "action_name": "test.action2",
            "status": "failed",
            "created_at": datetime.now().isoformat()
        }

        def get_side_effect(key):
            if b"audit_1" in key.encode():
                return json.dumps(entry1_data).encode('utf-8')
            elif b"audit_2" in key.encode():
                return json.dumps(entry2_data).encode('utf-8')
            return None

        redis_mock.get.side_effect = get_side_effect

        # Execute
        actions = audit_manager.get_user_actions("user123", limit=10)

        # Verify
        assert len(actions) > 0

    def test_get_actions_by_type(self, audit_manager, redis_mock):
        """Test retrieving actions by type"""
        # Setup
        import json
        redis_mock.smembers.return_value = {
            b"audit_1",
            b"audit_2"
        }

        entry1_data = {
            "audit_id": "audit_1",
            "company_id": "test_company",
            "user_id": "user123",
            "action_type": "booking",
            "action_name": "google_calendar.create_event",
            "status": "success",
            "created_at": datetime.now().isoformat()
        }

        redis_mock.get.return_value = json.dumps(entry1_data).encode('utf-8')

        # Execute
        actions = audit_manager.get_actions_by_type("booking", limit=10)

        # Verify
        assert redis_mock.smembers.called

    def test_ttl_calculation(self, audit_manager):
        """Test TTL calculation for retention"""
        # Default: 90 days
        ttl_seconds = audit_manager.ttl_days * 24 * 60 * 60
        expected = 90 * 24 * 60 * 60

        assert ttl_seconds == expected

    def test_disabled_audit_manager(self, redis_mock):
        """Test AuditManager when disabled"""
        with patch('app.models.audit_trail.get_redis') as mock_get_redis:
            mock_get_redis.return_value = redis_mock

            manager = AuditManager(
                company_id="test_company",
                enabled=False
            )

            # Execute
            entry = manager.log_action(
                user_id="user123",
                action_type="api_call",
                action_name="test.action"
            )

            # Verify - should create entry but not persist
            assert entry is not None
            assert not redis_mock.setex.called

    def test_serialization_deserialization(self, audit_manager):
        """Test entry serialization and deserialization"""
        # Create entry
        entry = AuditEntry(
            audit_id="test_123",
            company_id="test_company",
            user_id="user123",
            action_type="booking",
            action_name="test.action",
            status="success",
            compensable=True,
            compensation_action="rollback.action",
            compensation_params={"id": "123"},
            input_params={"param": "value"},
            result={"result": "data"},
            error_message=None,
            duration_ms=100.5,
            agent_name="test_agent",
            conversation_id="conv_123",
            tags=["test", "booking"]
        )

        # Serialize
        import json
        from dataclasses import asdict
        serialized = json.dumps(asdict(entry))

        # Deserialize
        deserialized_dict = json.loads(serialized)

        # Verify
        assert deserialized_dict["audit_id"] == "test_123"
        assert deserialized_dict["compensable"] is True
        assert deserialized_dict["duration_ms"] == 100.5


class TestAuditEntryDataclass:
    """Test AuditEntry dataclass"""

    def test_create_minimal_entry(self):
        """Test creating entry with minimal fields"""
        entry = AuditEntry(
            audit_id="test_1",
            company_id="company_1",
            user_id="user_1",
            action_type="api_call",
            action_name="test.action"
        )

        assert entry.audit_id == "test_1"
        assert entry.status == "pending"
        assert entry.compensable is False
        assert entry.created_at is not None

    def test_create_full_entry(self):
        """Test creating entry with all fields"""
        now = datetime.now().isoformat()

        entry = AuditEntry(
            audit_id="test_2",
            company_id="company_1",
            user_id="user_1",
            action_type="booking",
            action_name="calendar.create",
            status="success",
            compensable=True,
            compensation_action="calendar.delete",
            compensation_params={"id": "123"},
            compensated_at=None,
            input_params={"date": "2025-01-01"},
            result={"event_id": "evt_123"},
            error_message=None,
            duration_ms=250.75,
            created_at=now,
            updated_at=now,
            agent_name="schedule_agent",
            conversation_id="conv_456",
            tags=["booking", "calendar"]
        )

        assert entry.compensable is True
        assert entry.duration_ms == 250.75
        assert entry.tags == ["booking", "calendar"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
