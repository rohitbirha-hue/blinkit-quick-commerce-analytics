-- ============================================================================
-- 04_outlet_performance.sql
-- Purpose: Store Format Matrix, Within-Tier Benchmarking, & Category Mix
-- ============================================================================

-- Q4. OUTLET PERFORMANCE MATRIX & WITHIN-TIER BENCHMARKING
WITH outlet_metrics AS (
    SELECT 
        Outlet_Location_Type AS city_tier,
        Outlet_Type,
        Outlet_Size,
        ROUND(AVG(outlet_age_years), 1) AS avg_store_age,
        COUNT(*) AS total_skus,
        ROUND(SUM(Sales), 2) AS total_revenue,
        ROUND(AVG(Sales), 2) AS avg_ticket_per_sku,
        ROUND(AVG(Rating), 2) AS avg_rating
    FROM vw_blinkit_analytics
    GROUP BY Outlet_Location_Type, Outlet_Type, Outlet_Size
)
SELECT 
    city_tier,
    Outlet_Type,
    Outlet_Size,
    avg_store_age,
    total_revenue,
    avg_ticket_per_sku,
    avg_rating,
    DENSE_RANK() OVER (PARTITION BY city_tier ORDER BY total_revenue DESC) AS rank_within_tier,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 2) AS overall_rev_share_pct
FROM outlet_metrics
ORDER BY city_tier, rank_within_tier;

-- Q5. TOP 3 PERFORMING CATEGORIES INSIDE EACH OUTLET TYPE
WITH ranked_categories AS (
    SELECT 
        Outlet_Type,
        Item_Type,
        ROUND(SUM(Sales), 2) AS total_sales,
        ROW_NUMBER() OVER (PARTITION BY Outlet_Type ORDER BY SUM(Sales) DESC) AS category_rank
    FROM vw_blinkit_analytics
    GROUP BY Outlet_Type, Item_Type
)
SELECT 
    Outlet_Type,
    category_rank,
    Item_Type,
    total_sales
FROM ranked_categories
WHERE category_rank <= 3
ORDER BY Outlet_Type, category_rank;
