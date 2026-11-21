# Healthcare Claims Analysis

A Python script that analyzes health insurance claims the way a revenue cycle team would: what was billed, what was paid, what was denied, what is still pending, and whether the money received matches what the payers owe.

## How it works
1. **Status overview:** counts claims and billed dollars by status (paid, denied, pending)
2. **Integrity check:** for paid claims, the allowed amount should equal the insurer's payment plus the patient's share, and any claim that doesn't balance is listed
3. **Financial summary by payer:** billed, allowed, paid, patient responsibility, the adjustment (billed minus allowed), and paid as a percentage of billed
4. **Denials:** denial rate per payer (denied claims divided by all claims, pending included) and a count of denial reasons
5. **Monthly view:** a pivot table of paid amounts by payer and month of service
6. **Aging of pending claims:** groups open claims into 0-30, 31-60, 61-90, and 90+ day buckets
7. **Reconciliation:** compares what the claims say each payer paid against the payments actually received, and classifies each payer as MATCH, SHORT-PAID, or OVER-PAID
8. Exports the reconciliation exceptions to CSV

## Example results (sample data)

16 claims, $3,000 billed: 11 paid ($2,260), 2 denied ($300), 3 pending ($440).

| Payer | Claims | Billed | Allowed | Paid | Patient | Adjustment | Paid % of billed |
|-------|--------|--------|---------|------|---------|------------|------------------|
| Aetna | 3 | 590 | 430 | 350 | 80 | 160 | 59.3% |
| BlueCross | 4 | 720 | 450 | 350 | 90 | 270 | 48.6% |
| Medicare | 4 | 950 | 510 | 408 | 102 | 440 | 42.9% |

- **Doesn't balance:** claim C014 (allowed 140, but paid 100 + patient 30 = 130)
- **Denials:** Aetna 1 of 6 (missing prior authorization), BlueCross 1 of 5 (duplicate claim), Medicare 0 of 5
- **Pending aging** (as of 2024-03-15): 0-30 days $60, 31-60 days $200, 61-90 days $0, 90+ days $180
- **Reconciliation:** Aetna matches, BlueCross over-paid by $10, Medicare short-paid by $8

## How to run
```bash
python claims_analysis.py
```
This creates `claims_exceptions.csv` in the same folder when run.

## What I learned
- Healthcare billing basics: billed vs. allowed vs. paid vs. patient responsibility, denials, and accounts receivable aging
- Using named aggregation: `.agg(claims=("claim_id", "count"), ...)`
- Building an integrity check (allowed − paid − patient share should be zero) and rounding to avoid floating-point noise
- Taking the `.mean()` of a True/False column to get a rate
- Using `pd.cut()` with bins and labels to group values into aging buckets, and `observed=False` to keep empty buckets visible
- Using `pivot_table()` with `fill_value=0` and `.dt.strftime()` to build monthly views
- Reconciling two sources with an outer merge and classifying differences with a tolerance
- Using `.copy()` before adding columns to a filtered DataFrame

## Limitations
- All data is fictional. Real claims contain protected health information (HIPAA) and must never be committed to a public repository.
- The denial rate counts pending claims in the denominator, which lowers the rate until those claims are resolved.
- Aging is measured from the service date. Real accounts-receivable aging usually starts from the date the claim was submitted.
- The payments received are hard-coded sample values. Real data comes from payer remittance files.
- Money is stored as floating-point numbers. Production systems use exact decimals or whole cents.

## Dependencies
Requires pandas:
```bash
pip install pandas
```
