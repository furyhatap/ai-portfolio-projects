"""
Automated Stock Analysis PDF Report Generator
Usage: pip install yfinance pandas fpdf2
       python report_generator.py
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from fpdf import FPDF


# ─── SETTINGS ──────────────────────────────────────────────
STOCKS  = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]
PERIOD  = "3mo"
OUTPUT  = "stock_report.pdf"
# ────────────────────────────────────────────────────────────


def calculate_rsi(price: pd.Series, period: int = 14) -> float:
    delta = price.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def fetch_stock_data(symbol: str) -> dict:
    df = yf.download(symbol, period=PERIOD, interval="1d",
                     progress=False, auto_adjust=True)
    if df.empty or len(df) < 50:
        return None

    close = df["Close"].squeeze()
    last_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    change_pct = ((last_price - prev_price) / prev_price) * 100

    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1])
    rsi  = calculate_rsi(close)

    high_52w = float(close.max())
    low_52w  = float(close.min())

    if rsi < 30 and ma20 > ma50:
        signal = "BUY"
    elif rsi > 70 or ma20 < ma50:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "symbol":     symbol,
        "price":      last_price,
        "change_pct": round(change_pct, 2),
        "rsi":        rsi,
        "ma20":       round(ma20, 2),
        "ma50":       round(ma50, 2),
        "high_52w":   round(high_52w, 2),
        "low_52w":    round(low_52w, 2),
        "signal":     signal,
    }


class StockReportPDF(FPDF):

    def header(self):
        self.set_fill_color(25, 50, 95)
        self.rect(0, 0, 210, 28, "F")
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.set_y(8)
        self.cell(0, 10, "US STOCK ANALYSIS REPORT", align="C", ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')}", align="C", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10,
                  f"Page {self.page_no()}  |  NewsIntel AI  |  Not financial advice",
                  align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(240, 244, 250)
        self.set_text_color(25, 50, 95)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def summary_box(self, stocks_data: list[dict]):
        self.section_title("Executive Summary")
        buy_count  = sum(1 for s in stocks_data if s["signal"] == "BUY")
        sell_count = sum(1 for s in stocks_data if s["signal"] == "SELL")
        hold_count = sum(1 for s in stocks_data if s["signal"] == "HOLD")

        self.set_font("Helvetica", "", 11)
        self.cell(0, 7, f"  Total stocks analyzed: {len(stocks_data)}", ln=True)
        self.cell(0, 7, f"  BUY signals:  {buy_count}", ln=True)
        self.cell(0, 7, f"  SELL signals: {sell_count}", ln=True)
        self.cell(0, 7, f"  HOLD signals: {hold_count}", ln=True)
        self.ln(4)

    def stock_table(self, stocks_data: list[dict]):
        self.section_title("Stock Analysis Table")

        headers = ["Symbol", "Price ($)", "Change %", "RSI", "MA20", "MA50", "Signal"]
        widths  = [22, 28, 24, 18, 28, 28, 22]

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(25, 50, 95)
        self.set_text_color(255, 255, 255)
        for h, w in zip(headers, widths):
            self.cell(w, 8, h, border=1, align="C", fill=True)
        self.ln()

        self.set_font("Helvetica", "", 9)
        for i, s in enumerate(stocks_data):
            fill = i % 2 == 0
            self.set_fill_color(248, 250, 253) if fill else self.set_fill_color(255, 255, 255)
            self.set_text_color(0, 0, 0)

            signal_color = {"BUY": (34, 139, 34), "SELL": (200, 30, 30), "HOLD": (180, 130, 0)}
            change_color = (34, 139, 34) if s["change_pct"] >= 0 else (200, 30, 30)

            self.cell(22, 7, s["symbol"],           border=1, align="C", fill=fill)
            self.cell(28, 7, f"{s['price']:.2f}",   border=1, align="C", fill=fill)

            self.set_text_color(*change_color)
            self.cell(24, 7, f"{s['change_pct']:+.2f}%", border=1, align="C", fill=fill)

            self.set_text_color(0, 0, 0)
            self.cell(18, 7, str(s["rsi"]),          border=1, align="C", fill=fill)
            self.cell(28, 7, f"{s['ma20']:.2f}",     border=1, align="C", fill=fill)
            self.cell(28, 7, f"{s['ma50']:.2f}",     border=1, align="C", fill=fill)

            self.set_text_color(*signal_color.get(s["signal"], (0, 0, 0)))
            self.cell(22, 7, s["signal"],             border=1, align="C", fill=fill)
            self.set_text_color(0, 0, 0)
            self.ln()

        self.ln(6)

    def stock_details(self, s: dict):
        self.section_title(f"  {s['symbol']} — Detailed Analysis")
        self.set_font("Helvetica", "", 10)

        rows = [
            ("Current Price",   f"${s['price']:.2f}"),
            ("Daily Change",    f"{s['change_pct']:+.2f}%"),
            ("RSI (14)",        str(s["rsi"])),
            ("MA20",            f"${s['ma20']:.2f}"),
            ("MA50",            f"${s['ma50']:.2f}"),
            ("52W High",        f"${s['high_52w']:.2f}"),
            ("52W Low",         f"${s['low_52w']:.2f}"),
            ("Signal",          s["signal"]),
        ]

        for label, value in rows:
            self.set_font("Helvetica", "B", 10)
            self.cell(50, 7, f"  {label}:", ln=False)
            self.set_font("Helvetica", "", 10)
            self.cell(0, 7, value, ln=True)

        self.ln(4)


def generate_pdf(stocks_data: list[dict]):
    pdf = StockReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.summary_box(stocks_data)
    pdf.stock_table(stocks_data)

    for s in stocks_data:
        pdf.stock_details(s)

    pdf.output(OUTPUT)
    print(f"\n✅ PDF report saved: {OUTPUT}")


def main():
    print("\n⏳ Fetching stock data...")
    stocks_data = []
    for symbol in STOCKS:
        data = fetch_stock_data(symbol)
        if data:
            stocks_data.append(data)
            print(f"  ✓ {symbol}: ${data['price']:.2f}  [{data['signal']}]")
        else:
            print(f"  ✗ {symbol}: Failed to fetch")

    if not stocks_data:
        print("\n[!] No data available. Check internet connection.")
        return

    print(f"\n📄 Generating PDF report for {len(stocks_data)} stocks...")
    generate_pdf(stocks_data)


if __name__ == "__main__":
    main()
