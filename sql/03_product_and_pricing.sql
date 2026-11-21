-- ============================================================================
-- 03_product_and_pricing.sql
-- Purpose: Pareto 80/20 Category Analysis, Shelf-Visibility ROI, & Price Tiers
-- ============================================================================

-- Q1. PARETO ANALYSIS (80/20 RULE): Which categories drive 80% of revenue?
WITH category_sales AS (
    SELECT 
        Item_Type,
        COUNT(*) AS sku_count,
        ROUND(SUM(Sales), 2) AS category_revenue,
        ROUND(AVG(Rating), 2) AS avg_rating
    FROM vw_blinkit_analytics
    GROUP BY Item_Type
),
pareto_calc AS (
    SELECT 
        *,
        ROUND(category_revenue * 100.0 / SUM(category_revenue) OVER (), 2) AS pct_of_total_rev,
        ROUND(SUM(category_revenue) OVER (ORDER BY category_revenue DESC) * 100.0 / SUM(category_revenue) OVER (), 2) AS cumulative_rev_pct
    FROM category_sales
)
SELECT 
    Item_Type,
    sku_count,
    category_revenue,
    pct_of_total_rev,
    cumulative_rev_pct,
    CASE 
        WHEN cumulative_rev_pct <= 80.00 THEN 'Core Revenue Driver (Top 80%)'
        ELSE 'Long-Tail Assortment (Bottom 20%)'
    END AS pareto_classification
FROM pareto_calc
ORDER BY category_revenue DESC;

-- Q2. SHELF-SPACE / APP VISIBILITY ROI BY CATEGORY
SELECT 
    Item_Type,
    ROUND(AVG(Item_Visibility) * 100, 2) AS avg_visibility_pct,
    ROUND(SUM(Sales), 2) AS total_revenue,
    ROUND(AVG(revenue_per_visibility_unit), 2) AS visibility_efficiency_score,
    RANK() OVER (ORDER BY AVG(revenue_per_visibility_unit) DESC) AS efficiency_rank
FROM vw_blinkit_analytics
GROUP BY Item_Type
ORDER BY efficiency_rank;

-- Q3. HEALTH-CONSCIOUS CONSUMER TRENDS: Fat Content across Price Tiers
SELECT 
    price_tier,
    Item_Fat_Content,
    COUNT(*) AS total_items,
    ROUND(SUM(Sales), 2) AS total_revenue,
    ROUND(SUM(Sales) * 100.0 / SUM(SUM(Sales)) OVER (PARTITION BY price_tier), 2) AS tier_revenue_share_pct,
    ROUND(AVG(Rating), 2) AS avg_rating
FROM vw_blinkit_analytics
GROUP BY price_tier, Item_Fat_Content
ORDER BY price_tier, total_revenue DESC;
