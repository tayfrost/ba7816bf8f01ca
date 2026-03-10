// Switch between real backend and mock data
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

// Employees API
import { getEmployees as realGetEmployees } from "./employees";
import { getEmployees as mockGetEmployees } from "./mock/employees";

export const getEmployees = USE_MOCKS ? mockGetEmployees : realGetEmployees;

// Types
export type { UsageQuery, UsageResponse, Series, SeriesPoint } from "./usage";
export type { Provider, IntegrationStatus } from "./integrations";
export type { RegisterPayload, LoginPayload, AuthResponse, MeResponse } from "./auth";

// Real implementations
import { getUsage as realGetUsage } from "./usage";
import {
  getIntegrations as realGetIntegrations,
  startIntegration as realStartIntegration,
  disconnectIntegration as realDisconnectIntegration,
} from "./integrations";

// Mock implementations
import { getUsage as mockGetUsage } from "./mock/usage";
import {
  getIntegrations as mockGetIntegrations,
  startIntegration as mockStartIntegration,
  disconnectIntegration as mockDisconnectIntegration,
} from "./mock/integrations";

import {
  register as realRegister,
  login as realLogin,
  getMe as realGetMe,
} from "./auth";

// Public API (switchable)
export const getUsage = USE_MOCKS ? mockGetUsage : realGetUsage;

export const getIntegrations = USE_MOCKS ? mockGetIntegrations : realGetIntegrations;
export const startIntegration = USE_MOCKS ? mockStartIntegration : realStartIntegration;
export const disconnectIntegration = USE_MOCKS ? mockDisconnectIntegration : realDisconnectIntegration;

export { submitSignup } from "./signup";
export type { SignupPayload } from "./signup";

export const register = realRegister;
export const login = realLogin;
export const getMe = realGetMe;