-- ============================================================
-- Email Management Agent - PostgreSQL Database Schema
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. EMAILS TABLE - Core email storage
-- ============================================================
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(512) NOT NULL UNIQUE,
    thread_id VARCHAR(512),
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    sender_domain VARCHAR(255) GENERATED ALWAYS AS (split_part(sender_email, '@', 2)) STORED,
    recipients JSONB NOT NULL DEFAULT '[]',
    cc_recipients JSONB DEFAULT '[]',
    subject VARCHAR(1000),
    body_text TEXT,
    body_html TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'quarantined')),
    dedup_hash VARCHAR(64) UNIQUE,
    is_duplicate BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_emails_message_id ON emails(message_id);
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_sender_email ON emails(sender_email);
CREATE INDEX idx_emails_sender_domain ON emails(sender_domain);
CREATE INDEX idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX idx_emails_processing_status ON emails(processing_status);
CREATE INDEX idx_emails_dedup_hash ON emails(dedup_hash);
CREATE INDEX idx_emails_subject_trgm ON emails USING gin (subject gin_trgm_ops);

-- ============================================================
-- 2. CLASSIFICATIONS TABLE - LLM classification results
-- ============================================================
CREATE TABLE IF NOT EXISTS classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    intent VARCHAR(50) NOT NULL
        CHECK (intent IN ('urgent', 'action_required', 'informational', 'newsletter', 'spam', 'meeting_request', 'unknown')),
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    urgency_score INTEGER CHECK (urgency_score >= 1 AND urgency_score <= 10),
    sentiment VARCHAR(20) CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    entities JSONB DEFAULT '{}',
    model_used VARCHAR(100),
    tokens_input INTEGER,
    tokens_output INTEGER,
    classified_at TIMESTAMPTZ DEFAULT NOW(),
    human_corrected BOOLEAN DEFAULT FALSE,
    human_intent VARCHAR(50),
    human_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_classifications_email_id ON classifications(email_id);
CREATE INDEX idx_classifications_intent ON classifications(intent);
CREATE INDEX idx_classifications_confidence ON classifications(confidence);
CREATE INDEX idx_classifications_classified_at ON classifications(classified_at DESC);

-- ============================================================
-- 3. ACTIONS TABLE - All actions taken by the agent
-- ============================================================
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    classification_id UUID REFERENCES classifications(id),
    action_type VARCHAR(50) NOT NULL
        CHECK (action_type IN ('reply', 'forward', 'archive', 'flag', 'create_task', 'schedule_meeting', 'quarantine', 'notify', 'draft_created', 'moved_folder', 'none')),
    action_status VARCHAR(50) DEFAULT 'completed'
        CHECK (action_status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled', 'awaiting_approval')),
    action_payload JSONB DEFAULT '{}',
    action_result JSONB DEFAULT '{}',
    external_task_id VARCHAR(255),
    external_event_id VARCHAR(255),
    external_message_id VARCHAR(255),
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    execution_duration_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_email_id ON actions(email_id);
CREATE INDEX idx_actions_action_type ON actions(action_type);
CREATE INDEX idx_actions_action_status ON actions(action_status);
CREATE INDEX idx_actions_requires_approval ON actions(requires_approval) WHERE requires_approval = TRUE;

-- ============================================================
-- 4. EXECUTION_LOGS TABLE - n8n execution tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255),
    workflow_name VARCHAR(255),
    email_id UUID REFERENCES emails(id),
    message_id VARCHAR(512),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    nodes_executed JSONB DEFAULT '[]',
    node_errors JSONB DEFAULT '[]',
    status VARCHAR(50) CHECK (status IN ('running', 'success', 'error', 'warning', 'cancelled')),
    llm_tokens_input INTEGER DEFAULT 0,
    llm_tokens_output INTEGER DEFAULT 0,
    llm_cost_usd DECIMAL(10,6) DEFAULT 0,
    input_payload JSONB,
    output_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_execution_logs_execution_id ON execution_logs(execution_id);
CREATE INDEX idx_execution_logs_email_id ON execution_logs(email_id);
CREATE INDEX idx_execution_logs_status ON execution_logs(status);
CREATE INDEX idx_execution_logs_started_at ON execution_logs(started_at DESC);

-- ============================================================
-- 5. USER_PREFERENCES TABLE - Per-user configuration
-- ============================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email VARCHAR(255) NOT NULL UNIQUE,
    auto_approve_threshold DECIMAL(3,2) DEFAULT 0.85,
    vip_senders JSONB DEFAULT '[]',
    blocked_senders JSONB DEFAULT '[]',
    default_tone VARCHAR(20) DEFAULT 'professional',
    default_response_length VARCHAR(20) DEFAULT 'standard',
    signature TEXT,
    slack_webhook_url VARCHAR(500),
    slack_channel VARCHAR(100),
    notify_on_urgent BOOLEAN DEFAULT TRUE,
    notify_on_action_required BOOLEAN DEFAULT TRUE,
    notion_database_id VARCHAR(255),
    preferred_model VARCHAR(50) DEFAULT 'gpt-4o-mini',
    fallback_model VARCHAR(50) DEFAULT 'gpt-4o',
    auto_reply_enabled BOOLEAN DEFAULT FALSE,
    auto_archive_newsletters BOOLEAN DEFAULT TRUE,
    spam_detection_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 6. DEAD_LETTER_QUEUE TABLE - Failed processing records
-- ============================================================
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID REFERENCES emails(id),
    message_id VARCHAR(512),
    original_payload JSONB,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    failed_node VARCHAR(255),
    error_message TEXT,
    error_code VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    next_retry_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'pending_retry'
        CHECK (status IN ('pending_retry', 'retrying', 'resolved', 'permanently_failed', 'manual_review')),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(255),
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX idx_dlq_failed_at ON dead_letter_queue(failed_at DESC);
CREATE INDEX idx_dlq_next_retry ON dead_letter_queue(next_retry_at) WHERE status = 'pending_retry';

-- ============================================================
-- VIEWS
-- ============================================================
CREATE OR REPLACE VIEW v_daily_metrics AS
SELECT 
    DATE_TRUNC('day', received_at) AS date,
    COUNT(*) AS total_emails,
    COUNT(*) FILTER (WHERE processing_status = 'completed') AS processed,
    COUNT(*) FILTER (WHERE processing_status = 'failed') AS failed,
    COUNT(*) FILTER (WHERE is_duplicate = TRUE) AS duplicates,
    AVG(processing_duration_ms) FILTER (WHERE processing_status = 'completed') AS avg_processing_ms
FROM emails
GROUP BY DATE_TRUNC('day', received_at)
ORDER BY date DESC;

CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT 
    e.id AS email_id,
    e.subject,
    e.sender_email,
    e.sender_name,
    e.received_at,
    c.intent,
    c.confidence,
    c.urgency_score,
    c.summary,
    a.action_type,
    a.created_at AS action_created_at
FROM emails e
JOIN classifications c ON e.id = c.email_id
JOIN actions a ON e.id = a.email_id
WHERE a.requires_approval = TRUE AND a.action_status = 'awaiting_approval'
ORDER BY c.urgency_score DESC, e.received_at DESC;

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_emails_updated_at BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_actions_updated_at BEFORE UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- INITIAL DATA
-- ============================================================
INSERT INTO user_preferences (
    user_email, auto_approve_threshold, default_tone, default_response_length,
    notify_on_urgent, notify_on_action_required, auto_archive_newsletters, spam_detection_enabled
) VALUES (
    'user@example.com', 0.85, 'professional', 'standard', TRUE, TRUE, TRUE, TRUE
) ON CONFLICT (user_email) DO NOTHING;
