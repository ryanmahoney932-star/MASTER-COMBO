import os
import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile
from aiogram.filters import Command

# Configure logging
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def parse_credential(line: str):
    """Extract (identifier, password) from messy line."""
    line = line.strip()
    if not line:
        return None

    # Remove common non‑credential prefixes
    line = re.sub(r'^(BD|signup|admin|login)\s*[:]?\s*', '', line, flags=re.I)

    parts = line.split(':')
    clean_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Skip URLs with protocol
        if '://' in p:
            continue
        # Skip domain/path fragments without '@' (e.g. "ft.education")
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$', p) and '@' not in p:
            continue
        clean_parts.append(p)

    if len(clean_parts) >= 2:
        password = clean_parts[-1]
        identifier = clean_parts[-2]
        if identifier and password:
            return (identifier, password)

    # Fallback: split by spaces/tabs
    if ' ' in line or '\t' in line:
        parts = re.split(r'[\t\s]+', line)
        if len(parts) >= 2:
            identifier = parts[-2].strip()
            password = parts[-1].strip()
            if identifier and password and not re.match(r'^https?://', identifier):
                return (identifier, password)

    return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Send me a list of credentials (as text or .txt).\n\n"
        "I will extract:\n"
        "• email:pass\n• user:pass\n• number:pass\n\n"
        "Example:\n`user:pass`\n`https://site.com:user:pass`"
    )

@dp.message(lambda msg: msg.document or (msg.text and len(msg.text) > 5))
async def handle_input(message: types.Message):
    if message.document:
        file = await bot.get_file(message.document.file_id)
        content = await bot.download_file(file.file_path)
        text = content.read().decode("utf-8", errors="ignore")
    else:
        text = message.text

    lines = text.strip().splitlines()
    parsed = []
    unparsed = []

    for line in lines:
        result = parse_credential(line)
        if result:
            parsed.append(result)
        else:
            if line.strip():
                unparsed.append(line.strip())

    # Remove duplicates (case‑insensitive identifier)
    seen = set()
    unique = []
    for identifier, password in parsed:
        key = identifier.lower()
        if key not in seen:
            seen.add(key)
            unique.append((identifier, password))

    if not unique:
        await message.answer("❌ No valid `identifier:password` pairs found.")
        return

    output_lines = [f"{user}:{pwd}" for user, pwd in unique]
    output_text = "\n".join(output_lines)
    file_bytes = output_text.encode("utf-8")
    input_file = BufferedInputFile(file_bytes, filename="combolist.txt")

    preview_lines = output_lines[:5]
    preview = "\n".join(preview_lines)
    if len(output_lines) > 5:
        preview += "\n..."

    caption = (
        f"✅ Parsed {len(lines)} lines total.\n"
        f"📦 Found {len(unique)} unique valid pairs.\n"
        f"⚠️ {len(unparsed)} lines could not be parsed.\n\n"
        f"Preview:\n{preview}"
    )

    await message.answer_document(input_file, caption=caption)

    if unparsed:
        unparsed_preview = "\n".join(unparsed[:5])
        if len(unparsed) > 5:
            unparsed_preview += "\n..."
        await message.answer(f"⚠️ Unparsed lines (first 5):\n{unparsed_preview}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
