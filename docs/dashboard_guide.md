# Dashboard guide

Run: `python -m src.main` then `streamlit run dashboard/app.py` (opens http://localhost:8501). If results are missing the app runs the engine itself.

**KPI cards:** paid renewals (11), auto-approved (2), pending exceptions (9), unscheduled bookings (3), orphaned paid invoices (3), estimated hours saved (illustrative, assumption-based). Average reconciliation time is shown as **unavailable** because no production reconciliation timestamps exist; measured manual stage times are shown instead (with n).

**Charts:** pipeline funnel, exceptions by primary reason, renewals per day, auto vs manual split, teacher-follow-up stage. SLA-breach views are limited to what timestamps support.

**Tables:** invoices pending > 12 h, teacher forms awaiting/correction, bookings awaiting scheduling, payment mismatches, unscheduled students, ownership queue with required action and SLA.

**Filters (sidebar):** payment date, teacher, student, batch, exception type, priority, region (derived from mobile prefix: +91 India, +971 GCC, +1 US). Region is *derived*, not a source field.

**Testing done:** headless render with Streamlit `AppTest`; live server health check; real-browser screenshot (Chromium via Playwright); all 7 filters (date, teacher, student, batch, exception type, priority, region) were each tested individually against independently computed values. Not tested: combined filters, mobile layout.
