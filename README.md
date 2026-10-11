# Book Dump

A Flask-based online library where users can browse, search, read, and upload
books. Administrators have separate tools for managing users, book records, and
uploaded files.

## Current technology stack

- **Backend:** Python and Flask
- **Database:** PostgreSQL, accessed with direct SQL through psycopg2
- **Frontend:** HTML, CSS, and vanilla JavaScript
- **Templates:** Jinja, provided by Flask
- **File storage:** Uses local storage path (for development)

## Python libraries

- **Flask** — routes, request handling, sessions, flash messages, and templates
- **psycopg2** — PostgreSQL driver and database access
- **Werkzeug** — password hashing and safe uploaded-filename handling; used by
  Flask as well

No frontend framework or JavaScript package is currently used.

## Implemented features

- User registration, login, logout, and role-based user/admin access
- Separate administrator login
- User dashboard, profile, password change, and profile-picture upload
- PDF book upload, browsing, preview, and download
- Basic and advanced book search
- User upload and download activity history
- Admin dashboard with user and book summaries
- Admin user management: add users, change roles, and delete users
- Admin book management, including deleting the database record and managed
  upload file
- Admin profile with the administrator's upload/download history and user
  addition/deletion history

## Potential future features

- Favorites and personal reading lists
- Comments, ratings, and reviews
- Pagination and richer search filters for large libraries
- Password reset by email and email verification
- User-facing upload review or moderation workflow
- Audit history for role changes, book deletions, and other admin actions
- Bulk import/export and backup/restore tools
- Automated tests, CI checks, and a documented production deployment setup
- CSRF protection and configurable upload size/type limits


Start the application with:

```powershell
python run.py
```
