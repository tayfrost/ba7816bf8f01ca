import json
import uuid
from datetime import timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from protos.db.v1 import db_pb2, db_pb2_grpc
from backend.New_database import new_crud_second_half as crud


def _timestamp_to_datetime(ts: Timestamp | None):
    if ts is None:
        return None
    dt = ts.ToDatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class DatabaseServiceServicer(db_pb2_grpc.DatabaseServiceServicer):
    def AddGoogleMailbox(self, request, context):
        try:
            user_id = uuid.UUID(request.user_id)
            token_json = json.loads(request.token_json)

            watch_expiration = None
            if request.HasField("watch_expiration"):
                watch_expiration = _timestamp_to_datetime(request.watch_expiration)

            mailbox = crud.create_google_mailbox(
                company_id=request.company_id,
                user_id=user_id,
                email_address=request.email_address,
                token_json=token_json,
                last_history_id=request.last_history_id or None,
                watch_expiration=watch_expiration,
            )

            return db_pb2.AddGoogleMailboxResponse(
                google_mailbox_id=mailbox.google_mailbox_id,
                company_id=mailbox.company_id,
                user_id=str(mailbox.user_id),
                email_address=mailbox.email_address,
                last_history_id=mailbox.last_history_id or "",
            )

        except json.JSONDecodeError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"token_json must be valid JSON: {e}")
            return db_pb2.AddGoogleMailboxResponse()

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return db_pb2.AddGoogleMailboxResponse()

        except RuntimeError as e:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(str(e))
            return db_pb2.AddGoogleMailboxResponse()

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return db_pb2.AddGoogleMailboxResponse()

    def AddMessageIncident(self, request, context):
        try:
            user_id = uuid.UUID(request.user_id)
            content_raw = json.loads(request.content_raw)
            sent_at = _timestamp_to_datetime(request.sent_at)

            incident = crud.create_message_incident(
                company_id=request.company_id,
                user_id=user_id,
                source=request.source,
                sent_at=sent_at,
                content_raw=content_raw,
                conversation_id=request.conversation_id or None,
            )

            return db_pb2.AddMessageIncidentResponse(
                message_id=str(incident.message_id),
                company_id=incident.company_id,
                user_id=str(incident.user_id),
                source=incident.source,
                conversation_id=incident.conversation_id or "",
            )

        except json.JSONDecodeError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"content_raw must be valid JSON: {e}")
            return db_pb2.AddMessageIncidentResponse()

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return db_pb2.AddMessageIncidentResponse()

        except RuntimeError as e:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(e))
            return db_pb2.AddMessageIncidentResponse()

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return db_pb2.AddMessageIncidentResponse()

    def AddIncidentScores(self, request, context):
        try:
            message_id = uuid.UUID(request.message_id)

            scores = crud.create_incident_scores(
                message_id=message_id,
                neutral_score=request.neutral_score,
                humor_sarcasm_score=request.humor_sarcasm_score,
                stress_score=request.stress_score,
                burnout_score=request.burnout_score,
                depression_score=request.depression_score,
                harassment_score=request.harassment_score,
                suicidal_ideation_score=request.suicidal_ideation_score,
                predicted_category=request.predicted_category or None,
                predicted_severity=request.predicted_severity,
            )

            return db_pb2.AddIncidentScoresResponse(
                id=scores.id,
                message_id=str(scores.message_id),
                predicted_category=scores.predicted_category or "",
                predicted_severity=scores.predicted_severity or 0,
            )

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return db_pb2.AddIncidentScoresResponse()

        except RuntimeError as e:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(str(e))
            return db_pb2.AddIncidentScoresResponse()

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return db_pb2.AddIncidentScoresResponse()