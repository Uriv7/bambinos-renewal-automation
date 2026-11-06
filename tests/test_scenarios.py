import copy
import pytest
from src.config import EngineConfig, REASONS

C = "CASE-1000"


def dec(evaluate, w, cfg=None):
    cases, res = evaluate(w, cfg)
    return cases[C], cases, res


def test_01_valid_paid_same_batch_renewal_is_auto_approved(evaluate, world):
    c, _, _ = dec(evaluate, world)
    assert c["decision"] == "AUTO_APPROVE" and c["reason_codes"] == []


def test_02_unpaid_invoice(evaluate, world):
    world["invoices"][0].update(payment_status="Failed", paid_at=None, gateway_payment_id=None)
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION" and "PAYMENT_NOT_VERIFIED" in c["reason_codes"]


def test_03_missing_faculty_form(evaluate, world):
    world["forms"] = []
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION" and "MISSING_FACULTY_FORM" in c["reason_codes"]


def test_03b_missing_form_escalates_after_12h(evaluate, world):
    world["forms"] = []
    cfg = EngineConfig(as_of="2026-11-02 12:00:00")
    c, *_ = dec(evaluate, world, cfg)
    assert "ORPHANED_INVOICE" in c["reason_codes"] and c["teacher_followup_stage"] == "escalate"


def test_04_wrong_invoice_amount_on_form(evaluate, world):
    world["forms"][0]["amount_paid"] = "9000.00"
    c, *_ = dec(evaluate, world)
    assert "AMOUNT_MISMATCH" in c["reason_codes"] and c["decision"] == "EXCEPTION"


def test_04b_amount_matching_alone_does_not_approve_when_other_checks_fail(evaluate, world):
    world["forms"][0]["student_id"] = "9999"
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION"


def test_05_wrong_student_id_on_form(evaluate, world):
    world["forms"][0]["student_id"] = "2001"
    c, *_ = dec(evaluate, world)
    assert "STUDENT_ID_MISMATCH" in c["reason_codes"]


def test_05b_student_not_in_reference(evaluate, world):
    world["reference"] = []
    c, *_ = dec(evaluate, world)
    assert "INVALID_REFERENCE" in c["reason_codes"]


def test_06_wrong_teacher_id(evaluate, world):
    world["forms"][0]["educator_id"] = "51"
    c, *_ = dec(evaluate, world)
    assert "TEACHER_ID_MISMATCH" in c["reason_codes"]


def test_06b_wrong_course(evaluate, world):
    world["forms"][0]["class_id"] = "11"
    c, *_ = dec(evaluate, world)
    assert "COURSE_MISMATCH" in c["reason_codes"]


def test_07_duplicate_invoice(evaluate, world):
    dup = copy.deepcopy(world["invoices"][0]); dup.update(id="1001", invoice_number="BMB-INV-T-1001", gateway_payment_id="pay_2",
                                                         invoice_link="https://x/invoice/BMB-INV-T-1001", created_at="2026-11-01 11:00:00")
    world["invoices"].append(dup)
    cases, _ = evaluate(world)
    assert "DUPLICATE_INVOICE" in cases[C]["reason_codes"] and "DUPLICATE_INVOICE" in cases["CASE-1001"]["reason_codes"]


def test_08_identical_duplicate_form_is_collapsed_and_still_approved(evaluate, world):
    f2 = copy.deepcopy(world["forms"][0]); f2.update(id="2", created_at="2026-11-01 10:35:00", remarks="resubmitted")
    world["forms"].append(f2)
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "AUTO_APPROVE" and "DUPLICATE_FACULTY_FORM" in c["info_codes"] and c["faculty_form_id"] == "1"


def test_08b_non_identical_duplicate_form_blocks(evaluate, world):
    f2 = copy.deepcopy(world["forms"][0]); f2.update(id="2", preferred_days="Mon,Wed", created_at="2026-11-01 10:35:00")
    world["forms"].append(f2)
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION" and "DUPLICATE_FACULTY_FORM" in c["reason_codes"]


def _booking(status="Pending_Batch_Allocation", batch="700"):
    return dict(id="500", faculty_form_id="1", invoice_id="1000", user_id="3000", student_id="2000", class_id="10", educator_id="50", classbatch_id=batch,
                sessions_count="24", is_renewal="Yes", continue_same_batch="Yes", preferred_days="Tue,Thu", preferred_time="17:00:00", request_status=status,
                batch_allocated="No", allocated_by=None, allocated_at=None, created_at="2026-11-01 10:40:00", updated_at="2026-11-01 10:40:00", deleted_at=None)


def _sched(i, date="2026-11-03", start="17:00:00", end="17:50:00", **kw):
    r = dict(id=str(900 + i), bookingrequest_id="500", invoice_id="1000", classschedule_id=str(8000 + i), classbatch_id="700", class_id="10", user_id="3000",
             student_id="2000", educator_id="50", class_date=date, start_time=start, end_time=end, booking_type="Regular_Renewal", is_cancelled="No",
             attended_class="No", created_at="2026-11-01 10:41:00", updated_at="2026-11-01 10:41:00", deleted_at=None)
    r.update(kw); return r


def test_09_existing_booking_is_not_recreated(evaluate, world):
    world["bookings"] = [_booking()]
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "AWAITING_SCHEDULING" and "BOOKING_ALREADY_EXISTS" in c["info_codes"]
    assert c["decision"] != "AUTO_APPROVE"


def test_10_existing_schedule_is_not_recreated(evaluate, world):
    world["bookings"] = [_booking("Completed")]; world["schedule"] = [_sched(1)]
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "ALREADY_PROCESSED" and "SCHEDULE_ALREADY_EXISTS" in c["info_codes"]


def test_11_full_batch(evaluate, world):
    world["reference"][0]["active_students_count"] = "6"
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION" and "BATCH_FULL" in c["reason_codes"]


def test_11b_full_batch_same_batch_with_assumption_a1_enabled(evaluate, world):
    world["reference"][0]["active_students_count"] = "6"
    c, *_ = dec(evaluate, world, EngineConfig(same_batch_seat_already_held=True))
    assert c["decision"] == "AUTO_APPROVE"


def test_12_inactive_batch(evaluate, world):
    world["reference"][0]["deleted_at"] = "2026-10-01 00:00:00"
    c, *_ = dec(evaluate, world)
    assert "BATCH_INACTIVE" in c["reason_codes"] and c["decision"] == "EXCEPTION"


def test_13_missing_batch_reference_on_form(evaluate, world):
    world["forms"][0]["current_classbatch_id"] = None
    c, *_ = dec(evaluate, world)
    assert "MISSING_REQUIRED_FIELD" in c["reason_codes"] and c["decision"] == "EXCEPTION"


def test_13b_form_batch_differs_from_students_batch(evaluate, world):
    world["forms"][0]["current_classbatch_id"] = "799"
    c, *_ = dec(evaluate, world)
    assert "INVALID_REFERENCE" in c["reason_codes"]


def test_14_partial_payment(evaluate, world):
    world["invoices"][0].update(payment_status="Partially_Paid", net_amount="5000.00", payment_type="Installment_1_of_2")
    c, *_ = dec(evaluate, world)
    assert "PARTIAL_PAYMENT" in c["reason_codes"] and "AMOUNT_MISMATCH" in c["reason_codes"]


def test_15_parent_phone_mismatch(evaluate, world):
    world["invoices"][0]["mobile"] = "+91-9000XXXX77"
    c, *_ = dec(evaluate, world)
    assert c["reason_codes"] == ["PARENT_CONTACT_MISMATCH"]


def test_16_missing_required_field(evaluate, world):
    world["forms"][0]["preferred_days"] = None
    c, *_ = dec(evaluate, world)
    assert "MISSING_REQUIRED_FIELD" in c["reason_codes"]


def test_17_scheduling_conflict_student_overlap(evaluate, world):
    world["bookings"] = [_booking("Completed")]
    world["schedule"] = [_sched(1), _sched(2, start="17:30:00", end="18:20:00", classbatch_id="701")]
    c, *_ = dec(evaluate, world)
    assert "SCHEDULING_CONFLICT" in c["reason_codes"] and c["decision"] == "EXCEPTION"


def test_17b_preexisting_batch_slot_overlap_is_informational_only(evaluate, world):
    other = copy.deepcopy(world["reference"][0]); other.update(student_id="2500", user_id="3500", current_classbatch_id="701", batch_start_time="17:30:00")
    world["reference"].append(other)
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "AUTO_APPROVE" and "SCHEDULING_CONFLICT" in c["info_codes"]


def test_18_multiple_children_one_parent_are_kept_separate(evaluate, world):
    i2 = copy.deepcopy(world["invoices"][0]); i2.update(id="1001", invoice_number="BMB-INV-T-1001", student_id="2001", gateway_payment_id="pay_2", invoice_link="https://x/invoice/BMB-INV-T-1001")
    f2 = copy.deepcopy(world["forms"][0]); f2.update(id="2", invoice_id="1001", student_id="2001", invoice_link="https://x/invoice/BMB-INV-T-1001")
    r2 = copy.deepcopy(world["reference"][0]); r2.update(student_id="2001")
    world["invoices"].append(i2); world["forms"].append(f2); world["reference"].append(r2)
    cases, _ = evaluate(world)
    assert cases["CASE-1000"]["decision"] == cases["CASE-1001"]["decision"] == "AUTO_APPROVE"
    assert cases["CASE-1000"]["idempotency_key"] != cases["CASE-1001"]["idempotency_key"]


def test_19_batch_change_renewal_is_never_auto_approved(evaluate, world):
    world["forms"][0].update(continue_same_batch="No", preferred_days="Sat,Sun", preferred_time_slot="11:00:00")
    c, *_ = dec(evaluate, world)
    assert c["decision"] == "EXCEPTION" and "MANUAL_REVIEW_REQUIRED" in c["reason_codes"]


def test_20_discount_requires_approval(evaluate, world):
    world["invoices"][0].update(net_amount="8000.00", discount_amount="2000.00"); world["forms"][0]["amount_paid"] = "8000.00"
    c, *_ = dec(evaluate, world)
    assert "DISCOUNT_REQUIRES_APPROVAL" in c["reason_codes"]


def test_21_form_with_typo_invoice_is_not_applied_but_hinted(evaluate, world):
    world["invoices"][0].update(id="1023", invoice_number="BMB-INV-T-1023", invoice_link="https://x/invoice/BMB-INV-T-1023")
    world["forms"][0].update(invoice_id="1032", invoice_link="https://x/invoice/BMB-INV-T-1032")
    cases, _ = evaluate(world)
    c = cases["CASE-1023"]
    assert c["decision"] == "EXCEPTION" and "INVALID_REFERENCE" in c["reason_codes"] and c["match_method"] == "PROBABLE_STUDENT_AMOUNT"
    assert cases["CASE-FORM-1"]["reason_codes"] == ["INVOICE_NOT_FOUND"]


def test_22_names_alone_never_match(evaluate, world):
    world["forms"][0].update(invoice_id="7777", student_id="2999")  # same names, different ids
    cases, _ = evaluate(world)
    assert cases[C]["decision"] == "EXCEPTION" and cases[C]["match_method"] == "NONE"


def test_23_every_exception_has_required_fields(evaluate, world):
    world["forms"] = []
    _, res = evaluate(world)
    for e in res["exceptions"]:
        for k in ("record_id", "invoice_id", "primary_reason_code", "explanation", "severity", "assigned_owner", "recommended_action", "created_at"):
            assert e[k] not in (None, "")


def test_24_ownership_follows_policy(evaluate, world):
    world["invoices"][0].update(payment_status="Failed", paid_at=None, gateway_payment_id=None)
    _, res = evaluate(world)
    assert res["exceptions"][0]["assigned_owner"] == REASONS["PAYMENT_NOT_VERIFIED"].owner == "Finance Ops"
    assert res["exceptions"][0]["priority"] == "P1"
