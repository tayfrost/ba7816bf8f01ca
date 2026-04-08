/**
 * Privacy Policy page — hosted at sentinelai.work/privacy
 *
 * Required by Google OAuth verification. Must be live and publicly accessible
 * before submitting the OAuth consent screen for review.
 *
 * Covers:
 *  - What data is collected
 *  - Why it is collected
 *  - How it is stored and protected
 *  - Google API Services User Data Policy compliance clause
 *  - Limited Use disclosure
 */

const LAST_UPDATED = "8 April 2026";
const CONTACT_EMAIL = "privacy@sentinelai.work";
const COMPANY_NAME = "SentinelAI";

export default function Privacy() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
        color: "#ffffff",
        fontFamily: "'Outfit', 'Inter', sans-serif",
      }}
    >
      {/* Simple header */}
      <header
        style={{
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          padding: "20px 0",
          marginBottom: "0",
        }}
      >
        <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", gap: 12 }}>
          <img src="/logo-icon.png" alt="SentinelAI" style={{ height: 32 }} />
          <span style={{ fontWeight: 900, fontSize: 16, letterSpacing: 2, textTransform: "uppercase" }}>
            SentinelAI
          </span>
        </div>
      </header>

      <main style={{ maxWidth: 760, margin: "0 auto", padding: "60px 24px 100px" }}>

        {/* Title */}
        <h1 style={{ fontSize: "2.4rem", fontWeight: 900, marginBottom: 8, letterSpacing: "-1px" }}>
          Privacy Policy
        </h1>
        <p style={{ opacity: 0.45, fontSize: 13, marginBottom: 48, fontWeight: 600, letterSpacing: 1 }}>
          LAST UPDATED: {LAST_UPDATED}
        </p>

        <Section title="1. Introduction">
          <p>
            {COMPANY_NAME} ("<strong>we</strong>", "<strong>our</strong>", or "<strong>us</strong>") operates the
            SentinelAI platform, which helps organisations detect early signs of workplace
            burnout, stress, and mental health distress through consent-based analysis of
            communication metadata. This Privacy Policy explains what data we collect, why we
            collect it, how we protect it, and your rights in relation to it.
          </p>
          <p>
            By using SentinelAI you agree to the collection and use of information in
            accordance with this policy.
          </p>
        </Section>

        <Section title="2. Data We Collect">
          <Subsection title="2.1 Gmail Data (via Google OAuth)">
            <p>
              When a user connects their Gmail account, we access the following data through
              the <strong>Gmail API</strong> using the scope{" "}
              <code style={codeStyle}>https://www.googleapis.com/auth/gmail.readonly</code>:
            </p>
            <ul style={listStyle}>
              <li>
                <strong>Email metadata</strong> — sender, recipient, subject line, timestamp,
                and thread/conversation identifiers.
              </li>
              <li>
                <strong>Message body text</strong> — extracted in real-time solely to run our
                machine-learning wellbeing classifier. The raw message body is{" "}
                <strong>never stored persistently</strong> in our database.
              </li>
              <li>
                <strong>Gmail profile</strong> — the authenticated user's email address, used
                as a unique identifier to associate the mailbox with the correct company account.
              </li>
              <li>
                <strong>OAuth credentials (refresh token)</strong> — stored encrypted in our
                database to maintain the Gmail watch subscription (Google Pub/Sub) and re-authenticate
                without requiring the user to repeat the OAuth flow.
              </li>
            </ul>
            <p>
              We do <strong>not</strong> access attachments, contacts, calendar data, or any
              Google product outside of Gmail.
            </p>
          </Subsection>

          <Subsection title="2.2 Slack Data">
            <p>
              When a Slack workspace is connected by a company admin, we collect:
            </p>
            <ul style={listStyle}>
              <li>Slack workspace ID and OAuth access token (for reading approved channels).</li>
              <li>
                Message text from monitored channels, processed in real-time by our classifier.
                Raw message text is <strong>not stored</strong>; only the resulting risk classification
                and anonymised metadata are retained.
              </li>
              <li>Slack user IDs and, where available, email addresses for identity linking.</li>
            </ul>
          </Subsection>

          <Subsection title="2.3 Account Data">
            <p>For company admin accounts we collect:</p>
            <ul style={listStyle}>
              <li>Name and work email address.</li>
              <li>Hashed password (bcrypt; plaintext is never stored).</li>
              <li>Company name, subscription plan, and billing information (processed by Stripe; we do not store card numbers).</li>
            </ul>
          </Subsection>

          <Subsection title="2.4 Automatically Collected Data">
            <ul style={listStyle}>
              <li>Server logs (IP address, user agent, timestamps) — retained for up to 30 days for security and debugging purposes.</li>
              <li>Session tokens stored in your browser's <code style={codeStyle}>localStorage</code>.</li>
            </ul>
          </Subsection>
        </Section>

        <Section title="3. Why We Collect This Data">
          <p>We collect and process the data described above for the following purposes:</p>
          <ul style={listStyle}>
            <li>
              <strong>Wellbeing monitoring</strong> — to detect statistical signals of burnout,
              stress, harassment, and mental health distress in workplace communication, and to
              surface anonymised alerts to authorised HR personnel.
            </li>
            <li>
              <strong>Service operation</strong> — to authenticate users, manage company accounts,
              process subscriptions, and deliver the platform.
            </li>
            <li>
              <strong>Security and fraud prevention</strong> — to detect and prevent abuse of
              the platform.
            </li>
            <li>
              <strong>Legal compliance</strong> — to comply with applicable laws and regulations.
            </li>
          </ul>
          <p>
            We do <strong>not</strong> use Gmail or Slack data for advertising, profiling outside
            the scope described above, or any purpose not listed in this policy.
          </p>
        </Section>

        <Section title="4. How We Store and Protect Your Data">
          <ul style={listStyle}>
            <li>
              All data is stored in a PostgreSQL database hosted on infrastructure secured with
              TLS in transit and AES-256 encryption at rest.
            </li>
            <li>
              OAuth tokens (Gmail refresh tokens, Slack access tokens) are stored encrypted in
              the database and are only decrypted at the time of use.
            </li>
            <li>
              Raw email and Slack message bodies are processed <strong>in memory only</strong>{" "}
              and are never written to disk or any persistent store.
            </li>
            <li>
              Access to production data is restricted to authorised personnel and is logged.
            </li>
            <li>
              We perform regular security reviews and apply patches promptly.
            </li>
          </ul>
        </Section>

        <Section title="5. Google API Services — Limited Use Disclosure">
          <p style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 12, padding: "16px 20px", lineHeight: 1.7 }}>
            SentinelAI's use of information received from Google APIs adheres to the{" "}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#e38d26", fontWeight: 700 }}
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements.
          </p>
          <p style={{ marginTop: 16 }}>
            Specifically, data obtained through the Gmail API is:
          </p>
          <ul style={listStyle}>
            <li>Used only to provide the wellbeing monitoring service described in this policy.</li>
            <li>Not transferred to third parties except as necessary to provide the service (e.g., our hosting provider).</li>
            <li>Not used for serving advertisements.</li>
            <li>Not used to train general-purpose AI/ML models unrelated to the service.</li>
            <li>Not sold or shared with data brokers.</li>
          </ul>
        </Section>

        <Section title="6. Data Sharing">
          <p>We do not sell your personal data. We share data only in the following circumstances:</p>
          <ul style={listStyle}>
            <li>
              <strong>Service providers</strong> — infrastructure hosting (servers, database),
              payment processing (Stripe), and email delivery. These providers are contractually
              bound to protect data and use it only for providing their services to us.
            </li>
            <li>
              <strong>Within your organisation</strong> — anonymised risk signals are shared with
              authorised HR administrators within your company only.
            </li>
            <li>
              <strong>Legal requirements</strong> — if required by law, court order, or to protect
              the safety of users or the public.
            </li>
          </ul>
        </Section>

        <Section title="7. Data Retention">
          <ul style={listStyle}>
            <li>Gmail and Slack OAuth tokens are retained until a user disconnects their account or the company account is deleted.</li>
            <li>Incident records (risk classifications and anonymised metadata) are retained for the duration of the company's subscription, then deleted within 90 days of cancellation.</li>
            <li>Server logs are retained for up to 30 days.</li>
            <li>Account data is retained until deletion is requested.</li>
          </ul>
        </Section>

        <Section title="8. Your Rights">
          <p>Depending on your jurisdiction, you may have the right to:</p>
          <ul style={listStyle}>
            <li>Access a copy of the personal data we hold about you.</li>
            <li>Request correction of inaccurate data.</li>
            <li>Request deletion of your data.</li>
            <li>Withdraw consent and disconnect your Gmail or Slack account at any time via your account settings.</li>
            <li>Object to or restrict processing in certain circumstances.</li>
          </ul>
          <p>
            To exercise any of these rights, contact us at{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} style={{ color: "#e38d26", fontWeight: 700 }}>
              {CONTACT_EMAIL}
            </a>.
          </p>
        </Section>

        <Section title="9. Cookies">
          <p>
            SentinelAI does not use tracking cookies. We use browser{" "}
            <code style={codeStyle}>localStorage</code> only to store your session token for
            authentication purposes. No third-party analytics or advertising cookies are used.
          </p>
        </Section>

        <Section title="10. Children's Privacy">
          <p>
            SentinelAI is intended for use by organisations and their adult employees. We do not
            knowingly collect data from individuals under the age of 16.
          </p>
        </Section>

        <Section title="11. Changes to This Policy">
          <p>
            We may update this Privacy Policy from time to time. We will notify company admins of
            material changes by email. Continued use of the service after changes constitutes
            acceptance of the updated policy.
          </p>
        </Section>

        <Section title="12. Contact">
          <p>
            For privacy-related questions or requests, contact us at:
          </p>
          <p style={{ marginTop: 8 }}>
            <strong>SentinelAI</strong><br />
            <a href={`mailto:${CONTACT_EMAIL}`} style={{ color: "#e38d26", fontWeight: 700 }}>
              {CONTACT_EMAIL}
            </a><br />
            <a href="https://sentinelai.work" style={{ color: "#e38d26", fontWeight: 700 }}>
              https://sentinelai.work
            </a>
          </p>
        </Section>

      </main>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 48 }}>
      <h2
        style={{
          fontSize: "1.15rem",
          fontWeight: 900,
          letterSpacing: "0.5px",
          textTransform: "uppercase",
          marginBottom: 16,
          paddingBottom: 10,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          color: "#e38d26",
        }}
      >
        {title}
      </h2>
      <div style={{ lineHeight: 1.75, opacity: 0.88, fontSize: 15 }}>{children}</div>
    </section>
  );
}

function Subsection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 900, letterSpacing: 0.5, marginBottom: 10, opacity: 0.7 }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

import React from "react";

const listStyle: React.CSSProperties = {
  paddingLeft: 20,
  marginTop: 8,
  marginBottom: 8,
  lineHeight: 1.9,
};

const codeStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.1)",
  padding: "1px 6px",
  borderRadius: 4,
  fontFamily: "monospace",
  fontSize: 13,
};
