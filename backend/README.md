# Library backend

Modules: `auth`, `books`, `loans`, `readers`. Each module has repository/service dependencies. Issuing, returning and reader history endpoints are not implemented yet.

## Database

For an existing database, run `migrations/001_library.sql` once before starting the new backend, for example with `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/001_library.sql` (use a PostgreSQL URL, without the SQLAlchemy `+asyncpg` suffix). The migration adds unique numeric reader cards to existing readers and creates books, copies and loans. Back up production data before schema changes.

A fresh database is initialized by the existing `create_all` startup. Reader cards are generated during registration; only conflicts on `uq_users_reader_card` trigger regeneration (up to 20 attempts). Librarian responses omit the field.

## API

All routes below require a Bearer token; paths are relative to the API root.

- `GET /auth/me`: profile; `reader_card` is optional and included only for readers.
- `GET /books?search=Толстой война&available=true&skip=0&limit=20`: paginated catalog. Each word must match either title or author, ignoring case and word order. Exact title/author matches rank first, followed by stable title/ID ordering. This is token search, without typo correction or stemming. `available=false` includes books with no copies. Limit: 1–100.
- `GET /books/{uuid}`: title, author, publication year, publisher, current availability. Librarians additionally receive `active_loans`, including copy/reader/librarian IDs and dates; readers never receive loan information. A missing book returns 404.

Availability means at least one copy has no loan with `returned_at IS NULL`. Overdue loans still occupy a copy. A partial unique index prevents two active loans for the same copy. Dates use timezone-aware timestamps and a calendar due date. Book copies must be added through database tooling until management endpoints exist.

Run checks from `backend`: `.venv/bin/python -m unittest discover -s tests -v`.
