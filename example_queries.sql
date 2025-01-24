-- Example queries for analyzing Datadog monitor data
-- These queries help analyze monitors by project, severity, and provide useful breakdowns

-- 1. Count of monitors by project
-- Shows how many monitors exist for each project
SELECT
    project,
    COUNT(*) as monitor_count
FROM monitors
WHERE is_active = 1
GROUP BY project
ORDER BY monitor_count DESC;

-- 2. Count of monitors by severity level (extracted from name)
-- Note: This assumes severity is indicated by [SEV-N] in the monitor name
-- Shows distribution of monitors across severity levels
SELECT
    CASE
        WHEN name LIKE '%[SEV-1]%' THEN 'SEV-1'
        WHEN name LIKE '%[SEV-2]%' THEN 'SEV-2'
        WHEN name LIKE '%[SEV-3]%' THEN 'SEV-3'
        WHEN name LIKE '%[SEV-4]%' THEN 'SEV-4'
        WHEN name LIKE '%[SEV-5]%' THEN 'SEV-5'
        ELSE 'Unspecified'
    END as severity,
    COUNT(*) as count
FROM monitors
WHERE is_active = 1
GROUP BY severity
ORDER BY
    CASE severity
        WHEN 'SEV-1' THEN 1
        WHEN 'SEV-2' THEN 2
        WHEN 'SEV-3' THEN 3
        WHEN 'SEV-4' THEN 4
        WHEN 'SEV-5' THEN 5
        ELSE 6
    END;

-- 3. Detailed breakdown by project and severity
-- Shows how many monitors of each severity exist per project
WITH severity_breakdown AS (
    SELECT
        project,
        CASE
            WHEN name LIKE '%[SEV-1]%' THEN 'SEV-1'
            WHEN name LIKE '%[SEV-2]%' THEN 'SEV-2'
            WHEN name LIKE '%[SEV-3]%' THEN 'SEV-3'
            WHEN name LIKE '%[SEV-4]%' THEN 'SEV-4'
            WHEN name LIKE '%[SEV-5]%' THEN 'SEV-5'
            ELSE 'Unspecified'
        END as severity
    FROM monitors
    WHERE is_active = 1
)
SELECT
    project,
    COUNT(*) as total_monitors,
    SUM(CASE WHEN severity = 'SEV-1' THEN 1 ELSE 0 END) as sev1_count,
    SUM(CASE WHEN severity = 'SEV-2' THEN 1 ELSE 0 END) as sev2_count,
    SUM(CASE WHEN severity = 'SEV-3' THEN 1 ELSE 0 END) as sev3_count,
    SUM(CASE WHEN severity = 'SEV-4' THEN 1 ELSE 0 END) as sev4_count,
    SUM(CASE WHEN severity = 'SEV-5' THEN 1 ELSE 0 END) as sev5_count,
    SUM(CASE WHEN severity = 'Unspecified' THEN 1 ELSE 0 END) as unspecified_count
FROM severity_breakdown
GROUP BY project
ORDER BY total_monitors DESC;

-- 4. Monitor type distribution by project
-- Shows what types of monitors are used in each project
SELECT
    project,
    type,
    COUNT(*) as count
FROM monitors
WHERE is_active = 1
GROUP BY project, type
ORDER BY project, count DESC;

-- 5. Recently updated monitors
-- Shows monitors that have been updated in the last 30 days
SELECT
    name,
    project,
    last_updated,
    type
FROM monitors
WHERE is_active = 1
    AND last_updated >= datetime('now', '-30 days')
ORDER BY last_updated DESC;

-- Usage examples:
-- 1. To run any query, use sqlite3 from command line:
--    sqlite3 data/monitors.db < example_queries.sql
--
-- 2. To get just one specific query, copy it to a new file or run directly:
--    sqlite3 data/monitors.db "SELECT project, COUNT(*) FROM monitors GROUP BY project"
--
-- 3. To format output as CSV:
--    sqlite3 -csv data/monitors.db "SELECT project, COUNT(*) FROM monitors GROUP BY project" > output.csv
--
-- 4. To get a quick overview of all severities:
--    sqlite3 data/monitors.db "SELECT CASE WHEN name LIKE '%[SEV-1]%' THEN 'SEV-1' ..."