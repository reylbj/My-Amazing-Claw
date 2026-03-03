#!/usr/bin/env python3
"""
AI资讯抓取脚本
信息源：36氪 / HuggingFace / TechCrunch / The Verge / Hacker News / Reddit / Mastodon / Substack
"""

import json
import re
import time
import requests
import feedparser
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class AINewsAggregator:

    def __init__(self):
        self.current_year = datetime.now().year
        self.min_year = self.current_year - 1
        self.output_dir = Path(__file__).resolve().parent.parent / "验证输出"
        self.sources = {
            '36kr':        True,
            'huggingface': True,
            'techcrunch':  True,
            'verge':       True,
            'hackernews':  True,
            'reddit':      True,
            'mastodon':    False,  # 活跃度低，产出为0，暂停
            'substack':    True,
        }

    def _is_recent_year(self, year: int) -> bool:
        """仅保留最近两年的内容，避免旧闻混入。"""
        return year >= self.min_year

    # ──────────────────────────────────────────────
    # RSS类信息源
    # ──────────────────────────────────────────────

    def _parse_rss(self, url: str, source: str, limit: int = 5,
                   ai_filter: bool = False) -> List[Dict]:
        feed = feedparser.parse(url)
        news = []
        keywords = ['ai', '人工智能', 'chatgpt', 'gpt', '大模型', '智能', 'llm', 'agent']

        for entry in feed.entries[:limit * 2]:
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            published = entry.get('published', '')

            # 过滤AI关键词
            if ai_filter:
                text = (title + summary).lower()
                if not any(k in text for k in keywords):
                    continue

            # 过滤旧资讯（仅保留最近两年）
            try:
                if published:
                    # 尝试解析日期
                    pub_date = feedparser._parse_date(published)
                    if pub_date and not self._is_recent_year(pub_date.tm_year):
                        continue
            except:
                pass  # 如果解析失败，保留该条目

            news.append({
                'title':     title,
                'link':      entry.get('link', ''),
                'published': published,
                'summary':   re.sub('<[^<]+?>', '', summary)[:200],
                'source':    source,
            })
            if len(news) >= limit:
                break
        return news

    def fetch_36kr(self) -> List[Dict]:
        print("📰 抓取36氪...")
        try:
            news = self._parse_rss("https://36kr.com/feed", "36氪", limit=7, ai_filter=True)
            print(f"  ✅ 36氪: {len(news)} 条")
            return news
        except Exception as e:
            print(f"  ❌ 36氪: {e}")
            return []

    def fetch_huggingface(self) -> List[Dict]:
        print("📰 抓取HuggingFace...")
        try:
            news = self._parse_rss("https://huggingface.co/blog/feed.xml", "HuggingFace", limit=5)
            print(f"  ✅ HuggingFace: {len(news)} 条")
            return news
        except Exception as e:
            print(f"  ❌ HuggingFace: {e}")
            return []

    def fetch_techcrunch_ai(self) -> List[Dict]:
        print("📰 抓取TechCrunch AI...")
        try:
            news = self._parse_rss(
                "https://techcrunch.com/category/artificial-intelligence/feed/",
                "TechCrunch", limit=5)
            print(f"  ✅ TechCrunch: {len(news)} 条")
            return news
        except Exception as e:
            print(f"  ❌ TechCrunch: {e}")
            return []

    def fetch_verge_ai(self) -> List[Dict]:
        print("📰 抓取The Verge AI...")
        try:
            news = self._parse_rss(
                "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
                "The Verge", limit=5)
            print(f"  ✅ The Verge: {len(news)} 条")
            return news
        except Exception as e:
            print(f"  ❌ The Verge: {e}")
            return []

    def fetch_substack_ai(self) -> List[Dict]:
        """抓取AI领域高质量Substack（RSS，无需登录）"""
        print("📰 抓取Substack AI...")
        news = []

        substacks = [
            ("https://www.aitidbits.ai/feed", "AI Tidbits"),
            ("https://www.therundown.ai/feed", "The Rundown AI"),
            ("https://substack.com/api/v1/publication/133012/sitemap_feed.xml", "Ben's Bites"),
        ]

        for feed_url, name in substacks:
            try:
                items = self._parse_rss(feed_url, f"Substack·{name}", limit=2)
                news.extend(items)
                time.sleep(0.5)
            except Exception:
                continue

        print(f"  ✅ Substack: {len(news)} 条")
        return news

    # ──────────────────────────────────────────────
    # API类信息源
    # ──────────────────────────────────────────────

    def fetch_hackernews_ai(self) -> List[Dict]:
        """Hacker News via Algolia API（完全免费，无需认证）"""
        print("📰 抓取Hacker News AI...")
        news = []
        seen = set()

        try:
            url = "https://hn.algolia.com/api/v1/search"
            for keyword in ["AI", "LLM", "ChatGPT"]:
                resp = requests.get(url, params={
                    "query": keyword,
                    "tags": "story",
                    "numericFilters": "points>20,created_at_i>1704067200",  # 2024-01-01之后
                    "hitsPerPage": 5
                }, timeout=10)

                if resp.status_code == 200:
                    for hit in resp.json().get('hits', []):
                        title = hit.get('title', '')
                        created_at = hit.get('created_at', '')

                        # 过滤旧资讯（仅保留最近两年）
                        try:
                            if created_at:
                                pub_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                if not self._is_recent_year(pub_date.year):
                                    continue
                        except:
                            pass

                        if title in seen:
                            continue
                        seen.add(title)
                        link = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        news.append({
                            'title':     title,
                            'link':      link,
                            'published': created_at,
                            'summary':   f"{hit.get('points', 0)}分 | {hit.get('num_comments', 0)}评论",
                            'source':    'Hacker News',
                            'points':    hit.get('points', 0),
                        })
                time.sleep(0.5)

            news.sort(key=lambda x: x.get('points', 0), reverse=True)
            news = news[:8]
            print(f"  ✅ Hacker News: {len(news)} 条")
            return news

        except Exception as e:
            print(f"  ❌ Hacker News: {e}")
            return []

    def fetch_reddit_ai(self) -> List[Dict]:
        """Reddit AI子版块（免费JSON API，无需认证）"""
        print("📰 抓取Reddit AI...")
        news = []
        seen = set()

        subreddits = [
            "MachineLearning",
            "artificial",
            "ChatGPT",
        ]

        headers = {"User-Agent": "OpenClaw/1.0 (AI News Aggregator)"}

        for sub in subreddits:
            try:
                resp = requests.get(
                    f"https://www.reddit.com/r/{sub}/hot.json",
                    params={"limit": 5},
                    headers=headers,
                    timeout=10
                )

                if resp.status_code == 200:
                    posts = resp.json().get('data', {}).get('children', [])
                    for post in posts:
                        d = post.get('data', {})
                        title = d.get('title', '')
                        score = d.get('score', 0)
                        created_utc = d.get('created_utc', 0)

                        if score < 50 or title in seen:
                            continue

                        # 过滤旧资讯（仅保留最近两年）
                        if created_utc and not self._is_recent_year(datetime.fromtimestamp(created_utc).year):
                            continue

                        seen.add(title)

                        news.append({
                            'title':     title,
                            'link':      d.get('url', ''),
                            'published': datetime.fromtimestamp(
                                d.get('created_utc', 0)).isoformat(),
                            'summary':   f"r/{sub} | {score}分 | {d.get('num_comments', 0)}评论",
                            'source':    f"Reddit·r/{sub}",
                            'points':    score,
                        })

                time.sleep(1)  # Reddit限速

            except Exception as e:
                print(f"    Reddit·r/{sub}: {e}")
                continue

        news.sort(key=lambda x: x.get('points', 0), reverse=True)
        news = news[:8]
        print(f"  ✅ Reddit: {len(news)} 条")
        return news

    def fetch_mastodon_ai(self) -> List[Dict]:
        """Mastodon AI相关内容（mastodon.social公开API，无需认证）"""
        print("📰 抓取Mastodon AI...")
        news = []
        seen = set()

        try:
            # mastodon.social公开搜索（无需认证）
            keywords = ["AI", "ChatGPT", "LLM"]

            for keyword in keywords[:2]:
                resp = requests.get(
                    "https://mastodon.social/api/v2/search",
                    params={"q": keyword, "type": "statuses", "limit": 10},
                    timeout=10
                )

                if resp.status_code == 200:
                    statuses = resp.json().get('statuses', [])
                    for status in statuses:
                        # 只要有一定互动量的
                        favs = status.get('favourites_count', 0)
                        boosts = status.get('reblogs_count', 0)
                        if favs + boosts < 3:
                            continue

                        content = re.sub('<[^<]+?>', '', status.get('content', ''))
                        if len(content) < 50 or content in seen:
                            continue
                        seen.add(content)

                        account = status.get('account', {})
                        handle = account.get('acct', '')
                        url = status.get('url', '')

                        news.append({
                            'title':     f"@{handle}: {content[:80]}...",
                            'link':      url,
                            'published': status.get('created_at', ''),
                            'summary':   content[:200],
                            'source':    'Mastodon',
                            'points':    favs + boosts,
                        })

                time.sleep(0.5)

            news.sort(key=lambda x: x.get('points', 0), reverse=True)
            news = news[:5]
            print(f"  ✅ Mastodon: {len(news)} 条")
            return news

        except Exception as e:
            print(f"  ❌ Mastodon: {e}")
            return []

    # ──────────────────────────────────────────────
    # 聚合 & 输出
    # ──────────────────────────────────────────────

    def aggregate_all(self) -> List[Dict]:
        print("\n🔍 开始抓取AI资讯...\n")
        all_news = []

        fetch_map = {
            '36kr':        self.fetch_36kr,
            'huggingface': self.fetch_huggingface,
            'techcrunch':  self.fetch_techcrunch_ai,
            'verge':       self.fetch_verge_ai,
            'hackernews':  self.fetch_hackernews_ai,
            'reddit':      self.fetch_reddit_ai,
            'mastodon':    self.fetch_mastodon_ai,
            'substack':    self.fetch_substack_ai,
        }

        for key, fn in fetch_map.items():
            if self.sources.get(key):
                all_news.extend(fn())
                time.sleep(1)

        # 去重
        seen, unique = set(), []
        for item in all_news:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique.append(item)

        print(f"\n📊 总计抓取: {len(all_news)} 条 | 去重后: {len(unique)} 条\n")
        return unique

    def filter_relevant(self, news: List[Dict]) -> List[Dict]:
        keywords = [
            'chatgpt', 'claude', 'gemini', 'gpt', 'ai agent', 'llm', '大模型',
            '人工智能', '产品', 'app', '应用', '工具', 'startup', '创业',
            '融资', 'funding', 'release', '发布', 'launch', '上线', 'model',
        ]
        return [
            item for item in news
            if any(k in (item['title'] + item.get('summary', '')).lower() for k in keywords)
        ]

    def save(self, news: List[Dict], filename: str):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        print(f"💾 已保存: {path}")
        return str(path)

    def format_briefing(self, news: List[Dict], top_n: int = 10) -> str:
        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        out = f"📊 今日AI简报（{today}）\n\n"
        for i, item in enumerate(news[:top_n], 1):
            out += f"{i}. [{item['source']}] {item['title']}\n"
            if item.get('summary'):
                out += f"   {item['summary'][:100]}...\n"
            out += f"   {item['link']}\n\n"
        return out


def main():
    agg = AINewsAggregator()
    today = datetime.now().strftime('%Y-%m-%d')

    all_news = agg.aggregate_all()
    relevant = agg.filter_relevant(all_news)
    print(f"🎯 筛选后: {len(relevant)} 条\n")

    agg.save(all_news,   f"ai_news_raw_{today}.json")
    agg.save(relevant,   f"ai_news_filtered_{today}.json")

    briefing = agg.format_briefing(relevant, top_n=10)
    print(briefing)

    path = agg.output_dir / f"ai_briefing_{today}.txt"
    agg.output_dir.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(briefing)
    print(f"💾 简报已保存: {path}")


if __name__ == "__main__":
    main()
