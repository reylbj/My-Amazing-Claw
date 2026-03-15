#!/usr/bin/env python3
"""
在本机可视化联调闲鱼发布流程，并停在发布前一刻。
可选自动点击“发布”按钮并验证结果。
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright

from xianyu_auto_publish import XianyuAutoPublisher


WORKDIR = Path(__file__).resolve().parent
CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SAFE_IMAGES = [
    str((WORKDIR / "data" / "default_publish_cover.png").resolve()),
]


async def wait_and_log(message: str, seconds: float = 2.0) -> None:
    print(f"[live-debug] {message}")
    await asyncio.sleep(seconds)


async def goto_with_retry(page, url: str, retries: int = 2) -> None:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return
        except Exception as exc:
            last_error = exc
            print(f"[live-debug] 打开页面失败，第 {attempt}/{retries} 次重试: {exc}")
            await asyncio.sleep(2)
    raise last_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="可视化闲鱼发布调试/发布工具")
    parser.add_argument("--auto-publish", action="store_true", help="填写完成后自动点击发布")
    parser.add_argument("--title", default="AI文案策划｜需求明确｜交付清晰")
    parser.add_argument(
        "--description",
        default="想把内容需求讲清楚、交付更省心，可以直接拍下沟通。\n\n【适合需求】\n• 小红书内容策划与整理\n• 公众号文章结构梳理\n• 商品详情页文案优化\n\n【交付内容】\n• 1版可直接使用的完整文案\n• 重点卖点与结构梳理\n• 1次细节微调\n\n【下单前请发】\n• 产品或业务信息\n• 目标人群与使用场景\n• 希望语气与交付时间",
    )
    parser.add_argument("--price", default="19.9")
    parser.add_argument("--orig-price", default="29.9")
    parser.add_argument("--schedule", default="1-5天")
    parser.add_argument("--pricing-mode", default="元/次")
    parser.add_argument(
        "--image",
        action="append",
        dest="images",
        default=[],
        help="可重复传入，但只会使用第1张主题封面；不传时使用本地安全占位图",
    )
    return parser


async def main() -> None:
    args = build_parser().parse_args()
    if not CHROME_PATH.exists():
        raise SystemExit(f"未找到 Chrome: {CHROME_PATH}")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        executable_path=str(CHROME_PATH),
        headless=False,
        slow_mo=350,
        args=[
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    context = await browser.new_context(
        no_viewport=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    page = await context.new_page()
    await page.bring_to_front()

    publisher = XianyuAutoPublisher()
    publisher.browser = browser
    publisher.page = page
    network_events = []
    upload_tracker = {
        "inflight": 0,
        "successes": 0,
        "last_activity": time.monotonic(),
    }

    async def wait_for_upload_idle(expected_images: int, timeout: float = 120.0, idle_seconds: float = 8.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            idle_long_enough = (time.monotonic() - upload_tracker["last_activity"]) >= idle_seconds
            if upload_tracker["inflight"] == 0 and upload_tracker["successes"] >= expected_images and idle_long_enough:
                return True
            await asyncio.sleep(1)
        return False

    async def record_response(response) -> None:
        url = response.url
        if not any(token in url for token in ("publish", "goofish.com/api", "h5api.m.goofish.com", "mtop")):
            if "stream-upload.goofish.com/api/upload.api" not in url:
                return
        try:
            body = await response.text()
        except Exception:
            body = ""
        if "stream-upload.goofish.com/api/upload.api" in url:
            upload_tracker["inflight"] = max(0, upload_tracker["inflight"] - 1)
            upload_tracker["last_activity"] = time.monotonic()
            if response.status == 200 and '"success":true' in body:
                upload_tracker["successes"] += 1
        network_events.append(
            {
                "kind": "response",
                "url": url,
                "status": response.status,
                "body": body[:1200],
            }
        )

    def record_request(request) -> None:
        url = request.url
        if not any(token in url for token in ("publish", "goofish.com/api", "h5api.m.goofish.com", "mtop")):
            if "stream-upload.goofish.com/api/upload.api" not in url:
                return
        if "stream-upload.goofish.com/api/upload.api" in url:
            upload_tracker["inflight"] += 1
            upload_tracker["last_activity"] = time.monotonic()
        network_events.append(
            {
                "kind": "request",
                "url": url,
                "method": request.method,
                "post_data": (request.post_data or "")[:1200],
            }
        )

    page.on("request", record_request)
    page.on("response", lambda response: asyncio.create_task(record_response(response)))

    try:
        await wait_and_log("加载 Cookie", 0.8)
        await publisher.load_cookies("data/xianyu_cookies.json")

        await wait_and_log("打开闲鱼发布页", 0.8)
        await goto_with_retry(page, "https://www.goofish.com/publish")
        await wait_and_log("页面已打开，开始逐项填写", 2.5)

        description_value = "\n\n".join([args.title, args.description])
        await publisher._fill_contenteditable(
            [
                '[contenteditable="true"][data-placeholder*="描述"]',
                'div.editor--MtHPS94K[contenteditable="true"]',
                'div[contenteditable="true"]',
            ],
            description_value,
            "描述",
        )
        await wait_and_log("描述已填写", 2.5)
        image_candidates = publisher.resolve_publish_images(args.images)
        if image_candidates:
            upload_input = page.locator('input[type="file"][name="file"]').first
            await upload_input.set_input_files(image_candidates)
            await wait_and_log("封面图已上传，继续填写其余字段", 1.5)
        if not await publisher.wait_for_text_signals(["预计工期", "计价方式"], timeout=15.0):
            raise RuntimeError("预计工期/计价方式字段未按预期出现")

        schedule_ok = await publisher._select_option(
            [
                '.ant-form-item:has(label[title="预计工期"]) .ant-select-selector',
                '.ant-form-item:has-text("预计工期") .ant-select-selector',
            ],
            [args.schedule, "1-5天", "5-10天", "待议"],
            "预计工期",
        )
        if not schedule_ok:
            raise RuntimeError("未能选择预计工期")
        await wait_and_log("预计工期已选择", 2.0)

        pricing_ok = await publisher._select_option(
            [
                '.ant-form-item:has(label[title="计价方式"]) .ant-select-selector',
                '.ant-form-item:has-text("计价方式") .ant-select-selector',
            ],
            [args.pricing_mode, "元/次", "其他"],
            "计价方式",
        )
        if not pricing_ok:
            raise RuntimeError("未能选择计价方式")
        await wait_and_log("计价方式已选择", 2.0)

        await publisher._fill_input(
            [
                'label[for="itemPriceDTO_priceInCent"] >> xpath=ancestor::div[contains(@class,"ant-form-item")]//input',
                '.ant-form-item:has(label[title="价格"]) input',
                'input[placeholder="0.00"]',
            ],
            args.price,
            "价格",
        )
        await publisher._fill_input(
            [
                'label[for="itemPriceDTO_origPriceInCent"] >> xpath=ancestor::div[contains(@class,"ant-form-item")]//input',
                '.ant-form-item:has(label[title="原价"]) input',
            ],
            args.orig_price,
            "原价",
        )
        await wait_and_log("价格与原价已填写", 2.0)

        await publisher._click_first(
            [
                'label:has-text("无需邮寄")',
                'span:has-text("无需邮寄")',
                'input[type="radio"][value="3"]',
            ],
            "无需邮寄",
        )
        await wait_and_log("发货方式已切到无需邮寄", 2.0)

        if image_candidates:
            await wait_and_log("封面图处理中，等待平台静默", 1.5)
            uploads_idle = await wait_for_upload_idle(expected_images=len(image_candidates), timeout=120.0)
            if not uploads_idle:
                raise RuntimeError("图片上传请求长时间未静默，暂不触发发布")
            ready_after_upload = await publisher.wait_for_publish_ready(
                expected_images=len(image_candidates),
                timeout=120.0,
            )
            if not ready_after_upload:
                raise RuntimeError("图片可能仍在处理中，页面未进入稳定可发布状态")
        else:
            raise RuntimeError("未找到可用封面图")

        await page.evaluate(
            """
() => {
  document.documentElement.style.zoom = '0.9';
  const button = document.querySelector('button.publish-button--KBpTVopQ');
  if (button) {
    button.style.outline = '4px solid #ff3b30';
    button.style.outlineOffset = '4px';
    button.style.boxShadow = '0 0 0 8px rgba(255,59,48,0.18)';
    button.scrollIntoView({ block: 'center', behavior: 'instant' });
  }
  const panel = document.createElement('div');
  panel.id = 'codex-live-debug-banner';
  panel.style.position = 'fixed';
  panel.style.top = '16px';
  panel.style.right = '16px';
  panel.style.zIndex = '999999';
  panel.style.background = 'rgba(20,20,20,0.88)';
  panel.style.color = '#fff';
  panel.style.padding = '14px 16px';
  panel.style.borderRadius = '12px';
  panel.style.fontSize = '14px';
  panel.style.lineHeight = '1.5';
  panel.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)';
  panel.innerHTML = 'Codex可视化联调<br>已停在发布前一刻<br>红框位置是发布按钮';
  const old = document.getElementById('codex-live-debug-banner');
  if (old) old.remove();
  document.body.appendChild(panel);
}
"""
        )
        await page.screenshot(path="data/live_prepublish_state.png", full_page=True)

        summary = await page.evaluate(
            """
() => {
  const text = (el) => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
  const q = (selector) => document.querySelector(selector);
  return {
    url: location.href,
    title: document.title,
    publishClass: q('button.publish-button--KBpTVopQ')?.className || '',
    publishText: text(q('button.publish-button--KBpTVopQ') || document.body).slice(0, 80),
    body: text(document.body).slice(0, 3000),
  };
}
"""
        )
        publish_ready = await publisher._publish_button_enabled()

        print("[live-debug] 当前页面摘要:")
        print(
            json.dumps(
                {
                    "publish_ready": publish_ready,
                    **summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        if args.auto_publish:
            if not publish_ready:
                print("[live-debug] 当前仍未检测到可发布状态，未自动点击发布。")
            else:
                print("[live-debug] 即将自动点击发布按钮。")
                await wait_and_log("3秒后点击发布", 3.0)
                await page.locator('button.publish-button--KBpTVopQ, button:has-text("发布")').first.click()
                await wait_and_log("已点击发布，等待结果", 15.0)
                await page.screenshot(path="data/live_publish_result.png", full_page=True)
                result = await page.evaluate(
                    """
() => {
  const text = (el) => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
  const nodes = Array.from(document.querySelectorAll('[role="alert"], [class*="toast"], [class*="message"], [class*="notice"]'))
    .map((el) => text(el))
    .filter(Boolean)
    .slice(0, 20);
  return {
    url: location.href,
    title: document.title,
    body: text(document.body).slice(0, 4000),
    notices: nodes,
  };
}
"""
                )
                print("[live-debug] 发布后页面摘要:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                print("[live-debug] 发布相关网络事件:")
                print(json.dumps(network_events[-20:], ensure_ascii=False, indent=2))
        else:
            print("[live-debug] 浏览器现在停在发布前一刻，不会自动点击发布。")

        input("[live-debug] 你检查完后，回到终端按回车关闭浏览器...")
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
