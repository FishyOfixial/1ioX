# Security Guide

## Required production environment variables

- `ENV=production`
- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `PUBLIC_BASE_URL`
- `CRON_TOKEN`
- `ONE_NCE_BASE_URL`
- `ONE_NCE_AUTH_HEADER`
- `MERCADOPAGO_ACCESS_TOKEN`
- `MERCADOPAGO_WEBHOOK_TOKEN`

Optional but recommended:

- `CSRF_TRUSTED_ORIGINS`
- `MERCADOPAGO_WEBHOOK_URL`
- `ONE_NCE_AUTH_URL`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `LOGIN_RATE_LIMIT_FAILURES`
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS`
- `LOGIN_RATE_LIMIT_LOCKOUT_SECONDS`

## Secure deployment checklist

- Set `ALLOWED_HOSTS` explicitly for every public hostname.
- Set `PUBLIC_BASE_URL` to the canonical HTTPS origin.
- Terminate TLS correctly at the proxy and forward `X-Forwarded-Proto`.
- Keep `ENV=production` in every production process.
- Run `python manage.py check --deploy` before release.
- Verify Mercado Pago webhook token and 1NCE credentials after each deploy.
- Use a shared cache backend in production if the app runs on more than one instance so login rate limiting applies consistently.

## Secret rotation

- Rotate `SECRET_KEY` only with a coordinated session invalidation window.
- Rotate `CRON_TOKEN`, `MERCADOPAGO_WEBHOOK_TOKEN`, `MERCADOPAGO_ACCESS_TOKEN`, and `ONE_NCE_AUTH_HEADER` on a schedule and immediately after any suspected leak.
- Store production secrets only in the deployment platform secret manager or environment configuration.
- Never commit `.env` files with real secrets.

## Incident response

1. Revoke exposed tokens and rotate affected credentials.
2. Review `auditlogs_systemlog` entries for:
   - failed logins
   - login rate limit events
   - unauthorized user management attempts
   - unauthorized SIM access attempts
   - webhook rejections
3. Verify whether unauthorized state changes or assignments were applied before the fix.
4. Re-run targeted authorization tests before restoring normal access.
