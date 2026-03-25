-- Phase 4 Academic Enforcement Database Constraints
-- Execute these constraints to ensure data integrity at database level

-- Constraint 1: Unique active enforcement rules
ALTER TABLE academic_enforcement_rules 
ADD CONSTRAINT unique_active_rule_per_type 
UNIQUE (rule_type) WHERE is_active = true;

-- Constraint 2: Valid attempt ranges
ALTER TABLE assignment_enforcement 
ADD CONSTRAINT valid_attempt_range 
CHECK (max_attempts >= 1 AND max_attempts <= 10);

-- Constraint 3: Valid time limits
ALTER TABLE assignment_enforcement 
ADD CONSTRAINT valid_time_limit 
CHECK (time_limit_minutes >= 5 OR time_limit_minutes IS NULL);

-- Constraint 4: Positive attempt numbers
ALTER TABLE student_submission_attempts 
ADD CONSTRAINT positive_attempt_number 
CHECK (attempt_number >= 1);

-- Constraint 5: Submission timeline logic
ALTER TABLE student_submission_attempts 
ADD CONSTRAINT valid_submission_timeline 
CHECK (submitted_at >= started_at OR submitted_at IS NULL);

-- Index 1: Performance index for attempt lookups
CREATE INDEX idx_attempts_student_assignment 
ON student_submission_attempts(student_id, assignment_id, attempt_number);

-- Index 2: Performance index for enforcement logs
CREATE INDEX idx_enforcement_log_timestamp 
ON submission_enforcement_log(timestamp DESC);

-- Index 3: Performance index for violations
CREATE INDEX idx_violations_student_date 
ON academic_violations(student_id, created_at DESC);

-- Constraint 6: Valid penalty amounts
ALTER TABLE academic_violations 
ADD CONSTRAINT valid_penalty_amount 
CHECK (penalty_applied >= 0.00 AND penalty_applied <= 100.00);