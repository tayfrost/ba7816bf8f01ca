import json
from datetime import datetime, timezone, timedelta

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from protos.db.v1 import db_pb2, db_pb2_grpc


def to_timestamp(dt):
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def test_full_grpc_flow():
    channel = grpc.insecure_channel("localhost:50051")
    stub = db_pb2_grpc.DatabaseServiceStub(channel)

    company_id = 47
    user_id = "c0b1ee2c-7e78-4794-97a3-9b5be1be533d"
    email = f"testEmail+{int(datetime.now(timezone.utc).timestamp())}@example.com"

    mailbox_resp = stub.AddGoogleMailbox(
        db_pb2.AddGoogleMailboxRequest(
            company_id=company_id,
            user_id=user_id,
            email_address=email,
            token_json=json.dumps({"access_token": "abc"}),
            last_history_id="100",
            watch_expiration=to_timestamp(datetime.now(timezone.utc) + timedelta(days=1)),
        )
    )

    assert mailbox_resp.company_id == company_id
    assert mailbox_resp.user_id == user_id
    assert mailbox_resp.email_address == email

    incident_resp = stub.AddMessageIncident(
        db_pb2.AddMessageIncidentRequest(
            company_id=company_id,
            user_id=user_id,
            source="gmail",
            sent_at=to_timestamp(datetime.now(timezone.utc)),
            content_raw=json.dumps({"subject": "test", "body": "message"}),
            conversation_id="conv-1",
        )
    )

    assert incident_resp.company_id == company_id
    assert incident_resp.user_id == user_id
    assert incident_resp.source == "gmail"
    assert incident_resp.message_id

    scores_resp = stub.AddIncidentScores(
        db_pb2.AddIncidentScoresRequest(
            message_id=incident_resp.message_id,
            neutral_score=0.1,
            humor_sarcasm_score=0.2,
            stress_score=0.3,
            burnout_score=0.4,
            depression_score=0.5,
            harassment_score=0.6,
            suicidal_ideation_score=0.7,
            predicted_category="stress",
            predicted_severity=2,
        )
    )

    assert scores_resp.message_id == incident_resp.message_id
    assert scores_resp.predicted_category == "stress"
    assert scores_resp.predicted_severity == 2