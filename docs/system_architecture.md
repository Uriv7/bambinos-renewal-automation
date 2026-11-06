# System architecture

```mermaid
flowchart LR
  GW[Razorpay / Stripe webhooks] --> N8N[n8n workflow]
  N8N --> API[Python reconciliation service]
  DB[(PostgreSQL / existing MySQL replica)] <--> API
  API --> DEC{Decision engine}
  DEC -->|clean| BK[Booking + schedule creator - idempotent]
  DEC -->|exception| Q[Exception queue]
  Q --> OPS[Ops owners]
  API --> LLM[LLM: wording + classification only]
  LLM --> MSG[Message drafts]
  MSG --> WA[WhatsApp Business API]
  BK --> WA
  API --> AUD[(Audit log)]
  DB --> DASH[Dashboard: Streamlit / Metabase]
  Q --> DASH
```

| Layer | Choice | Status |
|---|---|---|
| Rules engine | Python + pandas (`src/`) | **Built and tested** |
| State / idempotency | JSON ledger (prototype) -> unique key column in PostgreSQL | Prototype only |
| Orchestration | n8n: webhook -> HTTP call to engine -> branch | Design only |
| Payments | Gateway webhooks (signature-verified) | Design only |
| Messaging | WhatsApp Business API templates, human-approved at first | Design only (drafts generated) |
| Visibility | Streamlit dashboard (built); Metabase for production | Dashboard built |
| AI | LLM for classifying teacher remarks and polishing drafts, behind env key | Code path present, **not tested live** |

## Reliability patterns
Retry with exponential backoff on webhooks; dead-letter queue for failed runs; reconciliation job every 5 minutes re-evaluating open exceptions; feature flag per teacher cohort for shadow -> live; rollback = disable auto-approve flag and fall back to the manual queue (existing process continues unchanged).

## Security
No credentials in repo (`.env.example` only). PII masked in data; drafts avoid amounts, gateway ids and child names. Role-based access: Finance sees payments, teachers see only own students. Audit log immutable (append-only table).
