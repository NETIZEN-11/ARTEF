# Legacy migrations (not applied)

These were the original migrations. They no longer matched the SQLAlchemy models
(native UUID/JSONB columns where the models use VARCHAR(36)/JSON, different
`attack_taxonomy` columns, and 14 tables missing entirely), so a database built with
them could not be used by the application. No database was ever created from them: the
app created its schema from the models at startup.

They were replaced by a single baseline migration in `../versions/` generated from the
models (October 2026). Kept here for reference only; Alembic does not read this folder.
