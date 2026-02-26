import grpc
from backend.grpc.proto import slack_workspace_pb2, slack_workspace_pb2_grpc


def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = slack_workspace_pb2_grpc.SlackWorkspaceServiceStub(channel)

    #create slack user
    #create slack user
    #user_resp = stub.CreateSlackUser(slack_workspace_pb2.CreateSlackUserRequest(
    #team_id= "T123",
    #slack_user_id="U123",
    #name="AAAA",
    #surname="BBBB",
    #status="active",
    #))
    #print("SlackUser:", user_resp.slack_user) 

    # Create incident
    incident_resp = stub.CreateFlaggedIncident(slack_workspace_pb2.CreateFlaggedIncidentRequest(
        company_id=112,
        team_id="T123",
        slack_user_id="U123",
        message_ts="1700000000.000100",
        channel_id="C123",
        raw_message_text_json='{"text":"hello world"}',
        class_reason="anxiety",
    ))
    print("Incident:", incident_resp.incident)


if __name__ == "__main__":
    main()



"""Partial response"""
"""


(.venv) k24022340@ubuntu-22-04-desktop-l97-u2659889:~/SentinelAI$ python3 -m backend.grpc.proto.slack_client2
Incident: incident_id: 56
company_id: 112
team_id: "T123"
slack_user_id: "U123"
message_ts: "1700000000.000100"
channel_id: "C123"
raw_message_text_json: "{\"text\": \"hello world\"}"
class_reason: "anxiety"
created_at: "2026-02-21T15:07:35.484871+00:00"

"""