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
export { startPersonalGmail, startMemberGmail } from "./integrations";

export { submitSignup } from "./signup";
export type { SignupPayload } from "./signup";

export const register = realRegister;
export const login = realLogin;
export const getMe = realGetMe;

export type { Plan } from "./plans";
import { getPlans as realGetPlans } from "./plans";
export const getPlans = realGetPlans;

export type { CompanyResponse } from "./companies";

import {
  getMyCompany as realGetMyCompany,
  updateMyCompany as realUpdateMyCompany,
  deleteMyCompany as realDeleteMyCompany,
} from "./companies";

export const getMyCompany = realGetMyCompany;
export const updateMyCompany = realUpdateMyCompany;
export const deleteMyCompany = realDeleteMyCompany;

export type { SlackUserResponse } from "./slack";
import { getSlackUsers as realGetSlackUsers } from "./slack";
export const getSlackUsers = realGetSlackUsers;

export type { Incident, IncidentStats } from "./incidents";

import {
  getIncidents as realGetIncidents,
  getIncidentStats as realGetIncidentStats,
} from "./incidents";

export const getIncidents = realGetIncidents;
export const getIncidentStats = realGetIncidentStats;

export type { UserResponse } from "./users";

import {
  getUsers as realGetUsers,
  updateUserRole as realUpdateUserRole,
  deactivateUser as realDeactivateUser,
  inviteUser as realInviteUser,
} from "./users";

export const getUsers = realGetUsers;
export const updateUserRole = realUpdateUserRole;
export const deactivateUser = realDeactivateUser;
export const inviteUser = realInviteUser;