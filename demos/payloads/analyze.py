# Runs INSIDE the sandbox (demo 02).
import matplotlib

matplotlib.use("Agg")
import pandas as pd

df = pd.read_csv("/data/sales.csv")
pivot = df.pivot_table(index="month", columns="sales_region", values="net_revenue_usd")
growth = (pivot.iloc[-1] / pivot.iloc[0] - 1).sort_values(ascending=False)

print("Revenue growth Jan → Dec by region:")
for region, g in growth.items():
    print(f"  {region:<6} {g:+.1%}")

ax = pivot.plot(title="Monthly net revenue by region", figsize=(8, 4.5))
ax.set_ylabel("USD")
ax.figure.tight_layout()
ax.figure.savefig("/work/chart.png", dpi=120)
