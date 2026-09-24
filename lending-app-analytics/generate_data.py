"""
Synthetic data generator for: Digital Lending App - Funnel, Cohort & A/B Test Analysis
Mimics a fintech bookkeeping/lending app (Khatabook-style) user base over 6 months.
"""
import random
import csv
from datetime import datetime, timedelta

random.seed(42)

N_USERS = 6000
START_DATE = datetime(2026, 3, 1)
END_DATE = datetime(2026, 8, 31)
CHANNELS = ["Organic", "Paid Social", "Referral", "Google Ads", "Affiliate"]
CITY_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
DEVICES = ["Android", "iOS"]

# Funnel steps in order
FUNNEL_STEPS = ["App Install", "Signup", "KYC Verification", "First Transaction", "Loan Application", "Loan Approved"]

# Base conversion probability per step (varies by channel/tier to create realistic patterns)
BASE_CONV = {
    "App Install->Signup": 0.72,
    "Signup->KYC Verification": 0.55,
    "KYC Verification->First Transaction": 0.68,
    "First Transaction->Loan Application": 0.35,
    "Loan Application->Loan Approved": 0.62,
}

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days), seconds=random.randint(0, 86399))

users = []
funnel_events = []
activity_log = []

for uid in range(1, N_USERS + 1):
    channel = random.choices(CHANNELS, weights=[0.30, 0.20, 0.18, 0.22, 0.10])[0]
    tier = random.choices(CITY_TIERS, weights=[0.45, 0.35, 0.20])[0]
    device = random.choices(DEVICES, weights=[0.78, 0.22])[0]
    # A/B test: 50/50 split on onboarding flow (variant B = simplified KYC flow)
    ab_group = random.choice(["Control", "Variant_B"])

    install_date = random_date(START_DATE, END_DATE - timedelta(days=30))

    users.append({
        "user_id": uid, "channel": channel, "city_tier": tier,
        "device": device, "ab_group": ab_group,
        "install_date": install_date.date().isoformat()
    })

    # Channel/tier modifiers (referral & organic convert better; tier1 converts better)
    channel_mod = {"Organic": 1.10, "Referral": 1.18, "Paid Social": 0.90, "Google Ads": 0.95, "Affiliate": 0.85}[channel]
    tier_mod = {"Tier 1": 1.12, "Tier 2": 1.0, "Tier 3": 0.85}[tier]
    # Variant_B gets a genuine KYC-step lift (this is the effect we want the A/B test to detect)
    ab_mod_kyc = 1.22 if ab_group == "Variant_B" else 1.0

    current_date = install_date
    reached = {"App Install"}
    funnel_events.append({"user_id": uid, "step": "App Install", "event_date": current_date.date().isoformat()})

    # Signup
    p = BASE_CONV["App Install->Signup"] * channel_mod * tier_mod
    if random.random() < min(p, 0.97):
        current_date += timedelta(hours=random.randint(1, 48))
        funnel_events.append({"user_id": uid, "step": "Signup", "event_date": current_date.date().isoformat()})
        reached.add("Signup")

        # KYC
        p = BASE_CONV["Signup->KYC Verification"] * channel_mod * tier_mod * ab_mod_kyc
        if random.random() < min(p, 0.97):
            current_date += timedelta(hours=random.randint(1, 72))
            funnel_events.append({"user_id": uid, "step": "KYC Verification", "event_date": current_date.date().isoformat()})
            reached.add("KYC Verification")

            # First Transaction
            p = BASE_CONV["KYC Verification->First Transaction"] * channel_mod * tier_mod
            if random.random() < min(p, 0.97):
                current_date += timedelta(days=random.randint(1, 5))
                funnel_events.append({"user_id": uid, "step": "First Transaction", "event_date": current_date.date().isoformat()})
                reached.add("First Transaction")

                # Loan Application
                p = BASE_CONV["First Transaction->Loan Application"] * channel_mod * tier_mod
                if random.random() < min(p, 0.95):
                    current_date += timedelta(days=random.randint(1, 14))
                    funnel_events.append({"user_id": uid, "step": "Loan Application", "event_date": current_date.date().isoformat()})
                    reached.add("Loan Application")

                    # Loan Approved
                    p = BASE_CONV["Loan Application->Loan Approved"] * tier_mod
                    if random.random() < min(p, 0.95):
                        current_date += timedelta(days=random.randint(1, 7))
                        funnel_events.append({"user_id": uid, "step": "Loan Approved", "event_date": current_date.date().isoformat()})
                        reached.add("Loan Approved")

    # Weekly activity log for retained users (for cohort retention) - only for users who signed up
    if "Signup" in reached:
        signup_dt = install_date
        # activity probability decays over weeks, better for engaged (transaction) users
        base_retention = 0.60 if "First Transaction" in reached else 0.30
        for week in range(0, 20):
            week_date = signup_dt + timedelta(weeks=week)
            if week_date > END_DATE:
                break
            decay = base_retention * (0.85 ** week)
            if random.random() < decay:
                activity_log.append({
                    "user_id": uid,
                    "activity_date": week_date.date().isoformat(),
                    "week_number": week
                })

# Write CSVs
with open("/home/claude/proj/data/users.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["user_id", "channel", "city_tier", "device", "ab_group", "install_date"])
    w.writeheader()
    w.writerows(users)

with open("/home/claude/proj/data/funnel_events.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["user_id", "step", "event_date"])
    w.writeheader()
    w.writerows(funnel_events)

with open("/home/claude/proj/data/activity_log.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["user_id", "activity_date", "week_number"])
    w.writeheader()
    w.writerows(activity_log)

print(f"Users: {len(users)}, Funnel events: {len(funnel_events)}, Activity rows: {len(activity_log)}")
