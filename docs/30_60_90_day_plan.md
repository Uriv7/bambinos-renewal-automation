# 30-60-90 day plan

## Projected time savings (transparent model - not a historical figure)
`hours saved / month = renewals x auto-approval share x manual minutes avoided / 60`

| Input | Value | Basis |
|---|---|---|
| Monthly renewals | **unknown - obtain from Ops** (1,000 used only to illustrate scale) | assumption |
| Auto-approval share, current rules | 15.4% (2 of 13) | measured on sample |
| Auto-approval share, invoice-first simulation | 38.5% (5 of 13) | simulation on sample |
| Manual minutes per clean renewal | 10 | **assumption - run a time study** |

At 1,000 renewals/month: ~25.6 h (current rules) to ~64.1 h (invoice-first) of manual verification avoided. The bigger value is latency: sample shows a clean renewal waiting ~33 h for approval and 5 of 11 paid invoices > 24 h without a class. Share and minutes will change with real data; treat as a hypothesis.

## Days 1-30 - baseline and shadow
| Item | Detail |
|---|---|
| Activities | Validate assumptions A1 + instalment + discount policy; pull 3 months of production data; time study; run engine in **shadow mode** (no writes); pilot with 10-20 teachers; train Ops users on dashboard/queue |
| Deliverables | Baseline KPIs from full data; validated reason-code policy; shadow-run report; trained pilot cohort |
| Owner | AI Program Manager (lead), Ops Head (decisions), Data/Eng (extracts) |
| Dependencies | Read-only DB replica or CSV exports; named owners per role |
| Risks | Sample not representative; masked data hides mismatches; teachers ignore reminders |
| Success metrics | Engine decision agrees with Ops outcome on >= 95% of shadow cases; false-approve rate 0 |
| Go/no-go | Zero shadow cases where engine would auto-approve something Ops rejected (or each explained and rule-fixed) |
| Rollback | Nothing is live; stop the shadow job |

## Days 31-60 - controlled auto-approval
| Item | Detail |
|---|---|
| Activities | 50-100 teachers; auto-approve **same-batch, full-payment, clean** only; exception notifications live (human-approved WhatsApp); weekly false-positive/negative review; fix data entry (invoice picker); ownership/escalation rota |
| Deliverables | Gateway webhook + n8n flow; idempotent booking creator; exception queue; weekly review log |
| Owner | Program Manager, Eng, Ops Manager |
| Dependencies | Webhook signing keys; WhatsApp templates approved; booking-creation API |
| Risks | Wrong approval; duplicate booking; parent messaging errors |
| Success metrics | Clean renewals scheduled <= 4 business h; exceptions have owner < 30 min (P1); duplicate bookings = 0 |
| Go/no-go | 2 consecutive weeks with 0 wrong approvals and queue age within SLA |
| Rollback | Flip the auto-approve flag off; manual queue continues; cancel by idempotency key |

## Days 61-90 - scale
| Item | Detail |
|---|---|
| Activities | 200+ teachers; invoice-first (form optional) for same-batch; batch-change self-service link; Metabase; tune thresholds; measure savings vs baseline; continuous-improvement cadence |
| Deliverables | Production integrations, SLA dashboard, savings report vs the 30-day baseline |
| Owner | Program Manager, Ops Head |
| Dependencies | Validated baseline; change-management completed (`change_management.md`) |
| Risks | Teacher resistance; scope creep to sales/refunds; capacity logic wrong |
| Success metrics | Auto-approval share vs baseline; P50/P90 payment -> first class; exception rate trend; Ops hours on renewals |
| Go/no-go | KPI targets met for 2 weeks; Head of Ops sign-off |
| Rollback | Revert cohort to shadow mode by flag |
