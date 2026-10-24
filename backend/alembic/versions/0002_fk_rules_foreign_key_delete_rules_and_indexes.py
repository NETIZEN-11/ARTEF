"""foreign key delete rules and missing indexes

Generated with `alembic revision --autogenerate`, then given explicit constraint names
(PostgreSQL's default <table>_<column>_fkey) so the downgrade can drop them.

- cost_entries.run_id / test_case_id: CASCADE, so the retention job can delete old runs.
- guardrail_findings.guardrail_id: CASCADE, plus an index.
- review_queue.regression_id and review_labels.reviewer_id: RESTRICT, so deleting a
  regression or a user cannot silently destroy review decisions.
- Indexes on the second column of the user_roles and role_permissions primary keys.

Revision ID: 0002_fk_rules
Revises: 0001_baseline
Create Date: 2026-10-22 11:15:42.240974

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0002_fk_rules'
down_revision: Union[str, None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, referenced table, new ondelete, old ondelete)
_FOREIGN_KEYS = [
    ('cost_entries', 'run_id', 'runs', 'CASCADE', None),
    ('cost_entries', 'test_case_id', 'test_cases', 'CASCADE', None),
    ('guardrail_findings', 'guardrail_id', 'guardrails', 'CASCADE', None),
    ('review_labels', 'reviewer_id', 'users', 'RESTRICT', 'CASCADE'),
    ('review_queue', 'regression_id', 'regressions', 'RESTRICT', 'CASCADE'),
]


def _replace_foreign_keys(new: bool) -> None:
    for table, column, referred, new_rule, old_rule in _FOREIGN_KEYS:
        name = f'{table}_{column}_fkey'
        op.drop_constraint(name, table, type_='foreignkey')
        op.create_foreign_key(
            name, table, referred, [column], ['id'], ondelete=new_rule if new else old_rule
        )


def upgrade() -> None:
    _replace_foreign_keys(new=True)
    op.create_index('ix_guardrail_findings_guardrail_id', 'guardrail_findings', ['guardrail_id'], unique=False)
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'], unique=False)
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_role_permissions_permission_id', table_name='role_permissions')
    op.drop_index('ix_guardrail_findings_guardrail_id', table_name='guardrail_findings')
    _replace_foreign_keys(new=False)
