# User Manual — USAMIS-Python

This manual explains how each role uses USAMIS. Screenshots should be captured
from the running application (see `docs/screenshots/`); never substitute
fabricated images.

## 1. Signing in and out

1. Open the application URL; the login page appears.
2. Enter your username and password and click **Sign In**.
3. You are redirected to your role-specific dashboard.
4. To sign out, use **Sign out** in the top bar.

Repeated failed sign-ins temporarily lock the account (a security control).
Inactive or blocked accounts cannot sign in.

## 2. The layout

- **Sidebar** — the modules available to your role.
- **Top bar** — your name, role badge, Profile, Password, and Sign out.
- **Content area** — tables, forms, and dashboards with flash notifications.

You only see modules you are permitted to use; the server independently
enforces the same rules.

## 3. Administrator

1. **Dashboard** — totals for students, departments, programs, offerings,
   enrollments, pending requests, and fee figures.
2. **Users** — create, edit, activate/deactivate, and assign roles.
   You cannot deactivate your own account.
3. **Roles** — read-only view of the permission matrix.
4. **Audit Log** — filter by action or entity to review sensitive operations.
5. All academic, fee, and report modules are available to you.

## 4. Academic staff (Registrar)

1. **Dashboard** — counts plus the latest pending enrollment requests.
2. **Students** — search, filter, create, edit, and view profiles; deactivate
   (withdraw) a student via a soft status change.
3. **Departments / Programs** — maintain the academic structure.
4. **Courses / Semesters** — maintain the catalogue, prerequisites, semesters,
   and course offerings (teacher and capacity).
5. **Enrollments** — approve or reject pending requests; drop enrollments.
6. **Reports** — students per department, enrollment by status, grade
   distribution, fee defaulters, low attendance.

## 5. Teacher

1. **Dashboard** — your assigned offerings with enrolled and graded counts.
2. **Grade Entry** — open an offering, enter a score (0–100) per student, and
   optionally tick **publish**. Only your own courses appear; accessing another
   course is forbidden.
3. **Attendance** — choose a date and status and record attendance for all
   enrolled students; duplicate dates are prevented.
4. **Reports** — read-only academic reports.

## 6. Finance officer

1. **Dashboard** — fees assessed, collected, outstanding, and recent payments.
2. **Fees** — create fee categories, assess fees (with optional adjustment and
   due date), and record payments (positive amount, unique reference).
3. **Fee account** — open a student to see assessments, payments, and the
   computed balance and status.
4. **Reports** — fee defaulters list.

## 7. Student

1. **Dashboard** — current enrollments, weighted average, attendance summary,
   and fee balance.
2. **Enroll in Course** — pick an offering and submit; the server checks
   eligibility. If rejected, a reason is shown (duplicate, capacity full,
   prerequisite unmet, registration closed).
3. **My Enrollments** — status of each request.
4. **My Grades** — published grades and the credit-weighted average.
5. **My Attendance** — your attendance records.
6. **My Fees** — assessments, payments, balance, and status.

Students can only ever see their own records; changing a URL to another
student's identifier produces **Access Denied**.

## 8. Common tasks

- **Change your password** — top bar → *Password*, then save.
- **Update your profile** — top bar → *Profile*.
- **Handle errors** — a 403 means you lack permission; a 404 means the record
  does not exist; both show a friendly page, never a stack trace.

## 9. Screen inventory

| # | Screen | Route |
|---|---|---|
| 1 | Login | `/auth/login` |
| 2 | 403 / 404 / 500 | error pages |
| 3 | Administrator dashboard | `/dashboard/` |
| 4 | Student dashboard | `/dashboard/` |
| 5 | Teacher dashboard | `/dashboard/` |
| 6 | Academic staff dashboard | `/dashboard/` |
| 7 | Students list / profile / create / edit | `/students/...` |
| 8 | Departments | `/departments/` |
| 9 | Programs | `/programs/` |
| 10 | Courses + prerequisites | `/courses/...` |
| 11 | Semesters + offerings | `/semesters/...` |
| 12 | Enrollment request / management | `/enrollments/...` |
| 13 | Grade entry / my grades | `/grades/...` |
| 14 | Attendance | `/attendance/...` |
| 15 | Fees / payments | `/fees/...` |
| 16 | Reports | `/reports/...` |
| 17 | Users / roles | `/admin/...` |
| 18 | Audit log | `/admin/audit` |
| 19 | Profile / password | `/auth/profile`, `/auth/password` |
