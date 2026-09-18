import logging
import os
from datetime import datetime, timezone

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

API_URL = "https://v3.football.api-sports.io"
TOKEN = os.getenv("TELEGRAM_SCOREBOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def api_get(path: str, params: dict | None = None) -> dict:
    if not API_KEY:
        raise RuntimeError("Football data API is not configured yet")

    headers = {"x-apisports-key": API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{API_URL}{path}", headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def format_fixture(fixture: dict) -> str:
    teams = fixture.get("teams", {})
    goals = fixture.get("goals", {})
    league = fixture.get("league", {})
    status = fixture.get("fixture", {}).get("status", {})

    home = teams.get("home", {}).get("name", "Home")
    away = teams.get("away", {}).get("name", "Away")
    home_score = goals.get("home")
    away_score = goals.get("away")
    short = status.get("short", "?")
    elapsed = status.get("elapsed")

    score = f"{home_score if home_score is not None else '-'} - {away_score if away_score is not None else '-'}"
    status_text = f"{short} {elapsed}'" if elapsed else short
    league_name = league.get("name", "Football")

    return f"⚽ {home} {score} {away}\n   {status_text} · {league_name}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚽ Welcome to SABONG24 Football Scores!\n\n"
        "Use /live for live matches or /today for today's fixtures and results."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚽ Football Scores\n\n"
        "/live — live football matches\n"
        "/today — today's fixtures and results\n"
        "/help — show this help"
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not API_KEY:
        await update.message.reply_text(
            "⚽ The bot is online, but live scores have not been connected yet."
        )
        return

    try:
        data = await api_get("/fixtures", {"live": "all"})
        fixtures = data.get("response", [])

        if not fixtures:
            await update.message.reply_text("⚽ No live football matches right now.")
            return

        lines = [format_fixture(item) for item in fixtures[:20]]
        await update.message.reply_text("\n\n".join(lines))
    except Exception:
        logger.exception("Failed to fetch live fixtures")
        await update.message.reply_text("⚠️ Live scores are temporarily unavailable. Please try again.")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not API_KEY:
        await update.message.reply_text(
            "⚽ The bot is online, but football fixtures have not been connected yet."
        )
        return

    date = datetime.now(timezone.utc).date().isoformat()

    try:
        data = await api_get("/fixtures", {"date": date})
        fixtures = data.get("response", [])

        if not fixtures:
            await update.message.reply_text("⚽ No football fixtures/results found for today.")
            return

        lines = [format_fixture(item) for item in fixtures[:30]]
        await update.message.reply_text("\n\n".join(lines))
    except Exception:
        logger.exception("Failed to fetch today's fixtures")
        await update.message.reply_text("⚠️ Today's fixtures are temporarily unavailable. Please try again.")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_SCOREBOT_TOKEN environment variable is required")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("today", today))

    app.run_polling()


if __name__ == "__main__":
    main()
