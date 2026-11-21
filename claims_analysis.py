import json
import pandas as pd

claims_json = '''
[
 {"claim_id":"C001","payer":"Aetna","service_date":"2024-01-05","cpt_code":"99213","billed":150,"allowed":110,"paid":90,"patient_resp":20,"status":"paid","denial_reason":null},
 {"claim_id":"C002","payer":"Aetna","service_date":"2024-01-12","cpt_code":"99214","billed":220,"allowed":160,"paid":130,"patient_resp":30,"status":"paid","denial_reason":null},
 {"claim_id":"C003","payer":"Aetna","service_date":"2024-01-20","cpt_code":"80053","billed":80,"allowed":0,"paid":0,"patient_resp":0,"status":"denied","denial_reason":"Missing prior authorization"},
 {"claim_id":"C004","payer":"Medicare","service_date":"2024-01-08","cpt_code":"99213","billed":150,"allowed":95,"paid":76,"patient_resp":19,"status":"paid","denial_reason":null},
 {"claim_id":"C005","payer":"Medicare","service_date":"2024-01-15","cpt_code":"71046","billed":300,"allowed":140,"paid":112,"patient_resp":28,"status":"paid","denial_reason":null},
 {"claim_id":"C006","payer":"Medicare","service_date":"2024-02-02","cpt_code":"99215","billed":350,"allowed":180,"paid":144,"patient_resp":36,"status":"paid","denial_reason":null},
 {"claim_id":"C007","payer":"BlueCross","service_date":"2024-01-10","cpt_code":"99213","billed":150,"allowed":120,"paid":100,"patient_resp":20,"status":"paid","denial_reason":null},
 {"claim_id":"C008","payer":"BlueCross","service_date":"2024-01-25","cpt_code":"93000","billed":120,"allowed":70,"paid":50,"patient_resp":20,"status":"paid","denial_reason":null},
 {"claim_id":"C009","payer":"BlueCross","service_date":"2024-02-05","cpt_code":"99214","billed":220,"allowed":0,"paid":0,"patient_resp":0,"status":"denied","denial_reason":"Duplicate claim"},
 {"claim_id":"C010","payer":"BlueCross","service_date":"2024-02-14","cpt_code":"99213","billed":150,"allowed":120,"paid":100,"patient_resp":20,"status":"paid","denial_reason":null},
 {"claim_id":"C011","payer":"Aetna","service_date":"2024-02-10","cpt_code":"99214","billed":220,"allowed":160,"paid":130,"patient_resp":30,"status":"paid","denial_reason":null},
 {"claim_id":"C012","payer":"Aetna","service_date":"2024-02-18","cpt_code":"85025","billed":60,"allowed":null,"paid":null,"patient_resp":null,"status":"pending","denial_reason":null},
 {"claim_id":"C013","payer":"Medicare","service_date":"2024-02-20","cpt_code":"99213","billed":150,"allowed":95,"paid":76,"patient_resp":19,"status":"paid","denial_reason":null},
 {"claim_id":"C014","payer":"BlueCross","service_date":"2024-02-25","cpt_code":"71046","billed":300,"allowed":140,"paid":100,"patient_resp":30,"status":"paid","denial_reason":null},
 {"claim_id":"C015","payer":"Medicare","service_date":"2024-01-30","cpt_code":"99214","billed":200,"allowed":null,"paid":null,"patient_resp":null,"status":"pending","denial_reason":null},
 {"claim_id":"C016","payer":"Aetna","service_date":"2023-12-15","cpt_code":"99213","billed":180,"allowed":null,"paid":null,"patient_resp":null,"status":"pending","denial_reason":null}
]
'''

df = pd.DataFrame(json.loads(claims_json))
df["service_date"] = pd.to_datetime(df["service_date"])

# 1. Overview by status
print("CLAIMS BY STATUS")
print(df.groupby("status")["billed"].agg(["count", "sum"]))

# 2. Integrity check on paid claims
paid_only = df[df["status"] == "paid"].copy()
imbalance = (paid_only["allowed"] - paid_only["paid"] - paid_only["patient_resp"]).round(2)
print("\nCLAIMS THAT DON'T BALANCE")
print(paid_only[imbalance.abs() > 0.01][["claim_id", "allowed", "paid", "patient_resp"]])

# 3. Financial summary by payer (paid claims only)
by_payer = paid_only.groupby("payer").agg(
    claims=("claim_id", "count"),
    billed=("billed", "sum"),
    allowed=("allowed", "sum"),
    paid=("paid", "sum"),
    patient_resp=("patient_resp", "sum"),
)
by_payer["adjustment"] = by_payer["billed"] - by_payer["allowed"]
by_payer["paid_pct_of_billed"] = (by_payer["paid"] / by_payer["billed"] * 100).round(1)
print("\nFINANCIAL SUMMARY BY PAYER")
print(by_payer)

# 4. Denials
df["denied"] = df["status"] == "denied"
denials = df.groupby("payer").agg(
    claims=("claim_id", "count"),
    denied=("denied", "sum"),
    denial_rate=("denied", "mean"),
)
denials["denial_rate"] = (denials["denial_rate"] * 100).round(1)
print("\nDENIALS")
print(denials)
print(df["denial_reason"].value_counts())

# 5. Monthly paid amounts
paid_only["month"] = paid_only["service_date"].dt.strftime("%Y-%m")
print("\nPAID BY MONTH OF SERVICE")
print(paid_only.pivot_table(index="payer", columns="month", values="paid", aggfunc="sum", fill_value=0))

# 6. Aging of pending claims
reference_date = pd.Timestamp("2024-03-15")
pending = df[df["status"] == "pending"].copy()
pending["days_open"] = (reference_date - pending["service_date"]).dt.days
pending["aging"] = pd.cut(
    pending["days_open"],
    bins=[-1, 30, 60, 90, 10000],
    labels=["0-30", "31-60", "61-90", "90+"]
)
print("\nPENDING CLAIMS AGING")
print(pending.groupby("aging", observed=False)["billed"].sum())

# 7. Reconcile with payments received
remittances = pd.DataFrame({
    "payer": ["Aetna", "Medicare", "BlueCross"],
    "received": [350, 400, 360]
})
recon = pd.merge(by_payer[["paid"]].reset_index(), remittances, on="payer", how="outer")
recon["difference"] = recon["received"] - recon["paid"]


def classify(d):
    if abs(d) < 0.01:
        return "MATCH"
    elif d < 0:
        return "SHORT-PAID"
    else:
        return "OVER-PAID"


recon["status"] = recon["difference"].apply(classify)
print("\nRECONCILIATION: CLAIMS vs MONEY RECEIVED")
print(recon)

recon[recon["status"] != "MATCH"].to_csv("claims_exceptions.csv", index=False)