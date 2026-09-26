# EmailJS OTP Authentication Setup Guide

This document outlines the step-by-step procedure for configuring the EmailJS email delivery service with AirRoute Delhi.

---

## 1. Architectural Overview

AirRoute Delhi employs a **server-to-server** email dispatch architecture:

```text
User enters email in browser
             ↓
Browser sends request to FastAPI backend (`/auth/send-otp`)
             ↓
Backend validates email & generates cryptographically secure 6-digit OTP
             ↓
Backend hashes OTP with cryptographic salt & stores it in SQLite (5-minute expiry)
             ↓
Backend dispatches HTTPS request to EmailJS REST API (`/api/v1.0/email/send`)
             ↓
EmailJS delivers email to recipient inbox
             ↓
User enters 6-digit code in browser
             ↓
Backend verifies against salted hash, invalidates OTP (single-use), and authenticates user
```

### Security Guarantees
- **No Private Keys in Browser:** EmailJS credentials (`SERVICE_ID`, `TEMPLATE_ID`, `PUBLIC_KEY`, `PRIVATE_KEY`) reside exclusively in backend environment variables.
- **No OTP in Client State:** The plaintext OTP is never returned in any API response or stored in frontend JavaScript.
- **Single-Use Invalidation:** Upon successful verification or after 5 failed attempts, the OTP is deleted from the database.
- **Brute-Force & Rate-Limit Protection:** Enforces 60-second resend cooldown, max 5 attempts per code, and max 5 OTP requests per hour per email.

---

## 2. Obtaining Credentials from EmailJS Dashboard

1. **Sign in to EmailJS**: [https://dashboard.emailjs.com](https://dashboard.emailjs.com)
2. **Email Service ID (`EMAILJS_SERVICE_ID`)**:
   - Go to **Email Services** in the left sidebar.
   - Click **Add New Service** (e.g., Gmail, Outlook, or Custom SMTP).
   - Once connected, note the **Service ID** (e.g., `service_abcd123`).
3. **Email Template ID (`EMAILJS_TEMPLATE_ID`)**:
   - Go to **Email Templates** in the left sidebar.
   - Click **Create New Template**.
   - Note the **Template ID** located in the top bar or Settings tab (e.g., `template_xyz789`).
4. **Public Key (`EMAILJS_PUBLIC_KEY`)**:
   - Click your profile icon or go to **Account** -> **API Keys**.
   - Copy the **Public Key** (e.g., `abcdEFGH123456`).
5. **Private Key (`EMAILJS_PRIVATE_KEY`)** *(Optional but recommended)*:
   - In **Account** -> **API Keys**, locate the **Private Key**.
   - If enabled in your EmailJS security settings ("Require Private Key for REST API"), set this in your backend `.env`.

---

## 3. Configuring the EmailJS Template

In the EmailJS Template editor, ensure your template maps the following variables:

### Subject:
```text
Your AirRoute Delhi verification code: {{otp}}
```

### Content / Body:
```html
<p>Hello {{to_name}},</p>

<p>To authenticate your AirRoute Delhi account, please use the following One-Time Password (OTP):</p>

<h2 style="letter-spacing: 4px; font-family: monospace; color: #0284c7;">{{otp}}</h2>

<p>This OTP is valid for <strong>5 minutes</strong>.</p>
<p>Do not share this OTP with anyone.</p>

<p>If you did not request this code, you can safely ignore this email.</p>

<p>Thanks,<br>AirRoute Delhi Team</p>
```

### Supported Template Variables:
The backend supplies the following primary variables:
- `{{to_email}}`: Recipient email address
- `{{to_name}}`: Recipient display name
- `{{otp}}`: 6-digit numeric OTP code
- `{{message}}`: Pre-formatted message string
- Aliases: `{{OTP}}`, `{{passcode}}`, `{{token}}`, `{{code}}`, `{{company_name}}`, `{{time}}`

---

## 4. Environment Variables Configuration

### Local Development (`.env` in repository root or `backend/.env`)

```ini
# Operational Environment
ENVIRONMENT=development

# EmailJS Server-Side Configuration
EMAILJS_SERVICE_ID=service_your_service_id
EMAILJS_TEMPLATE_ID=template_your_template_id
EMAILJS_PUBLIC_KEY=your_emailjs_public_key
EMAILJS_PRIVATE_KEY=your_optional_private_key
```

### Production Deployment (Render)

Add the following environment variables in the Render Dashboard under **Environment**:

| Variable Key | Description |
| :--- | :--- |
| `ENVIRONMENT` | `production` |
| `EMAILJS_SERVICE_ID` | Your EmailJS Service ID |
| `EMAILJS_TEMPLATE_ID` | Your EmailJS Template ID |
| `EMAILJS_PUBLIC_KEY` | Your EmailJS Public Key |
| `EMAILJS_PRIVATE_KEY` | (Optional) Your EmailJS Private Key |

---

## 5. Development Mode Simulation

If `EMAILJS_SERVICE_ID` is left empty in `ENVIRONMENT=development` or `ENVIRONMENT=test`:
- The backend logs an informational message indicating delivery simulation.
- The plaintext OTP is **never** printed to logs or returned in the API.
- Test suites pass automatically without requiring network access.

---

## 6. What Must NEVER Be Committed to GitHub

- Never commit `.env` or files containing real `EMAILJS_PUBLIC_KEY`, `EMAILJS_PRIVATE_KEY`, or database credentials.
- Verify `.gitignore` maintains entries for:
  ```gitignore
  .env
  .env.*
  !*.example
  *.db
  backend/users.db
  ```
