"""Schema-level guarantees: tables, constraints, foreign keys and the DB-side rules."""

import sqlite3

import pytest

from app.db.init_db import REQUIRED_TABLES, init_db, verify_integrity


def _src(conn, key, publisher, url=None):
    conn.execute(
        "INSERT INTO sources (source_key, url, title, publisher, source_type) VALUES (?,?,?,?,?)",
        (key, url or f"https://example.org/{key}", key, publisher, "other"),
    )
    return conn.execute("SELECT id FROM sources WHERE source_key=?", (key,)).fetchone()[0]


def _monument(conn, slug, src_id):
    conn.execute(
        "INSERT INTO monuments (slug, name, latitude, longitude, coordinates_source_id, era,"
        " architectural_style, location, city) VALUES (?,?,?,?,?,?,?,?,?)",
        (slug, slug.title(), 28.6, 77.2, src_id, "era", "style", "loc", "city"),
    )
    return conn.execute("SELECT id FROM monuments WHERE slug=?", (slug,)).fetchone()[0]


def _claim(conn, mid, key, legend=0):
    conn.execute(
        "INSERT INTO claims (monument_id, claim_key, claim_type, text, is_legend) VALUES (?,?,?,?,?)",
        (mid, key, "tradition" if legend else "built", "text", legend),
    )
    return conn.execute("SELECT id FROM claims WHERE monument_id=? AND claim_key=?", (mid, key)).fetchone()[0]


def _link(conn, cid, mid, sid):
    conn.execute("INSERT INTO monument_sources (claim_id, monument_id, source_id, note) VALUES (?,?,?,?)",
                 (cid, mid, sid, "note"))


@pytest.fixture()
def world(empty_db):
    c = empty_db
    s1, s2 = _src(c, "a", "Publisher A"), _src(c, "b", "Publisher B")
    m1, m2 = _monument(c, "one", s1), _monument(c, "two", s1)
    return c, s1, s2, m1, m2


def test_all_five_required_tables_exist(empty_db):
    names = {r[0] for r in empty_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(REQUIRED_TABLES) <= names


def test_init_db_is_repeatable(tmp_path):
    path = init_db(tmp_path / "x.db")
    init_db(path)  # must not raise


def test_foreign_keys_are_enforced(world):
    c, s1, _, m1, _ = world
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO claims (monument_id, claim_key, claim_type, text, is_legend)"
                  " VALUES (999,'k','built','t',0)")
    cid = _claim(c, m1, "k")
    with pytest.raises(sqlite3.IntegrityError):  # unknown source
        _link(c, cid, m1, 999)
    with pytest.raises(sqlite3.IntegrityError):  # claim/monument pair must match
        _link(c, cid, 999, s1)


def test_cascade_and_restrict(world):
    c, s1, _, m1, _ = world
    cid = _claim(c, m1, "k")
    _link(c, cid, m1, s1)
    c.execute("INSERT INTO stories (monument_id, body, model_version) VALUES (?,?,?)", (m1, "b", "v1"))
    with pytest.raises(sqlite3.IntegrityError):  # stories must never vanish silently
        c.execute("DELETE FROM monuments WHERE id=?", (m1,))
    with pytest.raises(sqlite3.IntegrityError):  # sources in use cannot be deleted
        c.execute("DELETE FROM sources WHERE id=?", (s1,))


@pytest.mark.parametrize("lat,lon", [(91, 77), (-91, 77), (28, 181), (28, -181)])
def test_coordinate_range_checks(world, lat, lon):
    c, s1, *_ = world
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO monuments (slug,name,latitude,longitude,coordinates_source_id,era,"
                  "architectural_style,location,city) VALUES ('bad','Bad',?,?,?,'e','s','l','c')",
                  (lat, lon, s1))


def test_slug_format_and_uniqueness(world):
    c, s1, *_ = world
    with pytest.raises(sqlite3.IntegrityError):
        _monument(c, "Bad Slug", s1)
    with pytest.raises(sqlite3.IntegrityError):
        _monument(c, "one", s1)


def test_is_legend_must_be_explicit_boolean_and_match_type(world):
    c, _, _, m1, _ = world
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO claims (monument_id,claim_key,claim_type,text,is_legend)"
                  " VALUES (?,'k','built','t',2)", (m1,))
    with pytest.raises(sqlite3.IntegrityError):  # a 'tradition' claim cannot pose as fact
        c.execute("INSERT INTO claims (monument_id,claim_key,claim_type,text,is_legend)"
                  " VALUES (?,'k','tradition','t',0)", (m1,))
    with pytest.raises(sqlite3.IntegrityError):  # and fact cannot be flagged legend
        c.execute("INSERT INTO claims (monument_id,claim_key,claim_type,text,is_legend)"
                  " VALUES (?,'k2','built','t',1)", (m1,))


def test_two_source_rule_view_flags_under_sourced_claims(world):
    c, s1, s2, m1, _ = world
    thin = _claim(c, m1, "thin")
    _link(c, thin, m1, s1)
    assert any("m1" not in p and "thin" in p for p in verify_integrity(c))
    _link(c, thin, m1, s2)  # second, different publisher
    assert verify_integrity(c) == []


def test_same_publisher_twice_does_not_satisfy_rule(world):
    c, s1, _, m1, _ = world
    s1b = _src(c, "a2", "Publisher A")
    cid = _claim(c, m1, "dup-pub")
    _link(c, cid, m1, s1)
    _link(c, cid, m1, s1b)
    assert len(verify_integrity(c)) == 1


def test_relationship_requires_verified_nonlegend_claim(world):
    c, s1, s2, m1, m2 = world
    good = _claim(c, m1, "good")
    _link(c, good, m1, s1)
    insert = ("INSERT INTO monument_relationships (from_monument_id,to_monument_id,relation_type,note,claim_id)"
              " VALUES (?,?, 'same_dynasty','n',?)")
    with pytest.raises(sqlite3.IntegrityError, match="distinct publishers"):  # only one publisher
        c.execute(insert, (m1, m2, good))
    _link(c, good, m1, s2)
    c.execute(insert, (m1, m2, good))  # now allowed

    legend = _claim(c, m1, "legend", legend=1)
    _link(c, legend, m1, s1)
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(insert.replace("'same_dynasty'", "'successor_of'"), (m1, m2, legend))


def test_relationship_claim_must_concern_an_endpoint(world):
    c, s1, s2, m1, m2 = world
    m3 = _monument(c, "three", s1)
    cid = _claim(c, m3, "elsewhere")
    _link(c, cid, m3, s1)
    _link(c, cid, m3, s2)
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO monument_relationships (from_monument_id,to_monument_id,relation_type,note,claim_id)"
                  " VALUES (?,?, 'same_dynasty','n',?)", (m1, m2, cid))


def test_relationship_constraints(world):
    c, s1, s2, m1, m2 = world
    cid = _claim(c, m1, "k")
    _link(c, cid, m1, s1)
    _link(c, cid, m1, s2)
    with pytest.raises(sqlite3.IntegrityError):  # self loop
        c.execute("INSERT INTO monument_relationships (from_monument_id,to_monument_id,relation_type,note,claim_id)"
                  " VALUES (?,?, 'same_dynasty','n',?)", (m1, m1, cid))
    with pytest.raises(sqlite3.IntegrityError):  # unknown relation type
        c.execute("INSERT INTO monument_relationships (from_monument_id,to_monument_id,relation_type,note,claim_id)"
                  " VALUES (?,?, 'friends','n',?)", (m1, m2, cid))
