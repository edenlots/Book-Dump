# Security Review

**Date:** 2026-10-11  
**Scope:** Static review of the Flask application code, templates, startup configuration, and database schema for risks relevant to public deployment.

This review identified two high-severity issues. It was not a live deployment or penetration test; production infrastructure, reverse-proxy configuration, and runtime behavior were not assessed.

## Findings

### HIGH — Development debugger enabled in application entry point

**Location:** [run.py](./run.py#L5)

The entry point starts Flask with `debug=True`, and the README directs operators to start the application with `python run.py`. Exposing this development server publicly can expose Werkzeug's interactive debugger and reloader, turning an application error into a potential remote code execution path.

**Recommended action:** Do not expose Flask's development server. Disable debug mode and serve the application through a production WSGI server with debug access disabled.

### HIGH — Administrative POST actions lack CSRF protection

**Locations:** [app/routes.py](./app/routes.py#L472), [app/routes.py](./app/routes.py#L502), [app/routes.py](./app/routes.py#L526), [app/routes.py](./app/routes.py#L562); [admin_users.html](./app/templates/admin_users.html#L41), [admin_books.html](./app/templates/admin_books.html#L84)

Admin-only POST endpoints rely on the session and role check but do not validate a CSRF token. Their corresponding forms submit without a token. If an administrator is logged in, a malicious site may be able to induce the browser to submit actions such as creating or deleting users, changing roles, or deleting books.

**Recommended action:** Add CSRF protection to every state-changing form and endpoint, and configure session cookies appropriately for the production deployment (including `Secure`, `HttpOnly`, and a suitable `SameSite` policy).
