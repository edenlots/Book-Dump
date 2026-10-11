README

A web-based project of an online library system.
It uses Python Flask framework with direct connection to PostgreSQL database.

Tech stack in use
- basic HTML and CSS
- Javascript vanilla
- Python Flask Framework
- PostgreSQL

Python Libraries:
- werkzeug (for user account security)
- psycopg2

Features:
- Role-based access (user/admin account)
- Admin can manage users and books, including deleting book records and their uploaded files
- Admin profile with upload, download, user addition, and user deletion history
- upload/download book
- favorites (coming soon)
- update password
- reset password (coming soon)
- comments section (coming soon)

Database Schema uploaded!

For an existing database, apply `migrations/20261011_account_history.sql` before
creating or deleting accounts, or opening the admin profile history.
