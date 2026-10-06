from dotenv import load_dotenv
load_dotenv()

import asyncio
import math
import logging
import os
import csv
import io
import hashlib
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, Contact,
    BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPER_ADMIN_ID = 1120621262
ADMIN_PASSWORD = "KING0770"
DB_PATH = "taxi.db"
SUB_PRICE = 30
REF_TARGET = 5
REF_BONUS_DAYS = 3
AVG_SPEED = 30
NEAR_RADIUS = 2.0
CARD_NUMBER = "013585959"
MAX_ORDERS_PER_HOUR = 5
MIN_PRICE_PERCENT = 80
MAX_NEGOTIATION_ROUNDS = 3
FIRST50_LIMIT = 50
FIRST50_DAYS = 7
CITIES = ["Гиссар", "Душанбе", "Худжанд", "Куляб", "Вахдат"]

logging.basicConfig(level=logging.INFO)

T = {
    "ru": {
        "choose_role": "👋 С возвращением! Выберите роль:",
        "client": "🚕 Я клиент",
        "driver": "🚗 Я водитель",
        "complaint": "⚠️ Пожаловаться",
        "change": "🔄 Сменить роль",
        "change_lang": "🌍 Сменить язык",
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
        "sub_no": "❌ Подписки нет — оплатите 30 сомони",
        "wait_approve": "⏳ Ожидайте одобрения админом.\n\nПока заявка не принята — работать нельзя.",
        "rejected": "❌ Ваша заявка отклонена.\n\nСвяжитесь с администратором.",
        "cancel": "❌ Отмена",
        "logs": "📜 Логи",
        "blacklist": "🚫 Чёрный список",
        "admins_manage": "👑 Админы",
        "ban_user": "🚫 Забанить",
        "unban_user": "✅ Разбанить",
        "bans_list": "📋 Список банов",
        "broadcast_admins": "📢 Рассылка админам",
        "broadcast_drivers": "📢 Рассылка водителям",
        "broadcast_clients": "📢 Рассылка пассажирам",
        "admins_list": "👑 Список админов",
        "drivers_list": "🚗 Список водителей",
        "clients_list": "👤 Список пассажиров",
    },
    "tj": {
        "choose_role": "👋 Хуш омадед! Нақши худро интихоб кунед:",
        "client": "🚕 Ман мизоҷ",
        "driver": "🚗 Ман ронанда",
        "complaint": "⚠️ Шикоят",
        "change": "🔄 Иваз кардани нақш",
        "change_lang": "🌍 Иваз кардани забон",
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
        "sub_no": "❌ Обуна нест — 30 сомонӣ пардохт кунед",
        "wait_approve": "⏳ Интизори тасдиқи админ.",
        "rejected": "❌ Дархости шумо рад карда шуд.",
        "cancel": "❌ Бекор кардан",
        "logs": "📜 Логҳо",
        "blacklist": "🚫 Рӯйхати сиёҳ",
        "admins_manage": "👑 Админҳо",
        "ban_user": "🚫 Баст",
        "unban_user": "✅ Кушодан",
        "bans_list": "📋 Рӯйхати бастҳо",
        "broadcast_admins": "📢 Паём ба админҳо",
        "broadcast_drivers": "📢 Паём ба ронандагон",
        "broadcast_clients": "📢 Паём ба мизоҷон",
        "admins_list": "👑 Рӯйхати админҳо",
        "drivers_list": "🚗 Рӯйхати ронандагон",
        "clients_list": "👤 Рӯйхати мизоҷон",
    },
}

def tr(lang, key):
    return T.get(lang, T["ru"]).get(key, T["ru"].get(key, key))

TARIFFS = {
    "economy": {"name": "🚕 Эконом", "base": 10, "rate": 3},
}

CAR_CLASSES = ["Эконом"]

router = Router()

class Reg(StatesGroup):
    phone = State()
    call_phone = State()
    first_name = State()
    last_name = State()
    city = State()

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
    comment = State()
    client_offer = State()
    confirm = State()

class DriverOffer(StatesGroup):
    waiting = State()

class Complaint(StatesGroup):
    text = State()

class AdminReply(StatesGroup):
    waiting = State()

class Admin2FA(StatesGroup):
    waiting_password = State()

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
    target = State()

class AddrSave(StatesGroup):
    title = State()

class AdminManage(StatesGroup):
    waiting_add_id = State()
    waiting_ban_id = State()
    waiting_ban_reason = State()
    waiting_unban_id = State()
    waiting_ban_admin_id = State()
    waiting_unban_admin_id = State()
    waiting_ban_driver_id = State()
    waiting_ban_client_id = State()

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

def min_price_for(recommended):
    return int(recommended * MIN_PRICE_PERCENT / 100)

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

async def log_action(uid, action, details=""):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO logs(user_id, action, details, created_at) VALUES(?,?,?,?)", (uid, action, details[:500], datetime.now().isoformat()))
            await db.commit()
    except Exception as e:
        logging.warning("Log error: " + str(e))

async def is_super_admin(uid):
    return uid == SUPER_ADMIN_ID

async def is_admin(uid):
    if uid == SUPER_ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        return bool(row)

async def add_admin(uid, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins(user_id, added_by, added_at) VALUES(?,?,?)", (uid, added_by, datetime.now().isoformat()))
        await db.commit()

async def remove_admin(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        await db.commit()

async def get_all_admins():
    result = [SUPER_ADMIN_ID]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        for r in rows:
            if r[0] not in result:
                result.append(r[0])
    return result

async def get_all_helpers():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return [r[0] for r in rows]

async def is_banned(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT banned FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        return row and row[0] == 1

async def ban_user(uid, reason, banned_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=1, ban_reason=?, banned_by=?, banned_at=? WHERE user_id=?", (reason, banned_by, datetime.now().isoformat(), uid))
        await db.commit()

async def unban_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=0, ban_reason='', banned_by=NULL, banned_at=NULL WHERE user_id=?", (uid,))
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
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def city_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Гиссар")],
            [KeyboardButton(text="Душанбе")],
            [KeyboardButton(text="Худжанд")],
            [KeyboardButton(text="Куляб")],
            [KeyboardButton(text="Вахдат")],
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
                [KeyboardButton(text="📅 Пагоҳ")],
                [KeyboardButton(text="📅 Пасфардо")],
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
            [KeyboardButton(text="📅 Завтра")],
            [KeyboardButton(text="📅 Послезавтра")],
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
            [KeyboardButton(text=tr(lang, "complaint")), KeyboardButton(text=tr(lang, "change_lang"))],
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
            [KeyboardButton(text=tr(lang, "logs")), KeyboardButton(text=tr(lang, "blacklist"))],
            [KeyboardButton(text=tr(lang, "admins_manage")), KeyboardButton(text=tr(lang, "bans_list"))],
            [KeyboardButton(text=tr(lang, "broadcast"))],
            [KeyboardButton(text=tr(lang, "export")), KeyboardButton(text=tr(lang, "exit"))],
        ],
        resize_keyboard=True
    )

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            role TEXT, phone TEXT, call_phone TEXT,
            first_name TEXT, last_name TEXT,
            city TEXT DEFAULT '',
            online INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0, rides INTEGER DEFAULT 0,
            total_rides INTEGER DEFAULT 0,
            approved INTEGER DEFAULT 0,
            rejected INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            banned_by INTEGER,
            banned_at TIMESTAMP,
            lang TEXT DEFAULT 'ru',
            sub_until TIMESTAMP,
            first50_used INTEGER DEFAULT 0,
            referred_by INTEGER,
            ref_count INTEGER DEFAULT 0,
            ref_activated INTEGER DEFAULT 0,
            car_brand TEXT, car()

_plate TEXT, car_class TEXT,
            car_photoasync TEXT, self_photo TEXT,
            driver_lat REAL, driver_lon REAL,
            def created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 has        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER, driver_id INTEGER,
            from_lat REAL, from_lon REAL, to_lat REAL, to_lon REAL,
            distance REAL, price INTEGER, tariff TEXT,
            payment TEXT DEFAULT 'cash',
            promo TEXT DEFAULT '', discount INTEGER DEFAULT 0,
            scheduled_at TIMESTAMP,
            comment TEXT DEFAULT '',
            recommended_price INTEGER DEFAULT 0,
            negotiation_round INTEGER DEFAULT 0,
            last_offer_by TEXT DEFAULT '',
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
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT, details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admins(
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        for col in ["first_name TEXT", "last_name TEXT", "car_class TEXT", "car_photo TEXT", "self_photo TEXT", "total_rides INTEGER DEFAULT 0", "approved INTEGER DEFAULT 0", "rejected INTEGER DEFAULT 0", "lang TEXT DEFAULT 'ru'", "call_phone TEXT", "banned INTEGER DEFAULT 0", "city TEXT DEFAULT ''", "ban_reason TEXT DEFAULT ''", "banned_by INTEGER", "banned_at TIMESTAMP", "first50_used INTEGER DEFAULT 0"]:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN " + col)
            except Exception:
                pass
        for col in ["promo TEXT DEFAULT ''", "discount INTEGER DEFAULT 0", "review TEXT DEFAULT ''", "scheduled_at TIMESTAMP", "comment TEXT DEFAULT ''", "recommended_price INTEGER DEFAULT 0", "negotiation_round INTEGER DEFAULT 0", "last_offer_by TEXT DEFAULT ''"]:
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

async def has_city(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT city FROM users WHERE user_id=?", (uid,))
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

async def days_left_subscription(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row or not row[0]:
            return 0
        try:
            until = datetime.fromisoformat(row[0])
            delta = until - datetime.now()
            return max(0, delta.days)
        except Exception:
            return 0

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

async def get_drivers_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='driver' AND car_photo IS NOT NULL")
        return (await cur.fetchone())[0]

async def notify_admins(bot, text, only_super=False, only_helpers=False):
    if only_super:
        try:
            await bot.send_message(SUPER_ADMIN_ID, text)
        except Exception:
            pass
        return
    if only_helpers:
        helpers = await get_all_helpers()
        for h in helpers:
            try:
                await bot.send_message(h, text)
            except Exception:
                pass
        return
    admins = await get_all_admins()
    for a in admins:
        try:
            await bot.send_message(a, text)
        except Exception:
            pass
            @router.message(F.text.in_(["🇷🇺 Русский", "🇷🇺 Русский язык"]))
async def set_lang_ru(message: Message, state: FSMContext):
    uid = message.from_user.id
    await set_lang(uid, "ru")
    if not await is_registered(uid):
        await state.set_state(Reg.phone)
        await message.answer("📱 Шаг 1/5: Отправьте свой номер телефона:", reply_markup=phone_kb())
        return
    if not await has_city(uid):
        await state.set_state(Reg.city)
        await message.answer("🏙️ Выберите ваш город:", reply_markup=city_kb())
        return
    await message.answer("👋 С возвращением! Выберите роль:", reply_markup=main_menu("ru"))

@router.message(F.text.in_(["🇹🇯 Тоҷикӣ", "🇹🇯 Тоҷикӣ забон"]))
async def set_lang_tj(message: Message, state: FSMContext):
    uid = message.from_user.id
    await set_lang(uid, "tj")
    if not await is_registered(uid):
        await state.set_state(Reg.phone)
        await message.answer("📱 Қадами 1/5: Рақами телефони худро фиристед:", reply_markup=phone_kb())
        return
    if not await has_city(uid):
        await state.set_state(Reg.city)
        await message.answer("🏙️ Шаҳри худро интихоб кунед:", reply_markup=city_kb())
        return
    await message.answer("👋 Хуш омадед! Нақши худро интихоб кунед:", reply_markup=main_menu("tj"))

@router.message(F.text.in_(["🌍 Сменить язык", "🌍 Иваз кардани забон"]))
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

    if await is_banned(uid):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT ban_reason FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            reason = row[0] if row and row[0] else "не указана"
        await message.answer("🚫 Вы заблокированы.\n\n📝 Причина: " + reason + "\n\nСвяжитесь с администратором.")
        return

    if not await is_registered(uid):
       ами await state.set_state(Reg.phone)
        await Telegram ни message.answer("го🇷🇺 Добро пожалҳовать!\n🇹🇯 Хуш ома додед!\n\n👇 Выберитешта язык / Забонро интихоб ку шнедуд:", reply_markup=lang_kb.\())
        return

    if not await has_cnity(uid):
        await state.set_state(Reg\n.city)
       📞 lang = await get_lang(uid)
        txt = "🏙️ Выберите ваш город:" if lang == "ru" else "🏙️ Шаҳри худро интихоб кунед:"
        await message.answer(txt, reply_markup=city_kb())
        return

    lang = await get_lang( Қаuidдами)
    await message.answer(tr(l ang, "choose_role"), reply_markup=main_menu(lang))

@router.message(2Reg.phone, F.contact/)
async def reg_phone(message:5 Message, state: FSMContext):
    uid =: message.from_user.id
    Ра phone = message.contact.phoneқ_number
    lang = await get_lang(амиuid)
    async with aiosql иite.connect(DB_PATHлова) asгии db:
        await db.execute("INSERT INTO худ users(user_id, phone) VALUES(?, ?)ро ON CONFLICT(user_id) DO UPDATE ба SET phone=excluded.phone",ро (uid, phone))
        await db.commit()
   и await state.set_state(Reg.call_ зангphone)
    if lang == "tj на":
        text = "✅ Рақвисед (ё - барои гузаштан):"
    else:
        text = "✅ Telegram-номер сохранён.\n\n📞 Шаг 2/5: Напишите свой номер для звонка (или - чтобы пропустить):"
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

@router.message(Reg.phone)
async def reg_phone_wrong(message: Message):
    await message.answer("⚠️ Нажмите кнопку «📱 Отправить номер» внизу.")

@router.message(Reg.call_phone)
async def reg_call_phone(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_lang(uid)
    txt = (message.text or "").strip()
    call_phone = "" if txt == "-" else txt[:30]
    if call_phone:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET call_phone=? WHERE user_id=?", (call_phone, uid))
            await db.commit()
    await state.set_state(Reg.first_name)
    if lang == "tj":
        await message.answer("👤 Қадами 3/5: Номи худро нависед:")
    else:
        await message.answer("👤 Шаг 3/5: Напишите своё имя:")

@router.message(Reg.first_name)
async def reg_first_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()[:50]
    if not name:
        await message.answer("Напишите имя.")
        return
    lang = await get_lang(message.from_user.id)
    await state.update_data(first_name=name)
    await state.set_state(Reg.last_name)
    if lang == "tj":
        await message.answer("👤 Ном: " + name + "\n\n👤 Қадами 4/5: Насаби худро нависед:")
    else:
        await message.answer("👤 Имя: " + name + "\n\n👤 Шаг 4/5: Напишите свою фамилию:")

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
        await db.commit()
    await state.set_state(Reg.city)
    if lang == "tj":
        await message.answer("🏙️ Қадами 5/5: Шаҳри худро интихоб кунед:", reply_markup=city_kb())
    else:
        await message.answer("🏙️ Шаг 5/5: Выберите свой город:", reply_markup=city_kb())

@router.message(Reg.city)
async def reg_city(message: Message, state: FSMContext):
    city = (message.text or "").strip()
    if city not in CITIES:
        await message.answer("⚠️ Выберите город из кнопок ниже:", reply_markup=city_kb())
        return
    data = await state.get_data()
    uid = message.from_user.id
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET city=? WHERE user_id=?", (city, uid))
        cur = await db.execute("SELECT phone, call_phone, first_name, last_name FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        await db.commit()
    await state.clear()
    phone = row[0] if row else "-"
    call_phone = row[1] if row and row[1] else "—"
    fname = row[2] if row else "-"
    lname = row[3] if row else "-"
    name = (fname + " " + lname).strip()

    await log_action(uid, "register", name + " | " + city + " | " + phone)

    text_admin = "🆕 Новый пользователь\n\n👤 " + name + "\n🏙️ Город: " + city + "\n📱 Telegram: " + str(phone) + "\n📞 Звонок: " + str(call_phone) + "\n🆔 " + str(uid)
    await notify_admins(message.bot, text_admin)

    text_user = "✅ Регистрация завершена!\n\n👤 " + name + "\n🏙️ " + city + "\n📱 " + phone + "\n📞 " + call_phone + "\n\n" + ("Выберите роль:" if lang == "ru" else "Нақши худро интихоб кунед:")
    await message.answer(text_user, reply_markup=main_menu(lang))

@router.message(F.text.in_(["🚕 Я клиент", "🚕 Ман мизоҷ"]))
async def role_client(message: Message):
    uid = message.from_user.id
    if await is_banned(uid):
        await message.answer("🚫 Вы заблокированы.")
        return
    if not await is_registered(uid):
        await message.answer("Сначала /start")
        return
    if not await has_city(uid):
        await message.answer("Сначала выберите город. /start")
        return
    lang = await get_lang(uid)
    await set_role(uid, "client")
    await log_action(uid, "role_client")
    await message.answer(tr(lang, "you_client"), reply_markup=client_menu(lang))

@router.message(F.text.in_(["🚗 Я водитель", "🚗 Ман ронанда"]))
async def role_driver(message: Message, state: FSMContext):
    uid = message.from_user.id
    if await is_banned(uid):
        await message.answer("🚫 Вы заблокированы.")
        return
    if not await is_registered(uid):
        await message.answer("Сначала /start")
        return
    if not await has_city(uid):
        await message.answer("Сначала выберите город. /start")
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
    if sub_ok:
        days = await days_left_subscription(uid)
        sub_text = tr(lang, "sub_ok") + "\n📅 Осталось дней: " + str(days)
    else:
        sub_text = tr(lang, "sub_no")
    await message.answer(tr(lang, "you_driver") + sub_text, reply_markup=driver_menu(lang))

@router.message(F.text.in_(["🔄 Сменить роль", "🔄 Иваз кардани нақш"]))
async def change_role(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    await message.answer(tr(lang, "choose_role"), reply_markup=main_menu(lang))

@router.message(F.text.in_(["💳 Подписка", "💳 Обуна"]))
async def sub_info(message: Message):
    uid = message.from_user.id
    lang = await get_lang(uid)
    sub_ok = await has_subscription(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until, first50_used FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if sub_ok and row and row[0]:
        days = await days_left_subscription(uid)
        until = datetime.fromisoformat(row[0]).strftime("%d.%m.%Y %H:%M")
        text = "✅ Подписка активна\n📅 До: " + until + "\n⏳ Осталось дней: " + str(days)
    else:
        text = "❌ Подписки нет\n\n💰 Стоимость: 30 сомони/день"
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить 30 сомони", callback_data="sub_pay")
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
    text = ("💳 Оплата подписки\n\n💰 30 сомони\n\nРеквизиты:\n"
            "1. DC-банк        013585959\n"
            "2. ESKHATA-банк   013585959\n"
            "3. ALIF-банк      013585959\n"
            "4. SPITAMEN-банк  013585959\n\n"
            "1️⃣ Переведите 30 сомони на любую карту\n"
            "2️⃣ Отправьте скриншот чека (фото)")
    await call.message.edit_text(text)
    await log_action(uid, "sub_request")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, last_name, city, phone FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    fname = row[0] if row else "?"
    lname = row[1] if row else "?"
    city = row[2] if row and row[2] else "?"
    phone = row[3] if row else "?"
    name = (fname + " " + lname).strip()
    text_admin = "💳 Заявка на подписку\n\n👤 " + name + "\n🏙️ " + city + "\n📱 " + phone + "\n🆔 " + str(uid)
    await notify_admins(call.bot, text_admin, only_helpers=False)
    await state.set_state(SubPayment.receipt)
    await call.answer()

@router.message(SubPayment.receipt, F.photo)
async def sub_receipt_photo(message: Message, state: FSMContext):
    uid = message.from_user.id
    photo_id = message.photo[-1].file_id
    await state.clear()
    lang = await get_lang(uid)
    await log_action(uid, "sub_receipt")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, last_name, city FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    fname = row[0] if row else "?"
    lname = row[1] if row else "?"
    city = row[2] if row and row[2] else "?"
    name = (fname + " " + lname).strip()

    caption = "💳 Чек об оплате\n\n👤 " + name + "\n🏙️ " + city + "\n🆔 " + str(uid)
    admins = await get_all_admins()
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить", callback_data="sub_ok:" + str(uid))
    b.button(text="❌ Отклонить", callback_data="sub_no:" + str(uid))
    b.adjust(2)
    for admin in admins:
        try:
            await message.bot.send_photo(admin, photo=photo_id, caption=caption, reply_markup=b.as_markup())
        except Exception:
            pass
    await message.answer("✅ Чек отправлен админу!", reply_markup=driver_menu(lang))

@router.message(SubPayment.receipt)
async def sub_receipt_wrong(message: Message):
    await message.answer("⚠️ Отправьте фото чека.")

@router.callback_query(F.data.startswith("sub_ok:"))
async def sub_confirm(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    until = await give_subscription(uid, days=1)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sub_requests SET status='approved' WHERE driver_id=? AND status='pending'", (uid,))
        await db.commit()
    await log_action(uid, "sub_approved", "by=" + str(call.from_user.id))
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
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sub_requests SET status='rejected' WHERE driver_id=? AND status='pending'", (uid,))
        await db.commit()
    await log_action(uid, "sub_rejected", "by=" + str(call.from_user.id))
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
    @router.message(F.text.in_(["🚕 Заказать такси", "🚕 Фармоиши такси"]))
async def order_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    if await is_banned(uid):
        await message.answer("🚫 Вы заблокированы.")
        return
    if not await has_city(uid):
        await message.answer("Сначала выберите город. /start")
        return
    lang = await get_lang(uid)
    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders WHERE client_id=? AND created_at >= ?", (uid, hour_ago))
        cnt = (await cur.fetchone())[0]
    if cnt >= MAX_ORDERS_PER_HOUR:
        await message.answer("⚠️ Слишком много заказов. Попробуйте через час.")
        return
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
    if "from_lat" not in data:
        await message.answer("⚠️ Ошибка. Начните заново.")
        await state.clear()
        return
    dist = haversine(data["from_lat"], data["from_lon"], message.location.latitude, message.location.longitude)
    if dist < 0.1:
        await message.answer("⚠️ Слишком близко. Отправьте другую точку.")
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
    await state.update_data(tariff=key, price=price, recommended_price=price)
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

@router.message(OrderFlow.when, F.text.in_(["🚕 Сейчас", "⏰ Через 30 мин", "⏰ Через 1 час", "⏰ Через 2 часа", "⏰ Через 4 часа", "📅 Завтра", "📅 Послезавтра", "🚕 Ҳозир", "⏰ Баъди 30 дақиқа", "⏰ Баъди 1 соат", "⏰ Баъди 2 соат", "⏰ Баъди 4 соат", "📅 Пагоҳ", "📅 Пасфардо"]))
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
    elif txt in ("📅 Завтра", "📅 Пагоҳ"):
        scheduled = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    elif txt in ("📅 Послезавтра", "📅 Пасфардо"):
        scheduled = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        scheduled = now
    await state.update_data(scheduled_at=scheduled.isoformat())
    await state.set_state(OrderFlow.comment)
    await message.answer("📝 Напишите комментарий к заказу (или - чтобы пропустить):\n\nНапример: «У 2-го подъезда», «С детьми», «Не звонить, писать»", reply_markup=ReplyKeyboardRemove())

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
    await state.set_state(OrderFlow.comment)
    await message.answer("📝 Напишите комментарий к заказу (или - чтобы пропустить):")

@router.message(OrderFlow.when)
async def when_wrong(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await message.answer("Выберите из кнопок ниже:", reply_markup=when_kb(lang))

@router.message(OrderFlow.comment)
async def order_comment(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    comment = "" if txt == "-" else txt[:200]
    await state.update_data(comment=comment)
    data = await state.get_data()
    recommended = data.get("recommended_price", data.get("price", 0))
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен — " + str(recommended) + " сомони", callback_data="offer_agree")
    builder.button(text="💰 Предложить свою цену", callback_data="offer_custom")
    builder.adjust(1)
    await state.set_state(OrderFlow.client_offer)
    await message.answer("🚕 " + TARIFFS[data["tariff"]]["name"] + "\n📏 ~" + str(round(data["distance"], 1)) + " км\n💰 Рекомендуемая цена: " + str(recommended) + " сомони\n\nКак поедем?", reply_markup=builder.as_markup())

@router.callback_query(OrderFlow.client_offer, F.data == "offer_agree")
async def offer_agree(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    recommended = data.get("recommended_price", data.get("price", 0))
    await state.update_data(price=recommended, promo="", discount=0)
    await show_confirm(call.message, state)
    await call.answer()

@router.callback_query(OrderFlow.client_offer, F.data == "offer_custom")
async def offer_custom(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 Введите свою цену в сомони (только число):")
    await call.answer()

@router.message(OrderFlow.client_offer, F.text)
async def client_offer_save(message: Message, state: FSMContext):
    try:
        offer = int((message.text or "").strip())
        if offer < 1:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Введите целое число.")
        return
    data = await state.get_data()
    recommended = data.get("recommended_price", data.get("price", 0))
    minimum = min_price_for(recommended)
    if offer < minimum:
        await message.answer("⚠️ Слишком низкая цена. Введите больше.")
        return
    await state.update_data(price=offer, promo="", discount=0)
    await show_confirm(message, state)

async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    sched_text = ""
    if data.get("scheduled_at"):
        try:
            sdt = datetime.fromisoformat(data["scheduled_at"])
            if (sdt - datetime.now()).total_seconds() > 300:
                sched_text = "\n📅 На время: " + sdt.strftime("%d.%m %H:%M")
        except Exception:
            pass
    comment_text = ""
    if data.get("comment"):
        comment_text = "\n💬 " + data["comment"]
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.adjust(2)
    await state.set_state(OrderFlow.confirm)
    text = ("🚕 " + TARIFFS[data["tariff"]]["name"] + "\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + sched_text + comment_text + "\n\nПодтвердить заказ?")
    try:
        await message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await message.answer(text, reply_markup=builder.as_markup())

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
        cur = await db.execute("INSERT INTO orders(client_id, from_lat, from_lon, to_lat, to_lon, distance, price, tariff, payment, promo, discount, scheduled_at, comment, recommended_price, status, last_offer_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (call.from_user.id, data["from_lat"], data["from_lon"], data["to_lat"], data["to_lon"], data["distance"], data["price"], data["tariff"], data.get("payment", "cash"), data.get("promo", ""), data.get("discount", 0), sched_at, data.get("comment", ""), data.get("recommended_price", 0), status, "client"))
        order_id = cur.lastrowid
        await db.commit()
    await state.clear()
    await log_action(call.from_user.id, "order_created", "id=" + str(order_id) + " price=" + str(data["price"]))
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заказ", callback_data="client_cancel:" + str(order_id))
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    eta = estimate_minutes(data["distance"])
    if is_scheduled:
        sdt = datetime.fromisoformat(sched_at)
        await call.message.edit_text("✅ Заказ #" + str(order_id) + " создан!\n\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + "\n\n📅 На время: " + sdt.strftime("%d.%m.%Y %H:%M") + "\n\nМы напомним водителям заранее.")
    else:
        await call.message.edit_text("✅ Заказ #" + str(order_id) + " создан!\n\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + "\n⏳ " + str(eta) + " мин\n\n🔍 Ищем водителя...")
        await notify_drivers(call.bot, order_id, data)
    await call.message.answer("Ожидайте:", reply_markup=builder.as_markup())

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, last_name, city, phone FROM users WHERE user_id=?", (call.from_user.id,))
        row = await cur.fetchone()
    fname = row[0] if row else "?"
    lname = row[1] if row else "?"
    city = row[2] if row and row[2] else "?"
    phone = row[3] if row else "?"
    text_admin = "📦 Новый заказ #" + str(order_id) + "\n\n👤 " + (fname + " " + lname).strip() + "\n🏙️ " + city + "\n📱 " + str(phone) + "\n💰 " + str(data["price"]) + " сомони"
    await notify_admins(call.bot, text_admin)
    await call.answer()

async def notify_drivers(bot: Bot, order_id: int, data: dict):
    flat = data.get("from_lat")
    flon = data.get("from_lon")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT city FROM users WHERE user_id=?", (data.get("client_id", 0),))
        row = await cur.fetchone()
    if not row or not row[0]:
        client_city = ""
    else:
        client_city = row[0]

    if not client_city:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT client_id FROM orders WHERE id=?", (order_id,))
            crow = await cur.fetchone()
        if crow:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT city FROM users WHERE user_id=?", (crow[0],))
                r2 = await cur.fetchone()
            if r2:
                client_city = r2[0]

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, driver_lat, driver_lon, city FROM users WHERE role='driver' AND online=1 AND approved=1 AND rejected=0 AND banned=0 AND city=?", (client_city,))
        drivers = await cur.fetchall()

    if not drivers:
        return

    near = []
    far = []
    for uid, dlat, dlon, dcity in drivers:
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
    builder.button(text="✅ Принять — " + str(data["price"]) + " сомони", callback_data="accept:" + str(order_id))
    builder.button(text="💰 Предложить свою цену", callback_data="driver_offer:" + str(order_id))
    builder.adjust(1)
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    text = ("🔔 Новый заказ #" + str(order_id) + "\n\n"
            "🚕 " + TARIFFS[data["tariff"]]["name"] + "\n"
            "📏 ~" + str(round(data["distance"], 1)) + " км\n"
            "💳 " + pay_text + "\n"
            "💰 Клиент предлагает: " + str(data["price"]) + " сомони")
    if data.get("comment"):
        text += "\n💬 " + data["comment"]
    for uid, _ in near:
        try:
            await bot.send_message(uid, text, reply_markup=builder.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))
    if near:
        await asyncio.sleep(45)
    for uid, _ in far:
        try:
            await bot.send_message(uid, text, reply_markup=builder.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))

@router.callback_query(F.data.startswith("driver_offer:"))
async def driver_offer_start(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, negotiation_round FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row or row[0] not in ("pending", "scheduled", "negotiating"):
        await call.answer("Заказ недоступен", show_alert=True)
        return
    if row[1] >= MAX_NEGOTIATION_ROUNDS:
        await call.answer("Максимум 3 раунда", show_alert=True)
        return
    await state.set_state(DriverOffer.waiting)
    await state.update_data(order_id=order_id)
    await call.message.answer("📝 Введите свою цену в сомони (только число):")
    await call.answer()

@router.message(DriverOffer.waiting)
async def driver_offer_save(message: Message, state: FSMContext):
    try:
        offer = int((message.text or "").strip())
        if offer < 1:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Введите целое число.")
        return
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, price, recommended_price, negotiation_round, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[4] not in ("pending", "scheduled", "negotiating"):
            await message.answer("⚠️ Заказ уже недоступен.")
            return
        client_id = row[0]
        recommended = row[2] or row[1]
        round_n = row[3] + 1
        minimum = min_price_for(recommended)
        if offer < minimum:
            await message.answer("⚠️ Слишком низкая цена. Введите больше.")
            return
        await db.execute("UPDATE orders SET driver_id=?, status='negotiating', negotiation_round=?, last_offer_by='driver' WHERE id=?", (message.from_user.id, round_n, order_id))
        await db.commit()
    if round_n >= MAX_NEGOTIATION_ROUNDS:
        await message.answer("⚠️ Максимум 3 раунда. Если клиент не согласен — заказ отменится.")
    else:
        await message.answer("📤 Ваша цена " + str(offer) + " сомони отправлена клиенту. Ожидайте ответа.")
    ckb = InlineKeyboardBuilder()
    ckb.button(text="✅ Согласен — " + str(offer) + " сомони", callback_data="client_accept:" + str(order_id) + ":" + str(offer))
    ckb.button(text="💰 Предложить свою", callback_data="client_counter:" + str(order_id))
    ckb.adjust(1)
    text = ("🚗 Водитель предлагает: " + str(offer) + " сомони\n\n"
            "Вы предлагали: " + str(row[1]) + " сомони\n"
            "Раунд: " + str(round_n) + "/" + str(MAX_NEGOTIATION_ROUNDS) + "\n\n"
            "Согласны?")
    try:
        await message.bot.send_message(client_id, text, reply_markup=ckb.as_markup())
    except Exception:
        pass

@router.callback_query(F.data.startswith("client_accept:"))
async def client_accept(call: CallbackQuery):
    parts = call.data.split(":")
    order_id = int(parts[1])
    offer = int(parts[2])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, driver_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[2] != "negotiating":
            await call.answer("Заказ уже закрыт", show_alert=True)
            return
        client_id = row[0]
        driver_id = row[1]
        await db.execute("UPDATE orders SET price=?, status='accepted' WHERE id=?", (offer, order_id))
        await db.commit()
    try:
        await call.message.edit_text("✅ Договорились! Цена: " + str(offer) + " сомони")
    except Exception:
        pass
    await finalize_accept(call.bot, order_id, driver_id, client_id, offer)

@router.callback_query(F.data.startswith("client_counter:"))
async def client_counter(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT negotiation_round, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row or row[1] != "negotiating":
        await call.answer("Заказ закрыт", show_alert=True)
        return
    if row[0] >= MAX_NEGOTIATION_ROUNDS:
        await call.answer("Максимум раундов", show_alert=True)
        return
    await state.set_state(OrderFlow.client_offer)
    await state.update_data(counter_order_id=order_id)
    await call.message.answer("📝 Введите свою цену в сомони:")
    await call.answer()

@router.message(OrderFlow.client_offer, F.text)
async def client_counter_save(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("counter_order_id") or data.get("order_id")
    if not order_id:
        await message.answer("⚠️ Ошибка. Начните заново.")
        await state.clear()
        return
    try:
        offer = int((message.text or "").strip())
        if offer < 1:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Введите целое число.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, recommended_price, negotiation_round, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[3] != "negotiating":
            await message.answer("⚠️ Заказ недоступен.")
            await state.clear()
            return
        driver_id = row[0]
        recommended = row[1]
        round_n = row[2] + 1
        minimum = min_price_for(recommended)
        if offer < minimum:
            await message.answer("⚠️ Слишком низкая цена. Введите больше.")
            return
        await db.execute("UPDATE orders SET price=?, negotiation_round=?, last_offer_by='client' WHERE id=?", (offer, round_n, order_id))
        await db.commit()
    await state.clear()
    dkb = InlineKeyboardBuilder()
    dkb.button(text="✅ Принять — " + str(offer) + " сомони", callback_data="accept:" + str(order_id))
    dkb.button(text="💰 Предложить свою", callback_data="driver_offer:" + str(order_id))
    dkb.adjust(1)
    text = ("💸 Клиент предлагает: " + str(offer) + " сомони\n\n"
            "Раунд: " + str(round_n) + "/" + str(MAX_NEGOTIATION_ROUNDS))
    try:
        await message.bot.send_message(driver_id, text, reply_markup=dkb.as_markup())
    except Exception:
        pass
    await message.answer("📤 Ваша цена отправлена водителю.")
    @router.callback_query(F.data.startswith("accept:"))
async def accept_order(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, client_id, price, from_lat, from_lon, to_lat, to_lon, payment, negotiation_round, last_offer_by, recommended_price FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row:
            await call.answer("Не найден", show_alert=True)
            return
        status = row[0]
        client_id = row[1]
        price = row[2]
        if status not in ("pending", "scheduled", "negotiating"):
            await call.answer("Уже занят", show_alert=True)
            return
        if status == "negotiating" and row[9] == "driver":
            await call.answer("Ждём ответа клиента", show_alert=True)
            return
        await db.execute("UPDATE orders SET driver_id=?, status='accepted' WHERE id=?", (call.from_user.id, order_id))
        await db.commit()
    await finalize_accept(call.bot, order_id, call.from_user.id, client_id, price)

async def finalize_accept(bot: Bot, order_id: int, driver_id: int, client_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT from_lat, from_lon, to_lat, to_lon, payment, comment FROM orders WHERE id=?", (order_id,))
        orow = await cur.fetchone()
        cur = await db.execute("SELECT car_brand, car_plate, car_class, driver_lat, driver_lon, phone, first_name, last_name, car_photo, self_photo, call_phone, city FROM users WHERE user_id=?", (driver_id,))
        drow = await cur.fetchone()
        cur = await db.execute("SELECT phone, first_name, last_name, call_phone, city FROM users WHERE user_id=?", (client_id,))
        crow = await cur.fetchone()
    flat, flon, tlat, tlon = orow[0], orow[1], orow[2], orow[3]
    payment = orow[4]
    comment = orow[5] or ""
    car_brand = drow[0] if drow and drow[0] else "-"
    car_plate = drow[1] if drow and drow[1] else "-"
    car_class = drow[2] if drow and drow[2] else "-"
    driver_phone = drow[5] if drow else "-"
    driver_name = ((drow[6] or "") + " " + (drow[7] or "")).strip() if drow else "Водитель"
    driver_self_photo = drow[9] if drow else None
    driver_call_phone = drow[10] if drow and drow[10] else "—"
    driver_city = drow[11] if drow and len(drow) > 11 and drow[11] else "—"
    client_phone = crow[0] if crow else "-"
    client_name = ((crow[1] or "") + " " + (crow[2] or "")).strip() if crow else "Клиент"
    client_call_phone = crow[3] if crow and crow[3] else "—"
    client_city = crow[4] if crow and len(crow) > 4 and crow[4] else "—"
    dlat = drow[3] if drow else None
    dlon = drow[4] if drow else None
    eta_driver = estimate_minutes(haversine(dlat, dlon, flat, flon)) if dlat and dlon else None
    eta_ride = estimate_minutes(haversine(flat, flon, tlat, tlon))
    eta_driver_text = str(eta_driver) + " мин" if eta_driver else "-"
    eta_ride_text = str(eta_ride) + " мин" if eta_ride else "-"
    pay_text = "💵 Наличные" if payment == "cash" else "💳 Картой"
    comment_text = "\n💬 " + comment if comment else ""
    await log_action(driver_id, "accept_order", "id=" + str(order_id) + " price=" + str(price))

    try:
        await bot.send_message(driver_id, "✅ Вы приняли заказ #" + str(order_id) + "\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ До клиента: " + eta_driver_text + "\n⏳ Поездка: " + eta_ride_text + "\n\n👤 " + client_name + "\n🏙️ " + str(client_city) + "\n📱 Telegram: " + str(client_phone) + "\n📞 Звонок: " + str(client_call_phone) + comment_text)
    except Exception:
        pass
    try:
        await bot.send_location(driver_id, latitude=flat, longitude=flon)
        await bot.send_message(driver_id, "🚕 Маршрут к клиенту (точка A):\n" + nav_link(dlat if dlat else flat, dlon if dlon else flon, flat, flon))
    except Exception:
        pass

    dkb = InlineKeyboardBuilder()
    dkb.button(text="🚗 Я выехал", callback_data="drv_status:on_way:" + str(order_id))
    dkb.button(text="📍 Я рядом", callback_data="drv_status:near:" + str(order_id))
    dkb.button(text="✅ Я приехал (взял клиента)", callback_data="drv_status:picked:" + str(order_id))
    dkb.button(text="📡 Включить Live-локацию", callback_data="live_loc:" + str(order_id))
    dkb.button(text="💬 Чат с клиентом", callback_data="chat_start:" + str(order_id))
    dkb.button(text="✅ Завершить поездку", callback_data="finish:" + str(order_id))
    dkb.adjust(1)
    try:
        await bot.send_message(driver_id, "🎛 Управление поездкой:", reply_markup=dkb.as_markup())
    except Exception:
        pass

    ckb = InlineKeyboardBuilder()
    ckb.button(text="💬 Чат с водителем", callback_data="chat_start:" + str(order_id))
    ckb.button(text="📍 Где водитель", callback_data="where_driver:" + str(order_id))
    ckb.adjust(1)
    caption = ("🚗 Водитель принял заказ #" + str(order_id) + "\n\n"
               "👤 " + driver_name + "\n"
               "🏙️ " + str(driver_city) + "\n"
               "📱 Telegram: " + str(driver_phone) + "\n"
               "📞 Звонок: " + str(driver_call_phone) + "\n\n"
               "🚙 " + car_brand + " " + car_plate + " (" + car_class + ")\n\n"
               "💰 " + str(price) + " сомони\n"
               "💳 " + pay_text + "\n\n"
               "⏱️ Подъедет через: " + eta_driver_text + "\n"
               "⏳ Поездка: " + eta_ride_text + comment_text)
    try:
        if driver_self_photo:
            await bot.send_photo(client_id, photo=driver_self_photo, caption=caption)
        else:
            await bot.send_message(client_id, caption)
    except Exception:
        await bot.send_message(client_id, caption)
    try:
        await bot.send_message(client_id, "🎛 Действия:", reply_markup=ckb.as_markup())
    except Exception:
        pass

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
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT driver_lat, driver_lon FROM users WHERE user_id=?", (call.from_user.id,))
            drow = await cur.fetchone()
        cur_lat = drow[0] if drow and drow[0] else tlat
        cur_lon = drow[1] if drow and drow[1] else tlon
        try:
            await call.bot.send_message(call.from_user.id, "🚕 Маршрут к месту назначения (точка B):\n" + nav_link(cur_lat, cur_lon, tlat, tlon))
        except Exception:
            pass
    await call.answer("Отправлено клиенту")

@router.callback_query(F.data.startswith("live_loc:"))
async def live_loc(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row:
        await call.answer("Заказ не найден", show_alert=True)
        return
    client_id = row[0]
    await call.message.answer("📡 Как включить Live-локацию:\n\n"
                              "1. Нажмите на скрепку 📎 внизу\n"
                              "2. Выберите «Геопозиция»\n"
                              "3. Нажмите «Транслировать 1 час»\n\n"
                              "Клиент увидит вашу движущуюся метку на карте.")
    try:
        await call.bot.send_message(client_id, "📡 Водитель включает трансляцию геопозиции.\n\nСледите за ним в чате с ботом.")
    except Exception:
        pass
    await call.answer("Инструкция отправлена")

@router.callback_query(F.data.startswith("where_driver:"))
async def where_driver(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT driver_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[1] not in ("accepted", "arrived", "started"):
            await call.answer("Заказ не активен", show_alert=True)
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

@router.message(F.text.in_(["🟢 Я на линии", "🟢 Ман дар хат"]))
async def go_online(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT approved, rejected, banned FROM users WHERE user_id=?", (uid,))
        arow = await cur.fetchone()
    if arow and arow[2]:
        await message.answer("🚫 Вы заблокированы.")
        return
    if arow and arow[1]:
        await message.answer(tr(lang, "rejected"))
        return
    if not arow or not arow[0]:
        await message.answer(tr(lang, "wait_approve"))
        return
    sub_ok = await has_subscription(uid)
    if not sub_ok:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT first50_used FROM users WHERE user_id=?", (uid,))
            f50 = await cur.fetchone()
        if not f50 or not f50[0]:
            drivers_count = await get_drivers_count()
            if drivers_count < FIRST50_LIMIT:
                await give_subscription(uid, days=FIRST50_DAYS)
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("UPDATE users SET first50_used=1 WHERE user_id=?", (uid,))
                    await db.commit()
                await message.answer("🎉 Поздравляем! Вы в числе первых " + str(FIRST50_LIMIT) + " водителей!\n\n🎁 Вам дано " + str(FIRST50_DAYS) + " дней подписки бесплатно.")
            else:
                await message.answer(tr(lang, "sub_no"))
                return
        else:
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
        cur = await db.execute("SELECT phone, first_name, last_name, call_phone, city FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        await db.commit()
    await state.clear()
    lang = await get_lang(uid)
    phone = row[0] if row else "-"
    name = ((row[1] or "") + " " + (row[2] or "")).strip() if row else "-"
    call_phone = row[3] if row and row[3] else "—"
    city = row[4] if row and row[4] else "—"
    await log_action(uid, "driver_registration", car_brand + " " + car_plate + " | " + city)
    await message.answer("✅ Данные отправлены админу.\n\n⏳ Ожидайте одобрения.", reply_markup=driver_menu(lang))

    text = ("🆕 НОВЫЙ ВОДИТЕЛЬ\n\n👤 " + name + "\n🏙️ " + str(city) + "\n📱 Telegram: " + str(phone) + "\n📞 Звонок: " + str(call_phone) + "\n🆔 " + str(uid) + "\n\n🚗 " + car_brand + " " + car_plate + "\n🎯 " + car_class)
    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data="drv_ok:" + str(uid))
    b.button(text="❌ Отклонить", callback_data="drv_no:" + str(uid))
    b.adjust(2)
    super_admin = SUPER_ADMIN_ID
    helpers = await get_all_helpers()
    try:
        await message.bot.send_message(super_admin, text)
        if car_photo:
            await message.bot.send_photo(super_admin, photo=car_photo, caption="📸 Фото машины")
        if photo_id:
            await message.bot.send_photo(super_admin, photo=photo_id, caption="📸 Фото водителя")
        await message.bot.send_message(super_admin, "🎛 Решение:", reply_markup=b.as_markup())
    except Exception as e:
        logging.warning("Error super: " + str(e))
    for h in helpers:
        try:
            await message.bot.send_message(h, text)
            if car_photo:
                await message.bot.send_photo(h, photo=car_photo, caption="📸 Фото машины")
            if photo_id:
                await message.bot.send_photo(h, photo=photo_id, caption="📸 Фото водителя")
            await message.bot.send_message(h, "🎛 Решение:", reply_markup=b.as_markup())
        except Exception as e:
            logging.warning("Error helper: " + str(e))

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
    await log_action(message.from_user.id, "driver_online")
    days = await days_left_subscription(message.from_user.id)
    await message.answer("🟢 Вы на линии.\n⏳ Подписка: " + str(days) + " дн.", reply_markup=driver_menu(lang))

@router.message(DriverReg.location)
async def drv_location_wrong(message: Message):
    await message.answer("Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(F.text.in_(["🔴 Уйти с линии", "🔴 Аз хат рафтан"]))
async def go_offline(message: Message):
    uid = message.from_user.id
    await set_online(uid, 0)
    lang = await get_lang(uid)
    await log_action(uid, "driver_offline")
    await message.answer("🔴 Вы ушли с линии.", reply_markup=driver_menu(lang))

@router.callback_query(F.data.startswith("drv_ok:"))
async def driver_approve(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approved=1, rejected=0 WHERE user_id=?", (uid,))
        await db.commit()
    await log_action(uid, "driver_approved", "by=" + str(call.from_user.id))
    lang = await get_lang(uid)
    try:
        await call.bot.send_message(uid, "🎉 " + ("Вас приняли на работу!" if lang == "ru" else "Шуморо ба кор қабул карданд!") + "\n\n💳 Оформите подписку (30 сомони)\n🟢 Нажмите Я на линии")
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
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approved=0, rejected=1 WHERE user_id=?", (uid,))
        await db.commit()
    await log_action(uid, "driver_rejected", "by=" + str(call.from_user.id))
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
    @router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(Admin2FA.waiting_password)
    await message.answer("🔐 Введите пароль админа:")

@router.message(Admin2FA.waiting_password)
async def admin_2fa(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    txt = (message.text or "").strip()
    if txt != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль.")
        await log_action(message.from_user.id, "admin_2fa_fail")
        await state.clear()
        return
    await state.clear()
    await log_action(message.from_user.id, "admin_login")
    lang = await get_lang(message.from_user.id)
    await message.answer("👑 Админ-панель", reply_markup=admin_menu(lang))

@router.message(F.text.in_(["🔙 Выйти", "🔙 Баромад"]))
async def admin_exit(message: Message):
    if not await is_admin(message.from_user.id):
        return
    lang = await get_lang(message.from_user.id)
    await message.answer("Выход.", reply_markup=main_menu(lang))

@router.message(F.text.in_(["📊 Статистика", "📊 Омор"]))
async def admin_stats(message: Message):
    if not await is_admin(message.from_user.id):
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
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE banned=1")
        bans = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM sub_requests WHERE status='approved'")
        subs = (await cur.fetchone())[0]
    text = ("📊 Статистика\n\n"
            "👤 Клиентов: " + str(clients) + "\n"
            "🚗 Водителей: " + str(drivers) + "\n"
            "📦 Заказов: " + str(total) + "\n"
            "✅ Завершено: " + str(fin) + "\n"
            "❌ Отменено: " + str(can) + "\n"
            "💰 Оборот: " + str(rev) + " сомони\n"
            "💵 Комиссия 10%: " + str(int(rev * 0.1)) + " сомони\n"
            "💳 Подписок оплачено: " + str(subs) + "\n"
            "🚫 Забанено: " + str(bans) + "\n"
            "⚠️ Новых жалоб: " + str(comp))
    await message.answer(text)

@router.message(F.text.in_(["👑 Админы", "👑 Админҳо"]))
async def admins_manage(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Только главный админ может управлять помощниками.")
        return
    helpers = await get_all_helpers()
    text = "👑 Управление админами\n\n"
    text += "Главный админ:\n🆔 " + str(SUPER_ADMIN_ID) + "\n\n"
    text += "Помощники (" + str(len(helpers)) + "):\n"
    if not helpers:
        text += "Нет помощников\n"
    else:
        for h in helpers:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT first_name, last_name, city FROM users WHERE user_id=?", (h,))
                row = await cur.fetchone()
            if row:
                name = (row[0] or "") + " " + (row[1] or "")
                city = row[2] or "—"
                text += "🆔 " + str(h) + " — " + name.strip() + " (" + city + ")\n"
            else:
                text += "🆔 " + str(h) + "\n"
    text += "\nКоманды:\n/add_admin ID — добавить\n/remove_admin ID — удалить"
    await message.answer(text)

@router.message(Command("add_admin"))
async def add_admin_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Только главный админ.")
        return
    args = (message.text or "").split()
    if len(args) < 2:
        await message.answer("Формат: /add_admin 123456789")
        return
    try:
        new_id = int(args[1])
    except Exception:
        await message.answer("ID должен быть числом.")
        return
    if new_id == SUPER_ADMIN_ID:
        await message.answer("Это главный админ.")
        return
    await add_admin(new_id, SUPER_ADMIN_ID)
    await log_action(new_id, "added_as_admin", "by=" + str(SUPER_ADMIN_ID))
    await message.answer("✅ Помощник добавлен: " + str(new_id))
    try:
        await message.bot.send_message(new_id, "👑 Вы назначены помощником админа!\n\nТеперь вам приходят заявки водителей, подписки и жалобы.")
    except Exception:
        pass

@router.message(Command("remove_admin"))
async def remove_admin_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Только главный админ.")
        return
    args = (message.text or "").split()
    if len(args) < 2:
        await message.answer("Формат: /remove_admin 123456789")
        return
    try:
        rem_id = int(args[1])
    except Exception:
        await message.answer("ID должен быть числом.")
        return
    await remove_admin(rem_id)
    await log_action(rem_id, "removed_from_admin", "by=" + str(SUPER_ADMIN_ID))
    await message.answer("✅ Помощник удалён: " + str(rem_id))
    try:
        await message.bot.send_message(rem_id, "❌ Вы больше не помощник админа.")
    except Exception:
        pass

@router.message(F.text.in_(["👑 Список админов"]))
async def admins_list_btn(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    helpers = await get_all_helpers()
    text = "👑 Список админов\n\n"
    text += "1. Главный: 🆔 " + str(SUPER_ADMIN_ID) + "\n"
    for i, h in enumerate(helpers, start=2):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT first_name, last_name, city FROM users WHERE user_id=?", (h,))
            row = await cur.fetchone()
        if row:
            name = ((row[0] or "") + " " + (row[1] or "")).strip()
            city = row[2] or "—"
            text += str(i) + ". 🆔 " + str(h) + " — " + name + " (" + city + ")\n"
        else:
            text += str(i) + ". 🆔 " + str(h) + "\n"
    await message.answer(text)

@router.message(F.text.in_(["🚗 Список водителей"]))
async def drivers_list_full(message: Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, first_name, last_name, phone, call_phone, city, rating, rides, total_rides, banned FROM users WHERE role='driver' ORDER BY total_rides DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Водителей нет.")
        return
    text = "🚗 Список водителей (" + str(len(rows)) + ")\n\n"
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    for uid, fn, ln, phone, cphone, city, rating, rides, total, banned in rows:
        name = ((fn or "") + " " + (ln or "")).strip() or "—"
        flag = "🚫" if banned else "✅"
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)=?", (uid, today))
            d1 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished' AND DATE(created_at)>=?", (uid, week_ago))
            d30 = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE driver_id=? AND status='finished'", (uid,))
            dall = await cur.fetchone()
        text += (flag + " " + name + "\n"
                 "🏙️ " + str(city or "—") + "\n"
                 "📱 " + str(phone or "—") + "\n"
                 "📞 " + str(cphone or "—") + "\n"
                 "⭐ " + str(round(rating or 5.0, 1)) + " | 🚕 " + str(total or 0) + "\n"
                 "💰 Сегодня: " + str(d1[1]) + " | 30д: " + str(d30[1]) + " | Всего: " + str(dall[1]) + "\n"
                 "🆔 " + str(uid) + "\n\n")
    await message.answer(text)

@router.message(F.text.in_(["👤 Список пассажиров"]))
async def clients_list_full(message: Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, first_name, last_name, phone, call_phone, city, banned FROM users WHERE role='client' ORDER BY user_id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Пассажиров нет.")
        return
    text = "👤 Список пассажиров (" + str(len(rows)) + ")\n\n"
    for uid, fn, ln, phone, cphone, city, banned in rows[:50]:
        name = ((fn or "") + " " + (ln or "")).strip() or "—"
        flag = "🚫" if banned else "✅"
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE client_id=? AND status='finished'", (uid,))
            s = await cur.fetchone()
            cur = await db.execute("SELECT driver_id FROM orders WHERE client_id=? AND status='finished' AND driver_id IS NOT NULL ORDER BY id DESC LIMIT 3", (uid,))
            dlist = await cur.fetchall()
        drivers_str = ""
        for (did,) in dlist:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT first_name, last_name FROM users WHERE user_id=?", (did,))
                r = await cur.fetchone()
            if r:
                drivers_str += ((r[0] or "") + " " + (r[1] or "")).strip() + " | "
        text += (flag + " " + name + "\n"
                 "🏙️ " + str(city or "—") + "\n"
                 "📱 " + str(phone or "—") + "\n"
                 "🚕 Поездок: " + str(s[0]) + " | 💰 " + str(s[1]) + " сомони\n"
                 "👥 Ездил с: " + (drivers_str or "—") + "\n"
                 "🆔 " + str(uid) + "\n\n")
    await message.answer(text)

@router.message(F.text.in_(["🚫 Забанить", "🚫 Баст"]))
async def ban_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminManage.waiting_ban_id)
    await message.answer("🚫 Введите ID пользователя для бана:\n\nУзнать ID — через @userinfobot")

@router.message(AdminManage.waiting_ban_id)
async def ban_get_id(message: Message, state: FSMContext):
    try:
        target_id = int((message.text or "").strip())
    except Exception:
        await message.answer("ID должен быть числом.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, last_name, role FROM users WHERE user_id=?", (target_id,))
        row = await cur.fetchone()
    if not row:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return
    await state.update_data(ban_target=target_id)
    await state.set_state(AdminManage.waiting_ban_reason)
    name = ((row[0] or "") + " " + (row[1] or "")).strip()
    await message.answer("Пользователь: " + name + " (" + str(row[2] or "—") + ")\n\n📝 Введите причину бана:")

@router.message(AdminManage.waiting_ban_reason)
async def ban_set_reason(message: Message, state: FSMContext):
    reason = (message.text or "").strip()[:200]
    if not reason:
        await message.answer("Напишите причину.")
        return
    data = await state.get_data()
    target_id = data.get("ban_target")
    await ban_user(target_id, reason, message.from_user.id)
    await log_action(target_id, "banned", "reason=" + reason + " by=" + str(message.from_user.id))
    await state.clear()
    await message.answer("✅ Пользователь " + str(target_id) + " забанен.\n📝 Причина: " + reason)
    try:
        await message.bot.send_message(target_id, "🚫 Вы заблокированы.\n\n📝 Причина: " + reason + "\n\nСвяжитесь с администратором.")
    except Exception:
        pass

@router.message(F.text.in_(["✅ Разбанить"]))
async def unban_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminManage.waiting_unban_id)
    await message.answer("✅ Введите ID пользователя для разбана:")

@router.message(AdminManage.waiting_unban_id)
async def unban_do(message: Message, state: FSMContext):
    try:
        target_id = int((message.text or "").strip())
    except Exception:
        await message.answer("ID должен быть числом.")
        return
    await unban_user(target_id)
    await log_action(target_id, "unbanned", "by=" + str(message.from_user.id))
    await state.clear()
    await message.answer("✅ Пользователь " + str(target_id) + " разбанен.")
    try:
        await message.bot.send_message(target_id, "✅ Вы разблокированы. Можете снова пользоваться ботом.")
    except Exception:
        pass

@router.message(F.text.in_(["📋 Список банов"]))
async def bans_list(message: Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, first_name, last_name, role, ban_reason, banned_by, banned_at FROM users WHERE banned=1 ORDER BY banned_at DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("✅ Никто не забанен.")
        return
    text = "🚫 Забаненные (" + str(len(rows)) + ")\n\n"
    for uid, fn, ln, role, reason, by, dt in rows:
        name = ((fn or "") + " " + (ln or "")).strip() or "—"
        text += ("🆔 " + str(uid) + " — " + name + " (" + str(role or "—") + ")\n"
                 "📝 " + str(reason or "—") + "\n"
                 "👮 Забанил: " + str(by or "—") + "\n"
                 "📅 " + str(dt or "—") + "\n\n")
    await message.answer(text)

@router.message(F.text.in_(["🚗 Водители", "🚗 Ронандагон"]))
async def admin_drivers(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await drivers_list_full(message)

@router.message(F.text.in_(["👤 Клиенты", "👤 Мизоҷон"]))
async def admin_clients(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await clients_list_full(message)

@router.message(F.text.in_(["📦 Заказы", "📦 Фармоишҳо"]))
async def admin_orders(message: Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, client_id, driver_id, price, status FROM orders ORDER BY id DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    text = "📦 Заказы\n\n"
    for oid, cid, did, price, status in rows:
        text += "#" + str(oid) + " " + str(price) + " сомони " + status + " К:" + str(cid) + " В:" + str(did or "—") + "\n"
    await message.answer(text)

@router.message(F.text.in_(["⚠️ Жалобы", "⚠️ Шикоятҳо"]))
async def admin_complaints(message: Message):
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT code, discount, uses, max_uses, active FROM promos ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    text = "🎁 Промокоды\n\n"
    if not rows:
        text += "Нет промокодов.\n"
    else:
        for code, disc, uses, mx, act in rows:
            text += ("✅" if act else "❌") + " " + code + " — " + str(disc) + "% (" + str(uses) + "/" + str(mx) + ")\n"
    text += "\nСоздать: /newpromo"
    await message.answer(text)

@router.message(Command("newpromo"))
async def new_promo(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
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
            await message.answer("✅ Промокод " + data["code"] + " — " + str(disc) + "%")
        except Exception:
            await message.answer("⚠️ Уже существует.")
    await state.clear()

@router.message(F.text.in_(["⭐ Отзывы", "⭐ Шарҳҳо"]))
async def admin_reviews(message: Message):
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
        return
    now = datetime.now()
    day_ago = (now - timedelta(days=1)).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND created_at >= ?", (day_ago,))
        d1 = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE status='finished' AND created_at >= ?", (week_ago,))
        d7 = await cur.fetchone()
    per_day = d7[1] / 7 if d7[0] else 0
    month = per_day * 30
    text = ("📈 Прогноз\n\n"
            "За сутки: " + str(d1[0]) + " заказов, " + str(d1[1]) + " сомони\n"
            "За 7 дней: " + str(d7[0]) + " заказов, " + str(d7[1]) + " сомони\n\n"
            "📊 Средний доход/день: " + str(round(per_day, 1)) + " сомони\n"
            "Прогноз на 30 дней: " + str(int(month)) + " сомони\n"
            "💵 Комиссия 10%: " + str(int(month * 0.1)) + " сомони")
    await message.answer(text)

@router.message(F.text.in_(["📜 Логи", "📜 Логҳо"]))
async def admin_logs(message: Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, action, details, created_at FROM logs ORDER BY id DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Логов нет.")
        return
    text = "📜 Последние 30 логов\n\n"
    for uid, action, details, dt in rows:
        d = dt[:16] if dt else ""
        text += "[" + d + "] " + str(uid) + " — " + action + "\n"
        if details:
            text += "   " + details[:80] + "\n"
    await message.answer(text)

@router.message(F.text.in_(["🚫 Чёрный список", "🚫 Рӯйхати сиёҳ"]))
async def admin_blacklist(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await bans_list(message)

@router.message(F.text.in_(["📢 Рассылка", "📢 Паём"]))
async def broadcast_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="👑 Админам", callback_data="bc_target:admins")
    builder.button(text="🚗 Водителям", callback_data="bc_target:drivers")
    builder.button(text="👤 Пассажирам", callback_data="bc_target:clients")
    builder.adjust(1)
    await message.answer("📢 Кому отправить рассылку?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("bc_target:"))
async def broadcast_choose(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    target = call.data.split(":")[1]
    await state.update_data(bc_target=target)
    await state.set_state(Broadcast.text)
    names = {"admins": "админам", "drivers": "водителям", "clients": "пассажирам"}
    await call.message.edit_text("📢 Напишите текст для рассылки " + names.get(target, target) + ".\n\nОтмена: /cancel")
    await call.answer()

@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    if await is_admin(message.from_user.id):
        await message.answer("Отменено.", reply_markup=admin_menu(lang))
    else:
        await message.answer("Отменено.", reply_markup=main_menu(lang))

@router.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    text = message.text
    data = await state.get_data()
    target = data.get("bc_target", "clients")
    await state.clear()

    if target == "admins":
        if message.from_user.id != SUPER_ADMIN_ID:
            await message.answer("Только главный админ может рассылать админам.")
            return
        recipients = await get_all_admins()
    elif target == "drivers":
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE role='driver' AND banned=0")
            recipients = [r[0] for r in await cur.fetchall()]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE role='client' AND banned=0")
            recipients = [r[0] for r in await cur.fetchall()]

    sent = 0
    for uid in recipients:
        try:
            await message.bot.send_message(uid, "📢 Сообщение от администратора:\n\n" + text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await log_action(message.from_user.id, "broadcast", "target=" + target + " sent=" + str(sent))
    lang = await get_lang(message.from_user.id)
    await message.answer("✅ Отправлено: " + str(sent) + " получателям", reply_markup=admin_menu(lang))

@router.message(F.text.in_(["📥 Экспорт CSV", "📥 CSV содирот"]))
async def admin_export(message: Message):
    if not await is_admin(message.from_user.id):
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

@router.message(F.text.in_(["🌍 Сменить язык", "🌍 Иваз кардани забон"]))
async def change_lang_menu(message: Message):
    await message.answer("👇 Выберите язык:", reply_markup=lang_kb())
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
    await call.message.answer("💬 Чат открыт.\n\nМожно писать текст, отправлять фото, голосовые и геолокацию.\n\nДля выхода нажмите «❌ Выйти из чата».", reply_markup=chat_kb())
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

@router.message(ChatMode.chatting, F.photo)
async def chat_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    if not partner_id:
        await state.clear()
        return
    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    try:
        await message.bot.send_photo(partner_id, photo=photo_id, caption="📸 " + caption if caption else "📸 Фото")
    except Exception:
        pass

@router.message(ChatMode.chatting, F.voice)
async def chat_voice(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    if not partner_id:
        await state.clear()
        return
    try:
        await message.bot.send_message(partner_id, "🎤 Голосовое сообщение:")
        await message.bot.send_voice(partner_id, voice=message.voice.file_id)
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
        await message.bot.send_message(partner_id, role_text + " — " + name + ":\n\n" + message.text)
        await message.answer("✅ Отправлено", reply_markup=chat_kb())
    except Exception:
        await message.answer("⚠️ Не доставлено", reply_markup=chat_kb())

@router.callback_query(F.data.startswith("client_cancel:"))
async def client_cancel(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, driver_id FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[0] not in ("pending", "scheduled", "negotiating", "accepted", "arrived", "started"):
            await call.answer("Нельзя отменить", show_alert=True)
            return
        status, driver_id = row
        await db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        await db.commit()
    await log_action(call.from_user.id, "client_cancel", "id=" + str(order_id))
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
    await log_action(driver_id, "finish_ride", "id=" + str(order_id))
    await call.message.edit_text("✅ Поездка завершена.")
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data="rate:" + str(order_id) + ":" + str(i))
    builder.adjust(5)
    try:
        await call.bot.send_message(client_id, "🏁 Поездка #" + str(order_id) + " завершена!\n\nОцените водителя:", reply_markup=builder.as_markup())
    except Exception:
        pass
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
    days = await days_left_subscription(uid)
    text = ("💰 Мой заработок\n\n"
            "Сегодня: " + str(row1[0]) + " поездок, " + str(row1[1]) + " сомони\n"
            "7 дней: " + str(row2[0]) + " поездок, " + str(row2[1]) + " сомони\n"
            "30 дней: " + str(row3[0]) + " поездок, " + str(row3[1]) + " сомони\n"
            "Всего: " + str(row4[0]) + " поездок, " + str(row4[1]) + " сомони\n\n"
            "⏳ Подписка: " + str(days) + " дн.")
    await message.answer(text)

@router.message(F.text.in_(["📊 График заработка", "📊 Графики даромад"]))
async def graph_earn(message: Message):
    if await is_admin(message.from_user.id) and message.from_user.id == SUPER_ADMIN_ID:
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
        text = ("📊 График заработка\n\n"
                "📅 Сегодня: " + str(d1[0]) + " заказов, " + str(d1[1]) + " сомони\n"
                "📅 7 дней: " + str(d7[0]) + " заказов, " + str(d7[1]) + " сомони\n"
                "📅 30 дней: " + str(d30[0]) + " заказов, " + str(d30[1]) + " сомони\n"
                "📅 365 дней: " + str(d365[0]) + " заказов, " + str(d365[1]) + " сомони\n\n"
                "💳 Подписок: " + str(subs) + "\n💰 С подписок: " + str(sub_money) + " сомони\n\n"
                "💵 Комиссия 10%:\n"
                "Сегодня: " + str(int(d1[1] * 0.1)) + "\n"
                "7 дней: " + str(int(d7[1] * 0.1)) + "\n"
                "30 дней: " + str(int(d30[1] * 0.1)) + "\n\n"
                "🏆 Итого 30 дней: " + str(int(d30[1] * 0.1) + sub_money) + " сомони")
        await message.answer(text)
        return
    uid = message.from_user.id
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
    text = ("📊 Мой график\n\n"
            "Сегодня: " + str(row1[0]) + " поездок, " + str(row1[1]) + " сомони\n"
            "7 дней: " + str(row2[0]) + " поездок, " + str(row2[1]) + " сомони\n"
            "30 дней: " + str(row3[0]) + " поездок, " + str(row3[1]) + " сомони")
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
    days = await days_left_subscription(uid)
    text = ("📊 Моя статистика\n\n"
            "👤 " + name + "\n🚗 " + car + "\n"
            "⭐ Рейтинг: " + str(round(rating, 2)) + "\n"
            "🚕 Всего поездок: " + str(row[2] or 0) + "\n"
            "⭐ Оценок: " + str(rrow[0]) + "\n"
            "⏳ Подписка: " + str(days) + " дн.")
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
            cur = await db.execute("SELECT first_name, last_name, city FROM users WHERE user_id=?", (did,))
            urow = await cur.fetchone()
        name = ((urow[0] or "") + " " + (urow[1] or "")).strip() if urow else str(did)
        city = urow[2] if urow and urow[2] else "—"
        text += str(i) + ". " + name + " (" + city + ") — " + str(cnt) + " поездок, " + str(total) + " сомони\n"
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
    await state.update_data(tariff=key, price=price, recommended_price=price)
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Наличные", callback_data="pay:cash")
    builder.button(text="💳 Картой", callback_data="pay:card")
    builder.adjust(2)
    await state.set_state(OrderFlow.payment)
    await call.message.edit_text(TARIFFS[key]["name"] + "\n💰 " + str(price) + " сомони\n\nОплата?", reply_markup=builder.as_markup())
    await call.answer()

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
        cur = await db.execute("SELECT role, phone, first_name, last_name, city FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        role = row[0] if row and row[0] else "?"
        phone = row[1] if row and row[1] else "-"
        name = ((row[2] or "") + " " + (row[3] or "")).strip() if row else "-"
        city = row[4] if row and row[4] else "—"
        cur = await db.execute("INSERT INTO complaints(from_id, from_role, text) VALUES(?,?,?)", (uid, role, text))
        cid = cur.lastrowid
        await db.commit()
    await state.clear()
    await log_action(uid, "complaint", "id=" + str(cid))
    text_admin = ("⚠️ Жалоба #" + str(cid) + "\n\n"
                  "👤 " + name + "\n"
                  "🏙️ " + city + "\n"
                  "📱 " + str(phone) + "\n"
                  "🎭 " + role + "\n"
                  "🆔 " + str(uid) + "\n\n"
                  "📝 " + text)
    b = InlineKeyboardBuilder()
    b.button(text="✉️ Ответить", callback_data="reply_compl:" + str(cid))
    b.adjust(1)
    admins = await get_all_admins()
    for admin in admins:
        try:
            await message.bot.send_message(admin, text_admin, reply_markup=b.as_markup())
        except Exception:
            pass
    await message.answer("✅ Отправлено.", reply_markup=main_menu(lang))

@router.callback_query(F.data.startswith("reply_compl:"))
async def admin_reply_start(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("Только админ", show_alert=True)
        return
    cid = int(call.data.split(":")[1])
    await state.update_data(complaint_id=cid)
    await state.set_state(AdminReply.waiting)
    await call.message.answer("✍️ Ответ:")
    await call.answer()

@router.message(AdminReply.waiting)
async def admin_reply_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
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
    text = ("🎁 Приведи друга\n\nПригласите " + str(REF_TARGET) + " друзей и получите " + str(REF_BONUS_DAYS) + " дня подписки!\n\n"
            "📊 Приглашено: " + str(count) + "\n✅ Активировано: " + str(activated) + "\n\n🔗 " + ref_link)
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
