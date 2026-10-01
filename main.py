import asyncio
import math
import logging
import os
import csv
import io
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, Contact, BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = 0
DB_PATH = "taxi.db"
SUB_PRICE = 20
REF_TARGET = 5
REF_BONUS_DAYS = 3
AVG_SPEED = 30
NEAR_RADIUS = 2.0
CARD_NUMBER = "013585959"

logging.basicConfig(level=logging.INFO)

T = {
    "ru": {
        "welcome": "👋 Добро пожаловать в Такси-бот!",
        "lang_ask": "👇 Выберите язык / Забонро интихоб кунед:",
        "phone_ask": "📱 Шаг 1/3: Отправьте свой номер телефона:",
        "phone_btn": "📱 Отправить номер",
        "phone_saved": "✅ Номер сохранён.\n\n👤 Шаг 2/3: Напишите своё имя:",
        "last_ask": "\n\n👤 Шаг 3/3: Напишите свою фамилию:",
        "name_saved": "✅ Имя: ",
        "reg_done": "✅ Регистрация завершена!\n\n",
        "choose_role": "👋 С возвращением! Выберите роль:",
        "client": "🚕 Я клиент",
        "driver": "🚗 Я водитель",
        "complaint": "⚠️ Пожаловаться",
        "change": "🔄 Сменить роль",
        "order": "🚕 Заказать такси",
        "history": "📋 История",
        "ref": "🎁 Приведи друга",
        "online": "🟢 Я на линии",
        "offline": "🔴 Уйти с линии",
        "sub": "💳 Подписка",
        "car": "🚗 Моя машина",
        "earn": "💰 Мой заработок",
        "mystats": "📊 Моя статистика",
        "graph": "📊 График заработка",
        "top": "🏆 Топ водителей",
        "addr": "⭐ Мои адреса",
        "repeat": "🔄 Повторить заказ",
        "review": "⭐ Отзывы",
        "promo": "🎁 Промокоды",
        "subreq": "💳 Заявки",
        "drivers": "🚗 Водители",
        "clients": "👤 Клиенты",
        "orders": "📦 Заказы",
        "complaints": "⚠️ Жалобы",
        "stats": "📊 Статистика",
        "broadcast": "📢 Рассылка",
        "commissions": "💰 Комиссии",
        "forecast": "📈 Прогноз",
        "export": "📥 Экспорт CSV",
        "exit": "🔙 Выйти",
        "from": "📍 Откуда едем?",
        "to": "🎯 Куда едем?",
        "you_client": "✅ Вы вошли как клиент.",
        "you_driver": "✅ Вы вошли как водитель.\n\n",
        "sub_ok": "✅ Подписка активна",
        "sub_no": "❌ Подписки нет — оплатите 20 сомони",
        "wait_approve": "⏳ Ожидайте одобрения админом.\n\nПока заявка не принята — работать нельзя.",
        "rejected": "❌ Ваша заявка отклонена.\n\nСвяжитесь с администратором.",
        "cancel": "❌ Отмена",
        "change_lang": "🌍 Язык",
    },
    "tj": {
        "welcome": "👋 Хуш омадед ба боти Такси!",
        "lang_ask": "👇 Забонро интихоб кунед / Выберите язык:",
        "phone_ask": "📱 Қадами 1/3: Рақами телефони худро фиристед:",
        "phone_btn": "📱 Фиристодани рақам",
        "phone_saved": "✅ Рақам нигоҳ дошта шуд.\n\n👤 Қадами 2/3: Номи худро нависед:",
        "last_ask": "\n\n👤 Қадами 3/3: Насаби худро нависед:",
        "name_saved": "✅ Ном: ",
        "reg_done": "✅ Бақайдгирӣ анҷом ёфт!\n\n",
        "choose_role": "👋 Хуш омадед! Нақши худро интихоб кунед:",
        "client": "🚕 Ман мизоҷ",
        "driver": "🚗 Ман ронанда",
        "complaint": "⚠️ Шикоят",
        "change": "🔄 Иваз кардани нақш",
        "order": "🚕 Фармоиши такси",
        "history": "📋 Таърих",
        "ref": "🎁 Дӯстро даъват кунед",
        "online": "🟢 Ман дар хат",
        "offline": "🔴 Аз хат рафтан",
        "sub": "💳 Обуна",
        "car": "🚗 Мошини ман",
        "earn": "💰 Даромади ман",
        "mystats": "📊 Омори ман",
        "graph": "📊 Графики даромад",
        "top": "🏆 Беҳтарин ронандагон",
        "addr": "⭐ Суроғаҳои ман",
        "repeat": "🔄 Такрор кардан",
        "review": "⭐ Шарҳҳо",
        "promo": "🎁 Промокодҳо",
        "subreq": "💳 Дархостҳо",
        "drivers": "🚗 Ронандагон",
        "clients": "👤 Мизоҷон",
        "orders": "📦 Фармоишҳо",
        "complaints": "⚠️ Шикоятҳо",
        "stats": "📊 Омор",
        "broadcast": "📢 Паём",
        "commissions": "💰 Комиссияҳо",
        "forecast": "📈 Пешгӯӣ",
        "export": "📥 CSV содирот",
        "exit": "🔙 Баромад",
        "from": "📍 Аз куҷо меравем?",
        "to": "🎯 Ба куҷо меравем?",
        "you_client": "✅ Шумо ҳамчун мизоҷ дохил шудед.",
        "you_driver": "✅ Шумо ҳамчун ронанда дохил шудед.\n\n",
        "sub_ok": "✅ Обуна фаъол",
        "sub_no": "❌ Обуна нест — 20 сомонӣ пардохт кунед",
        "wait_approve": "⏳ Интизори тасдиқи админ.\n\nТо тасдиқ нашавад — кор кардан мумкин нест.",
        "rejected": "❌ Дархости шумо рад карда шуд.\n\nБо админ тамос гиред.",
        "cancel": "❌ Бекор кардан",
        "change_lang": "🌍 Забон",
    },
}

def tr(lang, key):
    return T.get(lang, T["ru"]).get(key, T["ru"].get(key, key))

TARIFFS = {
    "economy":  {"name": "🚕 Эконом",  "base": 10, "rate": 3},
    "comfort":  {"name": "🚙 Комфорт", "base": 15, "rate": 4},
    "business": {"name": "🚘 Бизнес",  "base": 25, "rate": 7},
}

CAR_CLASSES = ["Эконом", "Комфорт", "Бизнес"]

router = Router()

class Reg(StatesGroup):
    phone = State()
    first_name = State()
    last_name = State()

class DriverReg(StatesGroup):
    car_brand = State()
    car_plate = State()
    car_class = State()
    car_photo = State()
    self_photo = State()
    location = State()

class OrderFlow(StatesGroup):
    from_loc = State()
    to_loc = State()
    tariff = State()
    payment = State()
    promo = State()
    when = State()
    when_custom = State()
    confirm = State()

class Complaint(StatesGroup):
    text = State()

class AdminReply(StatesGroup):
    waiting = State()

class SubPayment(StatesGroup):
    receipt = State()

class PromoCreate(StatesGroup):
    code = State()
    discount = State()

class ChatMode(StatesGroup):
    chatting = State()

class Review(StatesGroup):
    text = State()

class Broadcast(StatesGroup):
    text = State()

class AddrSave(StatesGroup):
    title = State()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def nav_link(flat, flon, tlat, tlon):
    return "https://yandex.ru/maps/?rtext=" + str(flat) + "," + str(flon) + "~" + str(tlat) + "," + str(tlon) + "&rtt=auto"

def estimate_minutes(km, speed=AVG_SPEED):
    if not km:
        return None
    return max(1, round(km / speed * 60))

async def get_lang(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
    return "ru"

async def set_lang(uid, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id, lang) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang", (uid, lang))
        await db.commit()

def lang_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇹🇯 Тоҷикӣ")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def loc_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def class_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Эконом")],
            [KeyboardButton(text="Комфорт")],
            [KeyboardButton(text="Бизнес")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def when_kb(lang="ru"):
    if lang == "tj":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚕 Ҳозир")],
                [KeyboardButton(text="⏰ Баъди 30 дақиқа")],
                [KeyboardButton(text="⏰ Баъди 1 соат")],
                [KeyboardButton(text="⏰ Баъди 2 соат")],
                [KeyboardButton(text="⏰ Баъди 4 соат")],
                [KeyboardButton(text="🕐 Вақти дигар")],
            ],
            resize_keyboard=True, one_time_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Сейчас")],
            [KeyboardButton(text="⏰ Через 30 мин")],
            [KeyboardButton(text="⏰ Через 1 час")],
            [KeyboardButton(text="⏰ Через 2 часа")],
            [KeyboardButton(text="⏰ Через 4 часа")],
            [KeyboardButton(text="🕐 Своё время")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def chat_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="❌ Выйти из чата")],
        ],
        resize_keyboard=True
    )

def main_menu(lang="ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "client"))],
            [KeyboardButton(text=tr(lang, "driver"))],
            [KeyboardButton(text=tr(lang, "complaint"))],
        ],
        resize_keyboard=True
    )

def client_menu(lang="ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "order"))],
            [KeyboardButton(text=tr(lang, "repeat")), KeyboardButton(text=tr(lang, "addr"))],
            [KeyboardButton(text=tr(lang, "history")), KeyboardButton(text=tr(lang, "ref"))],
            [KeyboardButton(text=tr(lang, "complaint")), KeyboardButton(text=tr(lang, "change"))],
        ],
        resize_keyboard=True
    )

def driver_menu(lang="ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "online")), KeyboardButton(text=tr(lang, "offline"))],
            [KeyboardButton(text=tr(lang, "sub")), KeyboardButton(text=tr(lang, "car"))],
            [KeyboardButton(text=tr(lang, "earn")), KeyboardButton(text=tr(lang, "mystats"))],
            [KeyboardButton(text=tr(lang, "graph")), KeyboardButton(text=tr(lang, "top"))],
            [KeyboardButton(text=tr(lang, "ref")), KeyboardButton(text=tr(lang, "complaint"))],
            [KeyboardButton(text=tr(lang, "change"))],
        ],
        resize_keyboard=True
    )

def admin_menu(lang="ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "stats")), KeyboardButton(text=tr(lang, "graph"))],
            [KeyboardButton(text=tr(lang, "drivers")), KeyboardButton(text=tr(lang, "clients"))],
            [KeyboardButton(text=tr(lang, "orders")), KeyboardButton(text=tr(lang, "complaints"))],
            [KeyboardButton(text=tr(lang, "subreq")), KeyboardButton(text=tr(lang, "promo"))],
            [KeyboardButton(text=tr(lang, "review")), KeyboardButton(text=tr(lang, "top"))],
            [KeyboardButton(text=tr(lang, "commissions")), KeyboardButton(text=tr(lang, "forecast"))],
            [KeyboardButton(text=tr(lang, "broadcast")), KeyboardButton(text=tr(lang, "export"))],
            [KeyboardButton(text=tr(lang, "exit"))],
        ],
        resize_keyboard=True
    )

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            role TEXT, phone TEXT,
            first_name TEXT, last_name TEXT,
            online INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0, rides INTEGER DEFAULT 0,
            total_rides INTEGER DEFAULT 0,
            approved INTEGER DEFAULT 0,
            rejected INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'ru',
            sub_until TIMESTAMP,
            referred_by INTEGER,
            ref_count INTEGER DEFAULT 0, ref_activated INTEGER DEFAULT 0,
            car_brand TEXT, car_plate TEXT, car_class TEXT,
            car_photo TEXT, self_photo TEXT,
            driver_lat REAL, driver_lon REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER, driver_id INTEGER,
            from_lat REAL, from_lon REAL, to_lat REAL, to_lon REAL,
            distance REAL, price INTEGER, tariff TEXT,
            payment TEXT DEFAULT 'cash',
            promo TEXT DEFAULT '', discount INTEGER DEFAULT 0,
            scheduled_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            rating INTEGER DEFAULT 0,
            review TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS complaints(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER, from_role TEXT, text TEXT, answer TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sub_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS promos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, discount INTEGER,
            uses INTEGER DEFAULT 0, max_uses INTEGER DEFAULT 100,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS addresses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, title TEXT,
            lat REAL, lon REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        for col in ["first_name TEXT", "last_name TEXT", "car_class TEXT", "car_photo TEXT", "self_photo TEXT", "total_rides INTEGER DEFAULT 0", "approved INTEGER DEFAULT 0", "rejected INTEGER DEFAULT 0", "lang TEXT DEFAULT 'ru'"]:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN " + col)
            except Exception:
                pass
        for col in ["promo TEXT DEFAULT ''", "discount INTEGER DEFAULT 0", "review TEXT DEFAULT ''", "scheduled_at TIMESTAMP"]:
            try:
                await db.execute("ALTER TABLE orders ADD COLUMN " + col)
            except Exception:
                pass
        await db.commit()

async def is_registered(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT phone FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        return row and row[0]

async def set_role(uid, role):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id, role) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET role=excluded.role", (uid, role))
        await db.commit()

async def set_online(uid, val):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET online=? WHERE user_id=?", (val, uid))
        await db.commit()

async def has_subscription(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row or not row[0]:
            return False
        try:
            return datetime.fromisoformat(row[0]) > datetime.now()
        except Exception:
            return False

async def give_subscription(uid, days=1):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        base = datetime.now()
        if row and row[0]:
            try:
                old = datetime.fromisoformat(row[0])
                if old > base:
                    base = old
            except Exception:
                pass
        new_until = base + timedelta(days=days)
        await db.execute("UPDATE users SET sub_until=? WHERE user_id=?", (new_until.isoformat(), uid))
        await db.commit()
        return new_until
@router.message(F.text == "🇷🇺 Русский")
async def set_lang_ru(message: Message, state: FSMContext):
    uid = message.from_user.id
    await set_lang(uid, "ru")
    if await is_registered(uid):
        await message.answer("👋 С возвращением! Выберите роль:", reply_markup=main_menu("ru"))
    else:
        await state.set_state(Reg.phone)
        await message.answer("📱 Шаг 1/3: Отправьте свой номер телефона:", reply_markup=phone_kb())

@router.message(F.text == "🇹🇯 Тоҷикӣ")
async def set_lang_tj(message: Message, state: FSMContext):
    uid = message.from_user.id
    await set_lang(uid, "tj")
    if await is_registered(uid):
        await message.answer("👋 Хуш омадед! Нақши худро интихоб кунед:", reply_markup=main_menu("tj"))
    else:
        await state.set_state(Reg.phone)
        await message.answer("📱 Қадами 1/3: Рақами телефони худро фиристед:", reply_markup=phone_kb())

@router.message(F.text.in_(["🌍 Язык", "🌍 Забон"]))
async def change_lang(message: Message, state: FSMContext):
    await message.answer("👇 Выберите язык / Забонро интихоб кунед:", reply_markup=lang_kb())

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    args = (message.text or "").split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != uid:
                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute("SELECT referred_by FROM users WHERE user_id=?", (uid,))
                    row = await cur.fetchone()
                    if not row or not row[0]:
                        await db.execute("INSERT INTO users(user_id, referred_by) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET referred_by=excluded.referred_by", (uid, referrer_id))
                        await db.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (referrer_id,))
                        await db.commit()
                        try:
                            await message.bot.send_message(referrer_id, "🎁 По вашей ссылке зарегистрировался новый пользователь!")
                        except Exception:
                            pass
        except Exception:
            pass
    if not await is_registered(uid):
        await state.set_state(Reg.phone)
        await message.answer("🇷🇺 Добро пожаловать!\n🇹🇯 Хуш омадед!\n\n👇 Выберите язык / Забонро интихоб кунед:", reply_markup=lang_kb())
        return
    lang = await get_lang(uid)
    await message.answer(tr(lang, "choose_role"), reply_markup=main_menu(lang))

@router.message(Reg.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    uid = message.from_user.id
    phone = message.contact.phone_number
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id, phone) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone", (uid, phone))
        await db.commit()
    await state.set_state(Reg.first_name)
    await message.answer(tr(lang, "phone_saved"), reply_markup=ReplyKeyboardRemove())

@router.message(Reg.phone)
async def reg_phone_wrong(message: Message):
    await message.answer("⚠️ Нажмите кнопку внизу.")

@router.message(Reg.first_name)
async def reg_first_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()[:50]
    if not name:
        await message.answer("Напишите имя.")
        return
    lang = await get_lang(message.from_user.id)
    await state.update_data(first_name=name)
    await state.set_state(Reg.last_name)
    await message.answer(tr(lang, "name_saved") + name + tr(lang, "last_ask"))

@router.message(Reg.last_name)
async def reg_last_name(message: Message, state: FSMContext):
    last = (message.text or "").strip()[:50]
    if not last:
        await message.answer("Напишите фамилию.")
        return
    data = await state.get_data()
    uid = message.from_user.id
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET first_name=?, last_name=? WHERE user_id=?", (data["first_name"], last, uid))
        cur = await db.execute("SELECT phone FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        await db.commit()
    await state.clear()
    phone = row[0] if row else "-"
    if ADMIN_ID:
        try:
            uname = "@" + message.from_user.username if message.from_user.username else "-"
            await message.bot.send_message(ADMIN_ID, "Новый пользователь\n\n" + data["first_name"] + " " + last + "\n" + uname + "\n" + phone + "\nID: " + str(uid))
        except Exception:
            pass
    await message.answer(tr(lang, "reg_done") + data["first_name"] + " " + last + "\n" + phone + "\n\n" + tr(lang, "choose_role"), reply_markup=main_menu(lang))

@router.message(F.text.in_(["🚕 Я клиент", "🚕 Ман мизоҷ"]))
async def role_client(message: Message):
    uid = message.from_user.id
    if not await is_registered(uid):
        await message.answer("Сначала /start")
        return
    lang = await get_lang(uid)
    await set_role(uid, "client")
    await message.answer(tr(lang, "you_client"), reply_markup=client_menu(lang))

@router.message(F.text.in_(["🚗 Я водитель", "🚗 Ман ронанда"]))
async def role_driver(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not await is_registered(uid):
        await message.answer("Сначала /start")
        return
    lang = await get_lang(uid)
    await set_role(uid, "driver")
    await set_online(uid, 0)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class, car_photo, self_photo, approved, rejected FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if not row or not row[0] or not row[1] or not row[2] or not row[3] or not row[4]:
        await state.set_state(DriverReg.car_brand)
        await message.answer("🚗 Заполним данные о машине.\n\nУкажите марку автомобиля:", reply_markup=ReplyKeyboardRemove())
        return
    if row[6]:
        await message.answer(tr(lang, "rejected"), reply_markup=driver_menu(lang))
        return
    if not row[5]:
        await message.answer(tr(lang, "wait_approve"), reply_markup=driver_menu(lang))
        return
    sub_ok = await has_subscription(uid)
    sub_text = tr(lang, "sub_ok") if sub_ok else tr(lang, "sub_no")
    await message.answer(tr(lang, "you_driver") + sub_text, reply_markup=driver_menu(lang))

@router.message(F.text.in_(["🔄 Сменить роль", "🔄 Иваз кардани нақш"]))
async def change_role(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    await message.answer(tr(lang, "choose_role"), reply_markup=main_menu(lang))

@router.message(F.text.in_(["🚕 Заказать такси", "🚕 Фармоиши такси"]))
async def order_start(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await state.set_state(OrderFlow.from_loc)
    await message.answer(tr(lang, "from"), reply_markup=loc_kb())

@router.message(OrderFlow.from_loc, F.location)
async def from_loc(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await state.update_data(from_lat=message.location.latitude, from_lon=message.location.longitude)
    await state.set_state(OrderFlow.to_loc)
    await message.answer(tr(lang, "to"), reply_markup=loc_kb())

@router.message(OrderFlow.to_loc, F.location)
async def to_loc(message: Message, state: FSMContext):
    data = await state.get_data()
    dist = haversine(data["from_lat"], data["from_lon"], message.location.latitude, message.location.longitude)
    if dist < 0.1:
        await message.answer("⚠️ Слишком близко.")
        return
    await state.update_data(to_lat=message.location.latitude, to_lon=message.location.longitude, distance=dist)
    eta = estimate_minutes(dist)
    builder = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        price = int(t["base"] + t["rate"] * dist)
        builder.button(text=t["name"] + " - " + str(price) + " сомони", callback_data="tariff:" + key)
    builder.adjust(1)
    await state.set_state(OrderFlow.tariff)
    await message.answer("📏 ~" + str(round(dist, 1)) + " км\n⏳ ~" + str(eta) + " мин\n\nВыберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(OrderFlow.tariff, F.data.startswith("tariff:"))
async def choose_tariff(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    data = await state.get_data()
    price = int(TARIFFS[key]["base"] + TARIFFS[key]["rate"] * data["distance"])
    await state.update_data(tariff=key, price=price)
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Наличные", callback_data="pay:cash")
    builder.button(text="💳 Картой", callback_data="pay:card")
    builder.adjust(2)
    await state.set_state(OrderFlow.payment)
    await call.message.edit_text(TARIFFS[key]["name"] + "\n💰 " + str(price) + " сомони\n\nОплата?", reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(OrderFlow.payment, F.data.startswith("pay:"))
async def choose_payment(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(payment=method)
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Есть промокод", callback_data="promo_yes")
    builder.button(text="➡️ Пропустить", callback_data="promo_skip")
    builder.adjust(2)
    await state.set_state(OrderFlow.promo)
    await call.message.edit_text("🎁 У вас есть промокод?", reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(OrderFlow.promo, F.data == "promo_yes")
async def promo_yes(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 Напишите промокод:")
    await call.answer()

@router.message(OrderFlow.promo, F.text)
async def promo_apply(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT discount, uses, max_uses, active FROM promos WHERE code=?", (code,))
        row = await cur.fetchone()
    if not row or not row[3]:
        await message.answer("❌ Промокод не найден.")
        return
    discount, uses, max_uses, active = row
    if uses >= max_uses:
        await message.answer("❌ Исчерпан.")
        return
    data = await state.get_data()
    new_price = max(0, int(data["price"] * (100 - discount) / 100))
    await state.update_data(promo=code, discount=discount, price=new_price)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promos SET uses = uses + 1 WHERE code=?", (code,))
        await db.commit()
    lang = await get_lang(message.from_user.id)
    await state.set_state(OrderFlow.when)
    await message.answer("🕐 Когда подать машину?", reply_markup=when_kb(lang))

@router.callback_query(OrderFlow.promo, F.data == "promo_skip")
async def promo_skip(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    await state.set_state(OrderFlow.when)
    await call.message.edit_text("🕐 Когда подать машину?")
    await call.message.answer("Выберите:", reply_markup=when_kb(lang))
    await call.answer()

@router.message(OrderFlow.when, F.text.in_(["🚕 Сейчас", "⏰ Через 30 мин", "⏰ Через 1 час", "⏰ Через 2 часа", "⏰ Через 4 часа", "🚕 Ҳозир", "⏰ Баъди 30 дақиқа", "⏰ Баъди 1 соат", "⏰ Баъди 2 соат", "⏰ Баъди 4 соат"]))
async def when_choose(message: Message, state: FSMContext):
    txt = message.text
    now = datetime.now()
    if txt in ("🚕 Сейчас", "🚕 Ҳозир"):
        scheduled = now
    elif txt in ("⏰ Через 30 мин", "⏰ Баъди 30 дақиқа"):
        scheduled = now + timedelta(minutes=30)
    elif txt in ("⏰ Через 1 час", "⏰ Баъди 1 соат"):
        scheduled = now + timedelta(hours=1)
    elif txt in ("⏰ Через 2 часа", "⏰ Баъди 2 соат"):
        scheduled = now + timedelta(hours=2)
    elif txt in ("⏰ Через 4 часа", "⏰ Баъди 4 соат"):
        scheduled = now + timedelta(hours=4)
    else:
        scheduled = now
    await state.update_data(scheduled_at=scheduled.isoformat())
    await show_confirm(message, state)

@router.message(OrderFlow.when, F.text.in_(["🕐 Своё время", "🕐 Вақти дигар"]))
async def when_custom(message: Message, state: FSMContext):
    await state.set_state(OrderFlow.when_custom)
    await message.answer("📝 Напишите время в формате ЧЧ:ММ\nНапример: 06:30")

@router.message(OrderFlow.when_custom)
async def when_custom_save(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    try:
        parts = txt.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
        now = datetime.now()
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if scheduled <= now:
            scheduled = scheduled + timedelta(days=1)
    except Exception:
        await message.answer("⚠️ Неверный формат. Попробуйте ещё раз:")
        return
    await state.update_data(scheduled_at=scheduled.isoformat())
    await show_confirm(message, state)

@router.message(OrderFlow.when)
async def when_wrong(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await message.answer("Выберите из кнопок ниже:", reply_markup=when_kb(lang))

async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    promo_text = ""
    if data.get("promo"):
        promo_text = "\n🎁 Промокод: " + data["promo"]
    sched_text = ""
    if data.get("scheduled_at"):
        try:
            sdt = datetime.fromisoformat(data["scheduled_at"])
            if (sdt - datetime.now()).total_seconds() > 300:
                sched_text = "\n📅 На время: " + sdt.strftime("%d.%m %H:%M")
            else:
                sched_text = "\n🚕 Сейчас"
        except Exception:
            pass
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.adjust(2)
    await state.set_state(OrderFlow.confirm)
    await message.answer(TARIFFS[data["tariff"]]["name"] + "\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + promo_text + sched_text + "\n\nПодтвердить?", reply_markup=builder.as_markup())

@router.callback_query(OrderFlow.confirm, F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Отменено.")
    lang = await get_lang(call.from_user.id)
    await call.message.answer("В меню.", reply_markup=client_menu(lang))
    await call.answer()

@router.callback_query(OrderFlow.confirm, F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sched_at = data.get("scheduled_at")
    is_scheduled = False
    if sched_at:
        try:
            sdt = datetime.fromisoformat(sched_at)
            if (sdt - datetime.now()).total_seconds() > 300:
                is_scheduled = True
        except Exception:
            pass
    status = "scheduled" if is_scheduled else "pending"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders(client_id, from_lat, from_lon, to_lat, to_lon, distance, price, tariff, payment, promo, discount, scheduled_at, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (call.from_user.id, data["from_lat"], data["from_lon"], data["to_lat"], data["to_lon"], data["distance"], data["price"], data["tariff"], data.get("payment", "cash"), data.get("promo", ""), data.get("discount", 0), sched_at, status))
        order_id = cur.lastrowid
        await db.commit()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заказ", callback_data="client_cancel:" + str(order_id))
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    eta = estimate_minutes(data["distance"])
    if is_scheduled:
        sdt = datetime.fromisoformat(sched_at)
        await call.message.edit_text("✅ Заказ #" + str(order_id) + " создан!\n\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + "\n\n📅 На время: " + sdt.strftime("%d.%m.%Y %H:%M") + "\n\nМы напомним водителям за 40 минут.")
    else:
        await call.message.edit_text("✅ Заказ #" + str(order_id) + " создан!\n\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + "\n⏳ " + str(eta) + " мин\n\n🔍 Ищем водителя...")
        await notify_drivers(call.bot, order_id, data)
    await call.message.answer("Ожидайте:", reply_markup=builder.as_markup())
    await call.answer()

async def notify_drivers(bot: Bot, order_id: int, data: dict):
    flat = data.get("from_lat")
    flon = data.get("from_lon")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, driver_lat, driver_lon FROM users WHERE role='driver' AND online=1 AND approved=1 AND rejected=0")
        drivers = await cur.fetchall()
    if not drivers:
        return
    near = []
    far = []
    for uid, dlat, dlon in drivers:
        if dlat and dlon and flat and flon:
            dist = haversine(dlat, dlon, flat, flon)
            if dist <= NEAR_RADIUS:
                near.append((uid, dist))
            else:
                far.append((uid, dist))
        else:
            far.append((uid, 999))
    near.sort(key=lambda x: x[1])
    far.sort(key=lambda x: x[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Принять заказ", callback_data="accept:" + str(order_id))
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    text = "🔔 Новый заказ #" + str(order_id) + "\n\n" + TARIFFS[data["tariff"]]["name"] + "\n💳 " + pay_text + "\n📏 " + str(round(data["distance"], 1)) + " км\n💰 " + str(data["price"]) + " сомони"
    for uid, _ in near:
        try:
            for _i in range(3):
                await bot.send_message(uid, text, reply_markup=builder.as_markup())
                await asyncio.sleep(0.3)
        except Exception as e:
            logging.warning("Error: " + str(e))
    if near:
        await asyncio.sleep(45)
    for uid, _ in far:
        try:
            await bot.send_message(uid, text, reply_markup=builder.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))
@router.callback_query(F.data.startswith("accept:"))
async def accept_order(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, client_id, price, from_lat, from_lon, to_lat, to_lon, payment FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row:
            await call.answer("Не найден", show_alert=True)
            return
        status, client_id, price, flat, flon, tlat, tlon, payment = row
        if status not in ("pending", "scheduled"):
            await call.answer("Уже занят", show_alert=True)
            return
        await db.execute("UPDATE orders SET driver_id=?, status='accepted' WHERE id=?", (call.from_user.id, order_id))
        await db.commit()
    pay_text = "💵 Наличные" if payment == "cash" else "💳 Картой"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class, driver_lat, driver_lon, phone, first_name, last_name, car_photo, self_photo FROM users WHERE user_id=?", (call.from_user.id,))
        drow = await cur.fetchone()
        cur = await db.execute("SELECT phone, first_name, last_name FROM users WHERE user_id=?", (client_id,))
        crow = await cur.fetchone()
    car_brand = drow[0] if drow and drow[0] else "-"
    car_plate = drow[1] if drow and drow[1] else "-"
    car_class = drow[2] if drow and drow[2] else "-"
    driver_phone = drow[5] if drow else "-"
    driver_name = ((drow[6] or "") + " " + (drow[7] or "")).strip() if drow else "Водитель"
    driver_self_photo = drow[9] if drow else None
    client_phone = crow[0] if crow else "-"
    client_name = ((crow[1] or "") + " " + (crow[2] or "")).strip() if crow else "Клиент"
    dlat = drow[3] if drow else None
    dlon = drow[4] if drow else None
    if dlat and dlon:
        eta_driver = estimate_minutes(haversine(dlat, dlon, flat, flon))
    else:
        eta_driver = None
    eta_ride = estimate_minutes(haversine(flat, flon, tlat, tlon))
    eta_driver_text = str(eta_driver) + " мин" if eta_driver else "-"
    eta_ride_text = str(eta_ride) + " мин" if eta_ride else "-"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referred_by, ref_activated FROM users WHERE user_id=?", (call.from_user.id,))
        ref_row = await cur.fetchone()
        if ref_row and ref_row[0] and not ref_row[1]:
            referrer_id = ref_row[0]
            await db.execute("UPDATE users SET ref_activated=1 WHERE user_id=?", (call.from_user.id,))
            cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND ref_activated=1", (referrer_id,))
            cnt = (await cur.fetchone())[0]
            if cnt >= REF_TARGET and cnt % REF_TARGET == 0:
                await give_subscription(referrer_id, days=REF_BONUS_DAYS)
                try:
                    await call.bot.send_message(referrer_id, "🎉 Бонус! +" + str(REF_BONUS_DAYS) + " дня подписки!")
                except Exception:
                    pass
            await db.commit()
    await call.message.edit_text("✅ Вы приняли заказ #" + str(order_id) + "\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ До клиента: " + eta_driver_text + "\n⏳ Поездка: " + eta_ride_text + "\n\n👤 " + client_name + "\n📞 " + str(client_phone))
    await call.bot.send_location(call.from_user.id, latitude=flat, longitude=flon)
    await call.bot.send_message(call.from_user.id, "🚕 Маршрут к клиенту (точка A):\n" + nav_link(dlat if dlat else flat, dlon if dlon else flon, flat, flon))
    dkb = InlineKeyboardBuilder()
    dkb.button(text="🚗 Я выехал", callback_data="drv_status:on_way:" + str(order_id))
    dkb.button(text="📍 Я рядом", callback_data="drv_status:near:" + str(order_id))
    dkb.button(text="✅ Я приехал (взял клиента)", callback_data="drv_status:picked:" + str(order_id))
    dkb.button(text="💬 Чат с клиентом", callback_data="chat_start:" + str(order_id))
    dkb.button(text="✅ Завершить поездку", callback_data="finish:" + str(order_id))
    dkb.adjust(1)
    await call.bot.send_message(call.from_user.id, "🎛 Управление поездкой:", reply_markup=dkb.as_markup())
    ckb = InlineKeyboardBuilder()
    ckb.button(text="💬 Чат с водителем", callback_data="chat_start:" + str(order_id))
    ckb.button(text="📍 Где водитель", callback_data="where_driver:" + str(order_id))
    ckb.adjust(1)
    if driver_self_photo:
        try:
            await call.bot.send_photo(client_id, photo=driver_self_photo, caption="🚗 Водитель принял заказ #" + str(order_id) + "\n\n👤 " + driver_name + "\n📞 " + str(driver_phone) + "\n\n🚙 " + car_brand + " " + car_plate + " (" + car_class + ")\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ Подъедет через: " + eta_driver_text + "\n⏳ Поездка: " + eta_ride_text)
        except Exception:
            await call.bot.send_message(client_id, "🚗 Водитель принял заказ #" + str(order_id) + "\n\n👤 " + driver_name + "\n📞 " + str(driver_phone) + "\n\n🚙 " + car_brand + " " + car_plate + " (" + car_class + ")\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ Подъедет через: " + eta_driver_text)
    else:
        await call.bot.send_message(client_id, "🚗 Водитель принял заказ #" + str(order_id) + "\n\n👤 " + driver_name + "\n📞 " + str(driver_phone) + "\n\n🚙 " + car_brand + " " + car_plate + " (" + car_class + ")\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ Подъедет через: " + eta_driver_text)
    await call.bot.send_message(client_id, "🎛 Действия:", reply_markup=ckb.as_markup())
    await call.answer("Заказ принят")

@router.callback_query(F.data.startswith("drv_status:"))
async def drv_status(call: CallbackQuery):
    parts = call.data.split(":")
    status_type = parts[1]
    order_id = int(parts[2])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, status, to_lat, to_lon FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row or row[1] not in ("accepted", "arrived", "started"):
        await call.answer("Не активен", show_alert=True)
        return
    client_id = row[0]
    tlat = row[2]
    tlon = row[3]
    texts = {
        "on_way": "🚗 Водитель выехал к вам!",
        "near": "📍 Водитель уже рядом!",
        "arrived": "✅ Водитель приехал! Выходите к машине.",
        "picked": "🚗 Водитель забрал вас! Поехали к месту назначения.",
    }
    if status_type in texts:
        try:
            await call.bot.send_message(client_id, texts[status_type])
        except Exception:
            pass
    if status_type in ("arrived", "picked"):
        new_status = "arrived" if status_type == "arrived" else "started"
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
            await db.commit()
    if status_type == "picked":
        try:
            await call.bot.send_message(call.from_user.id, "🚕 Маршрут к месту назначения (точка B):\n" + nav_link(0, 0, tlat, tlon))
        except Exception:
            pass
    await call.answer("Отправлено клиенту")

@router.callback_query(F.data.startswith("where_driver:"))
async def where_driver(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[1] not in ("accepted", "arrived", "started"):
            await call.answer("Не активен", show_alert=True)
            return
        driver_id = row[0]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_lat, driver_lon FROM users WHERE user_id=?", (driver_id,))
        drow = await cur.fetchone()
    if drow and drow[0]:
        await call.bot.send_location(call.from_user.id, latitude=drow[0], longitude=drow[1])
        await call.answer("Локация отправлена")
    else:
        await call.answer("Водитель не отправил локацию", show_alert=True)

@router.callback_query(F.data.startswith("chat_start:"))
async def chat_start(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, driver_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row or row[2] not in ("accepted", "arrived", "started"):
        await call.answer("Чат доступен только во время поездки", show_alert=True)
        return
    client_id, driver_id, status = row
    if call.from_user.id == client_id:
        partner_id = driver_id
    elif call.from_user.id == driver_id:
        partner_id = client_id
    else:
        await call.answer("Вы не участник", show_alert=True)
        return
    await state.set_state(ChatMode.chatting)
    await state.update_data(order_id=order_id, partner_id=partner_id)
    await call.message.answer("💬 Чат открыт. Пишите сообщения.\n\nДля выхода нажмите Выйти из чата.", reply_markup=chat_kb())
    await call.answer()

@router.message(ChatMode.chatting, F.text == "❌ Выйти из чата")
async def chat_exit(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    await message.answer("Чат закрыт.", reply_markup=main_menu(lang))

@router.message(ChatMode.chatting, F.location)
async def chat_location(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    if not partner_id:
        await state.clear()
        return
    try:
        await message.bot.send_message(partner_id, "📍 Локация от собеседника:")
        await message.bot.send_location(partner_id, latitude=message.location.latitude, longitude=message.location.longitude)
    except Exception:
        pass

@router.message(ChatMode.chatting, F.text)
async def chat_send(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    if not partner_id:
        await state.clear()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, last_name, role FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
    name = ((row[0] or "") + " " + (row[1] or "")).strip() if row else "Собеседник"
    role = row[2] if row else ""
    role_text = "🚗 Водитель" if role == "driver" else "🚕 Клиент"
    try:
        await message.bot.send_message(partner_id, role_text + " - " + name + ":\n\n" + message.text)
        await message.answer("✅ Отправлено", reply_markup=chat_kb())
    except Exception:
        await message.answer("⚠️ Не доставлено", reply_markup=chat_kb())

@router.callback_query(F.data.startswith("client_cancel:"))
async def client_cancel(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, driver_id FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[0] not in ("pending", "scheduled", "accepted", "arrived", "started"):
            await call.answer("Нельзя", show_alert=True)
            return
        status, driver_id = row
        await db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        await db.commit()
    await call.message.edit_text("❌ Заказ отменён.")
    if driver_id:
        try:
            await call.bot.send_message(driver_id, "⚠️ Клиент отменил заказ #" + str(order_id))
        except Exception:
            pass
    await call.answer()

@router.callback_query(F.data.startswith("finish:"))
async def finish_ride(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, driver_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row:
            await call.answer("Не найден", show_alert=True)
            return
        client_id, driver_id, status = row
        if status not in ("accepted", "arrived", "started"):
            await call.answer("Уже завершён", show_alert=True)
            return
        await db.execute("UPDATE orders SET status='finished' WHERE id=?", (order_id,))
        await db.execute("UPDATE users SET rides=rides+1, total_rides=COALESCE(total_rides,0)+1 WHERE user_id=?", (driver_id,))
        await db.commit()
    await call.message.edit_text("✅ Поездка завершена.")
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data="rate:" + str(order_id) + ":" + str(i))
    builder.adjust(5)
    await call.bot.send_message(client_id, "🏁 Поездка #" + str(order_id) + " завершена!\n\nОцените водителя:", reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(F.data.startswith("rate:"))
async def rate_driver(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    order_id, score = int(parts[1]), int(parts[2])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, rating FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[1] != 0:
            await call.answer("Уже оценено")
            return
        driver_id = row[0]
        await db.execute("UPDATE orders SET rating=? WHERE id=?", (score, order_id))
        cur = await db.execute("SELECT rating, rides FROM users WHERE user_id=?", (driver_id,))
        old_rating, rides = await cur.fetchone()
        new_rating = ((old_rating * max(rides - 1, 0)) + score) / max(rides, 1)
        await db.execute("UPDATE users SET rating=? WHERE user_id=?", (new_rating, driver_id))
        await db.commit()
    await state.set_state(Review.text)
    await state.update_data(order_id=order_id, driver_id=driver_id)
    await call.message.edit_text("Спасибо! " + str(score) + " ⭐\n\nНапишите отзыв (или - чтобы пропустить):")
    await call.answer()

@router.message(Review.text)
async def review_save(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()
    lang = await get_lang(message.from_user.id)
    if text and text != "-":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET review=? WHERE id=?", (text[:500], data.get("order_id")))
            await db.commit()
        driver_id = data.get("driver_id")
        if driver_id:
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute("SELECT first_name FROM users WHERE user_id=?", (message.from_user.id,))
                    r = await cur.fetchone()
                name = r[0] if r else "Клиент"
                await message.bot.send_message(driver_id, "⭐ Новый отзыв\n\nОт: " + name + "\n\n" + text[:300])
            except Exception:
                pass
        await message.answer("✅ Отзыв сохранён. Спасибо!", reply_markup=main_menu(lang))
    else:
        await message.answer("✅ Спасибо!", reply_markup=main_menu(lang))

@router.message(F.text.in_(["📋 История", "📋 Таърих"]))
async def my_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, price, status, tariff FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 20", (message.from_user.id,))
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    text = "📋 История поездок\n\n"
    total = 0
    for oid, price, status, tariff in rows:
        text += "#" + str(oid) + " " + TARIFFS[tariff]["name"] + " " + str(price) + " сомони (" + status + ")\n"
        if status == "finished":
            total += price
    text += "\n💰 Всего потрачено: " + str(total) + " сомони"
    await message.answer(text)

@router.message(F.text.in_(["⚠️ Пожаловаться", "⚠️ Шикоят"]))
async def complaint_start(message: Message, state: FSMContext):
    await state.set_state(Complaint.text)
    await message.answer("⚠️ Опишите проблему:", reply_markup=ReplyKeyboardRemove())

@router.message(Complaint.text)
async def complaint_send(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT role, phone, first_name, last_name FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        role = row[0] if row and row[0] else "?"
        phone = row[1] if row and row[1] else "-"
        name = ((row[2] or "") + " " + (row[3] or "")).strip() if row else "-"
        cur = await db.execute("INSERT INTO complaints(from_id, from_role, text) VALUES(?,?,?)", (uid, role, text))
        cid = cur.lastrowid
        await db.commit()
    await state.clear()
    if ADMIN_ID:
        try:
            b = InlineKeyboardBuilder()
            b.button(text="✉️ Ответить", callback_data="reply_compl:" + str(cid))
            b.adjust(1)
            await message.bot.send_message(ADMIN_ID, "⚠️ Жалоба #" + str(cid) + "\n\n" + name + "\n📱 " + str(phone) + "\n🎭 " + role + "\n🆔 " + str(uid) + "\n\n📝 " + text, reply_markup=b.as_markup())
        except Exception:
            pass
    await message.answer("✅ Отправлено.", reply_markup=main_menu(lang))

@router.callback_query(F.data.startswith("reply_compl:"))
async def admin_reply_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    cid = int(call.data.split(":")[1])
    await state.update_data(complaint_id=cid)
    await state.set_state(AdminReply.waiting)
    await call.message.answer("✍️ Ответ:")
    await call.answer()

@router.message(AdminReply.waiting)
async def admin_reply_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    cid = data.get("complaint_id")
    if not cid:
        await state.clear()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT from_id FROM complaints WHERE id=?", (cid,))
        row = await cur.fetchone()
        if not row:
            await message.answer("Не найдена")
            await state.clear()
            return
        uid = row[0]
        await db.execute("UPDATE complaints SET answer=?, status='answered' WHERE id=?", (message.text, cid))
        await db.commit()
    try:
        await message.bot.send_message(uid, "✉️ Ответ на жалобу #" + str(cid) + "\n\n" + message.text)
        await message.answer("✅ Отправлено.")
    except Exception:
        await message.answer("⚠️ Не доставлено.")
    await state.clear()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    lang = await get_lang(message.from_user.id)
    await message.answer("👑 Админ-панель", reply_markup=admin_menu(lang))

@router.message(F.text.in_(["🔙 Выйти", "🔙 Баромад"]))
async def admin_exit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    lang = await get_lang(message.from_user.id)
    await message.answer("Выход.", reply_markup=main_menu(lang))

@router.message(F.text.in_(["📊 Статистика", "📊 Омор"]))
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='client'")
        clients = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='driver'")
        drivers = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        total = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM orders WHERE status='finished'")
        fin = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM orders WHERE status='cancelled'")
        can = (await cur.fetchone())[0]
        cur = await db.execute("SELECT SUM(price) FROM orders WHERE status='finished'")
        rev = (await cur.fetchone())[0] or 0
        cur = await db.execute("SELECT COUNT(*) FROM complaints WHERE status='new'")
        comp = (await cur.fetchone())[0]
    text = "📊 Статистика\n\n👤 Клиентов: " + str(clients) + "\n🚗 Водителей: " + str(drivers) + "\n📦 Заказов: " + str(total) + "\n✅ Завершено: " + str(fin) + "\n❌ Отменено: " + str(can) + "\n💰 Оборот: " + str(rev) + " сомони\n💵 Комиссия 10%: " + str(int(rev * 0.1)) + " сомони\n⚠️ Новых жалоб: " + str(comp)
    await message.answer(text)

@router.message(F.text.in_(["🚗 Водители", "🚗 Ронандагон"]))
async def admin_drivers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone, first_name, last_name, online, rating, rides, car_brand, car_plate, car_class, approved, rejected FROM users WHERE role='driver' ORDER BY rides DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Водителей нет.")
        return
    text = "🚗 Водители\n\n"
    for uid, phone, fn, ln, online, rating, rides, brand, plate, cls, approved, rejected in rows:
        on = "🟢" if online else "⚪"
        name = ((fn or "") + " " + (ln or "")).strip()
        status = "✅" if approved else ("❌" if rejected else "⏳")
        text += on + " [" + status + "] " + name + "\n📞 " + str(phone) + "\n🚙 " + str(brand or "-") + " " + str(plate or "-") + " (" + str(cls or "-") + ")\n⭐ " + str(round(rating, 1)) + " | 🚕 " + str(rides) + "\n\n"
    await message.answer(text)

@router.message(F.text.in_(["👤 Клиенты", "👤 Мизоҷон"]))
async def admin_clients(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone, first_name, last_name FROM users WHERE role='client' ORDER BY created_at DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Клиентов нет.")
        return
    text = "👤 Клиенты\n\n"
    for uid, phone, fn, ln in rows:
        name = ((fn or "") + " " + (ln or "")).strip() or "-"
        text += name + " - " + str(phone) + "\n"
    await message.answer(text)

@router.message(F.text.in_(["📦 Заказы", "📦 Фармоишҳо"]))
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, client_id, driver_id, price, status FROM orders ORDER BY id DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    text = "📦 Заказы\n\n"
    for oid, cid, did, price, status in rows:
        text += "#" + str(oid) + " " + str(price) + " сомони " + status + " К:" + str(cid) + " В:" + str(did or "-") + "\n"
    await message.answer(text)

@router.message(F.text.in_(["⚠️ Жалобы", "⚠️ Шикоятҳо"]))
async def admin_complaints(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, from_id, from_role, text FROM complaints WHERE status='new' ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("✅ Жалоб нет.")
        return
    for cid, fid, role, text in rows:
        b = InlineKeyboardBuilder()
        b.button(text="✉️ Ответить", callback_data="reply_compl:" + str(cid))
        b.adjust(1)
        await message.answer("⚠️ Жалоба #" + str(cid) + " от " + str(fid) + " (" + role + "):\n\n" + text, reply_markup=b.as_markup())

@router.message(F.text.in_(["💳 Заявки", "💳 Дархостҳо"]))
async def admin_sub_requests(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, driver_id FROM sub_requests WHERE status='pending' ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("✅ Заявок нет.")
        return
    for _, driver_id in rows:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Подтвердить", callback_data="sub_ok:" + str(driver_id))
        b.button(text="❌ Отклонить", callback_data="sub_no:" + str(driver_id))
        b.adjust(2)
        await message.answer("💳 Заявка от " + str(driver_id), reply_markup=b.as_markup())

@router.message(F.text.in_(["🎁 Промокоды", "🎁 Промокодҳо"]))
async def admin_promos(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT code, discount, uses, max_uses, active FROM promos ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    text = "🎁 Промокоды\n\n"
    if not rows:
        text += "Нет промокодов.\n"
    else:
        for code, disc, uses, mx, act in rows:
            text += ("✅" if act else "❌") + " " + code + " - " + str(disc) + "% (" + str(uses) + "/" + str(mx) + ")\n"
    text += "\nСоздать: /newpromo"
    await message.answer(text)

@router.message(Command("newpromo"))
async def new_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(PromoCreate.code)
    await message.answer("📝 Код промокода:")

@router.message(PromoCreate.code)
async def promo_set_code(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()[:20]
    if not code:
        await message.answer("Введите код.")
        return
    await state.update_data(code=code)
    await state.set_state(PromoCreate.discount)
    await message.answer("💰 Скидка в % (1-99):")

@router.message(PromoCreate.discount)
async def promo_set_disc(message: Message, state: FSMContext):
    try:
        disc = int(message.text.strip())
        if disc < 1 or disc > 99:
            raise ValueError
    except Exception:
        await message.answer("Введите 1-99.")
        return
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO promos(code, discount) VALUES(?, ?)", (data["code"], disc))
            await db.commit()
            await message.answer("✅ Промокод " + data["code"] + " - " + str(disc) + "%")
        except Exception:
            await message.answer("⚠️ Уже существует.")
    await state.clear()

@router.message(F.text.in_(["⭐ Отзывы", "⭐ Шарҳҳо"]))
async def admin_reviews(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, driver_id, rating, review FROM orders WHERE review != '' ORDER BY id DESC LIMIT 15")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Отзывов пока нет.")
        return
    text = "⭐ Последние отзывы\n\n"
    for oid, did, rating, review in rows:
        text += "Заказ #" + str(oid) + " Водитель: " + str(did) + " ⭐" + str(rating) + "\n"
        text += review[:150] + "\n\n"
    await message.answer(text)

@router.message(F.text.in_(["💰 Комиссии", "💰 Комиссияҳо"]))
async def admin_commissions(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND driver_id IS NOT NULL GROUP BY driver_id ORDER BY SUM(price) DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Нет завершённых заказов.")
        return
    text = "💰 Комиссии 10%\n\n"
    total_comm = 0
    for did, cnt, total in rows:
        comm = int(total * 0.1)
        total_comm += comm
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT first_name, last_name FROM users WHERE user_id=?", (did,))
            urow = await cur.fetchone()
        name = ((urow[0] or "") + " " + (urow[1] or "")).strip() if urow else str(did)
        text += name + ": " + str(cnt) + " поездок, " + str(comm) + " сомони\n"
    text += "\n💰 Итого: " + str(total_comm) + " сомони"
    await message.answer(text)

@router.message(F.text.in_(["📈 Прогноз", "📈 Пешгӯӣ"]))
async def admin_forecast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    now = datetime.now()
    day_ago = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND created_at >= ?", (day_ago,))
        d1 = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND created_at >= ?", (week_ago,))
        d7 = await cur.fetchone()
    per_day = d7[1] / 7 if d7[0] else 0
    month = per_day * 30
    text = "📈 Прогноз\n\nЗа сутки: " + str(d1[0]) + " заказов, " + str(d1[1]) + " сомони\nЗа 7 дней: " + str(d7[0]) + " заказов, " + str(d7[1]) + " сомони\n\n📊 Средний доход/день: " + str(round(per_day, 1)) + " сомони\nПрогноз на 30 дней: " + str(int(month)) + " сомони\n💵 Комиссия 10%: " + str(int(month * 0.1)) + " сомони"
    await message.answer(text)

@router.message(F.text.in_(["📢 Рассылка", "📢 Паём"]))
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(Broadcast.text)
    await message.answer("📢 Напишите текст. Отмена: /cancel", reply_markup=ReplyKeyboardRemove())

@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    await message.answer("Отменено.", reply_markup=admin_menu(lang))

@router.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE role IN ('client', 'driver')")
        rows = await cur.fetchall()
    sent = 0
    for (uid,) in rows:
        if uid == ADMIN_ID:
            continue
        try:
            await message.bot.send_message(uid, "📢 Сообщение от администратора:\n\n" + text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    lang = await get_lang(message.from_user.id)
    await message.answer("✅ Отправлено: " + str(sent), reply_markup=admin_menu(lang))

@router.message(F.text.in_(["📥 Экспорт CSV", "📥 CSV содирот"]))
async def admin_export(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, client_id, driver_id, price, status, tariff, distance, created_at FROM orders ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client", "Driver", "Price", "Status", "Tariff", "Distance", "Date"])
    for r in rows:
        writer.writerow(r)
    data = buf.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(data, filename="orders.csv")
    await message.answer_document(file, caption="📥 Экспорт: " + str(len(rows)))

@router.message(F.text.in_(["🎁 Приведи друга", "🎁 Дӯстро даъват кунед"]))
async def ref_info(message: Message):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT ref_count, ref_activated FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    count = row[0] if row else 0
    activated = row[1] if row else 0
    bot_info = await message.bot.get_me()
    ref_link = "https://t.me/" + bot_info.username + "?start=ref_" + str(uid)
    text = "🎁 Приведи друга\n\nПригласите " + str(REF_TARGET) + " друзей и получите " + str(REF_BONUS_DAYS) + " дня подписки!\n\n📊 Приглашено: " + str(count) + "\n✅ Активировано: " + str(activated) + "\n\n🔗 " + ref_link
    await message.answer(text)

@router.message(F.text.in_(["🚗 Моя машина", "🚗 Мошини ман"]))
async def my_car(message: Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    brand = row[0] if row and row[0] else "-"
    plate = row[1] if row and row[1] else "-"
    cls = row[2] if row and row[2] else "-"
    await state.set_state(DriverReg.car_brand)
    await message.answer("🚗 Ваша машина\n\n" + brand + " " + plate + " (" + cls + ")\n\nВведите новую марку:", reply_markup=ReplyKeyboardRemove())

@router.message(F.text.in_(["💰 Мой заработок", "💰 Даромади ман"]))
async def my_earn(message: Message):
    uid = message.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)=?", (uid, today))
        row1 = await cur.fetchone()
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)>=?", (uid, week_ago))
        row2 = await cur.fetchone()
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)>=?", (uid, month_ago))
        row3 = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished'", (uid,))
        row4 = await cur.fetchone()
    text = "💰 Мой заработок\n\nСегодня: " + str(row1[0]) + " поездок, " + str(row1[1]) + " сомони\n7 дней: " + str(row2[0]) + " поездок, " + str(row2[1]) + " сомони\n30 дней: " + str(row3[0]) + " поездок, " + str(row3[1]) + " сомони\nВсего: " + str(row4[0]) + " поездок, " + str(row4[1]) + " сомони"
    await message.answer(text)

@router.message(F.text.in_(["📊 График заработка", "📊 Графики даромад"]))
async def graph_earn(message: Message):
    is_admin = (message.from_user.id == ADMIN_ID)
    uid = message.from_user.id
    if is_admin:
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND DATE(created_at)=?", (today,))
            d1 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND DATE(created_at)>=?", (week_ago,))
            d7 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND DATE(created_at)>=?", (month_ago,))
            d30 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND DATE(created_at)>=?", (year_ago,))
            d365 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*) FROM sub_requests WHERE status='approved'")
            subs = (await cur.fetchone())[0]
            sub_money = subs * SUB_PRICE
        text = "📊 График заработка\n\n📅 Сегодня: " + str(d1[0]) + " заказов, " + str(d1[1]) + " сомони\n📅 7 дней: " + str(d7[0]) + " заказов, " + str(d7[1]) + " сомони\n📅 30 дней: " + str(d30[0]) + " заказов, " + str(d30[1]) + " сомони\n📅 365 дней: " + str(d365[0]) + " заказов, " + str(d365[1]) + " сомони\n\n💳 Подписок: " + str(subs) + "\n💰 С подписок: " + str(sub_money) + " сомони\n\n💵 Комиссия 10%:\nСегодня: " + str(int(d1[1] * 0.1)) + "\n7 дней: " + str(int(d7[1] * 0.1)) + "\n30 дней: " + str(int(d30[1] * 0.1)) + "\n\n🏆 Итого 30 дней: " + str(int(d30[1] * 0.1) + sub_money) + " сомони"
        await message.answer(text)
        return
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)=?", (uid, today))
        row1 = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)>=?", (uid, week_ago))
        row2 = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)>=?", (uid, month_ago))
        row3 = await cur.fetchone()
    text = "📊 Мой график\n\nСегодня: " + str(row1[0]) + " поездок, " + str(row1[1]) + " сомони\n7 дней: " + str(row2[0]) + " поездок, " + str(row2[1]) + " сомони\n30 дней: " + str(row3[0]) + " поездок, " + str(row3[1]) + " сомони"
    await message.answer(text)

@router.message(F.text.in_(["📊 Моя статистика", "📊 Омори ман"]))
async def my_stats(message: Message):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT rating, rides, total_rides, first_name, last_name, car_brand, car_plate, car_class FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(AVG(rating),0) FROM orders WHERE driver_id=? AND rating > 0", (uid,))
        rrow = await cur.fetchone()
    if not row:
        await message.answer("Ошибка.")
        return
    rating = row[0] or 5.0
    name = ((row[3] or "") + " " + (row[4] or "")).strip()
    car = str(row[5] or "-") + " " + str(row[6] or "-") + " (" + str(row[7] or "-") + ")"
    text = "📊 Моя статистика\n\n👤 " + name + "\n🚗 " + car + "\n⭐ Рейтинг: " + str(round(rating, 2)) + "\n🚕 Всего поездок: " + str(row[2] or 0) + "\n⭐ Оценок: " + str(rrow[0])
    await message.answer(text)

@router.message(F.text.in_(["🏆 Топ водителей", "🏆 Беҳтарин ронандагон"]))
async def top_drivers(message: Message):
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND DATE(created_at)>=? AND driver_id IS NOT NULL GROUP BY driver_id ORDER BY COUNT(*) DESC LIMIT 10", (week_ago,))
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Пока нет данных.")
        return
    text = "🏆 Топ-10 водителей за 7 дней\n\n"
    i = 1
    for did, cnt, total in rows:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT first_name, last_name FROM users WHERE user_id=?", (did,))
            urow = await cur.fetchone()
        name = ((urow[0] or "") + " " + (urow[1] or "")).strip() if urow else str(did)
        text += str(i) + ". " + name + " - " + str(cnt) + " поездок, " + str(total) + " сомони\n"
        i += 1
    await message.answer(text)

@router.message(F.text.in_(["⭐ Мои адреса", "⭐ Суроғаҳои ман"]))
async def my_addr(message: Message):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, title, lat, lon FROM addresses WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,))
        rows = await cur.fetchall()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить адрес", callback_data="addr_add")
    builder.adjust(1)
    if not rows:
        await message.answer("Нет сохранённых адресов.", reply_markup=builder.as_markup())
        return
    text = "⭐ Мои адреса\n\n"
    for aid, title, lat, lon in rows:
        text += "#" + str(aid) + " " + title + "\n"
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "addr_add")
async def addr_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddrSave.title)
    await call.message.answer("Напишите название адреса (Дом, Работа):")
    await call.answer()

@router.message(AddrSave.title)
async def addr_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()[:50]
    if not title:
        await message.answer("Напишите название.")
        return
    await state.update_data(addr_title=title)
    await message.answer("Отправьте геолокацию:", reply_markup=loc_kb())

@router.message(AddrSave.title, F.location)
async def addr_loc(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("addr_title", "Адрес")
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO addresses(user_id, title, lat, lon) VALUES(?,?,?,?)", (uid, title, message.location.latitude, message.location.longitude))
        await db.commit()
    await state.clear()
    lang = await get_lang(uid)
    await message.answer("✅ Адрес " + title + " сохранён!", reply_markup=client_menu(lang))

@router.message(F.text.in_(["🔄 Повторить заказ", "🔄 Такрор кардан"]))
async def repeat_order(message: Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT from_lat, from_lon, to_lat, to_lon, distance FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 1", (uid,))
        row = await cur.fetchone()
    if not row:
        await message.answer("У вас ещё нет заказов.")
        return
    builder = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        dist = row[4] or 0
        price = int(t["base"] + t["rate"] * dist)
        builder.button(text=t["name"] + " - " + str(price) + " сомони", callback_data="replay_tariff:" + key)
    builder.adjust(1)
    await state.set_state(OrderFlow.tariff)
    await state.update_data(from_lat=row[0], from_lon=row[1], to_lat=row[2], to_lon=row[3], distance=row[4])
    await message.answer("🔄 Повторить поездку\n" + str(round(row[4], 1)) + " км\n\nВыберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("replay_tariff:"))
async def replay_tariff(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    data = await state.get_data()
    price = int(TARIFFS[key]["base"] + TARIFFS[key]["rate"] * data["distance"])
    await state.update_data(tariff=key, price=price)
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Наличные", callback_data="pay:cash")
    builder.button(text="💳 Картой", callback_data="pay:card")
    builder.adjust(2)
    await state.set_state(OrderFlow.payment)
    await call.message.edit_text(TARIFFS[key]["name"] + "\n💰 " + str(price) + " сомони\n\nОплата?", reply_markup=builder.as_markup())
    await call.answer()

@router.message(F.text.in_(["🟢 Я на линии", "🟢 Ман дар хат"]))
async def go_online(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT approved, rejected FROM users WHERE user_id=?", (uid,))
        arow = await cur.fetchone()
    if arow and arow[1]:
        await message.answer(tr(lang, "rejected"))
        return
    if not arow or not arow[0]:
        await message.answer(tr(lang, "wait_approve"))
        return
    if not await has_subscription(uid):
        await message.answer(tr(lang, "sub_no"))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class, car_photo, self_photo FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if not row or not row[0] or not row[1] or not row[2] or not row[3] or not row[4]:
        await state.set_state(DriverReg.car_brand)
        await message.answer("🚗 Заполните данные о машине:", reply_markup=ReplyKeyboardRemove())
        return
    await state.set_state(DriverReg.location)
    await message.answer("🚗 " + row[0] + " " + row[1] + " (" + row[2] + ")\n\n📍 Отправьте геолокацию:", reply_markup=loc_kb())

@router.message(DriverReg.car_brand)
async def drv_brand(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        lang = await get_lang(message.from_user.id)
        await message.answer("Отменено.", reply_markup=driver_menu(lang))
        return
    brand = (message.text or "").strip()[:50]
    if not brand:
        await message.answer("Напишите марку.")
        return
    await state.update_data(car_brand=brand)
    await state.set_state(DriverReg.car_plate)
    await message.answer("🔢 Укажите номер (01 TJ 777 AA):", reply_markup=cancel_kb())

@router.message(DriverReg.car_plate)
async def drv_plate(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        lang = await get_lang(message.from_user.id)
        await message.answer("Отменено.", reply_markup=driver_menu(lang))
        return
    plate = (message.text or "").strip()[:20]
    if not plate:
        await message.answer("Напишите номер.")
        return
    await state.update_data(car_plate=plate)
    await state.set_state(DriverReg.car_class)
    await message.answer("🚗 Класс машины:", reply_markup=class_kb())

@router.message(DriverReg.car_class, F.text.in_(CAR_CLASSES))
async def drv_class(message: Message, state: FSMContext):
    cls = message.text
    await state.update_data(car_class=cls)
    await state.set_state(DriverReg.car_photo)
    await message.answer("✅ " + cls + "\n\n📸 Отправьте фото машины с номером:", reply_markup=ReplyKeyboardRemove())

@router.message(DriverReg.car_class)
async def drv_class_wrong(message: Message):
    await message.answer("Выберите из кнопок:", reply_markup=class_kb())

@router.message(DriverReg.car_photo, F.photo)
async def drv_car_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(car_photo=photo_id)
    await state.set_state(DriverReg.self_photo)
    await message.answer("✅ Фото машины сохранено.\n\n📸 Отправьте своё фото:")

@router.message(DriverReg.car_photo)
async def drv_car_photo_wrong(message: Message):
    await message.answer("Отправьте фото машины.")

@router.message(DriverReg.self_photo, F.photo)
async def drv_self_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    uid = message.from_user.id
    car_brand = data.get("car_brand", "")
    car_plate = data.get("car_plate", "")
    car_class = data.get("car_class", "")
    car_photo = data.get("car_photo", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET car_brand=?, car_plate=?, car_class=?, car_photo=?, self_photo=?, approved=0, rejected=0 WHERE user_id=?", (car_brand, car_plate, car_class, car_photo, photo_id, uid))
        cur = await db.execute("SELECT phone, first_name, last_name FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        await db.commit()
    await state.clear()
    lang = await get_lang(uid)
    phone = row[0] if row else "-"
    name = ((row[1] or "") + " " + (row[2] or "")).strip() if row else "-"
    await message.answer("✅ Данные отправлены админу.\n\n⏳ Ожидайте одобрения.", reply_markup=driver_menu(lang))
    if ADMIN_ID:
        try:
            text = "🆕 НОВЫЙ ВОДИТЕЛЬ\n\n👤 " + name + "\n📱 " + str(phone) + "\n🆔 " + str(uid) + "\n\n🚗 " + car_brand + " " + car_plate + "\n🎯 " + car_class
            b = InlineKeyboardBuilder()
            b.button(text="✅ Принять", callback_data="drv_ok:" + str(uid))
            b.button(text="❌ Отклонить", callback_data="drv_no:" + str(uid))
            b.adjust(2)
            await message.bot.send_message(ADMIN_ID, text)
            if car_photo:
                await message.bot.send_photo(ADMIN_ID, photo=car_photo, caption="📸 Фото машины")
            if photo_id:
                await message.bot.send_photo(ADMIN_ID, photo=photo_id, caption="📸 Фото водителя")
            await message.bot.send_message(ADMIN_ID, "🎛 Решение:", reply_markup=b.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))

@router.message(DriverReg.self_photo)
async def drv_self_photo_wrong(message: Message):
    await message.answer("Отправьте своё фото.")

@router.message(DriverReg.location, F.location)
async def drv_location(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET driver_lat=?, driver_lon=?, online=1 WHERE user_id=?", (message.location.latitude, message.location.longitude, message.from_user.id))
        await db.commit()
    await state.clear()
    lang = await get_lang(message.from_user.id)
    await message.answer("🟢 Вы на линии.", reply_markup=driver_menu(lang))

@router.message(DriverReg.location)
async def drv_location_wrong(message: Message):
    await message.answer("Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(F.text.in_(["🔴 Уйти с линии", "🔴 Аз хат рафтан"]))
async def go_offline(message: Message):
    uid = message.from_user.id
    await set_online(uid, 0)
    lang = await get_lang(uid)
    await message.answer("🔴 Вы ушли с линии.", reply_markup=driver_menu(lang))

@router.message(F.text.in_(["💳 Подписка", "💳 Обуна"]))
async def sub_info(message: Message):
    uid = message.from_user.id
    lang = await get_lang(uid)
    sub_ok = await has_subscription(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if sub_ok and row and row[0]:
        until = datetime.fromisoformat(row[0]).strftime("%d.%m.%Y %H:%M")
        text = "✅ Подписка активна\n📅 До: " + until
    else:
        text = "❌ Подписки нет\n\n💰 20 сомони/день"
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить 20 сомони", callback_data="sub_pay")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "sub_pay")
async def sub_pay(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM sub_requests WHERE driver_id=? AND status='pending'", (uid,))
        if await cur.fetchone():
            await call.answer("Заявка уже отправлена", show_alert=True)
            return
        await db.execute("INSERT INTO sub_requests(driver_id) VALUES(?)", (uid,))
        await db.commit()
    text = "💳 Оплата подписки\n\n💰 20 сомони\n\nРеквизиты:\n1. DC-банк        013585959\n2. ESKHATA-банк   013585959\n3. ALIF-банк      013585959\n4. SPITAMEN-банк  013585959\n\n1️⃣ Переведите 20 сомони\n2️⃣ Отправьте скриншот чека (фото)"
    await call.message.edit_text(text)
    if ADMIN_ID:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="❌ Отклонить", callback_data="sub_no:" + str(uid))
            builder.adjust(1)
            await call.bot.send_message(ADMIN_ID, "💳 Заявка на подписку\n\nID: " + str(uid), reply_markup=builder.as_markup())
        except Exception:
            pass
    await state.set_state(SubPayment.receipt)
    await call.answer()

@router.message(SubPayment.receipt, F.photo)
async def sub_receipt_photo(message: Message, state: FSMContext):
    uid = message.from_user.id
    photo_id = message.photo[-1].file_id
    await state.clear()
    lang = await get_lang(uid)
    if ADMIN_ID:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Подтвердить", callback_data="sub_ok:" + str(uid))
            builder.button(text="❌ Отклонить", callback_data="sub_no:" + str(uid))
            builder.adjust(2)
            await message.bot.send_photo(ADMIN_ID, photo=photo_id, caption="💳 Чек об оплате\n\nID: " + str(uid), reply_markup=builder.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))
    await message.answer("✅ Чек отправлен админу!", reply_markup=driver_menu(lang))

@router.message(SubPayment.receipt)
async def sub_receipt_wrong(message: Message):
    await message.answer("⚠️ Отправьте фото чека.")

@router.callback_query(F.data.startswith("sub_ok:"))
async def sub_confirm(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    until = await give_subscription(uid, days=1)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sub_requests SET status='approved' WHERE driver_id=? AND status='pending'", (uid,))
        await db.commit()
    try:
        await call.bot.send_message(uid, "✅ Подписка активирована!\n📅 До: " + until.strftime("%d.%m.%Y %H:%M"))
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="✅ Подписка выдана: " + str(uid))
        else:
            await call.message.edit_text("✅ Подписка выдана: " + str(uid))
    except Exception:
        pass
    await call.answer()

@router.callback_query(F.data.startswith("sub_no:"))
async def sub_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sub_requests SET status='rejected' WHERE driver_id=? AND status='pending'", (uid,))
        await db.commit()
    try:
        await call.bot.send_message(uid, "❌ Заявка отклонена.")
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="❌ Отклонено: " + str(uid))
        else:
            await call.message.edit_text("❌ Отклонено: " + str(uid))
    except Exception:
        pass
    await call.answer()

@router.callback_query(F.data.startswith("drv_ok:"))
async def driver_approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approved=1, rejected=0 WHERE user_id=?", (uid,))
        await db.commit()
    lang = await get_lang(uid)
    try:
        await call.bot.send_message(uid, "🎉 " + ("Вас приняли на работу!" if lang == "ru" else "Шуморо ба кор қабул карданд!") + "\n\n💳 Оформите подписку\n🟢 Нажмите Я на линии")
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="✅ Водитель принят: " + str(uid))
        else:
            await call.message.edit_text("✅ Водитель принят: " + str(uid))
    except Exception:
        pass
    await call.answer("Принят")

@router.callback_query(F.data.startswith("drv_no:"))
async def driver_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approved=0, rejected=1 WHERE user_id=?", (uid,))
        await db.commit()
    try:
        await call.bot.send_message(uid, "❌ Заявка отклонена.")
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="❌ Отклонён: " + str(uid))
        else:
            await call.message.edit_text("❌ Отклонён: " + str(uid))
    except Exception:
        pass
    await call.answer("Отклонён")

async def health(request):
    return web.Response(text="OK")

async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await init_db()
    await start_web()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())