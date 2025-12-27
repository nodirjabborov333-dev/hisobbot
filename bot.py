from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import sqlite3
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler


import sqlite3
from datetime import date

# =======================
# BOT TOKEN
# =======================
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")


# =======================
# DATABASE
# =======================
conn = sqlite3.connect("hisobbot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    record_date TEXT,
    revenue INTEGER,
    expense INTEGER,
    profit INTEGER
)
""")
conn.commit()

# =======================
# START COMMAND
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum 👋\n\n"
        "HisobBot ishga tushdi ✅\n\n"
        "Foydalanish:\n"
        "savdo 1200000\n"
        "xarajat 700000\n\n"
        "/oylik — oylik hisobot"
    )

# =======================
# MESSAGE HANDLER
# =======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()

    # SAVDO
    if text.startswith("savdo"):
        try:
            savdo = int(text.split()[1])
            context.user_data["savdo"] = savdo
            await update.message.reply_text(
                "Xarajatni yozing:\nmasalan: xarajat 700000"
            )
        except:
            await update.message.reply_text(
                "Xato format ❌\nTo‘g‘ri yozing:\nsavdo 1200000"
            )

    # XARAJAT
    elif text.startswith("xarajat"):
        try:
            xarajat = int(text.split()[1])

            if "savdo" not in context.user_data:
                await update.message.reply_text(
                    "Avval savdoni kiriting:\nsavdo 1200000"
                )
                return

            savdo = context.user_data["savdo"]
            foyda = savdo - xarajat
            today = date.today().isoformat()

            cursor.execute(
                """
                INSERT INTO records
                (telegram_id, record_date, revenue, expense, profit)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    update.effective_user.id,
                    today,
                    savdo,
                    xarajat,
                    foyda
                )
            )
            conn.commit()

            await update.message.reply_text(
                f"📊 Natija:\n"
                f"Savdo: {savdo:,} so‘m\n"
                f"Xarajat: {xarajat:,} so‘m\n"
                f"Foyda: {foyda:,} so‘m"
            )

        except:
            await update.message.reply_text(
                "Xato format ❌\nTo‘g‘ri yozing:\nxarajat 700000"
            )
    elif "bugun foyda" in text:
        today = date.today().isoformat()

        cursor.execute(
            """
            SELECT profit FROM records
            WHERE telegram_id = ? AND record_date = ?
            """,
            (update.effective_user.id, today)
        )
        row = cursor.fetchone()

        if row:
            await update.message.reply_text(
                f"📊 Bugungi foyda: {row[0]:,} so‘m"
            )
        else:
            await update.message.reply_text(
                "Bugun hali ma’lumot kiritilmadi."
            )

    else:
        await update.message.reply_text(
            "Buyruqni tushunmadim 🤔\n\n"
            "To‘g‘ri misollar:\n"
            "savdo 1200000\n"
            "xarajat 700000"
        )

# =======================
# OYLIK HISOBOT
# =======================
async def oylik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    month_start = today.replace(day=1).isoformat()

    cursor.execute(
        """
        SELECT SUM(revenue), SUM(expense), SUM(profit)
        FROM records
        WHERE telegram_id = ?
        AND record_date >= ?
        """,
        (update.effective_user.id, month_start)
    )

    result = cursor.fetchone()

    if result[0] is None:
        await update.message.reply_text("Bu oy hali ma’lumot yo‘q.")
        return

    await update.message.reply_text(
        f"📅 Joriy oy hisobot:\n"
        f"Savdo: {result[0]:,} so‘m\n"
        f"Xarajat: {result[1]:,} so‘m\n"
        f"Foyda: {result[2]:,} so‘m"
    )

    cursor.execute(
        """
        SELECT SUM(revenue), SUM(expense), SUM(profit)
        FROM records
        WHERE telegram_id = ?
        """,
        (update.effective_user.id,)
    )
    result = cursor.fetchone()

    if result[0] is None:
        await update.message.reply_text("Hali ma’lumot yo‘q.")
        return

    await update.message.reply_text(
        f"📅 Oylik hisobot:\n"
        f"Savdo: {result[0]:,} so‘m\n"
        f"Xarajat: {result[1]:,} so‘m\n"
        f"Foyda: {result[2]:,} so‘m"
    )

def send_reminders(app):
    today = date.today().isoformat()

    # Bugun yozgan userlar
    cursor.execute(
        "SELECT DISTINCT telegram_id FROM records WHERE record_date = ?",
        (today,)
    )
    done_users = {row[0] for row in cursor.fetchall()}

    # Umuman botdan foydalangan userlar
    cursor.execute("SELECT DISTINCT telegram_id FROM records")
    all_users = {row[0] for row in cursor.fetchall()}

    # Bugun yozmaganlarga eslatma
    for user_id in all_users - done_users:
        try:
            app.bot.send_message(
                chat_id=user_id,
                text="⏰ Eslatma: bugun savdo kiritilmadi."
            )
        except:
            pass

# =======================
# MAIN
# =======================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("oylik", oylik))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_reminders,
        "cron",
        hour=20,
        minute=0,
        args=[app]
    )
    scheduler.start()

    print("🤖 HisobBot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
