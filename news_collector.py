"""
AI News Collector Bot — Powered by Claude API
Usage: python news_collector.py
"""

import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET

# ─── SETTINGS ──────────────────────────────────────────────
RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US",
]

CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_ARTICLES = 10
# ────────────────────────────────────────────────────────────


def fetch_rss(url: str) -> list[dict]:
    """Fetch and parse RSS feed. Returns list of articles."""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        articles = []
        for item in root.findall(".//item")[:3]:
            title = item.findtext("title", "")
            desc  = item.findtext("description", "")
            link  = item.findtext("link", "")
            date  = item.findtext("pubDate", "")
            if title:
                articles.append({
                    "title": title,
                    "description": desc[:300] if desc else "",
                    "link": link,
                    "date": date,
                })
        return articles
    except Exception as e:
        print(f"  [!] Failed to fetch {url}: {e}")
        return []


def analyze_with_claude(articles: list[dict]) -> dict:
    """Send articles to Claude API for sentiment analysis and summary."""

    articles_text = "\n\n".join([
        f"Title: {a['title']}\nDescription: {a['description']}"
        for a in articles
    ])

    prompt = f"""You are a financial news analyst. Analyze the following news articles and return a JSON response.

Articles:
{articles_text}

Return ONLY valid JSON in this exact format:
{{
  "overall_sentiment": "BULLISH" or "BEARISH" or "NEUTRAL",
  "sentiment_score": (float between -1.0 and 1.0),
  "key_themes": ["theme1", "theme2", "theme3"],
  "market_impact": "HIGH" or "MEDIUM" or "LOW",
  "summary": "2-3 sentence summary of the news",
  "top_story": "The single most important headline",
  "trading_signal": "BUY" or "SELL" or "HOLD",
  "confidence": (integer 0-100)
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json"},
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    if response.status_code == 200:
        data = response.json()
        text = data["content"][0]["text"].strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    else:
        return {
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "key_themes": [],
            "market_impact": "LOW",
            "summary": "Analysis unavailable.",
            "top_story": "",
            "trading_signal": "HOLD",
            "confidence": 0
        }


def print_report(articles: list[dict], analysis: dict) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sentiment_icon = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(
        analysis.get("overall_sentiment", "NEUTRAL"), "🟡"
    )
    signal_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(
        analysis.get("trading_signal", "HOLD"), "🟡"
    )

    print("\n" + "=" * 65)
    print(f"   🤖  AI NEWS INTELLIGENCE REPORT — {now}")
    print("=" * 65)
    print(f"\n{sentiment_icon} Overall Sentiment : {analysis.get('overall_sentiment')}")
    print(f"   Sentiment Score  : {analysis.get('sentiment_score', 0):.2f}")
    print(f"   Market Impact    : {analysis.get('market_impact')}")
    print(f"{signal_icon} Trading Signal   : {analysis.get('trading_signal')}  "
          f"(Confidence: {analysis.get('confidence')}%)")

    print("\n─── Key Themes ─────────────────────────────────────────────")
    for theme in analysis.get("key_themes", []):
        print(f"  • {theme}")

    print("\n─── Top Story ──────────────────────────────────────────────")
    print(f"  {analysis.get('top_story', 'N/A')}")

    print("\n─── AI Summary ─────────────────────────────────────────────")
    print(f"  {analysis.get('summary', 'N/A')}")

    print("\n─── Latest Headlines ───────────────────────────────────────")
    for i, a in enumerate(articles[:5], 1):
        print(f"  {i}. {a['title']}")

    print("\n" + "=" * 65)
    print("⚠️  This is not financial advice. Always do your own research.")
    print("=" * 65 + "\n")


def main():
    print("\n⏳ Fetching latest financial news...")
    all_articles = []
    for feed in RSS_FEEDS:
        articles = fetch_rss(feed)
        all_articles.extend(articles)
        print(f"  ✓ Fetched {len(articles)} articles")

    all_articles = all_articles[:MAX_ARTICLES]

    if not all_articles:
        print("  [!] No articles found. Check your internet connection.")
        return

    print(f"\n🤖 Analyzing {len(all_articles)} articles with Claude AI...")
    analysis = analyze_with_claude(all_articles)

    print_report(all_articles, analysis)


if __name__ == "__main__":
    main()
