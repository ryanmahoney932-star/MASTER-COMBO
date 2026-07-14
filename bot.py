import os
import re
import logging
from telegram import Update, BufferedInputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

def parse_credential(line: str):
    line = line.strip()
    if not line:
        return None

    # Remove prefixes
    line = re.sub(r'^(BD|signup|admin|login)\s*[:]?\s*', '', line, flags=re.I)
    parts = line.split(':')
    clean_parts = []
    for p in parts:
        p = p.strip()
        if not p or '://' in p:
            continue
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$', p) and '@' not in p:
            continue
        clean_parts.append(p)

    if len(clean_parts) >= 2:
        return (clean_parts[-2], clean_parts[-1])

    if ' ' in line or '\t' in line:
        parts = re.split(r'[\t\s]+', line)
        if len(parts) >= 2:
            identifier = parts[-2].strip()
            password = parts[-1].strip()
            if identifier and password and not re.match(r'^https?://', identifier):
                return (identifier, password)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me credentials (text or .txt).\n"
        "I'll extract email:pass / user:pass / number:pass"
    )

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        text = content.decode("utf-8", errors="ignore")
    else:
        text = update.message.text

    lines = text.strip().splitlines()
    parsed, unparsed = [], []

    for line in lines:
        result = parse_credential(line)
        if result:
            parsed.append(result)
        else:
            if line.strip():
                unparsed.append(line.strip())

    seen = set()
    unique = []
    for identifier, password in parsed:
        key = identifier.lower()
        if key not in seen:
            seen.add(key)
            unique.append((identifier, password))

    if not unique:
        await update.message.reply_text("❌ No valid pairs found.")
        return

    output_text = "\n".join([f"{u}:{p}" for u, p in unique])
    file_bytes = output_text.encode("utf-8")

    preview = "\n".join([f"{u}:{p}" for u, p in unique[:5]])
    if len(unique) > 5:
        preview += "\n..."

    caption = (
        f"✅ Parsed {len(lines)} lines.\n"
        f"📦 Found {len(unique)} unique.\n"
        f"⚠️ {len(unparsed)} unparsed.\n\nPreview:\n{preview}"
    )

    await update.message.reply_document(
        BufferedInputFile(file_bytes, filename="combolist.txt"),
        caption=caption
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_input))
    app.run_polling()

if __name__ == "__main__":
    main()
