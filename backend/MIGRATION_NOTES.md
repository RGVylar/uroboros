# Alembic Migration Notes

## Issue: SQLAlchemy ENUM Auto-Create in op.create_table

### Problem
When using `sa.Enum()` in Alembic's `op.create_table()`, SQLAlchemy automatically tries to CREATE the ENUM type even with `create_type=False`. This causes errors when:
- The ENUM type already exists in the database
- Multiple migrations try to create the same ENUM
- Running migrations multiple times

Error message:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) type "friendship_status" already exists
```

### Root Cause
SQLAlchemy's `op.create_table()` has event listeners that automatically handle ENUM creation. The `create_type=False` parameter on the Enum column doesn't prevent this behavior reliably.

### Solution: Use Raw SQL in Alembic Migrations

Instead of using SQLAlchemy's `op.create_table()` with `sa.Enum()`, write the CREATE TABLE as raw SQL:

```python
def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE my_enum AS ENUM ('value1', 'value2');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;

        CREATE TABLE IF NOT EXISTS my_table (
            id SERIAL PRIMARY KEY,
            status my_enum NOT NULL DEFAULT 'value1',
            ...
        );

        CREATE INDEX IF NOT EXISTS idx_name ON my_table(column);
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS my_table CASCADE;
        DROP TYPE IF EXISTS my_enum;
    """)
```

### Key Techniques

1. **DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN null; END $$;**
   - PostgreSQL's idempotent way to create ENUMs
   - Silently skips if the type already exists
   - Avoids failures on retry

2. **CREATE TABLE IF NOT EXISTS**
   - Makes the statement idempotent
   - Safe to run multiple times

3. **CREATE INDEX IF NOT EXISTS**
   - Prevents index creation errors on retry

### When to Use Raw SQL vs SQLAlchemy Operations

| Scenario | Approach |
|----------|----------|
| Simple column additions | `op.add_column()` |
| Simple column removals | `op.drop_column()` |
| Creating tables with ENUM types | Raw SQL `op.execute()` |
| Complex schema changes | Raw SQL `op.execute()` |
| Conditional operations | Raw SQL with `DO $$ BEGIN ... END $$` |

### References
- [Alembic Operations](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [PostgreSQL DO Blocks](https://www.postgresql.org/docs/current/sql-do.html)
