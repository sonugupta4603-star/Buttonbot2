import asyncio, os, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
router = Router()

class PostMaker(StatesGroup):
    content = State()
    button = State()
    channel = State()

@router.message(CommandStart())
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("👋 *Welcome to Post Maker Bot!*\nSend /create to make a post with URL buttons.", parse_mode="Markdown")

@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("❌ Cancelled. Send /create to start again.")

@router.message(Command("create"))
async def create_post(m: Message, state: FSMContext):
    await state.set_state(PostMaker.content)
    await m.answer("📝 Send the **Text, Photo, or Video** for your post.", parse_mode="Markdown")

@router.message(PostMaker.content)
async def get_content(m: Message, state: FSMContext):
    await state.update_data(
        text=m.html_text if m.text else m.caption,
        photo_id=m.photo[-1].file_id if m.photo else None,
        video_id=m.video.file_id if m.video else None
    )
    await state.set_state(PostMaker.button)
    await m.answer("✅ Saved!\n🔗 Send Button Name & Link:\n`Button Name - https://link.com`\n*(Or type 'skip')*", parse_mode="Markdown")

@router.message(PostMaker.button)
async def get_button(m: Message, state: FSMContext):
    kb = None
    if m.text.lower() != 'skip':
        try:
            btn_text, btn_url = m.text.split("-", 1)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text.strip(), url=btn_url.strip())]])
            await state.update_data(keyboard=kb)
        except ValueError:
            return await m.answer("❌ Invalid format. Use:\n`Click Here - https://google.com`", parse_mode="Markdown")

    data = await state.get_data()
    await m.answer("👀 *Preview:*", parse_mode="Markdown")
    
    if data.get("photo_id"): await m.answer_photo(photo=data["photo_id"], caption=data.get("text", ""), reply_markup=kb, parse_mode="HTML")
    elif data.get("video_id"): await m.answer_video(video=data["video_id"], caption=data.get("text", ""), reply_markup=kb, parse_mode="HTML")
    else: await m.answer(text=data.get("text", ""), reply_markup=kb, parse_mode="HTML")

    await state.set_state(PostMaker.channel)
    await m.answer("📢 Send your **Channel Username** (e.g., `@mychannel`) to post it.\n*(Make me Admin first! Or send /cancel)*", parse_mode="Markdown")

@router.message(PostMaker.channel)
async def send_to_channel(m: Message, state: FSMContext, bot: Bot):
    ch = m.text.strip()
    data = await state.get_data()
    kb = data.get("keyboard")
    try:
        if data.get("photo_id"): await bot.send_photo(chat_id=ch, photo=data["photo_id"], caption=data.get("text", ""), reply_markup=kb, parse_mode="HTML")
        elif data.get("video_id"): await bot.send_video(chat_id=ch, video=data["video_id"], caption=data.get("text", ""), reply_markup=kb, parse_mode="HTML")
        else: await bot.send_message(chat_id=ch, text=data.get("text", ""), reply_markup=kb, parse_mode="HTML")
        await m.answer(f"✅ Successfully sent to {ch}!")
    except Exception as e:
        await m.answer(f"❌ Error: Am I admin in {ch}?\n`{e}`", parse_mode="Markdown")
    await state.clear()

async def handle(request): return web.Response(text="Bot is running!")
async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    asyncio.create_task(web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
