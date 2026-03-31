# Keycloak Setup for Hangar MCP Servers

Keycloak provides OAuth2/OIDC authentication with native Dynamic Client
Registration (DCR), which Claude Code, claude.ai, and Codex require.

This guide sets up a single `hangar` realm shared by all tool servers
(OAS, OCP, etc.), with Google social login for self-registration.

## 1. Environment variables

Add these to `~/hangar/.env` on the VPS:

```bash
# Keycloak admin (only used on first start)
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<strong-random-password>

# Keycloak Postgres
KC_DB_PASSWORD=<strong-random-password>

# Public hostname (must match your Caddy/DNS config)
KC_HOSTNAME=auth.lakesideai.dev

# Shared OIDC issuer (all tools use same realm)
OIDC_ISSUER_URL=https://auth.lakesideai.dev/realms/hangar

# OAS MCP auth
OAS_OIDC_CLIENT_ID=oas-mcp
OAS_OIDC_CLIENT_SECRET=          # fill after step 4b below
OAS_RESOURCE_SERVER_URL=https://mcp.lakesideai.dev/oas

# OCP MCP auth (uncomment when ready)
# OCP_OIDC_CLIENT_ID=ocp-mcp
# OCP_OIDC_CLIENT_SECRET=
# OCP_RESOURCE_SERVER_URL=https://mcp.lakesideai.dev/ocp

# Viewer auth (OIDC session-based login for /viewer, /dashboard, etc.)
# HANGAR_VIEWER_OIDC_CLIENT_ID=hangar-viewer
# HANGAR_VIEWER_OIDC_CLIENT_SECRET=  # fill after step 4h below
# HANGAR_VIEWER_SESSION_SECRET=      # generate: python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 2. Start the stack

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml up -d
```

Wait for Keycloak to become healthy (~30-45s on first start):

```bash
docker compose -f docker-compose.prod.yml logs keycloak -f
```

Look for: `Keycloak 26.x.x on JVM ... started in XXs`

> **If migrating from the old `~/oas/` stack:** stop the old Keycloak first
> to avoid DNS conflicts on the `web` Docker network:
> ```bash
> cd ~/oas && docker compose -f docker-compose.prod.yml stop keycloak
> ```
> If both stacks' Keycloaks are on the `web` network simultaneously,
> Caddy's `reverse_proxy keycloak:8080` resolves ambiguously and the
> admin console will fail to load. You can verify only one is running:
> ```bash
> docker network inspect web --format '{{range .Containers}}{{.Name}} {{end}}' | grep keycloak
> ```

## 3. Access the admin console

The Caddyfile blocks `/admin/*` and `/realms/master/*` by default.
To access the admin console:

1. Comment out the `@admin` block in `~/caddy/Caddyfile` and ensure
   Caddy proxies to the correct container:
```
auth.lakesideai.dev {
    # @admin path /admin/* /realms/master/*
    # handle @admin {
    #     respond "Forbidden" 403
    # }

    reverse_proxy keycloak:8080
}
```

> If you had a previous Keycloak running from another compose stack,
> use the explicit container name instead of `keycloak`:
> ```
> reverse_proxy hangar-keycloak-1:8080
> ```

2. Reload Caddy:
```bash
cd ~/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

3. Open **https://auth.lakesideai.dev/admin/** in an incognito window
   and log in with admin credentials.

4. Verify HTTPS is working correctly — the issuer should show `https://`:
```bash
curl -s https://auth.lakesideai.dev/realms/master/.well-known/openid-configuration \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['issuer'])"
```
Should print: `https://auth.lakesideai.dev/realms/master`

If it shows `http://` instead, Keycloak isn't receiving forwarded headers.
Add explicit header forwarding in the Caddyfile:
```
reverse_proxy keycloak:8080 {
    header_up X-Forwarded-Proto {scheme}
}
```

**Remember to re-enable the `@admin` block and reload Caddy when done
with all setup steps.**

## 4. Configure the hangar realm

### 4a. Create realm

1. Click the realm dropdown (top-left corner, shows "Keycloak" or "master")
2. Click **Create realm**
3. Realm name: `hangar`
4. Click **Create**

You should now see "hangar" in the realm dropdown.

### 4b. Create OAS MCP client

Make sure you're in the **hangar** realm (check the dropdown top-left).

1. **Clients** (left sidebar) -> **Create client**
2. **Step 1 — General settings:**
   - Client type: **OpenID Connect** (default)
   - Client ID: `oas-mcp`
   - Click **Next**
3. **Step 2 — Capability config:**
   - Client authentication: **ON** (toggles it to a confidential client)
   - Authorization: OFF
   - Under "Authentication flow", check:
     - [x] Standard flow
     - [x] Service accounts roles
   - Click **Next**
4. **Step 3 — Login settings:**
   - Leave defaults for now (we'll configure redirect URIs next)
   - Click **Save**
5. Go to the **Credentials** tab -> copy the **Client secret**
6. Paste into `~/hangar/.env` as `OAS_OIDC_CLIENT_SECRET`

### 4c. Configure redirect URIs (on oas-mcp client)

Still in **Clients -> oas-mcp -> Settings** tab, scroll to "Access settings":

**Valid redirect URIs** — add each on its own line:
```
http://localhost:*
http://127.0.0.1:*
https://claude.ai/api/mcp/auth_callback
https://claude.com/api/mcp/auth_callback
```

**Valid post logout redirect URIs:** `+` (same as redirect URIs)

**Web origins:** `+`

Click **Save** at the bottom.

### 4d. Create mcp:tools scope

1. **Client scopes** (left sidebar) -> **Create client scope**
2. Fill in:
   - Name: `mcp:tools`
   - Description: `Access to MCP tool endpoints`
   - Type: **Default**
   - Protocol: **OpenID Connect**
3. Toggle **Include in token scope** to **ON**
   (critical — without this the scope won't appear in the access token's
   `scope` claim, and the MCP server will reject the token)
4. Click **Save**

Now assign it to the `oas-mcp` client:
1. Go to **Clients** (left sidebar) -> click **oas-mcp** -> **Client scopes** tab
2. Click **Add client scope**
3. Find `mcp:tools` in the list, check it
4. Click **Add** -> **Default**

### 4e. Remove restrictive DCR policies

Keycloak's default anonymous access policies block DCR requests from
Claude Code, claude.ai, and Codex. Two policies must be deleted:

1. **Clients** (left sidebar) -> click the **Client registration** tab
   (in the tab bar at the top of the clients page, next to "Clients list")
2. You should see **Anonymous access policies** with two entries:
   - **Trusted Hosts** — blocks DCR from non-whitelisted hosts
   - **Allowed Client Scopes** — blocks the custom `mcp:tools` scope
3. Click the **...** menu (or trash icon) on each and delete both

> Removing these policies allows any client to register via DCR. This is
> safe because the MCP server validates every token independently — DCR
> registration alone grants no access.

Verify DCR is enabled:

```bash
curl -s https://auth.lakesideai.dev/realms/hangar/.well-known/openid-configuration \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('registration_endpoint','NOT FOUND'))"
```

Should print: `https://auth.lakesideai.dev/realms/hangar/clients-registrations/openid-connect`

### 4f. Audience mapper

By default, Keycloak doesn't include the tool client ID in the token's
`aud` claim. Without this, JWT audience validation fails.

1. **Client scopes** (left sidebar) -> click **mcp:tools** -> **Mappers** tab
2. Click **Add mapper** -> **By configuration**
3. Select **Audience** from the list
4. Fill in:
   - Name: `oas-mcp-audience`
   - Included Client Audience: select **oas-mcp** from the dropdown
   - Add to ID token: OFF
   - Add to access token: **ON**
5. Click **Save**

> When adding more tools: create additional audience mappers in the same
> `mcp:tools` scope for each tool client (e.g., `ocp-mcp-audience` ->
> `ocp-mcp`).

### 4g. Ensure username in access tokens

DCR-registered clients (Claude Code, claude.ai, Codex) may not include
`preferred_username` in access tokens by default. The MCP server works
around this by calling the OIDC userinfo endpoint, but adding the mapper
avoids the extra HTTP call per request.

1. **Client scopes** (left sidebar) -> click **profile** -> **Mappers** tab
2. Click on the **username** mapper (it exists by default)
3. Verify **Add to access token** is **ON**
   (if it's OFF, toggle it ON and click **Save**)

### 4h. Create viewer client (optional)

Skip this if you don't need the provenance viewer/dashboard.

1. **Clients** (left sidebar) -> **Create client**
2. **Step 1:** Client ID: `hangar-viewer` -> **Next**
3. **Step 2:**
   - Client authentication: **ON**
   - Check only: [x] Standard flow (no service accounts needed)
   - Click **Next**
4. **Step 3:** Leave defaults -> **Save**
5. **Credentials** tab -> copy **Client secret** -> paste into `.env`
   as `HANGAR_VIEWER_OIDC_CLIENT_SECRET`

In the client's **Settings** tab, set:

- **Valid redirect URIs:** `https://mcp.lakesideai.dev/oas/viewer/callback`
- **Valid post logout redirect URIs:** `https://mcp.lakesideai.dev/oas/viewer`
- **Web origins:** `https://mcp.lakesideai.dev`

Click **Save**.

### 4i. Create admin role for the viewer

1. **Realm roles** (left sidebar) -> **Create role**
2. Role name: `oas-admin`
3. Click **Save**
4. Assign to admin users:
   - **Users** (left sidebar) -> click the user -> **Role mappings** tab
   - Click **Assign role**
   - Change the filter dropdown from **Filter by clients** to
     **Filter by realm roles** — `oas-admin` will now appear
   - Check it and click **Assign**

### 4j. Create user accounts

1. **Users** (left sidebar) -> **Add user**
2. Fill in: username, email, first name, last name
3. Click **Create**
4. Go to **Credentials** tab -> **Set password**
5. Enter password, toggle **Temporary** to OFF (so they don't have to
   reset on first login)
6. Click **Save** -> **Save password**

## 5. Configure Google social login (self-registration)

This lets new users sign up with their Google account without needing
an admin to create their account manually. Skip this section if you
only want manually-created accounts.

### 5a. Google Cloud Console setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
   -> **APIs & Services** -> **Credentials**
2. Click **Create Credentials** -> **OAuth client ID**
3. Application type: **Web application**
4. Name: `Hangar Keycloak`
5. **Authorized redirect URIs:** add
   `https://auth.lakesideai.dev/realms/hangar/broker/google/endpoint`
6. **Authorized JavaScript origins:** add
   `https://auth.lakesideai.dev`
7. Click **Create** and note the **Client ID** and **Client Secret**

### 5b. Keycloak identity provider setup

1. In the `hangar` realm, go to **Identity providers** (left sidebar)
2. Click **Add provider** -> **Google**
3. Fill in:
   - **Client ID**: from Google Cloud Console (step 5a)
   - **Client Secret**: from Google Cloud Console (step 5a)
   - **Default Scopes**: `openid email profile`
4. Expand **Advanced settings**:
   - **Trust email**: ON (Google emails are verified)
   - **First login flow**: `first broker login` (default)
5. Click **Save**

### 5c. Realm login settings

1. **Realm settings** (left sidebar) -> **Login** tab
2. Set:
   - **User registration**: ON (allows the Keycloak form as fallback)
   - **Login with email**: ON
   - **Duplicate emails**: OFF
   - **Verify email**: ON (recommended for non-Google registrations)
3. Click **Save**

### 5d. Verify social login

1. Open an incognito browser window
2. Navigate to `https://auth.lakesideai.dev/realms/hangar/account/`
3. You should see a **Sign in with Google** button on the login page
4. Click it, sign in with a Google account
5. Verify the user appears in **Users** in the Keycloak admin console

New users automatically get `default-roles-hangar` (basic access, NOT
admin). Admin viewer access must be granted manually (step 4i).

## 6. Adding a new tool (e.g., OCP)

When adding a new MCP tool server to the hangar:

### 6a. Create the OIDC client

1. **Clients -> Create client** in the `hangar` realm
2. Client ID: `ocp-mcp` (must match the tool's `OIDC_CLIENT_ID`)
3. Client authentication: **ON**
4. Authentication flow: Standard flow + Service accounts
5. Configure redirect URIs (same pattern as step 4c)
6. Copy client secret to `.env` as `OCP_OIDC_CLIENT_SECRET`

### 6b. Add audience mapper

1. **Client scopes** -> **mcp:tools** -> **Mappers** tab
2. **Add mapper** -> **By configuration** -> **Audience**
3. Name: `ocp-mcp-audience`
4. Included Client Audience: `ocp-mcp`
5. Add to access token: **ON**
6. Click **Save**

### 6c. Assign scope to client

1. **Clients** -> **ocp-mcp** -> **Client scopes** tab
2. **Add client scope** -> select `mcp:tools` -> **Add** -> **Default**

### 6d. Update deployment

1. Uncomment (or add) the service in `docker-compose.prod.yml`
2. Add `handle_path /ocp/*` route to the Caddyfile
3. Reload Caddy and start the new service

## 7. Re-lock the admin console

Once all setup is done, re-enable the admin block in `~/caddy/Caddyfile`:

```
auth.lakesideai.dev {
    @admin path /admin/* /realms/master/*
    handle @admin {
        respond "Forbidden" 403
    }

    reverse_proxy keycloak:8080
}
```

```bash
cd ~/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## 8. Restart and verify

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml restart oas-mcp
```

Check the logs:

```bash
docker compose -f docker-compose.prod.yml logs oas-mcp --tail 20
```

You should see:
```
OAS MCP -- HTTP transport  |  auth: OIDC (https://auth.lakesideai.dev/realms/hangar)
```

Verify:

```bash
# OIDC discovery
curl -s https://auth.lakesideai.dev/realms/hangar/.well-known/openid-configuration \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('issuer:', d['issuer']); print('dcr:', d.get('registration_endpoint','MISSING'))"

# Protected resource metadata (served by MCP server, through Caddy path prefix)
curl -s https://mcp.lakesideai.dev/oas/.well-known/oauth-protected-resource

# Unauthenticated request -> 401
curl -s -o /dev/null -w '%{http_code}' -X POST https://mcp.lakesideai.dev/oas/mcp
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Admin console stuck on "Loading the Administration Console" | Caddy hitting wrong Keycloak container, or old+new Keycloak both on `web` network | Stop old Keycloak: `cd ~/oas && docker compose stop keycloak`. Use explicit container name in Caddyfile if needed: `reverse_proxy hangar-keycloak-1:8080` |
| Admin console JS error: "Failed to fetch dynamically imported module" | Browser cache from old Keycloak version, or `@admin` block still active | Try incognito window. Verify `@admin` block is commented out and Caddy was reloaded |
| OIDC discovery shows `http://` issuer instead of `https://` | Keycloak not receiving forwarded headers from Caddy | Add `header_up X-Forwarded-Proto {scheme}` to the `reverse_proxy` block in Caddyfile |
| `Token rejected: missing required scope 'mcp:tools'` | Scope not in token | Check **Include in token scope** is ON in the `mcp:tools` client scope (step 4d) |
| `Policy 'Trusted Hosts' rejected request` | DCR blocked by host policy | Delete the Trusted Hosts policy (step 4e) |
| `Policy 'Allowed Client Scopes' rejected request` | DCR blocked by scope policy | Delete the Allowed Client Scopes policy (step 4e) |
| JWT audience validation fails | Missing audience mapper | Add audience mapper to `mcp:tools` scope (step 4f) |
| `password authentication failed` on Keycloak start | Stale Postgres volume with different password | `docker volume rm hangar_postgres_data` and restart (loses all realm data) |
| Viewer callback fails | Wrong redirect URI | Verify viewer client has `https://mcp.lakesideai.dev/oas/viewer/callback` in Valid redirect URIs |
| Artifacts stored under UUID instead of username | DCR token missing `preferred_username` | Verify username mapper in `profile` scope has **Add to access token: ON** (step 4g) |
| `OIDC_CLIENT_ID is not set` warning in logs | Missing env var | Each tool needs `OIDC_CLIENT_ID` set in its compose `environment:` block |
