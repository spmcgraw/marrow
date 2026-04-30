---
title: OIDC authentication
description: Wire Marrow up to an OIDC provider for sign-in.
---

Marrow's backend acts as an OIDC Relying Party. Any compliant provider works — this page walks through Google and Keycloak, but the pattern is the same anywhere.

## How it works

1. User hits `GET /api/auth/login`. Backend redirects to the IdP.
2. IdP redirects back to `GET /api/auth/callback?code=…`.
3. Backend exchanges the code for tokens, upserts the user in the `users` table, claims any pending org memberships matching the email, auto-creates a personal org if the user has none, and sets the `marrow_session` cookie (httpOnly JWT, 24h).
4. Subsequent requests carry the cookie; routes use it for RBAC.

## Backend config

Add these to `api/.env` (or your prod env):

```env
OIDC_ISSUER=https://accounts.google.com
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://api.example.com/api/auth/callback
FRONTEND_URL=https://app.example.com
COOKIE_DOMAIN=.example.com
SECRET_KEY=<long random string>
CORS_ORIGINS=https://app.example.com
```

And on the frontend (web container env, or `web/.env.local` for dev):

```env
MARROW_API_URL=https://api.example.com
MARROW_OIDC_ENABLED=true
```

`MARROW_OIDC_ENABLED` enables the `/login` page and route-protection middleware. Without it the frontend assumes anonymous mode.

## Cookie domain

The session cookie is set on `COOKIE_DOMAIN`. For the cookie to be sent from the web app to the API:

- **Same domain** (e.g. both on `localhost`): `COOKIE_DOMAIN=localhost`.
- **Split subdomains** (e.g. `app.example.com` + `api.example.com`): `COOKIE_DOMAIN=.example.com` (note the leading dot).

If the cookie isn't being sent on API calls, this is almost always the misconfiguration.

## Provider setup

### Google

1. [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**.
2. Create an OAuth 2.0 Client ID for **Web application**.
3. Add Authorized redirect URIs: `https://api.example.com/api/auth/callback` (and `http://localhost:8000/api/auth/callback` for dev).
4. Copy the Client ID and Client Secret into `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET`.
5. Set `OIDC_ISSUER=https://accounts.google.com`.

### Keycloak

1. In your realm, **Clients** → **Create client**.
2. Client type: **OpenID Connect**. Client ID: `marrow`.
3. Enable **Client authentication**. Set **Valid redirect URIs** to your callback URL.
4. **Credentials** tab → copy the secret to `OIDC_CLIENT_SECRET`.
5. `OIDC_ISSUER=https://keycloak.example.com/realms/<realm>`.

### Other providers

Any OIDC-compliant provider works. The `OIDC_ISSUER` URL must serve a valid `/.well-known/openid-configuration`.

## Inviting members

Once OIDC is on, invite teammates by email from the org settings page (`/orgs/<id>/settings`). The invite creates a pending membership; when the user logs in via OIDC with that email, the membership is automatically claimed. See `routers/auth.py` for the claim flow.
