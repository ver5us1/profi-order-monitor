"""Observe board JSON responses in the user's persistent Chromium session."""

import asyncio
import logging
import random

from profi_order_monitor.config import Settings, initialize
from profi_order_monitor.parsing import find_matching_ids, has_board_payload
from profi_order_monitor.storage.files import save_snapshot

logger = logging.getLogger(__name__)


async def capture_response(response, settings: Settings):
    try:
        if settings.match_url not in response.url:
            return None
        if "json" not in response.headers.get("content-type", "").lower():
            return None
        data = await response.json()
        if not has_board_payload(data):
            return None
        path = save_snapshot(settings.downloads_dir, data)
        logger.info("Снимок %s; ID: %s", path.name, len(find_matching_ids(data)))
        return path
    except Exception as error:
        logger.warning("Обработка ответа: %s", type(error).__name__)
        return None


async def run_downloader(settings: Settings) -> None:
    from playwright.async_api import async_playwright

    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_dir), headless=False,
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()

            async def handle_response(response):
                await capture_response(response, settings)

            page.on("response", handle_response)
            await page.goto(settings.site_url, wait_until="domcontentloaded")
            logger.info("Браузер открыт; обновление каждые %s–%s с", settings.min_interval, settings.max_interval)
            while not page.is_closed():
                await asyncio.sleep(random.randint(settings.min_interval, settings.max_interval))
                if page.is_closed():
                    break
                try:
                    await page.reload(wait_until="domcontentloaded")
                except Exception as error:
                    logger.warning("Обновление страницы: %s", type(error).__name__)
                    break
        finally:
            await context.close()


def main() -> None:
    settings = initialize()
    try:
        asyncio.run(run_downloader(settings))
    except KeyboardInterrupt:
        logger.info("Сбор остановлен")


if __name__ == "__main__":
    main()
