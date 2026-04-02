# Manual Test instructions for PR 50

## Test 1: OIDC Disabled (backward compatibility)

This verifies the app works exactly as before when OIDC is not configured.

### Setup

1. Make sure your api/.env has no OIDC settings (they should be commented out or absent):
  DATABASE_URL=postgresql://freehold:freehold@localhost:5433/freehold
  SECRET_KEY=changeme
  STORAGE_PATH=./storage
  /# API_KEY=            ← leave commented out
  /# OIDC_ISSUER=        ← leave commented out
2. Make sure your web/.env.local has OIDC disabled:
  NEXT_PUBLIC_API_URL=`http://localhost:8000`
  NEXT_PUBLIC_API_KEY=
  NEXT_PUBLIC_OIDC_ENABLED=

### Start everything

1. Start Postgres (from the repo root): docker compose up -d
2. Start the backend (in a terminal):
  ```sql cd``` api
  ```sql source``` venv/bin/activate
  alembic upgrade head
  uvicorn main:app --reload
3. Start the frontend (in another terminal):
  ```sql cd``` web
  npm run dev

### Verify

1. Open `http://localhost:3000` in your browser
2. You should land on the workspaces page immediately — no login screen, no redirect
3. Create a workspace, a space, a collection, and a page — make sure you can edit and save the page
4. Check the sidebar — there should be no user info or sign-out button in the footer
5. Open `http://localhost:8000/api/auth/me` in a new tab — it should return something like ```json {"authenticated": false, ...}``` without erroring out

If all of that works, this test passes.

---

## Test 2: Full OIDC Login Flow (using Keycloak)

This is the most involved test. We'll spin up a local Keycloak instance as your identity provider.

### Part A: Set up Keycloak

1. Add Keycloak to your running Docker services:
    docker run -d --name keycloak \
    -p 8080:8080 \
    -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
    -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
    quay.io/keycloak/keycloak:latest start-dev
2. Wait about 30 seconds for it to start, then open `http://localhost:8080` in your browser
3. Click Administration Console and log in with `admin` / `admin`
4. Create a realm (a realm is like a tenant in Keycloak):
    - In the top-left dropdown (it says "Keycloak" or "master"), click it and then click Create realm
    - Set the Realm name to `freehold`
    - Click Create
5. Create a client (this represents your Freehold app):
    - In the left sidebar, click Clients → Create client
    - Client ID: `freehold-app`
    - Click Next
    - Turn ON Client authentication (this makes it a confidential client, which gives you a client secret)
    - Click Next
    - Set Valid redirect URIs to: `http://localhost:8000/api/auth/callback`
    - Set Web origins to: `http://localhost:3000`
    - Click Save
6. Get the client secret:
    - Stay on the client page, click the Credentials tab
    - Copy the Client secret value — you'll need it in the next step
7. Create a test user:
    - In the left sidebar, click Users → Create user
    - Set Username: `testuser`
    - Set Email: `test@example.com`
    - Set First name: `Test`, Last name: `User`
    - Turn ON Email verified
    - Click Create
    - Go to the Credentials tab on that user
    - Click Set password, enter `password`, turn OFF Temporary, click Save

### Part B: Configure Freehold

1. Update `api/.env`:
  DATABASE_URL=`postgresql://freehold:freehold@localhost:5433/freehold`
  SECRET_KEY=changeme
  STORAGE_PATH=./storage
  OIDC_ISSUER=`http://localhost:8080/realms/freehold`
  OIDC_CLIENT_ID=freehold-app
  OIDC_CLIENT_SECRET=<paste the secret from step 6>
  OIDC_REDIRECT_URI=`http://localhost:8000/api/auth/callback`
  FRONTEND_URL=`http://localhost:3000`
  COOKIE_DOMAIN=localhost
2. Update `web/.env.local`:
  NEXT_PUBLIC_API_URL=`http://localhost:8000`
  NEXT_PUBLIC_API_KEY=
  NEXT_PUBLIC_OIDC_ENABLED=true
3. Restart both the backend and frontend (Ctrl+C each and re-run the `uvicorn` and `npm run dev` commands)

### Part C: Walk through the flow

1. Open `http://localhost:3000` in your browser (use a fresh incognito window to avoid stale cookies)
2. You should be redirected to `/login` — you should see a login page with an SSO button
3. Click the SSO / Sign In button
4. You should be redirected to Keycloak's login page (`http://localhost:8080/...`)
5. Enter `testuser` / `password` and submit
6. Keycloak redirects you back to `http://localhost:8000/api/auth/callback`, which then redirects to the frontend
7. You should land on the workspaces page, now logged in
8. Check the sidebar footer — you should see "Test User" and/or `test@example.com`
9. Click Sign out in the sidebar
10. You should be redirected back to the `/login` page
11. Try navigating directly to `http://localhost:3000/workspaces` — you should be redirected back to `/login` (protected route)

If all of that works, this test passes.

## Cleanup

When you're done, stop Keycloak:
`docker stop keycloak && docker rm keycloak`

---

## Test 3: API Key Auth Still Works

This verifies that header-based API key auth works alongside OIDC.

1. Keep OIDC enabled from Test 2 (or re-enable it), and add an API key to api/.env: API_KEY=test-secret-key
2. (Keep all the OIDC settings from Test 2 as well)
3. Restart the backend (uvicorn main:app --reload)
4. Verify the API key works — run this from a terminal: `curl -H "X-API-Key: test-secret-key" http://localhost:8000/api/workspaces/`
5. You should get a JSON array of workspaces (or [] if none exist).
6. Verify a wrong API key is rejected: `curl -H "X-API-Key: wrong-key" http://localhost:8000/api/workspaces/`
7. You should get a 401 or 403 error.
8. Verify no auth is rejected (since both OIDC and API key are now configured): `curl http://localhost:8000/api/workspaces/`
9. This should also return an error (not the workspace list).
10. Test with the CLI (if you want to go further):
  cd api
 source venv/bin/activate

### First create a workspace via the API or browser, then:

API_KEY=test-secret-key freehold export --workspace <your-workspace-slug> --output /tmp/test-export.zip
11. This should succeed, proving CLI export works with API key auth even when OIDC is enabled.

If all of that works, this test passes.

---

## Summary of what each test proves

  ┌──────┬───────────────────────────────────────────────────────────┐
  │ Test │                          Proves                           │
  ├──────┼───────────────────────────────────────────────────────────┤
  │ 1    │ No regressions — the app works as before when OIDC is off │
  ├──────┼───────────────────────────────────────────────────────────┤
  │ 2    │ The full OIDC flow works end-to-end with a real IdP       │
  ├──────┼───────────────────────────────────────────────────────────┤
  │ 3    │ API key auth coexists with OIDC for CLI/script access     |
  ├──────┼───────────────────────────────────────────────────────────┤
  