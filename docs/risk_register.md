# Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Wrongly auto-approve a payment | Low (deterministic rules, conservative) | High | Mandatory-checks-only approval; shadow period; kill switch; audit | Head of Ops |
| R2 | Duplicate booking creation | Medium without keys | High | Idempotency key + unique constraint; existing booking => never recreate (tested) | Eng |
| R3 | Assumption A1 (seat already counted) is wrong | Medium | Medium | Default OFF; validate with Ops; capacity check on net-new seats | Scheduling Ops |
| R4 | Masked/partial identifiers hide real mismatches | Medium | Medium | Compare full numbers/hashes in production; student_id remains the anchor | Eng |
| R5 | Teachers ignore reminders | Medium | Medium | 12 h escalation; invoice-first removes the dependency | Ops Executive |
| R6 | LLM hallucinates in drafts | Low-Medium | Medium | LLM wording only, templates fallback, human approval, no figures added | PM |
| R7 | WhatsApp template rejection / throttling | Medium | Low | Pre-approved templates; email fallback | Eng |
| R8 | Gateway webhook loss | Low | High | Retry + periodic reconciliation against gateway API | Eng |
| R9 | Weekend/holiday behaviour untested (data Sun-Tue only) | Medium | Medium | Business calendar config; test with 3 months of data | PM |
| R10 | Sample-size overfitting (13 invoices) | High | Medium | Treat all rates as illustrative until the 3-month pull | PM |
| R11 | Privacy / PII exposure in drafts or repo | Low | High | Masked data, no amounts/ids in drafts, raw data excluded from public repo | PM |
| R12 | Discount leakage continues | Medium | Medium | Discount codes with approver id | Ops Manager |
