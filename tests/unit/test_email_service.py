"""
Unit tests for EmailService

Tests for multi-provider email service including SMTP, SendGrid, and Mailgun.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from app.services.email_service import (
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailTemplate
)


class TestEmailService:
    """Test suite for EmailService"""

    @pytest.fixture
    def smtp_config(self):
        """SMTP email configuration"""
        return EmailConfig(
            company_id="test_company",
            from_email="noreply@test.com",
            from_name="Test Company",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@gmail.com",
            smtp_password="test_password",
            use_tls=True
        )

    @pytest.fixture
    def sendgrid_config(self):
        """SendGrid email configuration"""
        return EmailConfig(
            company_id="test_company",
            from_email="noreply@test.com",
            from_name="Test Company",
            sendgrid_api_key="SG.test_key_123"
        )

    @pytest.fixture
    def mailgun_config(self):
        """Mailgun email configuration"""
        return EmailConfig(
            company_id="test_company",
            from_email="noreply@test.com",
            from_name="Test Company",
            mailgun_api_key="key-test123",
            mailgun_domain="mg.test.com"
        )

    @pytest.fixture
    def email_service_smtp(self, smtp_config):
        """EmailService with SMTP config"""
        return EmailService(config=smtp_config)

    @pytest.fixture
    def email_service_sendgrid(self, sendgrid_config):
        """EmailService with SendGrid config"""
        return EmailService(config=sendgrid_config)

    def test_init_smtp(self, email_service_smtp):
        """Test EmailService initialization with SMTP"""
        assert email_service_smtp.config.company_id == "test_company"
        assert email_service_smtp.provider == EmailProvider.SMTP
        assert email_service_smtp.max_retries == 3

    def test_init_sendgrid(self, email_service_sendgrid):
        """Test EmailService initialization with SendGrid"""
        assert email_service_sendgrid.provider == EmailProvider.SENDGRID
        assert email_service_sendgrid.config.sendgrid_api_key == "SG.test_key_123"

    def test_detect_provider_smtp(self, smtp_config):
        """Test provider detection for SMTP"""
        service = EmailService(config=smtp_config)
        assert service._detect_provider() == EmailProvider.SMTP

    def test_detect_provider_sendgrid(self, sendgrid_config):
        """Test provider detection for SendGrid"""
        service = EmailService(config=sendgrid_config)
        assert service._detect_provider() == EmailProvider.SENDGRID

    def test_detect_provider_mailgun(self, mailgun_config):
        """Test provider detection for Mailgun"""
        service = EmailService(config=mailgun_config)
        assert service._detect_provider() == EmailProvider.MAILGUN

    @patch('smtplib.SMTP')
    def test_send_email_smtp_success(self, mock_smtp, email_service_smtp):
        """Test sending email via SMTP successfully"""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Execute
        result = email_service_smtp.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            body_html="<h1>Test</h1>",
            body_text="Test"
        )

        # Verify
        assert result["success"] is True
        assert result["provider"] == "smtp"
        assert mock_server.starttls.called
        assert mock_server.login.called
        assert mock_server.send_message.called

    @patch('smtplib.SMTP')
    def test_send_email_smtp_failure(self, mock_smtp, email_service_smtp):
        """Test SMTP send failure"""
        # Setup mock to raise exception
        mock_smtp.side_effect = Exception("SMTP connection failed")

        # Execute
        result = email_service_smtp.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            body_html="<h1>Test</h1>"
        )

        # Verify
        assert result["success"] is False
        assert "error" in result

    @patch('requests.post')
    def test_send_email_sendgrid_success(self, mock_post, email_service_sendgrid):
        """Test sending email via SendGrid successfully"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"message": "success"}
        mock_post.return_value = mock_response

        # Execute
        result = email_service_sendgrid.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            body_html="<h1>Test</h1>",
            body_text="Test"
        )

        # Verify
        assert result["success"] is True
        assert result["provider"] == "sendgrid"
        assert mock_post.called

    @patch('requests.post')
    def test_send_email_sendgrid_failure(self, mock_post, email_service_sendgrid):
        """Test SendGrid send failure"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        # Execute
        result = email_service_sendgrid.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            body_html="<h1>Test</h1>"
        )

        # Verify
        assert result["success"] is False
        assert "error" in result

    def test_send_email_with_cc_bcc(self, email_service_smtp):
        """Test sending email with CC and BCC"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Execute
            result = email_service_smtp.send_email(
                to_email="recipient@test.com",
                subject="Test",
                body_html="<h1>Test</h1>",
                cc=["cc1@test.com", "cc2@test.com"],
                bcc=["bcc@test.com"]
            )

            # Verify
            assert result["success"] is True

    def test_send_email_with_reply_to(self, email_service_smtp):
        """Test sending email with reply-to"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Execute
            result = email_service_smtp.send_email(
                to_email="recipient@test.com",
                subject="Test",
                body_html="<h1>Test</h1>",
                reply_to="support@test.com"
            )

            # Verify
            assert result["success"] is True

    @patch('smtplib.SMTP')
    def test_retry_on_failure(self, mock_smtp, smtp_config):
        """Test retry mechanism on failure"""
        # Setup: Fail twice, then succeed
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.send_message.side_effect = [
            Exception("Temp failure 1"),
            Exception("Temp failure 2"),
            None  # Success on 3rd try
        ]

        service = EmailService(config=smtp_config, max_retries=3)

        # Execute
        result = service.send_email(
            to_email="recipient@test.com",
            subject="Test",
            body_html="<h1>Test</h1>"
        )

        # Verify - should succeed after retries
        assert result["success"] is True
        assert mock_server.send_message.call_count == 3

    def test_send_template_email(self, email_service_smtp):
        """Test sending template-based email"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Execute
            result = email_service_smtp.send_template_email(
                to_email="recipient@test.com",
                template_name="appointment_confirmation",
                template_vars={
                    "customer_name": "John Doe",
                    "appointment_date": "2025-01-15",
                    "appointment_time": "10:00 AM",
                    "treatment": "Botox"
                }
            )

            # Verify
            assert result["success"] is True

    def test_send_template_email_missing_vars(self, email_service_smtp):
        """Test sending template with missing variables"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Execute with missing required vars
            result = email_service_smtp.send_template_email(
                to_email="recipient@test.com",
                template_name="appointment_confirmation",
                template_vars={
                    "customer_name": "John Doe"
                    # Missing: appointment_date, appointment_time, treatment
                }
            )

            # Verify - should still send (vars replaced with empty or defaults)
            assert result["success"] is True

    def test_send_template_email_unknown_template(self, email_service_smtp):
        """Test sending with unknown template"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Execute
            result = email_service_smtp.send_template_email(
                to_email="recipient@test.com",
                template_name="nonexistent_template",
                template_vars={}
            )

            # Verify - should fail gracefully
            assert result["success"] is False
            assert "unknown template" in result["error"].lower()

    def test_template_variable_substitution(self, email_service_smtp):
        """Test template variable substitution"""
        template_html = "<h1>Hello {{customer_name}}</h1><p>Date: {{date}}</p>"
        variables = {
            "customer_name": "Jane Smith",
            "date": "2025-01-20"
        }

        # Execute substitution
        result = email_service_smtp._substitute_template_vars(template_html, variables)

        # Verify
        assert "Jane Smith" in result
        assert "2025-01-20" in result
        assert "{{" not in result

    def test_build_mime_message(self, email_service_smtp):
        """Test MIME message construction"""
        msg = email_service_smtp._build_mime_message(
            to_email="recipient@test.com",
            subject="Test Subject",
            body_html="<h1>HTML Content</h1>",
            body_text="Text Content",
            cc=["cc@test.com"],
            bcc=["bcc@test.com"],
            reply_to="reply@test.com"
        )

        # Verify
        assert msg["To"] == "recipient@test.com"
        assert msg["Subject"] == "Test Subject"
        assert msg["From"] == "Test Company <noreply@test.com>"
        assert msg["Cc"] == "cc@test.com"
        assert msg["Reply-To"] == "reply@test.com"


class TestEmailConfig:
    """Test EmailConfig dataclass"""

    def test_create_smtp_config(self):
        """Test creating SMTP configuration"""
        config = EmailConfig(
            company_id="test_co",
            from_email="test@test.com",
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass"
        )

        assert config.company_id == "test_co"
        assert config.smtp_port == 587
        assert config.use_tls is True

    def test_create_sendgrid_config(self):
        """Test creating SendGrid configuration"""
        config = EmailConfig(
            company_id="test_co",
            from_email="test@test.com",
            sendgrid_api_key="SG.key123"
        )

        assert config.sendgrid_api_key == "SG.key123"
        assert config.smtp_host is None

    def test_create_mailgun_config(self):
        """Test creating Mailgun configuration"""
        config = EmailConfig(
            company_id="test_co",
            from_email="test@test.com",
            mailgun_api_key="key-123",
            mailgun_domain="mg.test.com"
        )

        assert config.mailgun_api_key == "key-123"
        assert config.mailgun_domain == "mg.test.com"

    def test_default_values(self):
        """Test default configuration values"""
        config = EmailConfig(
            company_id="test",
            from_email="test@test.com"
        )

        assert config.from_name is None
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
        assert config.use_tls is True


class TestEmailTemplate:
    """Test EmailTemplate dataclass"""

    def test_create_template(self):
        """Test creating email template"""
        template = EmailTemplate(
            name="test_template",
            subject="Test: {{subject_var}}",
            body_html="<h1>{{title}}</h1><p>{{content}}</p>",
            body_text="{{title}}\n{{content}}",
            required_vars=["subject_var", "title", "content"]
        )

        assert template.name == "test_template"
        assert len(template.required_vars) == 3
        assert "{{title}}" in template.body_html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
