# Database Tables Overview


# How to look at the database.

<<<<<<< HEAD
To search for functions of the database, look at new_crud.py and new_crud_second_half.py.
new crud has utility functions, and functions for the tables:

Subscription_plan crud functions, 
Companies crud functions,
Subscriptons crud functions,
Users crud functions,
Slack Workspaces crud functions,
=======
To search for functions of the database, look at utils  and new_crud_second_half.py.
Utils has files each file is named after a table, thease will contain the crud functions needed. 
>>>>>>> 0ce01e0 (updated read me)

To search for thease functions look for large consective hashtags ######################    {Table name}   #########################


This schema supports a SaaS where **companies sign up**, you create **users (seats)** under each company, optionally connect **Slack** and **Gmail**, and store **flagged messages** with **scoring**.

Postgres extensions used:
- `citext` (case-insensitive text, mainly emails)
- `pgcrypto` (UUID generation via `gen_random_uuid()`)
- `vector` (installed; not used yet in the tables shown)

---

## `companies`

**Purpose:** Tenant table. One row per customer company.

**Key columns**
- `company_id` (PK, BIGSERIAL)
- `name` (TEXT, unique)
- `created_at` (TIMESTAMPTZ, default `now()`)
- `deleted_at` (TIMESTAMPTZ, nullable) — soft delete marker

**Constraints**
- `UNIQUE(name)` → company names are globally unique (even if soft-deleted)

**Notes**
- Soft delete = set `deleted_at`. The row remains, so the name stays reserved.

---

## `subscription_plans`

**Purpose:** Defines billing plans and seat limits.

**Key columns**
- `plan_id` (PK, BIGSERIAL)
- `plan_name` (TEXT, unique)
- `price_pennies` (BIGINT, >= 0)
- `currency` (CHAR(3), default `'GBP'`)
- `seat_limit` (INT, > 0)

**Constraints**
- `UNIQUE(plan_name)`
- `CHECK(price_pennies >= 0)`
- `CHECK(seat_limit > 0)`

---

## `subscriptions`

**Purpose:** A company’s subscription state (plan + billing period).

**Key columns**
- `subscription_id` (PK, BIGSERIAL)
- `company_id` (FK → `companies.company_id`)
- `plan_id` (FK → `subscription_plans.plan_id`)
- `status` (`trialing | active | past_due | canceled`)
- `current_period_start` / `current_period_end` (TIMESTAMPTZ)
- `created_at` (TIMESTAMPTZ, default `now()`)

**Constraints**
- `UNIQUE(company_id)` → **one subscription per company**
- `CHECK(status IN ('trialing','active','past_due','canceled'))`
- FKs are `ON DELETE RESTRICT` (can’t delete plan/company while referenced)

---

## `users`

**Purpose:** Company seats (admins/billers/viewers). This is your internal SaaS user identity (not Slack/Gmail identity). ANY USERS TRACKED WILL BE VIEWERS THOSE WHO HAVE ACCESS TO THE UI ARE THE ADMIN/BILLER 

**Key columns**
- `user_id` (PK, UUID)
- `company_id` (FK → `companies.company_id`)
- `display_name` (TEXT, nullable)
- `role` (`admin | biller | viewer`)
- `status` (`active | inactive`)
- `created_at` (TIMESTAMPTZ, default `now()`)
- `deleted_at` (TIMESTAMPTZ, nullable) — soft delete marker

**Constraints**
- `CHECK(role IN ('admin','biller','viewer'))`
- `CHECK(status IN ('active','inactive'))`
- `UNIQUE(company_id, user_id)` (supports composite FKs)
- Index: `idx_users_company(company_id)`

**Notes**
- Soft delete via `deleted_at` (like companies).

---

## `auth_users`

**Purpose:** Login accounts for the UI. Stores credentials and maps a login email to a company (and optionally to a `users.user_id` seat).

**Key columns**
- `auth_user_id` (PK, BIGSERIAL)
- `company_id` (FK → `companies.company_id`)
- `user_id` (FK → `users.user_id`, nullable)
- `email` (CITEXT, globally unique)
- `password_hash` (TEXT)
- `created_at` (TIMESTAMPTZ, default `now()`)

**Constraints**
- `UNIQUE(email)` → login emails are global (one email can’t belong to multiple companies)
- FKs are `ON DELETE RESTRICT`

**Notes**
- This is separate from Slack/Gmail emails. It’s purely for app login identity.

---

## `slack_workspaces`

**Purpose:** Connected Slack workspace installation for a company (OAuth token + lifecycle).

**Key columns**
- `slack_workspace_id` (PK, BIGSERIAL)
- `company_id` (FK → `companies.company_id`)
- `team_id` (TEXT) — Slack workspace/team id
- `access_token` (TEXT)
- `installed_at` (TIMESTAMPTZ, default `now()`)
- `revoked_at` (TIMESTAMPTZ, nullable)

**Constraints**
- `UNIQUE(team_id)` → a Slack workspace can only be connected once in the whole system
- `UNIQUE(company_id, team_id)` → enables composite FK usage
- Index: `idx_slack_workspaces_company(company_id)`
- FKs are `ON DELETE RESTRICT`

**Notes**
- “Active” = `revoked_at IS NULL`.

---

## `slack_accounts`

**Purpose:** Maps a Slack user identity to your SaaS `users` seat.

**Key columns**
- `company_id` (part of composite FKs)
- `team_id` (Slack workspace id)
- `slack_user_id` (Slack user id)
- `user_id` (UUID → `users.user_id`)
- `email` (CITEXT, nullable) — Slack-provided email metadata

**Constraints**
- **Primary key:** `(team_id, slack_user_id)` → unique Slack identity in a workspace
- Composite FK: `(company_id, team_id)` → `slack_workspaces(company_id, team_id)`
- Composite FK: `(company_id, user_id)` → `users(company_id, user_id)`
- Indexes: `idx_slack_accounts_user(user_id)`, `idx_slack_accounts_company(company_id)`
- FKs are `ON DELETE RESTRICT`

**Notes**
- `email` can match Gmail/login email but is not enforced unique.

---

## `google_mailboxes`

**Purpose:** Connected Gmail mailbox per monitored user (OAuth tokens + sync state).

**Key columns**
- `google_mailbox_id` (PK, BIGSERIAL)
- `company_id` (FK → `companies.company_id`)
- `user_id` (UUID) — seat that owns this mailbox connection
- `email_address` (CITEXT) — Gmail address of the connected mailbox
- `token_json` (JSONB) — OAuth tokens/scopes/etc
- `last_history_id` (TEXT, nullable) — Gmail incremental sync cursor (stored as text, incremented manually)
- `watch_expiration` (TIMESTAMPTZ, nullable) — Gmail watch expiry

**Constraints**
- Composite FK: `(company_id, user_id)` → `users(company_id, user_id)`
- `UNIQUE(company_id, email_address)` → one mailbox email per company
- Index: `idx_google_mailboxes_company(company_id)`
- FKs are `ON DELETE RESTRICT`

**Notes**
- This table represents **connected inboxes**, not a list of all contacts/senders.

---

## `message_incidents`

**Purpose:** Stores flagged messages (from Slack or Gmail) with raw provider payload.

**Key columns**
- `message_id` (PK, UUID)
- `company_id` (FK → `companies.company_id`)
- `user_id` (UUID) — the SaaS seat associated with the message (typically the monitored/sending user)
- `source` (`slack | gmail`)
- `sent_at` (TIMESTAMPTZ)
- `content_raw` (JSONB) — full raw message payload
- `conversation_id` (TEXT, nullable) — thread/channel/etc
- `created_at` (TIMESTAMPTZ, default `now()`)

**Constraints**
- `CHECK(source IN ('slack','gmail'))`
- Composite FK: `(company_id, user_id)` → `users(company_id, user_id)`
- FKs are `ON DELETE RESTRICT`

**Notes**
- This is the unified “flagged events” table across sources.

---

## `incident_scores`

**Purpose:** Stores ML scores/classifications for a `message_incidents` row (1:1).

**Key columns**
- `id` (PK, BIGSERIAL)
- `message_id` (FK → `message_incidents.message_id`, UNIQUE)
- Score columns:
  - `neutral_score`
  - `humor_sarcasm_score`
  - `stress_score`
  - `burnout_score`
  - `depression_score`
  - `harassment_score`
  - `suicidal_ideation_score`
- `predicted_category` (TEXT, nullable)
- `predicted_severity` (INT, nullable)
- `created_at` (TIMESTAMPTZ, default `now()`)

**Constraints**
- `UNIQUE(message_id)` → exactly one score row per incident
- FK is `ON DELETE CASCADE` → deleting the incident deletes its scores automatically

---

## Deletion behavior summary

Most foreign keys are **`ON DELETE RESTRICT`**, which means:
- You generally **do not hard-delete** companies/users/etc in normal operation.
- You use soft deletes (`deleted_at`) where provided.
- Hard delete requires manual cleanup (delete child rows first).

One exception:
- `incident_scores.message_id` is **`ON DELETE CASCADE`** so scores are removed automatically when an incident is deleted.


## USES IMPORTANT PLEASE READ
the crud.py files have a "session: optional[SASession] = None" parameter for most if not all functions. THIS IS FOR TESTING ONLY PLEASE DO NOT PASS IN OPTIONAL SESSIONS

IN ORDER TO CORRECTLY ON BOARD USERS YOU MUST
1) create a subscription plan
2) create a company
3) Have the company subscribe to a plan 
4) Add users of that compnay
5) connect the users mailboxes 

TO LOOK AT THE DB DESIGN PLS REFERE TO THIS LINK
https://docs.google.com/spreadsheets/d/15sU5jR5RN1UvCFWH77F3VLu21RcmtMl2y8YUn34Gc6I/edit?usp=sharing

---
