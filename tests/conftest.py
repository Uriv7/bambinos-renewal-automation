"""Synthetic fixtures: a clean paid same-batch renewal that each test mutates in exactly one way."""
import copy
from pathlib import Path

import pandas as pd
import pytest

from src.config import FILES, SCHEMAS, EngineConfig
from src.data_loader import load_all
from src.reconciliation import reconcile


def base_world():
    inv = dict(id="1000", invoice_number="BMB-INV-T-1000", user_id="3000", student_id="2000", class_id="10", educator_id="50",
               parent_name="Pa***", mobile="+91-9000XXXX01", email="pa***@x.com", currency="INR", amount="10000.00",
               discount_amount="0.00", net_amount="10000.00", payment_type="Full", payment_mode="UPI", payment_gateway="Razorpay",
               gateway_order_id="o1", gateway_payment_id="pay_1", invoice_link="https://x/invoice/BMB-INV-T-1000", payment_status="Paid",
               is_renewal="Yes", paid_at="2026-11-01 10:00:00", created_at="2026-11-01 09:55:00", updated_at="2026-11-01 10:00:00", deleted_at=None)
    form = dict(id="1", educator_id="50", educator_name="Ms. T", user_id="3000", student_id="2000", student_name="St***", parent_mobile="+91-9000XXXX01",
                class_id="10", current_classbatch_id="700", invoice_id="1000", invoice_link="https://x/invoice/BMB-INV-T-1000", amount_paid="10000.00",
                sessions_purchased="24", continue_same_batch="Yes", preferred_days="Tue,Thu", preferred_time_slot="17:00:00", remarks="",
                approval_status="Pending", approved_by=None, approved_at=None, created_at="2026-11-01 10:30:00", updated_at="2026-11-01 10:30:00", deleted_at=None)
    ref = dict(student_id="2000", user_id="3000", student_name_masked="St***", parent_name_masked="Pa***", registered_mobile_masked="+91-9000XXXX01",
               registered_email_masked="pa***@x.com", current_classbatch_id="700", classbatch_name="B", class_id="10", class_name="C", category_id="1",
               category_name="Eng", educator_id="50", educator_name="Ms. T", standard_fee_24_sessions_inr="10000.00", batch_days="Tue,Thu",
               batch_start_time="17:00:00", active_students_count="3", max_batch_size="6", deleted_at=None)
    return {"invoices": [inv], "forms": [form], "bookings": [], "schedule": [], "reference": [ref]}


def write_world(world, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for key, fname in FILES.items():
        df = pd.DataFrame(world[key], columns=SCHEMAS[key])
        df.to_csv(folder / fname, index=False, na_rep="NULL")
    return folder


@pytest.fixture
def world():
    return copy.deepcopy(base_world())


@pytest.fixture
def evaluate(tmp_path):
    def _ev(w, cfg=None, name="in"):
        d = write_world(w, tmp_path / name)
        res = reconcile(load_all(d), cfg or EngineConfig())
        return {c["case_id"]: c for c in res["cases"]}, res
    return _ev
