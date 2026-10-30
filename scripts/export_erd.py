"""Generate an actual-model ER diagram source, including every SQL foreign key."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import models  # noqa: F401
from app.extensions import db

lines=['erDiagram']
for table in db.metadata.sorted_tables:
    lines.append(f'    {table.name} {{')
    for column in table.columns:
        kind=str(column.type).split('(')[0].replace(' ', '_')
        flag=' PK' if column.primary_key else (' FK' if column.foreign_keys else '')
        lines.append(f'        {kind} {column.name}{flag}')
    lines.append('    }')
    for fk in table.foreign_keys:
        parent=fk.column.table.name
        # Optionality at the parent end reflects whether the child FK may be null.
        parent_end='|o' if fk.parent.nullable else '||'
        child_end='o|' if fk.parent.unique else 'o{'
        lines.append(f'    {parent} {parent_end}--{child_end} {table.name} : "{fk.parent.name}"')
target=Path(__file__).resolve().parents[1]/'docs/diagrams/07-actual-model-erd.mmd'
target.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(target)
