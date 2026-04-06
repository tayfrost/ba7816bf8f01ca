import { apiFetch } from "./client";

export type SlackUserResponse = {
  id: number;
  team_id: string;
  slack_user_id: string;
  name: string;
  surname: string;
  created_at: string;
  status: string;
};

export async function getSlackUsers(): Promise<SlackUserResponse[]> {
  return apiFetch<SlackUserResponse[]>("/integrations/slack/users");
}