"""Independent checks for presentation syntax and pure algorithm imports."""
import ast
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from scripts.export_schema import schema_sql

ROOT = Path(__file__).resolve().parents[2]


def test_layer_1_all_templates_compile_without_server():
    env = Environment(loader=FileSystemLoader(ROOT/'app/frontend/templates'))
    for path in (ROOT/'app/frontend/templates').rglob('*.html'):
        env.parse(path.read_text(encoding='utf-8'))


def test_layer_3_algorithms_do_not_import_web_or_database():
    forbidden = {'flask', 'flask_login', 'sqlalchemy', 'psycopg2'}
    for path in (ROOT/'app/algorithms').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                assert all(alias.name.split('.')[0] not in forbidden for alias in node.names), path.name
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or '').split('.')[0] not in forbidden, path.name


def test_layer_4_export_matches_committed_sql():
    assert (ROOT/'schema.sql').read_text(encoding='utf-8') == schema_sql()
