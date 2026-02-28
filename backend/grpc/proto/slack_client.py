import grpc
from backend.grpc.proto import slack_workspace_pb2, slack_workspace_pb2_grpc


def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = slack_workspace_pb2_grpc.SlackWorkspaceServiceStub(channel)

    # 1) Plan
    plan_resp = stub.CreateSubscriptionPlan(
        slack_workspace_pb2.CreateSubscriptionPlanRequest(
            plan_name="Plan1",
            cost_pennies=0,
            max_employees=5,
            currency="GBP",
        )
    )
    print("Plan:", plan_resp.plan)

    # 2) Company
    company_resp = stub.CreateCompany(
        slack_workspace_pb2.CreateCompanyRequest(
            plan_id=plan_resp.plan.plan_id,
            company_name="Derja Ltd",
        )
    )
    print("Company:", company_resp.company)

    # 3) Workspace
    ws_resp = stub.CreateSlackWorkspace(
        slack_workspace_pb2.CreateSlackWorkspaceRequest(
            company_id=company_resp.company.company_id,
            team_id="T123",
            access_token="xoxb-test",
        )
    )
    print("Workspace:", ws_resp.workspace)


if __name__ == "__main__":
    main()


"""
the response received by running this file was:
Plan: plan_id: 183
plan_name: "Starter"
currency: "GBP"
max_employees: 5

Company: company_id: 112
plan_id: 183
company_name: "Acme Ltd"

Workspace: id: 49
company_id: 112
team_id: "T123"

"""