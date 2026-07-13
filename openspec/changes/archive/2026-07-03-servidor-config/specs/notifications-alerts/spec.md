## ADDED Requirements

### Requirement: Telegram alert notification
The system SHALL send alerts via a Telegram bot webhook when critical events occur.

#### Scenario: Healthcheck failure notification
- **WHEN** the `/readyz` endpoint returns non-200 status
- **THEN** a notification SHALL be sent to a configured Telegram chat
- **AND** the notification SHALL include: service name, timestamp, error detail

#### Scenario: Bot configured via env vars
- **WHEN** the application starts
- **THEN** it SHALL read `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from environment variables
- **AND** SHALL gracefully degrade (no crash) if these variables are not set

#### Scenario: Rate-limited notifications
- **WHEN** the same error occurs repeatedly within 5 minutes
- **THEN** the system SHALL NOT send duplicate notifications (cooldown period)
