export const MOCK_INCIDENTS = [
  {
    incident_id: "INC-8821",
    class_reason: "Credential Leak",
    slack_user_id: "U123456",
    channel_id: "C-security-logs",
    timestamp: new Date().toISOString(),
    raw_message_text: { 
      text: "Hey team, here is the prod AWS_SECRET_KEY: AKIAI... please use it for the migration." 
    }
  },
  {
    incident_id: "INC-9942",
    class_reason: "Suspicious Attachment",
    slack_user_id: "U789012",
    channel_id: "C-general",
    timestamp: new Date().toISOString(),
    raw_message_text: { 
      text: "Check out this updated payroll.zip file for the quarterly review." 
    }
  }
];