-- UK Inflation Data Tables
-- Designed for efficient CPI/CPIH/RPI rate calculations and contribution analysis
-- All tables prefixed with 'uk_inflation_' for easy identification

-- Drop tables if they exist (in dependency order)
DROP TABLE IF EXISTS uk_inflation_price_data CASCADE;
DROP TABLE IF EXISTS uk_inflation_coicop_hierarchy CASCADE;

-- =============================================================================
-- COICOP Hierarchy Reference Table
-- =============================================================================
-- Stores the hierarchical structure of COICOP categories
-- Enables efficient parent-child queries and contribution calculations
CREATE TABLE uk_inflation_coicop_hierarchy (
    coicop_id VARCHAR(15) PRIMARY KEY,  -- e.g., '00', '01.1', '01.1.1.1', '12.7.0.4'
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 4),
    parent_id VARCHAR(15),              -- Reference to parent COICOP
    description TEXT NOT NULL,          -- e.g., 'BREAD & CEREALS'
    sort_order BIGINT,                  -- For proper hierarchical ordering
    
    -- Constraints
    FOREIGN KEY (parent_id) REFERENCES uk_inflation_coicop_hierarchy(coicop_id),
    
    -- Level 0 (root) and Level 1 items should have no parent, others should have a parent
    CONSTRAINT check_level_parent_rules CHECK (
        (level IN (0, 1) AND parent_id IS NULL) OR (level > 1 AND parent_id IS NOT NULL)
    )
);

-- =============================================================================
-- Price Data Table
-- =============================================================================
-- Stores minimal data: index values and weights for calculation
-- Optimized for fast retrieval of current + historical data for rate calculations
CREATE TABLE uk_inflation_price_data (
    date DATE NOT NULL,                 -- First day of month (e.g., '2024-12-01')
    coicop_id VARCHAR(15) NOT NULL,     -- Reference to COICOP category
    series_type VARCHAR(5) NOT NULL,    -- 'CPI', 'CPIH', 'RPI'
    index_value DECIMAL(12,4),          -- Price index value (e.g., 123.4567)
    weight_value DECIMAL(10,4),         -- Weight for contribution calculations
    
    -- Data quality metadata
    data_quality VARCHAR(20) DEFAULT 'ACTUAL',  -- 'ACTUAL', 'PROVISIONAL', 'ESTIMATED'
    source_column INTEGER,              -- Original ONS column number for traceability
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key ensures no duplicates
    PRIMARY KEY (date, coicop_id, series_type),
    
    -- Foreign key to hierarchy
    FOREIGN KEY (coicop_id) REFERENCES uk_inflation_coicop_hierarchy(coicop_id),
    
    -- Constraints
    CHECK (series_type IN ('CPI', 'CPIH', 'RPI')),
    CHECK (index_value IS NULL OR index_value >= 0),
    CHECK (weight_value IS NULL OR weight_value >= 0)
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Core hierarchy indexes
CREATE INDEX idx_uk_inflation_hierarchy_level 
    ON uk_inflation_coicop_hierarchy(level);
CREATE INDEX idx_uk_inflation_hierarchy_parent 
    ON uk_inflation_coicop_hierarchy(parent_id);
CREATE INDEX idx_uk_inflation_hierarchy_sort 
    ON uk_inflation_coicop_hierarchy(sort_order);

-- Critical indexes for YoY rate calculations
-- This index optimizes the "current + 12 months ago" lookup pattern
CREATE INDEX idx_uk_inflation_yoy_calc 
    ON uk_inflation_price_data(coicop_id, series_type, date);

-- Index for date-based queries (monthly reports)
CREATE INDEX idx_uk_inflation_date_series 
    ON uk_inflation_price_data(date, series_type);

-- Composite index for hierarchy + data joins
CREATE INDEX idx_uk_inflation_hierarchy_data 
    ON uk_inflation_price_data(series_type, date) 
    INCLUDE (coicop_id, index_value, weight_value);

-- Index for time series analysis
CREATE INDEX idx_uk_inflation_timeseries 
    ON uk_inflation_price_data(coicop_id, series_type, date)
    INCLUDE (index_value, weight_value);

-- =============================================================================
-- Helper Functions for Sort Order
-- =============================================================================

-- Function to generate sort order for proper hierarchical sorting
-- Converts '01.1.1.1' to padded numeric format for sorting
CREATE OR REPLACE FUNCTION uk_inflation_calculate_sort_order(coicop_id_input VARCHAR(15))
RETURNS BIGINT AS $$
DECLARE
    parts TEXT[];
    padded_parts TEXT[];
    part TEXT;
    result_str TEXT := '';
BEGIN
    -- Split COICOP ID by dots
    parts := string_to_array(coicop_id_input, '.');
    
    -- Pad each part to 4 digits
    FOREACH part IN ARRAY parts
    LOOP
        padded_parts := array_append(padded_parts, lpad(part, 4, '0'));
    END LOOP;
    
    -- Join and convert to bigint
    result_str := array_to_string(padded_parts, '');
    
    -- Ensure we don't exceed BIGINT limits
    IF length(result_str) > 18 THEN
        result_str := left(result_str, 18);
    END IF;
    
    RETURN result_str::BIGINT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- Common Query Patterns (as Views for Documentation)
-- =============================================================================

-- View: Get current month data with 12-month historical for YoY calculations
CREATE VIEW uk_inflation_yoy_ready AS
SELECT 
    current.date,
    current.coicop_id,
    current.series_type,
    h.level,
    h.parent_id,
    h.description,
    current.index_value as current_index,
    previous.index_value as previous_index,
    current.weight_value,
    -- Pre-calculate YoY rate for convenience
    CASE 
        WHEN previous.index_value IS NOT NULL AND previous.index_value > 0
        THEN ROUND(((current.index_value / previous.index_value) - 1) * 100, 4)
        ELSE NULL
    END as yoy_rate_pct
FROM uk_inflation_price_data current
LEFT JOIN uk_inflation_price_data previous ON (
    current.coicop_id = previous.coicop_id 
    AND current.series_type = previous.series_type
    AND previous.date = current.date - INTERVAL '12 months'
)
JOIN uk_inflation_coicop_hierarchy h ON current.coicop_id = h.coicop_id
WHERE current.index_value IS NOT NULL;

-- View: Hierarchy tree structure for easy navigation
CREATE VIEW uk_inflation_hierarchy_tree AS
WITH RECURSIVE tree AS (
    -- Level 0 and 1 (root categories)
    SELECT 
        coicop_id,
        level,
        parent_id,
        description,
        sort_order,
        coicop_id as root_id,
        0 as depth,
        ARRAY[coicop_id]::VARCHAR[] as path
    FROM uk_inflation_coicop_hierarchy 
    WHERE level <= 1 AND parent_id IS NULL
    
    UNION ALL
    
    -- Recursive: children
    SELECT 
        h.coicop_id,
        h.level,
        h.parent_id,
        h.description,
        h.sort_order,
        t.root_id,
        t.depth + 1,
        t.path || h.coicop_id
    FROM uk_inflation_coicop_hierarchy h
    JOIN tree t ON h.parent_id = t.coicop_id
)
SELECT 
    *,
    repeat('  ', depth) || coicop_id || ': ' || description as indented_description
FROM tree
ORDER BY root_id, sort_order;

-- =============================================================================
-- Data Validation Functions
-- =============================================================================

-- Function to validate data consistency
CREATE OR REPLACE FUNCTION uk_inflation_validate_data()
RETURNS TABLE(
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Check 1: All COICOP IDs in price_data exist in hierarchy
    RETURN QUERY
    SELECT 
        'Missing COICOP IDs'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
        COALESCE(COUNT(*)::TEXT || ' price records with missing COICOP IDs', 'All COICOP IDs valid')::TEXT
    FROM (
        SELECT DISTINCT coicop_id 
        FROM uk_inflation_price_data p
        WHERE NOT EXISTS (
            SELECT 1 FROM uk_inflation_coicop_hierarchy h WHERE h.coicop_id = p.coicop_id
        )
    ) missing;
    
    -- Check 2: Date consistency (no gaps in monthly data for headline)
    RETURN QUERY
    SELECT 
        'Date Gaps in Headline'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END::TEXT,
        COALESCE(COUNT(*)::TEXT || ' missing months in headline data', 'No date gaps')::TEXT
    FROM (
        WITH expected_dates AS (
            SELECT generate_series(
                (SELECT MIN(date) FROM uk_inflation_price_data WHERE coicop_id = '00'),
                (SELECT MAX(date) FROM uk_inflation_price_data WHERE coicop_id = '00'),
                '1 month'::interval
            )::DATE as expected_date
        )
        SELECT ed.expected_date
        FROM expected_dates ed
        WHERE NOT EXISTS (
            SELECT 1 FROM uk_inflation_price_data p 
            WHERE p.date = ed.expected_date AND p.coicop_id = '00'
        )
    ) gaps;
    
    -- Check 3: Weight values should exist for index values
    RETURN QUERY
    SELECT 
        'Missing Weights'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END::TEXT,
        COALESCE(COUNT(*)::TEXT || ' records with index but no weight', 'All records have weights')::TEXT
    FROM uk_inflation_price_data
    WHERE index_value IS NOT NULL AND weight_value IS NULL;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Comments and Documentation
-- =============================================================================

COMMENT ON TABLE uk_inflation_coicop_hierarchy IS 
'COICOP classification hierarchy for UK inflation data. Supports 4-level structure following international standards.';

COMMENT ON TABLE uk_inflation_price_data IS 
'Core inflation data storage. Minimal schema optimized for rate calculations and contribution analysis.';

COMMENT ON COLUMN uk_inflation_price_data.date IS 
'First day of month (e.g., 2024-12-01 for December 2024 data)';

COMMENT ON COLUMN uk_inflation_price_data.index_value IS 
'Price index value. Base periods: CPI/CPIH=2015=100, RPI=Jan 1987=100';

COMMENT ON COLUMN uk_inflation_price_data.weight_value IS 
'Weight for contribution calculations. Units may vary by series type.';

COMMENT ON VIEW uk_inflation_yoy_ready IS 
'Pre-joined view with current and 12-month historical data for YoY rate calculations';

-- =============================================================================
-- Success Message
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'UK Inflation tables created successfully!';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - uk_inflation_coicop_hierarchy';
    RAISE NOTICE '  - uk_inflation_price_data';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - uk_inflation_yoy_ready';
    RAISE NOTICE '  - uk_inflation_hierarchy_tree';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - uk_inflation_calculate_sort_order()';
    RAISE NOTICE '  - uk_inflation_validate_data()';
END $$;