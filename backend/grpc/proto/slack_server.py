import grpc
from concurrent import futures
import json
from datetime import timezone

from backend import crud
from backend.grpc.proto import slack_workspace_pb2, slack_workspace_pb2_grpc


class SlackWorkspaceService(slack_workspace_pb2_grpc.SlackWorkspaceServiceServicer):
    def CreateSubscriptionPlan(self, request, context):
        plan_name = (request.plan_name or "").strip()
        currency = (request.currency or "").strip().upper() or "GBP"
        cost_pennies = int(request.cost_pennies)
        max_employees = int(request.max_employees)

        # g
        if len(plan_name) < 2:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "plan_name must be at least 2 characters.")
        if cost_pennies < 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "cost_pennies must be >= 0.")
        if max_employees <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "max_employees must be > 0.")
        if len(currency) != 3:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "currency must be a 3-letter code like 'GBP'.")

        try:
            plan = crud.create_sub_plan(
                p_name=plan_name,
                cost_pennies=cost_pennies,
                max_employ=max_employees,
                currency=currency,
            )

            return slack_workspace_pb2.CreateSubscriptionPlanResponse(
                plan=slack_workspace_pb2.SubscriptionPlan(
                    plan_id=int(plan.plan_id),
                    plan_name=str(plan.plan_name),
                    plan_cost_pennies=int(plan.plan_cost_pennies),
                    currency=str(plan.currency),
                    max_employees=int(plan.max_employees),
                )
            )

        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except RuntimeError as e:
            msg = str(e)
            low = msg.lower()
            if "already exists" in low or "duplicate" in low or "unique" in low:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, msg)
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, msg)
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {e}")

    def CreateCompany(self, request, context):
        plan_id = int(request.plan_id)
        company_name = (request.company_name or "").strip()

        if plan_id <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "plan_id must be > 0.")
        if len(company_name) < 2:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "company_name must be at least 2 characters.")

        try:
            company = crud.create_company(
                plan_id=plan_id,
                company_name=company_name,
            )

            return slack_workspace_pb2.CreateCompanyResponse(
                company=slack_workspace_pb2.Company(
                    company_id=int(company.company_id),
                    plan_id=int(company.plan_id),
                    company_name=str(company.company_name),
                )
            )

        except ValueError as e:
            # e.g. plan not found
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except RuntimeError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {e}")

    def CreateSlackWorkspace(self, request, context):
        company_id = int(request.company_id)
        team_id = (request.team_id or "").strip()
        access_token = (request.access_token or "").strip()

        if company_id <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "company_id must be > 0.")
        if not team_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "team_id is required.")
        if not access_token:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "access_token is required.")

        try:
            ws = crud.create_workspace(
                company_id=company_id,
                team_id=team_id,
                access_token=access_token,
            )

            return slack_workspace_pb2.CreateSlackWorkspaceResponse(
                workspace=slack_workspace_pb2.SlackWorkspace(
                    id=int(ws.id),
                    company_id=int(ws.company_id),
                    team_id=str(ws.team_id),
                )
            )

        except ValueError as e:
            # e.g. company_id not found
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except RuntimeError as e:
            msg = str(e)
            low = msg.lower()
            if "duplicate" in low or "already exists" in low or "unique" in low:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, msg)
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, msg)
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {e}")
    
    def CreateSlackUser(self, request, context):
        team_id = (request.team_id or "").strip()
        slack_user_id = (request.slack_user_id or "").strip()
        name = (request.name or "").strip()
        surname = (request.surname or "").strip()
        status = (request.status or "").strip() or "active"

        if not team_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "team_id is required")
        if not slack_user_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "slack_user_id is required")
        if len(name) <= 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "name must be > 1 char")
        if len(surname) <= 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "surname must be > 1 char")

        try:
            user = crud.create_slack_user(
                team_id=team_id,
                slack_user_id=slack_user_id,
                name=name,
                surname=surname,
                status=status,
            )

            return slack_workspace_pb2.CreateSlackUserResponse(
                slack_user=slack_workspace_pb2.SlackUser(
                    id=int(user.id),
                    team_id=str(user.team_id),
                    slack_user_id=str(user.slack_user_id),
                    name=str(user.name),
                    surname=str(user.surname),
                    status=str(user.status),
                )
            )

        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except RuntimeError as e:
            msg = str(e)
            low = msg.lower()
            if "duplicate" in low or "already exists" in low or "unique" in low:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, msg)
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, msg)
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {e}")

    def CreateFlaggedIncident(self, request, context):
        company_id = int(request.company_id)
        team_id = (request.team_id or "").strip()
        slack_user_id = (request.slack_user_id or "").strip()
        message_ts = (request.message_ts or "").strip()
        channel_id = (request.channel_id or "").strip()
        class_reason = (request.class_reason or "").strip() or None
        raw_json = (request.raw_message_text_json or "").strip()

        if company_id <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "company_id must be > 0")
        if not team_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "team_id is required")
        if not slack_user_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "slack_user_id is required")
        if not message_ts:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "message_ts is required")
        if not channel_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "channel_id is required")
        if not raw_json:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "raw_message_text_json is required")

        try:
            raw_dict = json.loads(raw_json)
            if not isinstance(raw_dict, dict):
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "raw_message_text_json must decode to a JSON object")
        except json.JSONDecodeError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"raw_message_text_json is not valid JSON: {e}")

        try:
            inc = crud.create_flagged_incident(
                company_id=company_id,
                team_id=team_id,
                slack_user_id=slack_user_id,
                message_ts=message_ts,
                channel_id=channel_id,
                raw_message_text=raw_dict,
                class_reason=class_reason,
            )

            created_at = inc.created_at
            # convert to ISO string
            created_iso = created_at.astimezone(timezone.utc).isoformat() if created_at else ""

            return slack_workspace_pb2.CreateFlaggedIncidentResponse(
                incident=slack_workspace_pb2.FlaggedIncident(
                    incident_id=int(inc.incident_id),
                    company_id=int(inc.company_id),
                    team_id=str(inc.team_id),
                    slack_user_id=str(inc.slack_user_id),
                    message_ts=str(inc.message_ts),
                    channel_id=str(inc.channel_id),
                    raw_message_text_json=json.dumps(inc.raw_message_text),
                    class_reason=str(inc.class_reason) if inc.class_reason else "",
                    created_at=created_iso,
                )
            )

        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except RuntimeError as e:
            # FK failures / constraint failures
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {e}")

    
    def GetSlackWorkspaceByTeamId(self, request, context):
        """not tested yet"""
        team_id = (request.team_id or "").strip()
        if not team_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "team_id is required")

        # Query via SQLAlchemy directly (ILL MAKE A CRUD GET SOON)
        from backend import alchemy_oop as model
        from sqlalchemy import select

        session = crud.Session()
        try:
            ws = session.execute(
                select(model.Workspace).where(model.Workspace.team_id == team_id)
            ).scalar_one_or_none()

            if ws is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"workspace team_id={team_id} not found")

            return slack_workspace_pb2.GetSlackWorkspaceByTeamIdResponse(
                workspace=slack_workspace_pb2.SlackWorkspace(
                    id=int(ws.id),
                    company_id=int(ws.company_id),
                    team_id=str(ws.team_id),
                )
            )
        finally:
            session.close()

def serve(host: str = "0.0.0.0", port: int = 50051) -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    slack_workspace_pb2_grpc.add_SlackWorkspaceServiceServicer_to_server(
        SlackWorkspaceService(), server
    )
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"gRPC server listening on {host}:{port}")
    server.wait_for_termination()



if __name__ == "__main__":
    serve()