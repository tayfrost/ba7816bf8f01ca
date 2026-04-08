import { apiFetch } from "./client";

export type UserResponse = {
  user_id: string;
  company_id: number;
  display_name: string | null;
  email: string;
  role: "admin" | "biller" | "viewer";
  status: string;
};

export async function getUsers(): Promise<UserResponse[]> {
  return apiFetch<UserResponse[]>("/users");
}

export async function updateUserRole(
  userId: string,
  newRole: "admin" | "biller" | "viewer"
) {
  return apiFetch(`/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: newRole }),
  });
}

export async function deactivateUser(userId: string) {
  return apiFetch(`/users/${userId}`, {
    method: "DELETE",
  });
}

export async function inviteUser(params: {
  email: string;
  name: string;
  surname: string;
  role: "admin" | "biller" | "viewer";
}): Promise<UserResponse> {
  const display_name = `${params.name} ${params.surname}`.trim();
  const query = new URLSearchParams({
    email: params.email,
    role: params.role,
    ...(display_name ? { display_name } : {}),
  });

  return apiFetch<UserResponse>(`/users/invite?${query.toString()}`, {
    method: "POST",
  });
}
