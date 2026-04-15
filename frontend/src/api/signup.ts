export type SignupPayload = {
  companyName: string;
  adminName: string;
  adminEmail: string;
};

// Placeholder for FastAPI integration
export async function submitSignup(data: SignupPayload) {
  console.log("Sending signup data to backend", data);
}
