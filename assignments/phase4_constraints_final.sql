"""
Phase 4: Database Constraints for Academic Enforcement
These constraints enforce academic rules at the database level
"""

-- Assignment constraints
ALTER TABLE assignments_phase4 
ADD CONSTRAINT valid_assignment_type 
CHECK (assignment_type IN ('HOMEWORK', 'PROJECT', 'EXERCISE', 'QUIZ', 'EXAM'));

ALTER TABLE assignments_phase4 
ADD CONSTRAINT exam_single_attempt 
CHECK (NOT (assignment_type = 'EXAM' AND max_attempts != 1));

ALTER TABLE assignments_phase4 
ADD CONSTRAINT exam_must_be_timed 
CHECK (NOT (assignment_type = 'EXAM' AND (NOT is_timed OR time_limit_minutes IS NULL)));

ALTER TABLE assignments_phase4 
ADD CONSTRAINT quiz_must_be_timed 
CHECK (NOT (assignment_type = 'QUIZ' AND NOT is_timed));

ALTER TABLE assignments_phase4 
ADD CONSTRAINT positive_time_limit 
CHECK (time_limit_minutes IS NULL OR time_limit_minutes > 0);

ALTER TABLE assignments_phase4 
ADD CONSTRAINT due_after_start 
CHECK (due_date > start_date);

ALTER TABLE assignments_phase4 
ADD CONSTRAINT positive_max_score 
CHECK (max_score > 0);

ALTER TABLE assignments_phase4 
ADD CONSTRAINT positive_max_attempts 
CHECK (max_attempts > 0);

-- Student assignment constraints
ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT valid_status 
CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'GRADED', 'LOCKED', 'EXPIRED', 'VIOLATED'));

ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT submitted_has_timestamp 
CHECK (NOT (status = 'SUBMITTED' AND submitted_at IS NULL));

ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT graded_has_timestamp 
CHECK (NOT (status = 'GRADED' AND graded_at IS NULL));

ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT graded_has_score 
CHECK (NOT (status = 'GRADED' AND score IS NULL));

ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT non_negative_attempts 
CHECK (attempts_count >= 0);

ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT non_negative_violations 
CHECK (lockdown_violations >= 0);

-- Prevent tampering with immutable timestamps
CREATE OR REPLACE FUNCTION prevent_timestamp_tampering()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent changing submitted_at once set
    IF OLD.submitted_at IS NOT NULL AND NEW.submitted_at != OLD.submitted_at THEN
        RAISE EXCEPTION 'Cannot modify submitted_at timestamp';
    END IF;
    
    -- Prevent changing graded_at once set
    IF OLD.graded_at IS NOT NULL AND NEW.graded_at != OLD.graded_at THEN
        RAISE EXCEPTION 'Cannot modify graded_at timestamp';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_timestamp_tampering_trigger
    BEFORE UPDATE ON student_assignments_phase4
    FOR EACH ROW
    EXECUTE FUNCTION prevent_timestamp_tampering();

-- Prevent attempt count manipulation
CREATE OR REPLACE FUNCTION prevent_attempt_manipulation()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent decreasing attempt count
    IF NEW.attempts_count < OLD.attempts_count THEN
        RAISE EXCEPTION 'Cannot decrease attempt count';
    END IF;
    
    -- Prevent skipping attempt numbers
    IF NEW.attempts_count > OLD.attempts_count + 1 THEN
        RAISE EXCEPTION 'Cannot skip attempt numbers';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_attempt_manipulation_trigger
    BEFORE UPDATE ON student_assignments_phase4
    FOR EACH ROW
    EXECUTE FUNCTION prevent_attempt_manipulation();

-- Prevent status regression
CREATE OR REPLACE FUNCTION prevent_status_regression()
RETURNS TRIGGER AS $$
BEGIN
    -- Define status hierarchy
    DECLARE
        old_priority INTEGER;
        new_priority INTEGER;
    BEGIN
        -- Assign priorities to statuses
        CASE OLD.status
            WHEN 'NOT_STARTED' THEN old_priority := 1;
            WHEN 'IN_PROGRESS' THEN old_priority := 2;
            WHEN 'SUBMITTED' THEN old_priority := 3;
            WHEN 'GRADED' THEN old_priority := 4;
            WHEN 'EXPIRED' THEN old_priority := 5;
            WHEN 'VIOLATED' THEN old_priority := 5;
            WHEN 'LOCKED' THEN old_priority := 6;
            ELSE old_priority := 0;
        END CASE;
        
        CASE NEW.status
            WHEN 'NOT_STARTED' THEN new_priority := 1;
            WHEN 'IN_PROGRESS' THEN new_priority := 2;
            WHEN 'SUBMITTED' THEN new_priority := 3;
            WHEN 'GRADED' THEN new_priority := 4;
            WHEN 'EXPIRED' THEN new_priority := 5;
            WHEN 'VIOLATED' THEN new_priority := 5;
            WHEN 'LOCKED' THEN new_priority := 6;
            ELSE new_priority := 0;
        END CASE;
        
        -- Prevent regression (except for specific allowed transitions)
        IF new_priority < old_priority AND NOT (
            (OLD.status = 'IN_PROGRESS' AND NEW.status = 'NOT_STARTED') OR
            (OLD.status = 'LOCKED' AND NEW.status IN ('SUBMITTED', 'EXPIRED', 'VIOLATED'))
        ) THEN
            RAISE EXCEPTION 'Invalid status transition from % to %', OLD.status, NEW.status;
        END IF;
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_status_regression_trigger
    BEFORE UPDATE ON student_assignments_phase4
    FOR EACH ROW
    EXECUTE FUNCTION prevent_status_regression();

-- Performance indexes
CREATE INDEX idx_student_assignments_status ON student_assignments_phase4(status);
CREATE INDEX idx_student_assignments_attempts ON student_assignments_phase4(attempts_count);
CREATE INDEX idx_student_assignments_student_assignment ON student_assignments_phase4(student_id, assignment_id);
CREATE INDEX idx_assignments_type_status ON assignments_phase4(assignment_type, status);
CREATE INDEX idx_assignments_due_date ON assignments_phase4(due_date);
CREATE INDEX idx_assignments_published ON assignments_phase4(status, published_at) WHERE status = 'PUBLISHED';

-- Academic violation constraints
ALTER TABLE academic_violations 
ADD CONSTRAINT valid_violation_type 
CHECK (violation_type IN ('TIME_EXCEEDED', 'MULTIPLE_TABS', 'COPY_PASTE', 'SUSPICIOUS_ACTIVITY', 'LOCKDOWN_BREACH'));

-- Unique constraint for one assignment per student
ALTER TABLE student_assignments_phase4 
ADD CONSTRAINT unique_student_assignment 
UNIQUE (assignment_id, student_id);