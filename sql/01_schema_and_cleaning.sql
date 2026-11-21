-- ============================================================================
-- 01_schema_and_cleaning.sql
-- Purpose: Categorical standardization, missing value imputation,
--          zero-visibility anomaly correction, and analytical view creation.
-- Compatible with: SQLite (via run_pipeline.py) & PostgreSQL
-- ============================================================================

-- A. Standardize inconsistent categorical labels in Item_Fat_Content
UPDATE blinkit_raw
SET Item_Fat_Content = CASE 
    WHEN UPPER(TRIM(Item_Fat_Content)) IN ('LF', 'LOW FAT') THEN 'Low Fat'
    WHEN UPPER(TRIM(Item_Fat_Content)) IN ('REG', 'REGULAR') THEN 'Regular'
    ELSE Item_Fat_Content
END;

-- B. Handle missing Outlet_Size values based on Outlet_Type domain logic
UPDATE blinkit_raw
SET Outlet_Size = 'Small'
WHERE (Outlet_Size IS NULL OR TRIM(Outlet_Size) = '')
  AND Outlet_Type = 'Grocery Store';

UPDATE blinkit_raw
SET Outlet_Size = 'Medium'
WHERE (Outlet_Size IS NULL OR TRIM(Outlet_Size) = '')
  AND Outlet_Type IN ('Supermarket Type1', 'Supermarket Type2', 'Supermarket Type3');

-- C. Fix 0.00 Item_Visibility (Physical products on shelves cannot have 0 visibility)
-- Impute 0 visibility using the category average visibility
UPDATE blinkit_raw
SET Item_Visibility = (
    SELECT AVG(NULLIF(b2.Item_Visibility, 0))
    FROM blinkit_raw b2
    WHERE b2.Item_Type = blinkit_raw.Item_Type
)
WHERE Item_Visibility = 0 OR Item_Visibility IS NULL;

-- D. Create Analytical View with Derived Business Dimensions
DROP VIEW IF EXISTS vw_blinkit_analytics;

CREATE VIEW vw_blinkit_analytics AS
SELECT 
    *,
    (2026 - Outlet_Establishment_Year) AS outlet_age_years,
    CASE 
        WHEN Item_MRP < 70 THEN '1. Economy (< ₹70)'
        WHEN Item_MRP BETWEEN 70 AND 139.99 THEN '2. Mass Market (₹70 - ₹139)'
        WHEN Item_MRP BETWEEN 140 AND 209.99 THEN '3. Mid-Premium (₹140 - ₹209)'
        ELSE '4. Premium (₹210+)'
    END AS price_tier,
    ROUND(Sales / NULLIF(Item_Visibility, 0), 2) AS revenue_per_visibility_unit
FROM blinkit_raw;
