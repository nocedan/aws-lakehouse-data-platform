from etl_job import (
    TABLES, TableConfig,
    iceberg_path, get_sql,
    DATABASE, LANDING_PREFIX,
)


# ── Config integrity ──────────────────────────────────────────────────────────

def test_six_tables_registered():
    assert len(TABLES) == 6


def test_all_tables_have_valid_compression():
    assert all(t.compression in ("snappy", "gzip") for t in TABLES)


def test_table_names_are_unique():
    names = [t.name for t in TABLES]
    assert len(names) == len(set(names))


# ── iceberg_path ──────────────────────────────────────────────────────────────

def test_iceberg_path():
    t = TableConfig("rental", compression="gzip")
    assert iceberg_path(t) == (
        f"s3://terraform-data-lake-bucket/{LANDING_PREFIX}/{DATABASE}/rental"
    )


# ── get_sql ───────────────────────────────────────────────────────────────────

def test_get_sql_default_is_select_star():
    t = TableConfig("inventory", compression="snappy")
    assert get_sql(t, "src_inventory") == "SELECT * FROM src_inventory"


def test_get_sql_custom_substitutes_alias():
    film = next(t for t in TABLES if t.name == "film")
    sql = get_sql(film, "my_alias")
    assert "FROM my_alias" in sql
    assert "film_id" in sql


def test_get_sql_custom_has_no_unresolved_placeholder():
    film = next(t for t in TABLES if t.name == "film")
    assert "{alias}" not in get_sql(film, "x")

