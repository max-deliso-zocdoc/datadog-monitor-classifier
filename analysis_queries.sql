-- Monitor Severity Distribution
SELECT '=== Monitor Severity Distribution ===' || char(10);
SELECT severity || ': ' || COUNT(*) || ' monitors'
FROM (
  SELECT CASE
    WHEN name LIKE '%SEV-1%' THEN 'SEV-1'
    WHEN name LIKE '%SEV-2%' THEN 'SEV-2'
    WHEN name LIKE '%SEV-3%' THEN 'SEV-3'
    WHEN name LIKE '%SEV-4%' THEN 'SEV-4'
    WHEN name LIKE '%SEV-5%' THEN 'SEV-5'
    ELSE 'UNKNOWN'
  END as severity
  FROM monitors
)
GROUP BY severity
ORDER BY severity;

-- Monitor Types Distribution
SELECT char(10) || '=== Monitor Types Distribution ===' || char(10);
SELECT type || ': ' || COUNT(*) || ' monitors'
FROM monitors
GROUP BY type
ORDER BY COUNT(*) DESC;

-- Project Distribution
SELECT char(10) || '=== Project Distribution ===' || char(10);
SELECT project || ': ' || COUNT(*) || ' monitors'
FROM monitors
WHERE project IS NOT NULL AND project != ''
GROUP BY project
ORDER BY COUNT(*) DESC;

-- Monitor States Distribution
SELECT char(10) || '=== Monitor States Distribution ===' || char(10);
SELECT overall_state || ': ' || COUNT(*) || ' monitors'
FROM monitors
GROUP BY overall_state
ORDER BY COUNT(*) DESC;

-- Most Common Tags
SELECT char(10) || '=== Most Common Tags ===' || char(10);
SELECT t.tag || ': ' || COUNT(*) || ' monitors'
FROM monitor_tags t
GROUP BY t.tag
ORDER BY COUNT(*) DESC
LIMIT 20;

-- Most Common Notification Targets
SELECT char(10) || '=== Most Common Notification Targets ===' || char(10);
SELECT n.target || ': ' || COUNT(*) || ' monitors'
FROM monitor_notifications n
GROUP BY n.target
ORDER BY COUNT(*) DESC
LIMIT 20;