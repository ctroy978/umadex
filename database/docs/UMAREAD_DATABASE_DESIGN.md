# UMARead Database Design Documentation

## Overview

The UMARead database schema is designed following module-agnostic principles that allow the core `student_assignments` table to track progress across all UMA modules while storing module-specific data in dedicated tables and JSONB fields.

## Design Decisions and Trade-offs

### 1. Question Caching System

**Decision**: Separate `reading_question_cache` table with composite unique constraint on (assignment_id, chunk_number, question_type, difficulty_level).

**Trade-offs**:
- ✅ Reduces AI API calls significantly
- ✅ Allows bulk cache invalidation per assignment
- ✅ Maintains question consistency across students
- ❌ Requires additional storage
- ❌ Cache management complexity

**Alternative Considered**: Generate questions on-demand
- Would reduce storage but increase API costs and latency

### 2. Two-Question Structure

**Decision**: Single response table with `question_type` field distinguishing summary vs comprehension questions.

**Trade-offs**:
- ✅ Simple schema, easy to query both question types
- ✅ Natural progression tracking (summary → comprehension)
- ✅ Flexible for future question types
- ❌ Slightly denormalized (difficulty_level NULL for summary)

### 3. Comprehensive Testing

**Decision**: JSONB storage for test questions and answers in `reading_comprehensive_tests`.

**Trade-offs**:
- ✅ Flexible question formats (multiple choice, short answer, essay)
- ✅ Easy to version and modify test structure
- ✅ Supports complex scoring rubrics
- ❌ Less queryable than normalized tables
- ❌ Requires careful JSON validation

### 4. Progress Tracking

**Decision**: Use existing `student_assignments.progress_metadata` JSONB field for chunk completion tracking.

**Trade-offs**:
- ✅ Module-agnostic design
- ✅ No changes to core tables
- ✅ Flexible for different module needs
- ❌ Less efficient for complex queries
- ❌ Requires application-level validation

## Sample Queries

### 1. Get Current Question for Student

```sql
-- Get the current question a student should answer
WITH student_progress AS (
    SELECT 
        sa.current_position as current_chunk,
        sa.progress_metadata->>'difficulty_level' as difficulty_level,
        sa.assignment_id
    FROM student_assignments sa
    WHERE sa.student_id = $1 
    AND sa.assignment_id = $2
    AND sa.status = 'in_progress'
),
last_response AS (
    SELECT 
        question_type,
        is_correct
    FROM reading_student_responses
    WHERE student_id = $1
    AND assignment_id = $2
    AND chunk_number = (SELECT current_chunk FROM student_progress)
    ORDER BY occurred_at DESC
    LIMIT 1
)
SELECT 
    q.id,
    q.question_text,
    q.question_type,
    q.difficulty_level,
    q.question_metadata
FROM reading_question_cache q
JOIN student_progress sp ON q.assignment_id = sp.assignment_id
WHERE q.chunk_number = sp.current_chunk
AND (
    -- If no response or last was comprehension, show summary
    (NOT EXISTS(SELECT 1 FROM last_response) AND q.question_type = 'summary')
    OR 
    -- If last summary was correct, show comprehension
    (EXISTS(SELECT 1 FROM last_response WHERE question_type = 'summary' AND is_correct) 
     AND q.question_type = 'comprehension' 
     AND q.difficulty_level = sp.difficulty_level::INTEGER)
);
```

### 2. Calculate Student Performance Metrics

```sql
-- Get student performance metrics for a reading assignment
WITH response_stats AS (
    SELECT 
        student_id,
        chunk_number,
        question_type,
        COUNT(*) as total_attempts,
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_attempts,
        AVG(time_spent_seconds) as avg_time_spent,
        MAX(difficulty_level) as max_difficulty
    FROM reading_student_responses
    WHERE assignment_id = $1
    GROUP BY student_id, chunk_number, question_type
)
SELECT 
    u.name as student_name,
    COUNT(DISTINCT rs.chunk_number) as chunks_attempted,
    AVG(rs.correct_attempts::FLOAT / rs.total_attempts) as accuracy_rate,
    AVG(rs.avg_time_spent) as avg_time_per_question,
    MAX(rs.max_difficulty) as highest_difficulty_reached,
    sa.status as assignment_status
FROM response_stats rs
JOIN users u ON u.id = rs.student_id
JOIN student_assignments sa ON sa.student_id = rs.student_id 
    AND sa.assignment_id = $1
GROUP BY u.name, sa.status
ORDER BY accuracy_rate DESC;
```

### 3. Teacher Analytics Dashboard

```sql
-- Get assignment-level analytics for teachers
WITH chunk_stats AS (
    SELECT 
        assignment_id,
        chunk_number,
        question_type,
        AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) as success_rate,
        AVG(attempt_number) as avg_attempts,
        COUNT(DISTINCT student_id) as students_attempted
    FROM reading_student_responses
    WHERE assignment_id IN (
        SELECT id FROM reading_assignments WHERE teacher_id = $1
    )
    GROUP BY assignment_id, chunk_number, question_type
),
problem_chunks AS (
    SELECT 
        assignment_id,
        chunk_number,
        MIN(success_rate) as min_success_rate
    FROM chunk_stats
    GROUP BY assignment_id, chunk_number
    HAVING MIN(success_rate) < 0.7 -- 70% threshold
)
SELECT 
    ra.title,
    ra.id as assignment_id,
    COUNT(DISTINCT cs.chunk_number) as total_chunks,
    COUNT(DISTINCT pc.chunk_number) as problem_chunks,
    AVG(cs.success_rate) as overall_success_rate,
    MAX(cs.students_attempted) as max_students
FROM reading_assignments ra
LEFT JOIN chunk_stats cs ON cs.assignment_id = ra.id
LEFT JOIN problem_chunks pc ON pc.assignment_id = ra.id
WHERE ra.teacher_id = $1
GROUP BY ra.title, ra.id
ORDER BY overall_success_rate ASC;
```

### 4. Generate Personalized Student Insights

```sql
-- Generate AI-ready event data for student insights
SELECT 
    se.event_type,
    se.event_data,
    se.occurred_at,
    sa.progress_metadata
FROM student_events se
JOIN student_assignments sa ON sa.student_id = se.student_id 
    AND sa.assignment_id = se.assignment_id
WHERE se.student_id = $1
AND se.assignment_type = 'umaread'
AND se.occurred_at >= NOW() - INTERVAL '30 days'
ORDER BY se.occurred_at DESC
LIMIT 100;
```

### 5. Manage Question Cache

```sql
-- Check cache coverage for an assignment
WITH chunks AS (
    SELECT DISTINCT chunk_number 
    FROM reading_chunks 
    WHERE assignment_id = $1
),
cache_coverage AS (
    SELECT 
        c.chunk_number,
        COUNT(DISTINCT CASE WHEN qc.question_type = 'summary' THEN 1 END) as has_summary,
        COUNT(DISTINCT qc.difficulty_level) as difficulty_levels_cached
    FROM chunks c
    LEFT JOIN reading_question_cache qc ON qc.assignment_id = $1 
        AND qc.chunk_number = c.chunk_number
    GROUP BY c.chunk_number
)
SELECT 
    chunk_number,
    has_summary > 0 as summary_cached,
    difficulty_levels_cached,
    8 - difficulty_levels_cached as missing_levels
FROM cache_coverage
ORDER BY chunk_number;
```

## Future Module Expansion

### Design Patterns for New Modules

1. **Progress Tracking**: All modules use `student_assignments` table with module-specific data in `progress_metadata` JSONB.

2. **Event Logging**: All modules log to `student_events` with `assignment_type` distinguishing modules.

3. **Module Tables**: Each module gets its own set of tables prefixed with module name (e.g., `vocabulary_*`, `debate_*`).

4. **Caching Pattern**: The question cache model can be adapted:
   ```sql
   CREATE TABLE vocabulary_term_cache (
       id UUID PRIMARY KEY,
       assignment_id UUID NOT NULL,
       term_number INTEGER NOT NULL,
       difficulty_level INTEGER,
       -- module-specific fields
   );
   ```

5. **Response Pattern**: Student interaction tables follow similar structure:
   ```sql
   CREATE TABLE vocabulary_student_attempts (
       id UUID PRIMARY KEY,
       student_id UUID NOT NULL,
       assignment_id UUID NOT NULL,
       -- module-specific fields
   );
   ```

### Example: UMAVocab Extension

```sql
-- Following the same patterns
CREATE TABLE vocabulary_term_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL,
    term_number INTEGER NOT NULL,
    difficulty_level INTEGER NOT NULL,
    
    -- Vocabulary-specific
    example_sentences JSONB NOT NULL,
    mnemonics TEXT,
    related_terms JSONB,
    
    ai_model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE vocabulary_student_practice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    assignment_id UUID NOT NULL,
    term_id UUID NOT NULL,
    
    practice_type VARCHAR(50) NOT NULL, -- 'definition', 'usage', 'spelling'
    is_correct BOOLEAN NOT NULL,
    time_spent_seconds INTEGER NOT NULL,
    
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Performance Considerations

### Key Indexes

1. **Lookup Performance**: Composite indexes on (assignment_id, chunk_number) for fast question retrieval.

2. **Student Progress**: Indexes on (student_id, assignment_id) for progress queries.

3. **Time-based Analytics**: Indexes on occurred_at for event analysis.

### Query Optimization Tips

1. **Use JSONB operators** for progress_metadata queries:
   ```sql
   WHERE progress_metadata @> '{"chunks_completed": [1,2,3]}'
   ```

2. **Partition student_events** by occurred_at if data grows large.

3. **Consider materialized views** for complex teacher analytics.

## Security Considerations

1. **RLS Policies**: All tables have row-level security ensuring:
   - Students only see their own data
   - Teachers only see their assignments
   - Cross-student data isolation

2. **SECURITY DEFINER Functions**: Helper functions run with elevated privileges but validate permissions internally.

3. **Input Validation**: All user inputs should be validated at API level before database insertion.

## Migration Notes

When deploying:

1. Run migration in transaction
2. Create indexes CONCURRENTLY in production
3. Warm question cache for active assignments
4. Monitor query performance and adjust indexes

## Conclusion

This design provides a robust foundation for UMARead while establishing patterns that other UMA modules can follow. The module-agnostic core with module-specific extensions ensures scalability and maintainability as the platform grows.