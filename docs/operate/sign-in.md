# Sign-in (Entra ID, OIDC)

Apps can accept users' sign-in tokens from Microsoft Entra ID or any OpenID Connect provider (Okta, Auth0, Keycloak, Google…), alongside API keys.

## 1. Accept access tokens (APIs and SPAs)

```yaml
auth:
  oidc:
    issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
    audience: [api://hr-bot]              # your app registration's App ID URI and/or client id
    roles_claim: roles                    # default; "groups" also works
    role_map: { "HR.Approvers": approver, "HR.Agents": refunds }
```

Callers send `Authorization: Bearer ACCESS_TOKEN`. The server checks the signature (keys are fetched and rotated automatically), issuer, audience and expiry. Provider roles or groups become app roles through `role_map`; handlers see them in `req.principal`.

**Entra ID setup:** register an app, *Expose an API* (App ID URI `api://hr-bot`), create *App roles* such as `HR.Approvers`, and assign users or groups to them.

## 2. Sign-in on the app's pages

The built-in pages (chat, approvals, extraction…) can sign people in themselves:

```yaml
auth:
  oidc:
    issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
    audience: [api://hr-bot]
    client_id: 11111111-2222-3333-4444-555555555555     # the app registration
    client_secret_env: HR_BOT_CLIENT_SECRET             # aiapp secret set HR_BOT_CLIENT_SECRET (confidential clients)
```

1. In the app registration, add a **Web** redirect URI: `https://YOUR-HOST/apps/APP/_auth/callback`.
2. Start the server with `--public-url https://YOUR-HOST` (or `AIAPP_PUBLIC_URL`).
3. Open `https://YOUR-HOST/apps/APP/`: people are sent to sign in and come back. The session lasts 8 hours in a sealed cookie for that app only.

Sign out at `/apps/APP/_auth/logout`; `/apps/APP/_auth/me` shows who is signed in. Requests made with the cookie must come from the app's own pages (cross-site requests are refused); scripts and other servers use tokens.

## 3. Opaque access tokens

Some providers issue tokens that aren't JWTs. Validate them with the provider's introspection endpoint (RFC 7662):

```yaml
auth:
  oidc:
    issuer: https://idp.example.com
    audience: [hr-bot]
    introspection:
      url: https://idp.example.com/oauth2/introspect
      client_id: hr-bot-resource
      client_secret_env: HR_BOT_INTROSPECTION_SECRET
```

Answers are cached for up to a minute, so a revoked token stops working within a minute.

## 4. Multi-tenant apps (SaaS)

For an Entra app used by several customer organisations:

```yaml
auth:
  oidc:
    issuer: https://login.microsoftonline.com/{tenantid}/v2.0
    audience: [api://hr-bot]
    client_id: 11111111-2222-3333-4444-555555555555
    tenants: [CUSTOMER_A_TENANT_ID, CUSTOMER_B_TENANT_ID]    # only these organisations
    tenant_isolation: true
```

With `tenant_isolation: true`, each tenant's `app.kv`, `app.memory` and `app.vectors` data is kept apart automatically, including in background jobs a tenant starts. The indexed `sources` stay shared. Handlers see the tenant in `req.principal.tenant`.

!!! note "Not isolated per tenant"
    Uploaded files, topics and SQL insights are shared by the whole app. Keep tenant data out of them, or include the tenant in your own keys.

## The console

The server's web console has its own sign-in; see [The console](console.md#hosted-console-with-sign-in).
