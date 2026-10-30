\echo USAMIS demo database summary
SELECT 'Students' AS record_type, count(*) AS total FROM students
UNION ALL SELECT 'Teachers', count(*) FROM teachers
UNION ALL SELECT 'Courses', count(*) FROM courses
UNION ALL SELECT 'Course offerings', count(*) FROM course_offerings
UNION ALL SELECT 'Enrollments', count(*) FROM enrollments
UNION ALL SELECT 'Grades', count(*) FROM grades
UNION ALL SELECT 'Attendance', count(*) FROM attendance
UNION ALL SELECT 'Synthetic training snapshots', count(*) FROM risk_snapshots
UNION ALL SELECT 'Trained experiments', count(*) FROM risk_experiments;
\echo Student profiles
SELECT student_number, first_name, last_name FROM students ORDER BY student_number;
\echo Teacher profiles
SELECT staff_number, first_name, last_name FROM teachers ORDER BY staff_number;
\echo Training data type
SELECT data_kind, count(*) AS snapshots FROM risk_snapshots GROUP BY data_kind;
