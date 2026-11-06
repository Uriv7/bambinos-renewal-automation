"""Central configuration: file schemas, thresholds and the reason-code policy.

The reason-code table below IS the machine-readable decision matrix
(docs/decision_matrix.md is generated from the same facts). Owner roles,
priorities and SLAs are PROPOSED targets, not existing company commitments.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FILES = {
    "invoices": "1_invoices.csv",
    "forms": "2_faculty_form_unapproved.csv",
    "bookings": "3_booking_requests.csv",
    "schedule": "4_class_schedule_bookings.csv",
    "reference": "reference_active_batches_and_students.csv",
}

SCHEMAS = {
    "invoices": ["id", "invoice_number", "user_id", "student_id", "class_id", "educator_id", "parent_name",
                 "mobile", "email", "currency", "amount", "discount_amount", "net_amount", "payment_type",
                 "payment_mode", "payment_gateway", "gateway_order_id", "gateway_payment_id", "invoice_link",
                 "payment_status", "is_renewal", "paid_at", "created_at", "updated_at", "deleted_at"],
    "forms": ["id", "educator_id", "educator_name", "user_id", "student_id", "student_name", "parent_mobile",
              "class_id", "current_classbatch_id", "invoice_id", "invoice_link", "amount_paid",
              "sessions_purchased", "continue_same_batch", "preferred_days", "preferred_time_slot", "remarks",
              "approval_status", "approved_by", "approved_at", "created_at", "updated_at", "deleted_at"],
    "bookings": ["id", "faculty_form_id", "invoice_id", "user_id", "student_id", "class_id", "educator_id",
                 "classbatch_id", "sessions_count", "is_renewal", "continue_same_batch", "preferred_days",
                 "preferred_time", "request_status", "batch_allocated", "allocated_by", "allocated_at",
                 "created_at", "updated_at", "deleted_at"],
    "schedule": ["id", "bookingrequest_id", "invoice_id", "classschedule_id", "classbatch_id", "class_id",
                 "user_id", "student_id", "educator_id", "class_date", "start_time", "end_time", "booking_type",
                 "is_cancelled", "attended_class", "created_at", "updated_at", "deleted_at"],
    "reference": ["student_id", "user_id", "student_name_masked", "parent_name_masked", "registered_mobile_masked",
                  "registered_email_masked", "current_classbatch_id", "classbatch_name", "class_id", "class_name",
                  "category_id", "category_name", "educator_id", "educator_name", "standard_fee_24_sessions_inr",
                  "batch_days", "batch_start_time", "active_students_count", "max_batch_size", "deleted_at"],
}

# Form fields that must be present for a renewal to be schedulable.
REQUIRED_FORM_FIELDS = ["educator_id", "user_id", "student_id", "class_id", "current_classbatch_id", "invoice_id",
                        "amount_paid", "sessions_purchased", "continue_same_batch", "preferred_days",
                        "preferred_time_slot"]

# Fields that define a faculty-form "payload" for identical-duplicate detection.
FORM_PAYLOAD_FIELDS = ["educator_id", "user_id", "student_id", "class_id", "current_classbatch_id", "invoice_id",
                       "amount_paid", "sessions_purchased", "continue_same_batch", "preferred_days",
                       "preferred_time_slot", "parent_mobile"]

P_SLA = {
    "P1": "Ops response within 30 min (operating hours)",
    "P2": "Resolve within 4 business hours",
    "P3": "Resolve within 1 business day",
}


@dataclass(frozen=True)
class ReasonPolicy:
    code: str
    blocking: bool          # True -> case can never be auto-approved while this is open
    severity: str           # Critical / High / Medium / Low
    owner: str              # proposed responsible role
    priority: str           # P1 / P2 / P3
    action: str             # required next action
    channel: str            # notification channel
    description: str


# Owner roles (proposed): Finance Ops, Teacher, Ops Executive, Scheduling Ops, Parent Success, Ops Manager
_R = ReasonPolicy
REASONS: dict[str, ReasonPolicy] = {p.code: p for p in [
    _R("PAYMENT_NOT_VERIFIED", True, "Critical", "Finance Ops", "P1",
       "Check gateway dashboard for the order; confirm captured/failed/pending before any approval.",
       "Ops queue + WhatsApp (parent)", "Payment is not 'Paid' with a gateway payment id and paid_at."),
    _R("INVOICE_NOT_FOUND", True, "High", "Ops Executive", "P2",
       "Locate the intended invoice (see probable match) and ask the teacher to resubmit with the right invoice.",
       "Ops queue + WhatsApp (teacher)", "Faculty form references an invoice id that does not exist."),
    _R("ORPHANED_INVOICE", True, "High", "Ops Executive", "P2",
       "Paid invoice has no form and no probable candidate form; contact teacher/parent to identify the renewal.",
       "Ops queue", "Paid invoice with no linked or candidate faculty form."),
    _R("MISSING_FACULTY_FORM", True, "High", "Teacher", "P2",
       "Teacher submits the renewal form (reminder at 2h, escalate to Ops Executive at 12h).",
       "WhatsApp (teacher)", "Paid invoice has no faculty form linked by exact invoice id."),
    _R("DUPLICATE_INVOICE", True, "High", "Finance Ops", "P1",
       "Confirm which invoice is authoritative; refund or merge the duplicate.",
       "Ops queue", "Same student/class has more than one paid/partial invoice in the renewal window."),
    _R("DUPLICATE_FACULTY_FORM", False, "Low", "Ops Executive", "P3",
       "Identical duplicate collapsed to the earliest form; non-identical duplicates need review.",
       "Audit log", "More than one active form for the same invoice."),
    _R("AMOUNT_MISMATCH", True, "High", "Finance Ops", "P1",
       "Reconcile invoice net amount vs teacher-entered amount vs standard fee before approving.",
       "Ops queue", "Invoice net amount differs from the form amount or the standard fee."),
    _R("DISCOUNT_REQUIRES_APPROVAL", True, "Medium", "Ops Manager", "P2",
       "Confirm the discount was authorised by Sales/Ops Head; record the approver.",
       "Ops queue", "Invoice carries a discount that has no recorded approval."),
    _R("STUDENT_ID_MISMATCH", True, "Critical", "Ops Executive", "P1",
       "Verify student identity with parent/teacher; never approve on name or phone similarity.",
       "Ops queue", "Student/user ids differ between invoice, form and reference."),
    _R("PARENT_CONTACT_MISMATCH", True, "Medium", "Parent Success", "P2",
       "Confirm with the registered parent number that the paying contact is authorised.",
       "WhatsApp (parent, registered number)", "Paying mobile differs from the registered parent mobile."),
    _R("TEACHER_ID_MISMATCH", True, "High", "Ops Executive", "P2",
       "Confirm the educator for the batch; correct the form or the batch record.",
       "Ops queue + WhatsApp (teacher)", "Educator differs between invoice, form and reference."),
    _R("COURSE_MISMATCH", True, "High", "Ops Executive", "P2",
       "Confirm the course/level being renewed.", "Ops queue", "class_id differs between sources."),
    _R("BATCH_INACTIVE", True, "High", "Scheduling Ops", "P1",
       "Find an equivalent active batch and agree it with the parent.", "Ops queue", "Batch missing or soft-deleted."),
    _R("BATCH_FULL", True, "High", "Scheduling Ops", "P1",
       "Check whether the student's seat is already counted (same-batch renewal); otherwise offer alternatives.",
       "Ops queue + WhatsApp (parent)", "active_students_count >= max_batch_size."),
    _R("SCHEDULING_CONFLICT", True, "High", "Scheduling Ops", "P2",
       "Resolve teacher/student overlap before creating schedule rows.", "Ops queue", "Overlapping sessions."),
    _R("BOOKING_ALREADY_EXISTS", False, "Low", "Ops Executive", "P3",
       "Do not create a new booking; continue from the existing one.", "Audit log", "Booking already exists for invoice."),
    _R("SCHEDULE_ALREADY_EXISTS", False, "Low", "Ops Executive", "P3",
       "Do not recreate schedule rows.", "Audit log", "Schedule rows already exist for the booking."),
    _R("PARTIAL_PAYMENT", True, "High", "Finance Ops", "P2",
       "Hold scheduling per policy; send instalment-2 reminder; confirm instalment policy with Ops Head.",
       "WhatsApp (parent) + Ops queue", "Payment status is Partially_Paid."),
    _R("MISSING_REQUIRED_FIELD", True, "Medium", "Ops Executive", "P2",
       "Obtain the missing field (e.g. target batch) from teacher/parent.", "Ops queue", "Mandatory field is empty."),
    _R("INVALID_REFERENCE", True, "High", "Ops Executive", "P2",
       "Fix the dangling/typo reference with the teacher; use the probable match as a hint only.",
       "Ops queue + WhatsApp (teacher)", "A reference id does not resolve to a record."),
    _R("TIMESTAMP_ANOMALY", True, "Medium", "Ops Executive", "P2",
       "Form was created before its invoice existed; verify the form really belongs to this invoice.",
       "Ops queue", "Impossible timeline between linked records."),
    _R("MANUAL_REVIEW_REQUIRED", True, "Medium", "Scheduling Ops", "P2",
       "Human decision needed (e.g. batch-change renewal).", "Ops queue", "Not safely automatable."),
]}


@dataclass
class EngineConfig:
    as_of: str | None = None                 # ISO timestamp; default = latest timestamp in the data
    standard_sessions: int = 24
    session_minutes: int = 50
    duplicate_invoice_window_days: int = 30
    # ASSUMPTION A1 (needs Ops validation): active_students_count already includes the renewing
    # student, so a same-batch renewal needs no extra seat. Conservative default = False.
    same_batch_seat_already_held: bool = False
    collapse_identical_duplicate_forms: bool = True
    teacher_reminder_hours: float = 2.0
    teacher_escalation_hours: float = 12.0
    scheduling_sla_hours: float = 4.0        # proposed; measured in clock hours in the prototype
    payment_sla_minutes: float = 5.0
    extra: dict = field(default_factory=dict)
