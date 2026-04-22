import io
import textwrap

from src.pydal2sql_core.cli_support import render_schema_from_code


def _render_and_collect_class_map_keys(code_after: str, tables: list[str] | None) -> set[str]:
    captured: dict[str, set[str]] = {}

    def renderer(context):
        captured["new"] = set(getattr(context.db_new, "_class_map", {}).keys())
        return ""

    success = render_schema_from_code(
        code_after,
        output_file=io.StringIO(),
        renderer=renderer,
        db_type="sqlite",
        tables=tables,
        magic=True,
        function_name="define_td_tables",
        use_typedal=True,
    )

    assert success
    return captured["new"]


def test_render_schema_populates_class_map_when_tables_filter_is_used():
    code_after = textwrap.dedent(
        """
        class Person(TypedTable):
            name: str
        
        class Building(TypedTable):
            street: str

        def define_td_tables(db):
            db.define(Person)
            db.define(Building)
        """,
    )

    keys_without_filter = _render_and_collect_class_map_keys(code_after, tables=None)
    keys_with_filter = _render_and_collect_class_map_keys(code_after, tables=["person"])

    assert "person" in keys_without_filter
    assert "person" in keys_with_filter

    # assert "building" in keys_without_filter
    # assert "building" not in keys_with_filter
