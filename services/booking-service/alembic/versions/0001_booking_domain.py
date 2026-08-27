"""Create slots, bookings, history, inbox and outbox.

Revision ID: 0001_booking
"""
from collections.abc import Sequence
from alembic import op

revision: str="0001_booking"
down_revision: str|None=None
branch_labels: str|Sequence[str]|None=None
depends_on: str|Sequence[str]|None=None

SLOT_STATES="'available','held','booked','blocked'"
BOOKING_STATES="'payment_pending','booked','confirmed','ready','in_progress','completed','feedback_pending','feedback_submitted','settled','cancelled','payment_failed','candidate_no_show','interviewer_no_show','technical_failure','refunded','rescheduled'"

def upgrade()->None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(f"CREATE TYPE slot_status AS ENUM ({SLOT_STATES})")
    op.execute(f"CREATE TYPE booking_status AS ENUM ({BOOKING_STATES})")
    op.execute("""CREATE TABLE slots (id uuid PRIMARY KEY, interviewer_id uuid NOT NULL, starts_at timestamptz NOT NULL, ends_at timestamptz NOT NULL, status slot_status NOT NULL DEFAULT 'available', held_by_candidate_id uuid, hold_token_hash varchar(64), hold_expires_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), CONSTRAINT ck_slots_time_range CHECK(starts_at<ends_at), CONSTRAINT uq_interviewer_slot UNIQUE(interviewer_id,starts_at,ends_at)); CREATE INDEX ix_slots_interviewer_id ON slots(interviewer_id); CREATE INDEX ix_slots_availability ON slots(status,starts_at)""")
    op.execute("""CREATE TABLE bookings (id uuid PRIMARY KEY, slot_id uuid NOT NULL REFERENCES slots(id), candidate_id uuid NOT NULL, interviewer_id uuid NOT NULL, starts_at timestamptz NOT NULL, ends_at timestamptz NOT NULL, time_range tstzrange NOT NULL, status booking_status NOT NULL, occupies_time boolean NOT NULL DEFAULT true, amount_paise integer NOT NULL DEFAULT 20000, currency varchar(3) NOT NULL DEFAULT 'INR', idempotency_key varchar(128) NOT NULL, payment_id uuid, rescheduled_from_id uuid, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), CONSTRAINT uq_booking_slot UNIQUE(slot_id), CONSTRAINT uq_booking_idempotency UNIQUE(candidate_id,idempotency_key), CONSTRAINT ck_booking_price CHECK(amount_paise=20000), CONSTRAINT ck_booking_currency CHECK(currency='INR'), CONSTRAINT ex_bookings_candidate_overlap EXCLUDE USING gist(candidate_id WITH =,time_range WITH &&) WHERE (occupies_time), CONSTRAINT ex_bookings_interviewer_overlap EXCLUDE USING gist(interviewer_id WITH =,time_range WITH &&) WHERE (occupies_time)); CREATE INDEX ix_bookings_candidate_id ON bookings(candidate_id); CREATE INDEX ix_bookings_interviewer_id ON bookings(interviewer_id); CREATE INDEX ix_bookings_slot_id ON bookings(slot_id)""")
    op.execute("""CREATE TABLE booking_status_history (id uuid PRIMARY KEY, booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE, from_status booking_status, to_status booking_status NOT NULL, reason varchar(500), changed_by uuid, occurred_at timestamptz NOT NULL DEFAULT now()); CREATE INDEX ix_booking_status_history_booking_id ON booking_status_history(booking_id)""")
    op.execute("CREATE TABLE processed_events(event_id uuid PRIMARY KEY,event_type varchar(128) NOT NULL,processed_at timestamptz NOT NULL DEFAULT now())")
    op.execute("""CREATE TABLE outbox_events(id uuid PRIMARY KEY,event_type varchar(128) NOT NULL,event_version integer NOT NULL,occurred_at timestamptz NOT NULL DEFAULT now(),correlation_id varchar(128) NOT NULL,payload jsonb NOT NULL,published_at timestamptz,publish_attempts integer NOT NULL DEFAULT 0,last_error text); CREATE INDEX ix_outbox_events_published_at ON outbox_events(published_at)""")

def downgrade()->None:
    for table in ("outbox_events","processed_events","booking_status_history","bookings","slots"): op.execute(f"DROP TABLE {table}")
    op.execute("DROP TYPE booking_status"); op.execute("DROP TYPE slot_status")
