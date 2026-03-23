#!/usr/bin/env python3
"""
Aggregate recent AI news from RSS feeds and free public APIs.

The script keeps the original class name and CLI behavior so scheduled jobs can
continue to call it unchanged.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import feedparser
import requests


RSS_AI_KEYWORDS = ("ai", "人工智能", "chatgpt", "gpt", "大模型", "智能", "llm", "agent")
RELEVANT_KEYWORDS = (
    "chatgpt",
    "claude",
    "gemini",
    "gpt",
    "ai agent",
    "llm",
    "大模型",
    "人工智能",
    "产品",
    "app",
    "应用",
    "工具",
    "startup",
    "创业",
    "融资",
    "funding",
    "release",
    "发布",
    "launch",
    "上线",
    "model",
)
RSS_SOURCES = {
    "36kr": ("36氪", "https://36kr.com/feed", 7, True),
    "huggingface": ("HuggingFace", "https://huggingface.co/blog/feed.xml", 5, False),
    "techcrunch": (
        "TechCrunch",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        5,
        False,
    ),
    "verge": ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", 5, False),
}
SUBSTACK_FEEDS = (
    ("https://www.aitidbits.ai/feed", "AI Tidbits"),
    ("https://www.therundown.ai/feed", "The Rundown AI"),
    ("https://substack.com/api/v1/publication/133012/sitemap_feed.xml", "Ben's Bites"),
)
HN_KEYWORDS = ("AI", "LLM", "ChatGPT")
REDDIT_SUBREDDITS = ("MachineLearning", "artificial", "ChatGPT")
MASTODON_KEYWORDS = ("AI", "ChatGPT")
SOURCE_SWITCHES = {
    "36kr": True,
    "huggingface": True,
    "techcrunch": True,
    "verge": True,
    "hackernews": True,
    "reddit": True,
    "mastodon": False,
    "substack": True,
}


class AINewsAggregator:
    """Collect news with conservative recency filtering and consistent shaping."""

    def __init__(self) -> None:
        self.current_year = datetime.now().year
        self.min_year = self.current_year - 1
        self.output_dir = Path(__file__).resolve().parent.parent / "验证输出"
        self.sources = dict(SOURCE_SWITCHES)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "OpenClaw/1.0 (AI News Aggregator)"})

    def _is_recent_year(self, year: int) -> bool:
        """Keep only the current year and the immediately previous year."""
        return year >= self.min_year

    def _is_recent_iso(self, value: str) -> bool:
        """Parse an ISO timestamp defensively because public feeds are inconsistent."""
        try:
            return self._is_recent_year(datetime.fromisoformat(value.replace("Z", "+00:00")).year)
        except ValueError:
            return True

    def _strip_html(self, value: str) -> str:
        """Normalize HTML-heavy feed content into plain text snippets."""
        return re.sub(r"<[^<]+?>", "", value or "")

    def _parse_rss(
        self,
        url: str,
        source: str,
        *,
        limit: int,
        ai_filter: bool = False,
    ) -> list[dict[str, Any]]:
        """Parse RSS entries into the shared output schema."""
        news: list[dict[str, Any]] = []
        feed = feedparser.parse(url)
        for entry in feed.entries[: limit * 2]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            published = entry.get("published", "")

            if ai_filter:
                lowered = f"{title}{summary}".lower()
                if not any(keyword in lowered for keyword in RSS_AI_KEYWORDS):
                    continue

            try:
                parsed = feedparser._parse_date(published)
                if parsed and not self._is_recent_year(parsed.tm_year):
                    continue
            except Exception:  # noqa: BLE001
                pass

            news.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": published,
                    "summary": self._strip_html(summary)[:200],
                    "source": source,
                }
            )
            if len(news) >= limit:
                break
        return news

    def _fetch_rss_source(self, key: str) -> list[dict[str, Any]]:
        """Wrap RSS fetching with the script's original human-readable logging."""
        label, url, limit, ai_filter = RSS_SOURCES[key]
        print(f"📰 抓取{label}...")
        try:
            news = self._parse_rss(url, label, limit=limit, ai_filter=ai_filter)
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ {label}: {exc}")
            return []
        print(f"  ✅ {label}: {len(news)} 条")
        return news

    def _get_json(self, url: str, **kwargs) -> dict[str, Any]:
        """Centralize JSON requests so timeouts and error handling stay uniform."""
        response = self.session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response.json()

    def fetch_36kr(self) -> list[dict[str, Any]]:
        return self._fetch_rss_source("36kr")

    def fetch_huggingface(self) -> list[dict[str, Any]]:
        return self._fetch_rss_source("huggingface")

    def fetch_techcrunch_ai(self) -> list[dict[str, Any]]:
        return self._fetch_rss_source("techcrunch")

    def fetch_verge_ai(self) -> list[dict[str, Any]]:
        return self._fetch_rss_source("verge")

    def fetch_substack_ai(self) -> list[dict[str, Any]]:
        """Fetch multiple high-signal Substack feeds through the same RSS parser."""
        print("📰 抓取Substack AI...")
        news: list[dict[str, Any]] = []
        for feed_url, name in SUBSTACK_FEEDS:
            try:
                news.extend(self._parse_rss(feed_url, f"Substack·{name}", limit=2))
                time.sleep(0.5)
            except Exception:  # noqa: BLE001
                continue
        print(f"  ✅ Substack: {len(news)} 条")
        return news

    def fetch_hackernews_ai(self) -> list[dict[str, Any]]:
        """Fetch Hacker News stories from the free Algolia mirror."""
        print("📰 抓取Hacker News AI...")
        news: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            for keyword in HN_KEYWORDS:
                payload = self._get_json(
                    "https://hn.algolia.com/api/v1/search",
                    params={
                        "query": keyword,
                        "tags": "story",
                        "numericFilters": "points>20,created_at_i>1704067200",
                        "hitsPerPage": 5,
                    },
                )
                for hit in payload.get("hits", []):
                    title = hit.get("title", "")
                    created_at = hit.get("created_at", "")
                    if not title or title in seen or not self._is_recent_iso(created_at):
                        continue
                    seen.add(title)
                    news.append(
                        {
                            "title": title,
                            "link": hit.get("url")
                            or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            "published": created_at,
                            "summary": f"{hit.get('points', 0)}分 | {hit.get('num_comments', 0)}评论",
                            "source": "Hacker News",
                            "points": hit.get("points", 0),
                        }
                    )
                time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Hacker News: {exc}")
            return []

        news.sort(key=lambda item: item.get("points", 0), reverse=True)
        result = news[:8]
        print(f"  ✅ Hacker News: {len(result)} 条")
        return result

    def fetch_reddit_ai(self) -> list[dict[str, Any]]:
        """Fetch Reddit hot posts from AI-related subreddits without authentication."""
        print("📰 抓取Reddit AI...")
        news: list[dict[str, Any]] = []
        seen: set[str] = set()
        for subreddit in REDDIT_SUBREDDITS:
            try:
                payload = self._get_json(
                    f"https://www.reddit.com/r/{subreddit}/hot.json",
                    params={"limit": 5},
                )
                for post in payload.get("data", {}).get("children", []):
                    data = post.get("data", {})
                    title = data.get("title", "")
                    score = data.get("score", 0)
                    created_utc = data.get("created_utc", 0)
                    if score < 50 or not title or title in seen:
                        continue
                    if created_utc and not self._is_recent_year(datetime.fromtimestamp(created_utc).year):
                        continue
                    seen.add(title)
                    news.append(
                        {
                            "title": title,
                            "link": data.get("url", ""),
                            "published": datetime.fromtimestamp(created_utc).isoformat(),
                            "summary": f"r/{subreddit} | {score}分 | {data.get('num_comments', 0)}评论",
                            "source": f"Reddit·r/{subreddit}",
                            "points": score,
                        }
                    )
                time.sleep(1)
            except Exception as exc:  # noqa: BLE001
                print(f"    Reddit·r/{subreddit}: {exc}")
        news.sort(key=lambda item: item.get("points", 0), reverse=True)
        result = news[:8]
        print(f"  ✅ Reddit: {len(result)} 条")
        return result

    def fetch_mastodon_ai(self) -> list[dict[str, Any]]:
        """Fetch public Mastodon search results and keep only posts with engagement."""
        print("📰 抓取Mastodon AI...")
        news: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            for keyword in MASTODON_KEYWORDS:
                payload = self._get_json(
                    "https://mastodon.social/api/v2/search",
                    params={"q": keyword, "type": "statuses", "limit": 10},
                )
                for status in payload.get("statuses", []):
                    favs = status.get("favourites_count", 0)
                    boosts = status.get("reblogs_count", 0)
                    content = self._strip_html(status.get("content", ""))
                    if favs + boosts < 3 or len(content) < 50 or content in seen:
                        continue
                    seen.add(content)
                    account = status.get("account", {})
                    news.append(
                        {
                            "title": f"@{account.get('acct', '')}: {content[:80]}...",
                            "link": status.get("url", ""),
                            "published": status.get("created_at", ""),
                            "summary": content[:200],
                            "source": "Mastodon",
                            "points": favs + boosts,
                        }
                    )
                time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Mastodon: {exc}")
            return []

        news.sort(key=lambda item: item.get("points", 0), reverse=True)
        result = news[:5]
        print(f"  ✅ Mastodon: {len(result)} 条")
        return result

    def aggregate_all(self) -> list[dict[str, Any]]:
        """Fetch all enabled sources and deduplicate by title."""
        print("\n🔍 开始抓取AI资讯...\n")
        fetchers = {
            "36kr": self.fetch_36kr,
            "huggingface": self.fetch_huggingface,
            "techcrunch": self.fetch_techcrunch_ai,
            "verge": self.fetch_verge_ai,
            "hackernews": self.fetch_hackernews_ai,
            "reddit": self.fetch_reddit_ai,
            "mastodon": self.fetch_mastodon_ai,
            "substack": self.fetch_substack_ai,
        }
        all_news: list[dict[str, Any]] = []
        for key, fetcher in fetchers.items():
            if self.sources.get(key):
                all_news.extend(fetcher())
                time.sleep(1)

        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in all_news:
            title = item["title"]
            if title in seen:
                continue
            seen.add(title)
            unique.append(item)

        print(f"\n📊 总计抓取: {len(all_news)} 条 | 去重后: {len(unique)} 条\n")
        return unique

    def filter_relevant(self, news: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only product-relevant news using the original keyword list."""
        return [
            item
            for item in news
            if any(keyword in f"{item['title']}{item.get('summary', '')}".lower() for keyword in RELEVANT_KEYWORDS)
        ]

    def save(self, news: list[dict[str, Any]], filename: str) -> str:
        """Persist JSON output and return the target path as a string."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"💾 已保存: {path}")
        return str(path)

    def format_briefing(self, news: list[dict[str, Any]], top_n: int = 10) -> str:
        """Create a compact human-readable briefing for morning review."""
        lines = [f"📊 今日AI简报（{datetime.now().strftime('%Y-%m-%d %H:%M')}）", ""]
        for index, item in enumerate(news[:top_n], start=1):
            lines.append(f"{index}. [{item['source']}] {item['title']}")
            if item.get("summary"):
                lines.append(f"   {item['summary'][:100]}...")
            lines.append(f"   {item['link']}")
            lines.append("")
        return "\n".join(lines)


def main() -> None:
    aggregator = AINewsAggregator()
    today = datetime.now().strftime("%Y-%m-%d")
    all_news = aggregator.aggregate_all()
    relevant = aggregator.filter_relevant(all_news)
    print(f"🎯 筛选后: {len(relevant)} 条\n")
    aggregator.save(all_news, f"ai_news_raw_{today}.json")
    aggregator.save(relevant, f"ai_news_filtered_{today}.json")
    briefing = aggregator.format_briefing(relevant, top_n=10)
    print(briefing)

    path = aggregator.output_dir / f"ai_briefing_{today}.txt"
    aggregator.output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(briefing, encoding="utf-8")
    print(f"💾 简报已保存: {path}")


if __name__ == "__main__":
    main()
