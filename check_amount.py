import pandas as pd

df = pd.read_csv("/Users/hyunsangryu/Downloads/Open_Market_Order_(OMO)_Charges_20260901.csv")

col = "OMOAwardAmount"

# 쉼표 제거 후 숫자 변환
df[col] = df[col].astype(str).str.replace(",", "", regex=False)
df[col] = pd.to_numeric(df[col], errors="coerce")

print(df[col].describe())
print()
print("변환 실패(NaN)한 행 개수:", df[col].isna().sum())
print()
print("25%:", df[col].quantile(0.25))
print("50%(중앙값):", df[col].quantile(0.50))
print("75%:", df[col].quantile(0.75))
print("90%:", df[col].quantile(0.90))
print("99%:", df[col].quantile(0.99))
print()
print("$500 이하 건수:", (df[col] <= 500).sum())
print("$500~$5,000 건수:", ((df[col] > 500) & (df[col] <= 5000)).sum())
print("$5,000~$50,000 건수:", ((df[col] > 5000) & (df[col] <= 50000)).sum())
print("$50,000 초과 건수:", (df[col] > 50000).sum())