# USAMIS-Python — Frontend Redesign

**Date:** 2026-10-12
**Scope:** UI/UX overhaul of the Flask/Jinja frontend. No backend data model,
routes, authorization or business logic changed (one real bug was fixed; see §5).

## 1. Design system

A single stylesheet (`app/static/css/app.css`) defines a modern university SaaS
look:

| Token | Value |
|---|---|
| Sidebar / navy | `#0F172A` → `#131C31` gradient |
| Royal blue (primary) | `#2563EB` |
| Cyan (accent) | `#06B6D4` |
| Background | `#F8FAFC` |
| Surface | `#FFFFFF` |
| Text / muted | `#0F172A` / `#64748B` |
| Radius | 16px (cards), 10px (buttons/inputs) |
| Font | Inter (Google Fonts) with system fallback |
| Spacing | 8px scale (`--sp-1` … `--sp-7`) |

Legacy CSS class names were preserved so all templates continue to work.

## 2. Application shell

- **Grouped sidebar** with section labels: Overview, My Studies, Academic
  Records, My Records, Finance, Administration.
- **14 inline SVG icons** (no icon-font dependency).
- **Active-route highlighting** (cyan left bar + gradient background).
- **Collapsible behaviour** with a mobile overlay and ARIA state on the toggle.
- **Topbar profile menu**: avatar with initials, dropdown (Profile / Change
  password / Sign out).
- **Breadcrumbs** block on every page.
- **Skip link** and semantic landmarks for keyboard/screen-reader users.
- Online status indicator in the sidebar footer.

Grouped labels are wrapped in the same permission checks as their links, so each
role sees only the groups it can use.

## 3. Dashboards (role-specific, live data)

| Role | Contents |
|---|---|
| Administrator | 5 KPI cards, 4 Chart.js charts (enrollment trend, grade distribution, students by department, fee collection), activity feed, quick actions |
| Academic staff | KPI cards + pending enrollment requests |
| Teacher | Assigned courses, grades-awaiting-publication and attendance-incomplete warning cards, per-course grading progress |
| Finance | Assessed / collected / outstanding KPIs, collection-rate progress, doughnut chart, recent payments |
| Student | Welcome header, academic average, attendance %, fee balance, progress bar, current courses, recent grades |

**Charts use real database values only** — no fabricated statistics. Chart data is
computed in `app/dashboard/__init__.py` and serialised into the template as JSON.

## 4. Module pages

Every list page now has a page header (title + description), breadcrumbs, a
toolbar (search/filter on the left, primary action on the right), status pills
and a helpful empty state. Form pages use a two-column responsive grid with a
consistent action bar. Detail pages follow the same header/breadcrumb pattern.

## 5. Bug found and fixed

The course detail page's "Add prerequisite" `<select>` was **always empty**: the
template looped over course *offerings* (the wrong entity) and the route never
passed candidate courses. Fixed in `app/courses/__init__.py` (route now supplies
`candidate_courses`, excluding the course itself and existing prerequisites) and
`app/templates/courses/detail.html`. Verified: the dropdown now lists 43 courses.

A second bug surfaced during the dashboard work: `Semester.label` is a Python
property, not a mapped column, so it could not be selected in a joined query —
this produced a **500** on the admin dashboard. Fixed by composing labels in
Python.

## 6. Accessibility

- Skip-to-content link.
- `aria-label` / `aria-expanded` / `aria-haspopup` on interactive controls.
- Chart canvases carry `role="img"` and descriptive `aria-label`.
- Visible focus ring (`:focus-visible`) throughout.
- `prefers-reduced-motion` disables transitions.
- Status conveyed by text as well as colour.

## 7. Verification

| Check | Result |
|---|---|
| Automated tests | 87 / 87 pass |
| Page crawl (5 roles × 16 routes) | no 5xx on any page |
| All templates block/if balanced | yes |
| Charts render with live data | 4 / 4 |
| Screenshots recaptured | 16 / 16 distinct |

## 8. Notes / limitations

- Chart.js is loaded from a CDN; for offline or hardened deployments, vendor it
  locally (add it to `app/static/js/`).
- The interface uses Inter from Google Fonts with a system fallback.
- The login page's demo-accounts panel is a development convenience and must be
  removed (or gated behind `DEBUG`) before production.
