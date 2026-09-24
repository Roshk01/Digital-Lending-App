# Digital Lending App — Funnel, Cohort Retention & A/B Test Analysis

**Business Analyst / Product Analyst portfolio project** — synthetic dataset modeled on a
fintech lending/bookkeeping app (6,000 users, 6-month window), built to demonstrate SQL,
statistical testing, and BI-ready reporting for Ops/Product/CX analyst roles.

## Business Questions
1. Where do users drop off between App Install and Loan Approval, and which acquisition
   channel converts best?
2. How does weekly user retention decay across signup cohorts?
3. Does a simplified KYC onboarding flow (Variant_B) significantly improve KYC completion
   vs. the current flow (Control)?

## Methodology & Tools
- **SQL (SQLite)**: CTEs, window functions (`NTILE`), conditional aggregation for funnel
  construction, cohort retention, and RFM-style engagement segmentation
  → see `sql/analysis_queries.sql`
- **Python (pandas, scipy)**: chi-square test of independence for the A/B test
  → see `analysis.py`
- **Visualization**: matplotlib/seaborn (funnel chart, channel comparison, cohort heatmap,
  segmentation, A/B result) — same charts could be rebuilt in Power BI/Tableau for a
  stakeholder-facing dashboard

## Key Findings

**1. Funnel** — Install → Loan Approved overall conversion is ~9.5%. Biggest drop-offs:
Signup → KYC (65.6%) and Transaction → Loan Application (39.7%) — KYC and loan-application
friction are the two stages to prioritize for improvement.

**2. Channel performance** — Referral (14.9%) and Organic (12.0%) convert 2-3x better than
Affiliate (4.1%) — a case for reallocating acquisition spend toward referral programs.

**3. Retention** — Week-0 to week-8 retention decays from ~45% to ~12-14% across cohorts,
fairly consistent month over month (no strong seasonal cohort effect).

**4. Engagement segments** — 34% of active users are "At Risk / Churning" (low recent
activity) vs. only 10% "Power Users" — a natural target list for a re-engagement campaign.

**5. A/B Test result** — Variant_B (simplified KYC) lifted KYC completion from **60.35% →
70.89%** (+17.5% relative lift). Chi-square test: χ²=54.76, **p<0.00001** — statistically
significant at α=0.05. **Recommendation: ship Variant_B to 100% of users.**

## Files
```
generate_data.py          - synthetic data generator (users, funnel events, activity log)
load_db.py                 - loads CSVs into SQLite (analytics.db)
sql/analysis_queries.sql   - all analysis SQL (funnel, cohort, segmentation, A/B)
analysis.py                 - runs queries, stats test, generates charts
data/                        - raw CSVs
output/                      - charts (PNG) + result tables (CSV/TXT)
```

## How this maps to a Business/Product Analyst JD
| JD requirement | Where it's demonstrated |
|---|---|
| SQL | CTEs, window functions (NTILE), conditional aggregation — `sql/analysis_queries.sql` |
| Statistics / statistical analysis | Chi-square test of independence on A/B test data |
| BI tools | Charts built as a portfolio stand-in for Power BI/Tableau dashboard |
| Python/scripting | pandas + scipy pipeline end-to-end |
| Problem-solving / business recommendation | Each finding ends in a concrete action (spend reallocation, ship Variant_B, target churn segment) |

## Suggested resume bullets
- Built an end-to-end funnel, retention, and A/B test analysis pipeline (SQL + Python) on
  6,000+ synthetic fintech app users; identified KYC as the largest funnel drop-off point.
- Ran a chi-square test of independence on onboarding A/B test data, finding a
  statistically significant 17.5% lift in KYC completion (p<0.001) for a simplified flow.
- Used SQL window functions (NTILE) to build an RFM-style engagement segmentation,
  flagging 34% of active users as churn-risk for a targeted retention campaign.
