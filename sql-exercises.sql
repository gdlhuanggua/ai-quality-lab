-- Run against a copy of data/assets.db using a SQLite client.
-- Inspect columns and constraints.
PRAGMA table_info(assets);
PRAGMA index_list(assets);

-- Filter and sort.
SELECT asset_code, name, owner, sensitivity
FROM assets
WHERE sensitivity = 'internal'
ORDER BY id DESC
LIMIT 10;

-- Group counts.
SELECT sensitivity, COUNT(*) AS asset_count
FROM assets
GROUP BY sensitivity;

-- No duplicate rows should exist because assets.asset_code is UNIQUE.
SELECT asset_code, COUNT(*) AS duplicate_count
FROM assets
GROUP BY asset_code
HAVING COUNT(*) > 1;

-- Study duplicate detection on a synthetic raw dataset instead.
WITH raw_assets(asset_code, name) AS (
    VALUES ('DUP-001', 'First'), ('DUP-001', 'Second'), ('DATA-001', 'Third')
)
SELECT asset_code, COUNT(*) AS duplicate_count
FROM raw_assets
GROUP BY asset_code
HAVING COUNT(*) > 1;
