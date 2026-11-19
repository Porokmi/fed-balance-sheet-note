"""Fed balance sheet, reserves and money-market pressure, 2019 to today.

Downloads public FRED series (no API key) and draws a two-panel chart:
  1. Fed total assets, bank reserves, ON RRP and the Treasury General Account ($ trillions)
  2. SOFR minus interest on reserve balances (basis points, 20-day average)
"""
import io
import urllib.request

import matplotlib.pyplot as plt
import pandas as pd

SERIES = {
    "WALCL": "Fed total assets",
    "WRESBAL": "Bank reserves",
    "RRPONTSYD": "Overnight reverse repo (ON RRP)",
    "WTREGEN": "Treasury General Account (TGA)",
    "SOFR": "SOFR",
    "IORB": "IORB",
}
START = "2019-01-01"


def fred(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={START}"
    with urllib.request.urlopen(url, timeout=30) as r:
        df = pd.read_csv(io.BytesIO(r.read()), index_col=0, parse_dates=True)
    return pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()


def main() -> None:
    d = {k: fred(k) for k in SERIES}
    # $ millions (weekly) and $ billions (daily RRP) -> $ trillions
    assets = d["WALCL"] / 1e6
    reserves = d["WRESBAL"] / 1e6
    tga = d["WTREGEN"] / 1e6
    rrp = d["RRPONTSYD"] / 1e3
    spread = ((d["SOFR"] - d["IORB"]).dropna() * 100).rolling(20).mean()

    pd.concat([assets, reserves, rrp.resample("W-WED").mean(), tga], axis=1,
              keys=["assets_tn", "reserves_tn", "rrp_tn", "tga_tn"]).to_csv("balance_sheet_weekly.csv")
    spread.to_frame("sofr_minus_iorb_bp_20d").to_csv("sofr_iorb_spread.csv")

    plt.rcParams.update({"font.family": "serif", "font.size": 9})
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6.2), sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    lines = [(assets, "Fed total assets", "#1b3a5c", "-"),
             (reserves, "Bank reserves", "#2f7d6d", "-"),
             (rrp, "ON RRP", "#b5651d", "-"),
             (tga, "Treasury General Account", "#7a7a7a", "--")]
    for s, label, color, ls in lines:
        ax1.plot(s.index, s.values, color=color, lw=1.6, ls=ls)
        ax1.annotate(f"{label}  ${s.iloc[-1]:.2f}T", (s.index[-1], s.iloc[-1]),
                     xytext=(6, 0), textcoords="offset points", va="center", color=color, fontsize=8)
    ax1.axvspan(pd.Timestamp("2022-06-01"), pd.Timestamp("2025-12-01"), color="#e8e8e8", zorder=0)
    ax1.text(pd.Timestamp("2022-07-01"), 9.3, "Quantitative tightening", fontsize=8, color="#555")
    ax1.set_ylabel("$ trillions")
    ax1.set_ylim(0, 9.8)
    ax1.set_title("The buffer is gone: ON RRP drained, reserves now absorb every shift", loc="left", fontsize=10)

    ax2.axhline(0, color="#999", lw=0.8)
    ax2.plot(spread.index, spread.values, color="#8c2d2d", lw=1.4)
    ax2.set_ylabel("SOFR − IORB (bp)")
    ax2.set_title("Repo pressure: SOFR above interest on reserves means cash is getting scarce", loc="left", fontsize=10)

    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e5e5e5", lw=0.6)
    fig.text(0.01, 0.005, "Source: FRED (WALCL, WRESBAL, RRPONTSYD, WTREGEN, SOFR, IORB). "
             "\nSpread is a 20-day average (IORB begins July 2021). QT shading: June 2022 to December 2025.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.02, 0.86, 1))
    fig.savefig("fed_balance_sheet.png", dpi=300)
    print("saved; latest:", assets.index[-1].date(), round(assets.iloc[-1], 2), round(reserves.iloc[-1], 2),
          round(rrp.iloc[-1], 4), round(tga.iloc[-1], 2), round(spread.iloc[-1], 1))


if __name__ == "__main__":
    main()
