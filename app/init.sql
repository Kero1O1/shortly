CREATE TABLE IF NOT EXISTS urls (
    id SERIAL PRIMARY KEY,
    long_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Safe additive migration for existing installations. Existing id-based links remain valid.
ALTER TABLE urls ADD COLUMN IF NOT EXISTS alias VARCHAR(30);
CREATE UNIQUE INDEX IF NOT EXISTS urls_alias_unique ON urls(alias) WHERE alias IS NOT NULL;
