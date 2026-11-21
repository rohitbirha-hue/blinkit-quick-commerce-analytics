-- ============================================================================
-- 02_executive_kpis.sql
-- Purpose: Executive Scorecard summarizing overall business health
-- ============================================================================

SELECT 
    COUNT(*) AS total_sku_transactions,
    COUNT(DISTINCT Outlet_Identifier) AS active_dark_stores,
    COUNT(DISTINCT Item_Type) AS product_categories,
    ROUND(SUM(Sales), 2) AS total_gross_revenue,
    ROUND(AVG(Sales), 2) AS avg_revenue_per_sku,
    ROUND(AVG(Rating), 2) AS avg_customer_rating,
    ROUND(SUM(CASE WHEN Rating >= 4.0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS high_rated_sku_pct
FROM vw_blinkit_analytics;
