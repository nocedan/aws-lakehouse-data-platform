from etl_job import TABLES


# ── Config integrity ──────────────────────────────────────────────────────────

def test_six_tables_registered():
    assert len(TABLES) == 6


def test_all_tables_have_valid_compression():
    assert all(t.compression in ("snappy", "gzip") for t in TABLES)


def test_table_names_are_unique():
    names = [t.name for t in TABLES]
    assert len(names) == len(set(names))


def test_all_queries_substitute_alias():
    for t in TABLES:
        sql = t.sql.format(alias="src_x")
        assert "FROM src_x" in sql
        assert "{alias}" not in sql

