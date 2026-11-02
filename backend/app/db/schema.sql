-- Raahein heritage database schema (SQLite; treated as read-only at runtime).
--
-- Design notes
--   * Plain ANSI-style DDL so it can move to PostgreSQL / Alembic later.
--   * Every historical statement is a row in `claims`; its evidence lives in
--     `monument_sources`.  A non-legend claim needs >= 2 sources from DISTINCT
--     publishers (see v_claim_rule_violations and the relationship trigger).
--   * `is_legend` is explicit: folklore is never mixed with historical fact.
--   * Timestamps are UTC ISO-8601 text.

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    source_key  TEXT    NOT NULL UNIQUE,                 -- stable id used by seed data
    url         TEXT    NOT NULL UNIQUE CHECK (url LIKE 'https://%' OR url LIKE 'http://%'),
    title       TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    publisher   TEXT    NOT NULL CHECK (length(trim(publisher)) > 0),
    source_type TEXT    NOT NULL CHECK (source_type IN
                    ('intergovernmental', 'government', 'encyclopedia', 'news', 'academic', 'other')),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS monuments (
    id                    INTEGER PRIMARY KEY,
    slug                  TEXT    NOT NULL UNIQUE
                              CHECK (slug <> '' AND slug NOT GLOB '*[^a-z0-9-]*'),
    name                  TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    description           TEXT    NOT NULL DEFAULT '',   -- derived from sourced claims at seed time
    latitude              REAL    NOT NULL CHECK (latitude  BETWEEN  -90 AND  90),
    longitude             REAL    NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    coordinates_source_id INTEGER NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    era                   TEXT    NOT NULL CHECK (length(trim(era)) > 0),
    architectural_style   TEXT    NOT NULL CHECK (length(trim(architectural_style)) > 0),
    location              TEXT    NOT NULL CHECK (length(trim(location)) > 0),
    city                  TEXT    NOT NULL CHECK (length(trim(city)) > 0),
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS claims (
    id          INTEGER PRIMARY KEY,
    monument_id INTEGER NOT NULL REFERENCES monuments (id) ON DELETE CASCADE,
    claim_key   TEXT    NOT NULL CHECK (length(trim(claim_key)) > 0),
    claim_type  TEXT    NOT NULL CHECK (claim_type IN
                    ('built', 'style', 'recognition', 'event', 'relationship', 'tradition')),
    text        TEXT    NOT NULL CHECK (length(trim(text)) > 0),
    is_legend   INTEGER NOT NULL CHECK (is_legend IN (0, 1)),
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (monument_id, claim_key),
    UNIQUE (id, monument_id),                            -- target for the composite FK below
    CHECK ((is_legend = 1) = (claim_type = 'tradition')) -- legends <=> 'tradition' claims
);

-- Evidence: which source backs which claim, plus a short paraphrase of what it says.
CREATE TABLE IF NOT EXISTS monument_sources (
    claim_id    INTEGER NOT NULL,
    monument_id INTEGER NOT NULL,
    source_id   INTEGER NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    note        TEXT    NOT NULL CHECK (length(trim(note)) > 0),
    PRIMARY KEY (claim_id, source_id),
    FOREIGN KEY (claim_id, monument_id) REFERENCES claims (id, monument_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS monument_relationships (
    id               INTEGER PRIMARY KEY,
    from_monument_id INTEGER NOT NULL REFERENCES monuments (id) ON DELETE CASCADE,
    to_monument_id   INTEGER NOT NULL REFERENCES monuments (id) ON DELETE CASCADE,
    relation_type    TEXT    NOT NULL CHECK (relation_type IN
                         ('architectural_influence', 'architectural_precursor', 'same_patron', 'same_dynasty', 'successor_of',
                          'capital_relationship', 'burial_association', 'historical_event',
                          'co_located_world_heritage')),
    note             TEXT    NOT NULL CHECK (length(trim(note)) > 0),
    claim_id         INTEGER NOT NULL REFERENCES claims (id) ON DELETE CASCADE,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (from_monument_id, to_monument_id, relation_type),
    CHECK (from_monument_id <> to_monument_id)
);

CREATE TABLE IF NOT EXISTS stories (
    id            INTEGER PRIMARY KEY,
    monument_id   INTEGER NOT NULL REFERENCES monuments (id) ON DELETE RESTRICT,
    language      TEXT    NOT NULL DEFAULT 'en' CHECK (length(trim(language)) > 0),
    body          TEXT    NOT NULL CHECK (length(trim(body)) > 0),
    model_version TEXT    NOT NULL CHECK (length(trim(model_version)) > 0),
    generated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (monument_id, language, model_version)
);

-- Indexes (SQLite does not index foreign keys automatically).
CREATE INDEX IF NOT EXISTS ix_monuments_city          ON monuments (city);
CREATE INDEX IF NOT EXISTS ix_monuments_coord_source  ON monuments (coordinates_source_id);
CREATE INDEX IF NOT EXISTS ix_claims_monument         ON claims (monument_id);
CREATE INDEX IF NOT EXISTS ix_ms_source               ON monument_sources (source_id);
CREATE INDEX IF NOT EXISTS ix_ms_monument             ON monument_sources (monument_id);
CREATE INDEX IF NOT EXISTS ix_rel_from                ON monument_relationships (from_monument_id);
CREATE INDEX IF NOT EXISTS ix_rel_to                  ON monument_relationships (to_monument_id);
CREATE INDEX IF NOT EXISTS ix_rel_claim               ON monument_relationships (claim_id);
CREATE INDEX IF NOT EXISTS ix_stories_monument        ON stories (monument_id);

-- Two-source rule helpers -------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_claim_source_stats AS
SELECT c.id                       AS claim_id,
       c.monument_id              AS monument_id,
       c.claim_key                AS claim_key,
       c.is_legend                AS is_legend,
       COUNT(ms.source_id)        AS source_count,
       COUNT(DISTINCT s.publisher) AS publisher_count
FROM claims c
LEFT JOIN monument_sources ms ON ms.claim_id = c.id
LEFT JOIN sources s           ON s.id = ms.source_id
GROUP BY c.id;

-- Rows here break the rules: historical claims need >= 2 distinct publishers,
-- legends need >= 1 source that records them.
CREATE VIEW IF NOT EXISTS v_claim_rule_violations AS
SELECT * FROM v_claim_source_stats
WHERE (is_legend = 0 AND publisher_count < 2)
   OR (is_legend = 1 AND source_count < 1);

-- A relationship edge is a historical statement: it must hang off a verified,
-- non-legend claim about one of its two endpoints.
CREATE TRIGGER IF NOT EXISTS trg_relationship_verified_insert
BEFORE INSERT ON monument_relationships
WHEN (SELECT is_legend FROM claims WHERE id = NEW.claim_id) <> 0
  OR (SELECT monument_id FROM claims WHERE id = NEW.claim_id)
         NOT IN (NEW.from_monument_id, NEW.to_monument_id)
  OR (SELECT COUNT(DISTINCT s.publisher)
        FROM monument_sources ms JOIN sources s ON s.id = ms.source_id
       WHERE ms.claim_id = NEW.claim_id) < 2
BEGIN
    SELECT RAISE(ABORT, 'relationship needs a non-legend claim about one endpoint with >= 2 distinct publishers');
END;

CREATE TRIGGER IF NOT EXISTS trg_relationship_verified_update
BEFORE UPDATE OF claim_id, from_monument_id, to_monument_id ON monument_relationships
WHEN (SELECT is_legend FROM claims WHERE id = NEW.claim_id) <> 0
  OR (SELECT monument_id FROM claims WHERE id = NEW.claim_id)
         NOT IN (NEW.from_monument_id, NEW.to_monument_id)
  OR (SELECT COUNT(DISTINCT s.publisher)
        FROM monument_sources ms JOIN sources s ON s.id = ms.source_id
       WHERE ms.claim_id = NEW.claim_id) < 2
BEGIN
    SELECT RAISE(ABORT, 'relationship needs a non-legend claim about one endpoint with >= 2 distinct publishers');
END;
