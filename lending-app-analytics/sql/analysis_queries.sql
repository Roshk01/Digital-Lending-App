-- ============================================================
-- Digital Lending App: Funnel, Cohort & Segmentation Analysis
-- ============================================================

-- 1. FUNNEL CONVERSION (overall) ------------------------------
-- Step-by-step drop-off using conditional aggregation
WITH step_flags AS (
    SELECT
        u.user_id,
        MAX(CASE WHEN f.step = 'App Install' THEN 1 ELSE 0 END) AS s1_install,
        MAX(CASE WHEN f.step = 'Signup' THEN 1 ELSE 0 END) AS s2_signup,
        MAX(CASE WHEN f.step = 'KYC Verification' THEN 1 ELSE 0 END) AS s3_kyc,
        MAX(CASE WHEN f.step = 'First Transaction' THEN 1 ELSE 0 END) AS s4_txn,
        MAX(CASE WHEN f.step = 'Loan Application' THEN 1 ELSE 0 END) AS s5_apply,
        MAX(CASE WHEN f.step = 'Loan Approved' THEN 1 ELSE 0 END) AS s6_approved
    FROM users u
    LEFT JOIN funnel_events f ON u.user_id = f.user_id
    GROUP BY u.user_id
)
SELECT
    SUM(s1_install) AS "App Install",
    SUM(s2_signup)  AS "Signup",
    SUM(s3_kyc)     AS "KYC Verification",
    SUM(s4_txn)     AS "First Transaction",
    SUM(s5_apply)   AS "Loan Application",
    SUM(s6_approved) AS "Loan Approved",
    ROUND(100.0 * SUM(s2_signup) / SUM(s1_install), 1)  AS "Install->Signup %",
    ROUND(100.0 * SUM(s3_kyc) / SUM(s2_signup), 1)      AS "Signup->KYC %",
    ROUND(100.0 * SUM(s4_txn) / SUM(s3_kyc), 1)         AS "KYC->Txn %",
    ROUND(100.0 * SUM(s5_apply) / SUM(s4_txn), 1)       AS "Txn->Apply %",
    ROUND(100.0 * SUM(s6_approved) / SUM(s5_apply), 1)  AS "Apply->Approved %"
FROM step_flags;


-- 2. FUNNEL CONVERSION BY ACQUISITION CHANNEL ------------------
WITH step_flags AS (
    SELECT
        u.user_id, u.channel,
        MAX(CASE WHEN f.step = 'App Install' THEN 1 ELSE 0 END) AS installed,
        MAX(CASE WHEN f.step = 'Loan Approved' THEN 1 ELSE 0 END) AS approved
    FROM users u
    LEFT JOIN funnel_events f ON u.user_id = f.user_id
    GROUP BY u.user_id, u.channel
)
SELECT
    channel,
    SUM(installed) AS installs,
    SUM(approved) AS loans_approved,
    ROUND(100.0 * SUM(approved) / SUM(installed), 2) AS "install_to_approval_rate_%"
FROM step_flags
GROUP BY channel
ORDER BY "install_to_approval_rate_%" DESC;


-- 3. WEEKLY COHORT RETENTION (window functions) ----------------
-- Cohort = week of signup; retention tracked by weeks since signup
WITH signups AS (
    SELECT user_id, MIN(event_date) AS signup_date
    FROM funnel_events
    WHERE step = 'Signup'
    GROUP BY user_id
),
cohorts AS (
    SELECT
        user_id,
        signup_date,
        strftime('%Y-%W', signup_date) AS cohort_week
    FROM signups
),
activity_with_cohort AS (
    SELECT
        a.user_id,
        c.cohort_week,
        a.week_number
    FROM activity_log a
    JOIN cohorts c ON a.user_id = c.user_id
),
cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_week
)
SELECT
    ac.cohort_week,
    cs.cohort_size,
    ac.week_number,
    COUNT(DISTINCT ac.user_id) AS active_users,
    ROUND(100.0 * COUNT(DISTINCT ac.user_id) / cs.cohort_size, 1) AS retention_pct
FROM activity_with_cohort ac
JOIN cohort_sizes cs ON ac.cohort_week = cs.cohort_week
GROUP BY ac.cohort_week, ac.week_number
ORDER BY ac.cohort_week, ac.week_number;


-- 4. RFM-STYLE ENGAGEMENT SEGMENTATION (window functions) ------
-- Recency = weeks since last activity, Frequency = active weeks count
WITH user_activity AS (
    SELECT
        user_id,
        COUNT(*) AS frequency,
        MAX(week_number) AS last_active_week
    FROM activity_log
    GROUP BY user_id
),
scored AS (
    SELECT
        user_id,
        frequency,
        last_active_week,
        NTILE(4) OVER (ORDER BY frequency DESC) AS freq_quartile,
        NTILE(4) OVER (ORDER BY last_active_week DESC) AS recency_quartile
    FROM user_activity
)
SELECT
    CASE
        WHEN freq_quartile = 1 AND recency_quartile = 1 THEN 'Power Users'
        WHEN recency_quartile >= 3 THEN 'At Risk / Churning'
        WHEN freq_quartile = 1 THEN 'Loyal but Cooling Off'
        ELSE 'Casual Users'
    END AS segment,
    COUNT(*) AS user_count,
    ROUND(AVG(frequency), 1) AS avg_active_weeks
FROM scored
GROUP BY segment
ORDER BY user_count DESC;


-- 5. A/B TEST RAW DATA (Control vs Variant_B onboarding) --------
-- Base = users who signed up (entered the onboarding flow); outcome = completed KYC
-- Feeds the chi-square test done in Python (analysis.py)
WITH signed_up AS (
    SELECT DISTINCT user_id FROM funnel_events WHERE step = 'Signup'
),
kyc_done AS (
    SELECT DISTINCT user_id FROM funnel_events WHERE step = 'KYC Verification'
)
SELECT
    u.ab_group,
    COUNT(DISTINCT s.user_id) AS total_signed_up,
    COUNT(DISTINCT k.user_id) AS kyc_completed,
    ROUND(100.0 * COUNT(DISTINCT k.user_id) / COUNT(DISTINCT s.user_id), 2) AS kyc_completion_rate_pct
FROM users u
JOIN signed_up s ON u.user_id = s.user_id
LEFT JOIN kyc_done k ON u.user_id = k.user_id
GROUP BY u.ab_group;
