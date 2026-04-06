export function logout() {
  try {
    localStorage.removeItem("sentinel_access_token");
  } catch {
    // ignore
  }

  window.location.href = "/login";
}