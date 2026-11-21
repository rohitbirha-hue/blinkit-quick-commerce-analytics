"""
run_pipeline.py
One-click end-to-end data engineering & analytics pipeline for Blinkit Grocery Sales.
1. Loads raw CSV into SQLite database (or generates realistic dataset if CSV is not present).
2. Executes SQL cleaning, standardization, and analytical view scripts.
3. Exports SQL query results to CSV reports in /insights.
4. Generates publication-grade charts in /assets for README.md.
"""

import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

CSV_PATH = os.path.join("data", "BlinkIT Grocery Data.csv")
DB_PATH = "blinkit.db"
ASSETS_DIR = "assets"
INSIGHTS_DIR = "insights"

os.makedirs("data", exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(INSIGHTS_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#CCCCCC"
plt.rcParams["axes.linewidth"] = 0.8
BLINKIT_YELLOW = "#F8CB46"
BLINKIT_GREEN = "#0C831F"
DARK_SLATE = "#1F2937"


def generate_sample_dataset(filepath):
    print(f"[INFO] '{filepath}' not found. Generating 8,523-row Blinkit dataset...")
    np.random.seed(42)
    n_rows = 8523
    item_types = [
        "Fruits and Vegetables", "Snack Foods", "Household", "Frozen Foods",
        "Dairy", "Canned", "Baking Goods", "Health and Hygiene",
        "Soft Drinks", "Meat", "Breads", "Hard Drinks",
        "Others", "Starchy Foods", "Breakfast", "Seafood"
    ]
    weights = [0.145, 0.141, 0.107, 0.100, 0.080, 0.076, 0.076, 0.061,
               0.052, 0.050, 0.029, 0.025, 0.020, 0.017, 0.013, 0.008]
    fat_choices = ["Low Fat", "Regular", "LF", "low fat", "reg"]
    fat_probs = [0.55, 0.30, 0.06, 0.04, 0.05]
    outlets = [
        ("OUT027", "Tier 3", "Medium", "Supermarket Type3", 1998),
        ("OUT013", "Tier 3", "High", "Supermarket Type1", 2000),
        ("OUT049", "Tier 1", "Medium", "Supermarket Type1", 2012),
        ("OUT035", "Tier 2", "Small", "Supermarket Type1", 2017),
        ("OUT046", "Tier 1", "Small", "Supermarket Type1", 2010),
        ("OUT017", "Tier 2", "", "Supermarket Type1", 2018),
        ("OUT045", "Tier 2", "", "Supermarket Type1", 2015),
        ("OUT018", "Tier 3", "Medium", "Supermarket Type2", 2020),
        ("OUT019", "Tier 1", "Small", "Grocery Store", 1998),
        ("OUT010", "Tier 3", "", "Grocery Store", 2011),
    ]
    chosen_outlets = [outlets[i] for i in np.random.choice(len(outlets), size=n_rows)]
    chosen_items = np.random.choice(item_types, size=n_rows, p=weights)
    mrp = np.round(np.random.uniform(31.0, 266.0, size=n_rows), 2)
    visibility = np.round(np.random.exponential(scale=0.065, size=n_rows), 6)
    visibility[np.random.rand(n_rows) < 0.06] = 0.0
    base_sales = mrp * np.random.uniform(0.65, 1.35, size=n_rows)
    outlet_mult = np.array([
        0.35 if o[3] == "Grocery Store" else (1.45 if o[3] == "Supermarket Type3" else 1.05)
        for o in chosen_outlets
    ])
    sales = np.round(base_sales * outlet_mult, 4)
    ratings = np.round(np.clip(np.random.normal(3.96, 0.65, size=n_rows), 1.0, 5.0), 1)
    df = pd.DataFrame({
        "Item_Fat_Content": np.random.choice(fat_choices, size=n_rows, p=fat_probs),
        "Item_Identifier": [f"FD{np.random.randint(100, 999)}" for _ in range(n_rows)],
        "Item_Type": chosen_items,
        "Outlet_Establishment_Year": [o[4] for o in chosen_outlets],
        "Outlet_Identifier": [o[0] for o in chosen_outlets],
        "Outlet_Location_Type": [o[1] for o in chosen_outlets],
        "Outlet_Size": [o[2] for o in chosen_outlets],
        "Outlet_Type": [o[3] for o in chosen_outlets],
        "Item_Visibility": visibility,
        "Item_Weight": np.round(np.random.uniform(4.5, 21.3, size=n_rows), 2),
        "Item_MRP": mrp,
        "Sales": sales,
        "Rating": ratings,
    })
    df.to_csv(filepath, index=False)
    print(f"[SUCCESS] Sample dataset saved to '{filepath}'.")


def load_and_clean_database():
    if not os.path.exists(CSV_PATH):
        generate_sample_dataset(CSV_PATH)
    print("[STEP 1] Loading CSV into SQLite database...")
    df_raw = pd.read_csv(CSV_PATH)
    if "Item_MRP" not in df_raw.columns and "MRP" in df_raw.columns:
        df_raw.rename(columns={"MRP": "Item_MRP"}, inplace=True)
    elif "Item_MRP" not in df_raw.columns:
        df_raw["Item_MRP"] = df_raw["Sales"]
    if "Rating" not in df_raw.columns and "Item_Rating" in df_raw.columns:
        df_raw.rename(columns={"Item_Rating": "Rating"}, inplace=True)
    conn = sqlite3.connect(DB_PATH)
    df_raw.to_sql("blinkit_raw", conn, if_exists="replace", index=False)
    print("[STEP 2] Executing SQL cleaning & analytical view script...")
    with open(os.path.join("sql", "01_schema_and_cleaning.sql"), "r", encoding="utf-8") as f:
        cleaning_sql = f.read()
    conn.executescript(cleaning_sql)
    conn.commit()
    return conn


def run_analytical_exports(conn):
    print("[STEP 3] Running SQL KPI & analytical queries and exporting summaries...")
    with open(os.path.join("sql", "02_executive_kpis.sql"), "r", encoding="utf-8") as f:
        kpi_sql = f.read()
    df_kpi = pd.read_sql_query(kpi_sql, conn)
    df_kpi.to_csv(os.path.join(INSIGHTS_DIR, "01_executive_kpis.csv"), index=False)
    print("\n--- EXECUTIVE KPI SCORECARD ---")
    print(df_kpi.to_string(index=False))

    pareto_sql = """
    WITH category_sales AS (
        SELECT Item_Type, COUNT(*) AS sku_count, ROUND(SUM(Sales), 2) AS category_revenue, ROUND(AVG(Rating), 2) AS avg_rating
        FROM vw_blinkit_analytics GROUP BY Item_Type
    ),
    pareto_calc AS (
        SELECT *,
            ROUND(category_revenue * 100.0 / SUM(category_revenue) OVER (), 2) AS pct_of_total_rev,
            ROUND(SUM(category_revenue) OVER (ORDER BY category_revenue DESC) * 100.0 / SUM(category_revenue) OVER (), 2) AS cumulative_rev_pct
        FROM category_sales
    )
    SELECT Item_Type, sku_count, category_revenue, pct_of_total_rev, cumulative_rev_pct,
        CASE WHEN cumulative_rev_pct <= 80.00 THEN 'Core Revenue Driver (Top 80%)' ELSE 'Long-Tail Assortment (Bottom 20%)' END AS pareto_classification
    FROM pareto_calc ORDER BY category_revenue DESC;
    """
    df_pareto = pd.read_sql_query(pareto_sql, conn)
    df_pareto.to_csv(os.path.join(INSIGHTS_DIR, "02_pareto_categories.csv"), index=False)

    outlet_sql = """
    WITH outlet_metrics AS (
        SELECT Outlet_Location_Type AS city_tier, Outlet_Type, Outlet_Size,
            ROUND(AVG(outlet_age_years), 1) AS avg_store_age, COUNT(*) AS total_skus,
            ROUND(SUM(Sales), 2) AS total_revenue, ROUND(AVG(Sales), 2) AS avg_ticket_per_sku, ROUND(AVG(Rating), 2) AS avg_rating
        FROM vw_blinkit_analytics GROUP BY Outlet_Location_Type, Outlet_Type, Outlet_Size
    )
    SELECT city_tier, Outlet_Type, Outlet_Size, avg_store_age, total_revenue, avg_ticket_per_sku, avg_rating,
        DENSE_RANK() OVER (PARTITION BY city_tier ORDER BY total_revenue DESC) AS rank_within_tier,
        ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 2) AS overall_rev_share_pct
    FROM outlet_metrics ORDER BY city_tier, rank_within_tier;
    """
    df_outlet = pd.read_sql_query(outlet_sql, conn)
    df_outlet.to_csv(os.path.join(INSIGHTS_DIR, "03_outlet_performance.csv"), index=False)
    return df_pareto


def generate_visualizations(conn, df_pareto):
    print("\n[STEP 4] Generating publication-grade portfolio charts...")
    fig, ax1 = plt.subplots(figsize=(12, 6), dpi=300)
    ax1.bar(df_pareto["Item_Type"], df_pareto["category_revenue"] / 1e3, color=BLINKIT_YELLOW, edgecolor=DARK_SLATE, width=0.65)
    ax1.set_ylabel("Total Revenue (₹ Thousands)", fontsize=11, fontweight="bold", color=DARK_SLATE)
    ax1.tick_params(axis="x", rotation=45, labelsize=9.5)
    plt.setp(ax1.get_xticklabels(), ha="right")
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter("₹{x:,.0f}K"))
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    ax2 = ax1.twinx()
    ax2.plot(df_pareto["Item_Type"], df_pareto["cumulative_rev_pct"], color=BLINKIT_GREEN, marker="o", linewidth=2.5, markersize=6)
    ax2.axhline(80, color="#DC2626", linestyle="--", linewidth=1.2, label="80% Pareto Threshold")
    ax2.set_ylabel("Cumulative Revenue Share (%)", fontsize=11, fontweight="bold", color=BLINKIT_GREEN)
    ax2.set_ylim(0, 105)
    ax2.yaxis.set_major_formatter(ticker.PercentFormatter())
    ax2.legend(loc="center right", frameon=True)

    plt.title("Blinkit Assortment Pareto Analysis: Revenue Concentration by Category", fontsize=14, fontweight="bold", pad=15, color=DARK_SLATE)
    fig.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "01_pareto_categories.png"))
    plt.close()

    vis_sql = """
    SELECT Item_Type, AVG(Item_Visibility) * 100 AS avg_visibility_pct,
           SUM(Sales) AS total_revenue, AVG(revenue_per_visibility_unit) AS efficiency_score
    FROM vw_blinkit_analytics GROUP BY Item_Type;
    """
    df_vis = pd.read_sql_query(vis_sql, conn)
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    scatter = ax.scatter(
        df_vis["avg_visibility_pct"], df_vis["total_revenue"] / 1e3,
        s=df_vis["efficiency_score"] / 8, c=df_vis["efficiency_score"],
        cmap="YlGn", edgecolors=DARK_SLATE, linewidth=1.2, alpha=0.9
    )
    ax.axvline(df_vis["avg_visibility_pct"].median(), color="#6B7280", linestyle="--", linewidth=1)
    ax.axhline((df_vis["total_revenue"] / 1e3).median(), color="#6B7280", linestyle="--", linewidth=1)
    for _, row in df_vis.iterrows():
        ax.annotate(row["Item_Type"], (row["avg_visibility_pct"], row["total_revenue"] / 1e3),
                    xytext=(5, 4), textcoords="offset points", fontsize=8.5, color=DARK_SLATE)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Visibility Efficiency Score (Rev / Visibility Unit)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Average App/Shelf Visibility (%)", fontsize=11, fontweight="bold", color=DARK_SLATE)
    ax.set_ylabel("Total Category Revenue (₹ Thousands)", fontsize=11, fontweight="bold", color=DARK_SLATE)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("₹{x:,.0f}K"))
    ax.grid(True, linestyle=":", alpha=0.5)
    plt.title("Digital Shelf ROI: Visibility Allocation vs. Revenue Generation", fontsize=14, fontweight="bold", pad=15, color=DARK_SLATE)
    fig.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "02_visibility_roi_matrix.png"))
    plt.close()

    heat_sql = """
    SELECT Outlet_Location_Type AS city_tier, Outlet_Type, SUM(Sales) / 1e3 AS revenue_k
    FROM vw_blinkit_analytics GROUP BY Outlet_Location_Type, Outlet_Type;
    """
    df_heat = pd.read_sql_query(heat_sql, conn)
    pivot_df = df_heat.pivot(index="Outlet_Type", columns="city_tier", values="revenue_k").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    sns.heatmap(
        pivot_df, annot=True, fmt=".1f", cmap="YlGnBu",
        cbar_kws={"label": "Total Revenue (₹ Thousands)"},
        linewidths=1.5, linecolor="white", annot_kws={"size": 11, "weight": "bold"}, ax=ax
    )
    ax.set_xlabel("City Tier", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_ylabel("Outlet Format", fontsize=11, fontweight="bold", labelpad=10)
    plt.yticks(rotation=0)
    plt.title("Revenue Heatmap (₹K): Store Format vs. City Tier", fontsize=13, fontweight="bold", pad=14, color=DARK_SLATE)
    fig.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "03_tier_outlet_heatmap.png"))
    plt.close()
    print("[SUCCESS] All 3 charts saved in '/assets' and CSV reports in '/insights'.")


if __name__ == "__main__":
    connection = load_and_clean_database()
    pareto_df = run_analytical_exports(connection)
    generate_visualizations(connection, pareto_df)
    connection.close()
    print("\nPipeline complete! Ready to commit and push to GitHub.")