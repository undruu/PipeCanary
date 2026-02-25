from app.monitoring.schema_engine import SchemaDiff, SchemaEngine


class TestSchemaDiff:
    def test_no_changes(self):
        columns = [
            {"name": "id", "type": "NUMBER", "nullable": False},
            {"name": "email", "type": "VARCHAR", "nullable": False},
        ]
        diff = SchemaEngine.diff_schemas(columns, columns)
        assert not diff.has_changes
        assert diff.added_columns == []
        assert diff.removed_columns == []
        assert diff.type_changes == []

    def test_added_column(self):
        old = [{"name": "id", "type": "NUMBER", "nullable": False}]
        new = [
            {"name": "id", "type": "NUMBER", "nullable": False},
            {"name": "email", "type": "VARCHAR", "nullable": False},
        ]
        diff = SchemaEngine.diff_schemas(old, new)
        assert diff.has_changes
        assert len(diff.added_columns) == 1
        assert diff.added_columns[0]["name"] == "email"

    def test_removed_column(self):
        old = [
            {"name": "id", "type": "NUMBER", "nullable": False},
            {"name": "email", "type": "VARCHAR", "nullable": False},
        ]
        new = [{"name": "id", "type": "NUMBER", "nullable": False}]
        diff = SchemaEngine.diff_schemas(old, new)
        assert diff.has_changes
        assert diff.removed_columns == ["email"]

    def test_type_change(self):
        old = [{"name": "id", "type": "NUMBER", "nullable": False}]
        new = [{"name": "id", "type": "VARCHAR", "nullable": False}]
        diff = SchemaEngine.diff_schemas(old, new)
        assert diff.has_changes
        assert len(diff.type_changes) == 1
        assert diff.type_changes[0]["column"] == "id"
        assert diff.type_changes[0]["old_type"] == "NUMBER"
        assert diff.type_changes[0]["new_type"] == "VARCHAR"

    def test_complex_drift(self, sample_schema_old, sample_schema_new):
        diff = SchemaEngine.diff_schemas(sample_schema_old, sample_schema_new)
        assert diff.has_changes
        # 'name' removed, 'full_name' and 'updated_at' added
        assert "name" in diff.removed_columns
        added_names = [c["name"] for c in diff.added_columns]
        assert "full_name" in added_names
        assert "updated_at" in added_names
        # created_at type changed
        type_change_cols = [c["column"] for c in diff.type_changes]
        assert "created_at" in type_change_cols

    def test_to_dict(self):
        diff = SchemaDiff(
            added_columns=[{"name": "new_col", "type": "VARCHAR", "nullable": True}],
            removed_columns=["old_col"],
            type_changes=[{"column": "id", "old_type": "NUMBER", "new_type": "VARCHAR"}],
        )
        d = diff.to_dict()
        assert "added_columns" in d
        assert "removed_columns" in d
        assert "type_changes" in d
