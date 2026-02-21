import grpc
from concurrent import futures

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