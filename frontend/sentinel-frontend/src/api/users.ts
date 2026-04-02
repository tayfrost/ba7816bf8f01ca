import { apiFetch } from "./client";

export type UserResponse = {
  user_id: number;
  name: string;
  surname: string;
  email: string;
  company_id: number;
  role: "admin" | "biller" | "viewer";
  status: string;
};

export async function getUsers(): Promise<UserResponse[]> {
  return apiFetch<UserResponse[]>("/users");
}

export async function updateUserRole(
  userId: number,
  newRole: "admin" | "biller" | "viewer"
) {
  return apiFetch(`/users/${userId}?new_role=${newRole}`, {
    method: "PATCH",
  });
}

export async function deactivateUser(userId: number) {
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
  const query = new URLSearchParams({
    email: params.email,
    name: params.name,
    surname: params.surname,
    role: params.role,
  });

  return apiFetch<UserResponse>(`/users/invite?${query.toString()}`, {
    method: "POST",
  });
}