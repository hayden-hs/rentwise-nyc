import pandas as pd

litigation = pd.read_csv("/Users/hyunsangryu/Downloads/Housing_Litigations_20260901.csv", low_memory=False)
charges = pd.read_csv("/Users/hyunsangryu/Downloads/Open_Market_Order_(OMO)_Charges_20260901.csv", low_memory=False)

print("=== Litigation CaseStatus 실제 값 분포 ===")
print(litigation["CaseStatus"].value_counts())
print()
print("=== Charges OMOStatusReason 실제 값 분포 ===")
print(charges["OMOStatusReason"].value_counts())