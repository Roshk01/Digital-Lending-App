"""
Digital Lending App: Funnel, Cohort Retention & A/B Test Analysis
Business questions:
  1. Where do users drop off in the install->loan-approval funnel, and which
     acquisition channel converts best?
  2. How does weekly retention decay across signup cohorts?
  3. Does the simplified KYC onboarding flow (Variant_B) significantly
     improve KYC completion vs the Control flow?
"""
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

conn = sqlite3.connect("/home/claude/proj/analytics.db")
sns.set_style("whitegrid")
OUT = "/home/claude/proj/output"

def run_query(sql):
    return pd.read_sql_query(sql, conn)

# ---------------------------------------------------------------
# 1. FUNNEL ANALYSIS
# ---------------------------------------------------------------
funnel_overall = run_query("""
WITH step_flags AS (
    SELECT u.user_id,
        MAX(CASE WHEN f.step='App Install' THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN f.step='Signup' THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN f.step='KYC Verification' THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN f.step='First Transaction' THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN f.step='Loan Application' THEN 1 ELSE 0 END) AS s5,
        MAX(CASE WHEN f.step='Loan Approved' THEN 1 ELSE 0 END) AS s6
    FROM users u LEFT JOIN funnel_events f ON u.user_id=f.user_id
    GROUP BY u.user_id
)
SELECT 'App Install' AS step, SUM(s1) AS users FROM step_flags
UNION ALL SELECT 'Signup', SUM(s2) FROM step_flags
UNION ALL SELECT 'KYC Verification', SUM(s3) FROM step_flags
UNION ALL SELECT 'First Transaction', SUM(s4) FROM step_flags
UNION ALL SELECT 'Loan Application', SUM(s5) FROM step_flags
UNION ALL SELECT 'Loan Approved', SUM(s6) FROM step_flags;
""")
funnel_overall["conversion_from_prev_%"] = (funnel_overall["users"].pct_change() * 100 + 100).round(1)
funnel_overall.loc[0, "conversion_from_prev_%"] = 100.0
print("\n=== FUNNEL (overall) ===")
print(funnel_overall.to_string(index=False))

# Funnel chart
plt.figure(figsize=(8, 5))
sns.barplot(data=funnel_overall, x="users", y="step", palette="viridis")
plt.title("User Funnel: App Install -> Loan Approved")
plt.xlabel("Users")
plt.tight_layout()
plt.savefig(f"{OUT}/1_funnel_overall.png", dpi=140)
plt.close()

# Funnel by channel
funnel_channel = run_query("""
WITH step_flags AS (
    SELECT u.user_id, u.channel,
        MAX(CASE WHEN f.step='App Install' THEN 1 ELSE 0 END) AS installed,
        MAX(CASE WHEN f.step='Loan Approved' THEN 1 ELSE 0 END) AS approved
    FROM users u LEFT JOIN funnel_events f ON u.user_id=f.user_id
    GROUP BY u.user_id, u.channel
)
SELECT channel, SUM(installed) AS installs, SUM(approved) AS loans_approved,
    ROUND(100.0*SUM(approved)/SUM(installed), 2) AS install_to_approval_rate_pct
FROM step_flags GROUP BY channel ORDER BY install_to_approval_rate_pct DESC;
""")
print("\n=== FUNNEL BY CHANNEL ===")
print(funnel_channel.to_string(index=False))

plt.figure(figsize=(8, 5))
sns.barplot(data=funnel_channel.sort_values("install_to_approval_rate_pct"),
            x="install_to_approval_rate_pct", y="channel", palette="mako")
plt.title("Install -> Loan Approval Rate by Acquisition Channel")
plt.xlabel("Conversion Rate (%)")
plt.tight_layout()
plt.savefig(f"{OUT}/2_funnel_by_channel.png", dpi=140)
plt.close()

# ---------------------------------------------------------------
# 2. COHORT RETENTION
# ---------------------------------------------------------------
cohort = run_query("""
WITH signups AS (
    SELECT user_id, MIN(event_date) AS signup_date FROM funnel_events
    WHERE step='Signup' GROUP BY user_id
),
cohorts AS (
    SELECT user_id, strftime('%Y-%W', signup_date) AS cohort_week FROM signups
),
awc AS (
    SELECT a.user_id, c.cohort_week, a.week_number
    FROM activity_log a JOIN cohorts c ON a.user_id=c.user_id
),
sizes AS (SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size FROM cohorts GROUP BY cohort_week)
SELECT awc.cohort_week, sizes.cohort_size, awc.week_number,
    COUNT(DISTINCT awc.user_id) AS active_users,
    ROUND(100.0*COUNT(DISTINCT awc.user_id)/sizes.cohort_size, 1) AS retention_pct
FROM awc JOIN sizes ON awc.cohort_week=sizes.cohort_week
GROUP BY awc.cohort_week, awc.week_number
ORDER BY awc.cohort_week, awc.week_number;
""")

# Keep cohorts with enough size + first 8 weeks for a readable heatmap
top_cohorts = cohort[cohort["cohort_size"] >= 100]["cohort_week"].unique()[:10]
pivot = cohort[(cohort["cohort_week"].isin(top_cohorts)) & (cohort["week_number"] <= 8)] \
    .pivot(index="cohort_week", columns="week_number", values="retention_pct")

plt.figure(figsize=(10, 6))
sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGnBu", cbar_kws={"label": "Retention %"})
plt.title("Weekly Cohort Retention (%)")
plt.xlabel("Weeks Since Signup")
plt.ylabel("Signup Cohort (Year-Week)")
plt.tight_layout()
plt.savefig(f"{OUT}/3_cohort_retention_heatmap.png", dpi=140)
plt.close()
print("\n=== COHORT RETENTION (sample) ===")
print(pivot.round(1).to_string())

# ---------------------------------------------------------------
# 3. ENGAGEMENT SEGMENTATION (RFM-style)
# ---------------------------------------------------------------
segments = run_query("""
WITH ua AS (
    SELECT user_id, COUNT(*) AS frequency, MAX(week_number) AS last_active_week
    FROM activity_log GROUP BY user_id
),
scored AS (
    SELECT user_id, frequency, last_active_week,
        NTILE(4) OVER (ORDER BY frequency DESC) AS freq_q,
        NTILE(4) OVER (ORDER BY last_active_week DESC) AS recency_q
    FROM ua
)
SELECT
    CASE
        WHEN freq_q=1 AND recency_q=1 THEN 'Power Users'
        WHEN recency_q>=3 THEN 'At Risk / Churning'
        WHEN freq_q=1 THEN 'Loyal but Cooling Off'
        ELSE 'Casual Users'
    END AS segment,
    COUNT(*) AS user_count,
    ROUND(AVG(frequency),1) AS avg_active_weeks
FROM scored GROUP BY segment ORDER BY user_count DESC;
""")
print("\n=== ENGAGEMENT SEGMENTATION ===")
print(segments.to_string(index=False))

plt.figure(figsize=(7, 5))
sns.barplot(data=segments, x="user_count", y="segment", palette="flare")
plt.title("User Engagement Segments")
plt.xlabel("Users")
plt.tight_layout()
plt.savefig(f"{OUT}/4_engagement_segments.png", dpi=140)
plt.close()

# ---------------------------------------------------------------
# 4. A/B TEST: Control vs Variant_B onboarding -> KYC completion
# ---------------------------------------------------------------
ab_raw = run_query("""
WITH signed_up AS (SELECT DISTINCT user_id FROM funnel_events WHERE step='Signup'),
kyc_done AS (SELECT DISTINCT user_id FROM funnel_events WHERE step='KYC Verification')
SELECT u.ab_group, COUNT(DISTINCT s.user_id) AS total_signed_up,
    COUNT(DISTINCT k.user_id) AS kyc_completed
FROM users u
JOIN signed_up s ON u.user_id=s.user_id
LEFT JOIN kyc_done k ON u.user_id=k.user_id
GROUP BY u.ab_group;
""")
print("\n=== A/B TEST RAW DATA ===")
print(ab_raw.to_string(index=False))

# Chi-square test of independence on the 2x2 contingency table
control = ab_raw[ab_raw.ab_group == "Control"].iloc[0]
variant = ab_raw[ab_raw.ab_group == "Variant_B"].iloc[0]

contingency = [
    [control.kyc_completed, control.total_signed_up - control.kyc_completed],
    [variant.kyc_completed, variant.total_signed_up - variant.kyc_completed],
]
chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

control_rate = control.kyc_completed / control.total_signed_up * 100
variant_rate = variant.kyc_completed / variant.total_signed_up * 100
lift = (variant_rate - control_rate) / control_rate * 100

print(f"\n=== A/B TEST RESULT ===")
print(f"Control KYC completion rate:   {control_rate:.2f}%")
print(f"Variant_B KYC completion rate: {variant_rate:.2f}%")
print(f"Relative lift: {lift:+.1f}%")
print(f"Chi-square statistic: {chi2:.3f}, p-value: {p_value:.5f}")
print(f"Statistically significant at alpha=0.05: {p_value < 0.05}")

with open(f"{OUT}/ab_test_result.txt", "w") as f:
    f.write(f"Control KYC completion rate:   {control_rate:.2f}% ({control.kyc_completed}/{control.total_signed_up})\n")
    f.write(f"Variant_B KYC completion rate: {variant_rate:.2f}% ({variant.kyc_completed}/{variant.total_signed_up})\n")
    f.write(f"Relative lift: {lift:+.1f}%\n")
    f.write(f"Chi-square statistic: {chi2:.3f}\n")
    f.write(f"p-value: {p_value:.5f}\n")
    f.write(f"Statistically significant at alpha=0.05: {p_value < 0.05}\n")

plt.figure(figsize=(6, 5))
sns.barplot(x=["Control", "Variant_B"], y=[control_rate, variant_rate], palette=["#888888", "#2b8cbe"])
plt.title(f"KYC Completion Rate by Onboarding Flow\n(p={p_value:.4f}, {'significant' if p_value<0.05 else 'not significant'})")
plt.ylabel("KYC Completion Rate (%)")
plt.tight_layout()
plt.savefig(f"{OUT}/5_ab_test_kyc.png", dpi=140)
plt.close()

# Save summary tables as CSV for the report / resume portfolio
funnel_overall.to_csv(f"{OUT}/funnel_overall.csv", index=False)
funnel_channel.to_csv(f"{OUT}/funnel_by_channel.csv", index=False)
segments.to_csv(f"{OUT}/engagement_segments.csv", index=False)

conn.close()
print("\nAll charts and tables saved to", OUT)
