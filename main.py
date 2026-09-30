import asyncio
import math
import logging
import os
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, Contact
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = 0
DB_PATH = "taxi.db"
SUB_PRICE = 20
REF_TARGET = 5
REF_BONUS_DAYS = 3
AVG_SPEED = 30

logging.basicConfig(level=logging.INFO)

TARIFFS = {
    "economy":  {"name": "🚕 Эконом",  "base": 10, "rate": 3},
    "comfort":  {"name": "🚙 Комфорт", "base": 15, "rate": 4},
    "business": {"name": "🚘 Бизнес",  "base": 25, "rate": 7},
}

router = Router()

class Reg(StatesGroup):
    phone = State()

class DriverReg(StatesGroup):
    car_brand = State()
    car_plate = State()
    location = State()

class OrderFlow(StatesGroup):
    from_loc = State()
    to_loc = State()
    tariff = State()
    payment = State()
    confirm = State()

class Complaint(StatesGroup):
    text = State()

class AdminReply(StatesGroup):
    waiting = State()

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

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Я клиент")],
            [KeyboardButton(text="🚗 Я водитель")],
            [KeyboardButton(text="⚠️ Пожаловаться")],
        ],
        resize_keyboard=True
    )

def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Заказать такси")],
            [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="🎁 Приведи друга")],
            [KeyboardButton(text="⚠️ Пожаловаться"), KeyboardButton(text="🔄 Сменить роль")],
        ],
        resize_keyboard=True
    )

def driver_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Я на линии"), KeyboardButton(text="🔴 Уйти с линии")],
            [KeyboardButton(text="💳 Подписка"), KeyboardButton(text="🚗 Моя машина")],
            [KeyboardButton(text="🎁 Приведи друга"), KeyboardButton(text="⚠️ Пожаловаться")],
            [KeyboardButton(text="🔄 Сменить роль")],
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🚗 Водители"), KeyboardButton(text="👤 Клиенты")],
            [KeyboardButton(text="📦 Заказы"), KeyboardButton(text="⚠️ Жалобы")],
            [KeyboardButton(text="💳 Заявки")],
            [KeyboardButton(text="🔙 Выйти")],
        ],
        resize_keyboard=True
    )

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            role TEXT, phone TEXT,
            online INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0, rides INTEGER DEFAULT 0,
            sub_until TIMESTAMP,
            referred_by INTEGER,
            ref_count INTEGER DEFAULT 0, ref_activated INTEGER DEFAULT 0,
            car_brand TEXT, car_plate TEXT,
            driver_lat REAL, driver_lon REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER, driver_id INTEGER,
            from_lat REAL, from_lon REAL, to_lat REAL, to_lon REAL,
            distance REAL, price INTEGER, tariff TEXT,
            payment TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'pending',
            rating INTEGER DEFAULT 0,
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
        """)
        for col in ["car_brand TEXT", "car_plate TEXT", "driver_lat REAL", "driver_lon REAL"]:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN " + col)
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
        await message.answer("👋 <b>Добро пожаловать в Такси-бот!</b>\n\n📱 Отправьте свой номер телефона:", reply_markup=phone_kb(), parse_mode="HTML")
        return
    await message.answer("👋 С возвращением!\n\nВыберите роль:", reply_markup=main_menu())

@router.message(Reg.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    uid = message.from_user.id
    phone = message.contact.phone_number
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id, phone) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone", (uid, phone))
        await db.commit()
    await state.clear()
    if ADMIN_ID:
        try:
            uname = "@" + message.from_user.username if message.from_user.username else "—"
            await message.bot.send_message(ADMIN_ID, "🆕 <b>Новый пользователь</b>\n\n👤 " + message.from_user.full_name + "\n🔗 " + uname + "\n📱 " + phone + "\n🆔 <code>" + str(uid) + "</code>", parse_mode="HTML")
        except Exception:
            pass
    await message.answer("✅ <b>Регистрация завершена!</b>\n\nВыберите роль:", reply_markup=main_menu(), parse_mode="HTML")

@router.message(Reg.phone)
async def reg_phone_wrong(message: Message):
    await message.answer("⚠️ Нажмите кнопку «📱 Отправить номер» внизу.")

@router.message(F.text == "🚕 Я клиент")
async def role_client(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("Сначала /start и отправьте номер.")
        return
    await set_role(message.from_user.id, "client")
    await message.answer("✅ Вы вошли как <b>клиент</b>.", reply_markup=client_menu(), parse_mode="HTML")

@router.message(F.text == "🚗 Я водитель")
async def role_driver(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("Сначала /start и отправьте номер.")
        return
    await set_role(message.from_user.id, "driver")
    await set_online(message.from_user.id, 0)
    sub_ok = await has_subscription(message.from_user.id)
    sub_text = "✅ Подписка активна" if sub_ok else f"❌ Подписки нет — оплатите {SUB_PRICE} сомони"
    await message.answer("✅ Вы вошли как <b>водитель</b>.\n\n" + sub_text + "\n\nНажмите «🟢 Я на линии».", reply_markup=driver_menu(), parse_mode="HTML")

@router.message(F.text == "🔄 Сменить роль")
async def change_role(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите роль:", reply_markup=main_menu())

@router.message(F.text == "💳 Подписка")
async def sub_info(message: Message):
    uid = message.from_user.id
    sub_ok = await has_subscription(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if sub_ok and row and row[0]:
        until = datetime.fromisoformat(row[0]).strftime("%d.%m.%Y %H:%M")
        text = "✅ <b>Подписка активна</b>\n📅 До: " + until
    else:
        text = f"❌ <b>Подписки нет</b>\n\n💰 Стоимость: {SUB_PRICE} сомони/день"
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить {SUB_PRICE} сомони", callback_data="sub_pay")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "sub_pay")
async def sub_pay(call: CallbackQuery):
    uid = call.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM sub_requests WHERE driver_id=? AND status='pending'", (uid,))
        if await cur.fetchone():
            await call.answer("⏳ Заявка уже отправлена", show_alert=True)
            return
        await db.execute("INSERT INTO sub_requests(driver_id) VALUES(?)", (uid,))
        await db.commit()
    if ADMIN_ID:
        try:
            uname = "@" + call.from_user.username if call.from_user.username else "—"
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Подтвердить", callback_data="sub_ok:" + str(uid))
            builder.button(text="❌ Отклонить", callback_data="sub_no:" + str(uid))
            builder.adjust(2)
            await call.bot.send_message(ADMIN_ID, "💳 <b>Заявка на подписку</b>\n\n👤 " + call.from_user.full_name + "\n🔗 " + uname + "\n🆔 <code>" + str(uid) + "</code>", reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception:
            pass
    await call.message.edit_text("✅ Заявка отправлена админу. Ожидайте.")
    await call.answer()

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
        await call.bot.send_message(uid, "✅ <b>Подписка активирована!</b>\n📅 До: " + until.strftime("%d.%m.%Y %H:%M"), parse_mode="HTML")
    except Exception:
        pass
    await call.message.edit_text("✅ Подписка выдана: " + str(uid))
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
        await call.bot.send_message(uid, "❌ Заявка на подписку отклонена.")
    except Exception:
        pass
    await call.message.edit_text("❌ Отклонено: " + str(uid))
    await call.answer()

@router.message(F.text == "🎁 Приведи друга")
async def ref_info(message: Message):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT ref_count, ref_activated FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    count = row[0] if row else 0
    activated = row[1] if row else 0
    bot_info = await message.bot.get_me()
    ref_link = "https://t.me/" + bot_info.username + "?start=ref_" + str(uid)
    text = "🎁 <b>Приведи друга</b>\n\nПригласите " + str(REF_TARGET) + " друзей и получите <b>" + str(REF_BONUS_DAYS) + " дня подписки</b> бесплатно!\n\n📊 Приглашено: <b>" + str(count) + "</b>\n✅ Активировано: <b>" + str(activated) + "</b>\n\n🔗 Ваша ссылка:\n<code>" + ref_link + "</code>"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🚗 Моя машина")
async def my_car(message: Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    brand = row[0] if row and row[0] else "не указана"
    plate = row[1] if row and row[1] else "не указан"
    await state.set_state(DriverReg.car_brand)
    await message.answer("🚗 <b>Ваша машина</b>\n\nМарка: <b>" + brand + "</b>\nНомер: <b>" + plate + "</b>\n\nВведите новую марку:", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

@router.message(F.text == "🟢 Я на линии")
async def go_online(message: Message, state: FSMContext):
    if not await has_subscription(message.from_user.id):
        await message.answer(f"❌ Нет активной подписки.\n\n💰 Стоимость: <b>{SUB_PRICE} сомони/день</b>\n\nНажмите «💳 Подписка».", parse_mode="HTML")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
    if not row or not row[0] or not row[1]:
        await state.set_state(DriverReg.car_brand)
        await message.answer("🚗 Укажите марку автомобиля (например Nexia):", reply_markup=ReplyKeyboardRemove())
        return
    await state.set_state(DriverReg.location)
    await message.answer("🚗 Машина: <b>" + row[0] + " " + row[1] + "</b>\n\n📍 Отправьте текущую геолокацию:", reply_markup=loc_kb(), parse_mode="HTML")

@router.message(DriverReg.car_brand)
async def drv_brand(message: Message, state: FSMContext):
    brand = (message.text or "").strip()[:50]
    if not brand:
        await message.answer("⚠️ Напишите марку текстом.")
        return
    await state.update_data(car_brand=brand)
    await state.set_state(DriverReg.car_plate)
    await message.answer("🔢 Укажите номер автомобиля (например <code>01 TJ 777 AA</code>):", parse_mode="HTML")

@router.message(DriverReg.car_plate)
async def drv_plate(message: Message, state: FSMContext):
    plate = (message.text or "").strip()[:20]
    if not plate:
        await message.answer("⚠️ Напишите номер текстом.")
        return
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET car_brand=?, car_plate=? WHERE user_id=?", (data["car_brand"], plate, message.from_user.id))
        await db.commit()
    await state.set_state(DriverReg.location)
    await message.answer("✅ Сохранено: <b>" + data["car_brand"] + " " + plate + "</b>\n\n📍 Отправьте геолокацию:", reply_markup=loc_kb(), parse_mode="HTML")

@router.message(DriverReg.location, F.location)
async def drv_location(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET driver_lat=?, driver_lon=?, online=1 WHERE user_id=?", (message.location.latitude, message.location.longitude, message.from_user.id))
        await db.commit()
    await state.clear()
    await message.answer("🟢 Вы на линии. Ожидайте заказы.", reply_markup=driver_menu())

@router.message(DriverReg.location)
async def drv_location_wrong(message: Message):
    await message.answer("⚠️ Нажмите кнопку «📍 Отправить геолокацию» внизу.")

@router.message(F.text == "🔴 Уйти с линии")
async def go_offline(message: Message):
    await set_online(message.from_user.id, 0)
    await message.answer("🔴 Вы ушли с линии.", reply_markup=driver_menu())

@router.message(F.text == "🚕 Заказать такси")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderFlow.from_loc)
    await message.answer("📍 Откуда едем? Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(OrderFlow.from_loc, F.location)
async def from_loc(message: Message, state: FSMContext):
    await state.update_data(from_lat=message.location.latitude, from_lon=message.location.longitude)
    await state.set_state(OrderFlow.to_loc)
    await message.answer("🎯 Куда едем? Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(OrderFlow.to_loc, F.location)
async def to_loc(message: Message, state: FSMContext):
    data = await state.get_data()
    dist = haversine(data["from_lat"], data["from_lon"], message.location.latitude, message.location.longitude)
    if dist < 0.1:
        await message.answer("⚠️ Слишком близко. Отправьте другую точку.")
        return
    await state.update_data(to_lat=message.location.latitude, to_lon=message.location.longitude, distance=dist)
    eta = estimate_minutes(dist)
    builder = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        price = int(t["base"] + t["rate"] * dist)
        builder.button(text=t["name"] + " — " + str(price) + " сомони", callback_data="tariff:" + key)
    builder.adjust(1)
    await state.set_state(OrderFlow.tariff)
    await message.answer("📏 Расстояние: ~" + str(round(dist, 1)) + " км\n⏳ Поездка займёт: ~" + str(eta) + " мин\n\nВыберите тариф:", reply_markup=builder.as_markup())

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
    await call.message.edit_text("🚕 <b>" + TARIFFS[key]["name"] + "</b>\n📏 ~" + str(round(data["distance"], 1)) + " км\n💰 <b>" + str(price) + " сомони</b>\n\nКак будете платить?", reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()

@router.callback_query(OrderFlow.payment, F.data.startswith("pay:"))
async def choose_payment(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(payment=method)
    data = await state.get_data()
    pay_text = "💵 Наличные" if method == "cash" else "💳 Картой"
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.adjust(2)
    await state.set_state(OrderFlow.confirm)
    await call.message.edit_text("🚕 <b>" + TARIFFS[data["tariff"]]["name"] + "</b>\n💰 <b>" + str(data["price"]) + " сомони</b>\n💳 " + pay_text + "\n\nПодтверждаете заказ?", reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()

@router.callback_query(OrderFlow.confirm, F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Заказ отменён.")
    await call.message.answer("Вы в главном меню.", reply_markup=client_menu())
    await call.answer()

@router.callback_query(OrderFlow.confirm, F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders(client_id, from_lat, from_lon, to_lat, to_lon, distance, price, tariff, payment) VALUES(?,?,?,?,?,?,?,?,?)", (call.from_user.id, data["from_lat"], data["from_lon"], data["to_lat"], data["to_lon"], data["distance"], data["price"], data["tariff"], data.get("payment", "cash")))
        order_id = cur.lastrowid
        await db.commit()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заказ", callback_data="client_cancel:" + str(order_id))
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    eta = estimate_minutes(data["distance"])
    await call.message.edit_text("✅ <b>Заказ #" + str(order_id) + " создан!</b>\n\n💰 " + str(data["price"]) + " сомони\n💳 " + pay_text + "\n⏳ ~" + str(eta) + " мин\n\n🔍 Ищем водителя…", parse_mode="HTML")
    await call.message.answer("Ожидайте. Можно отменить:", reply_markup=builder.as_markup())
    await notify_drivers(call.bot, order_id, data)
    await call.answer()

async def notify_drivers(bot: Bot, order_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE role='driver' AND online=1")
        drivers = await cur.fetchall()
    if not drivers:
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Принять заказ", callback_data="accept:" + str(order_id))
    pay_text = "💵 Наличные" if data.get("payment") == "cash" else "💳 Картой"
    text = "🔔 <b>Новый заказ #" + str(order_id) + "</b>\n\n🚕 " + TARIFFS[data["tariff"]]["name"] + "\n💳 " + pay_text + "\n📏 ~" + str(round(data["distance"], 1)) + " км\n💰 <b>" + str(data["price"]) + " сомони</b>"
    for (uid,) in drivers:
        try:
            await bot.send_message(uid, text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception as e:
            logging.warning("Не смог отправить: " + str(e))

@router.callback_query(F.data.startswith("accept:"))
async def accept_order(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, client_id, price, from_lat, from_lon, to_lat, to_lon, payment FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row:
            await call.answer("Заказ не найден", show_alert=True)
            return
        status, client_id, price, flat, flon, tlat, tlon, payment = row
        if status != "pending":
            await call.answer("⚠️ Заказ уже занят", show_alert=True)
            return
        await db.execute("UPDATE orders SET driver_id=?, status='accepted' WHERE id=?", (call.from_user.id, order_id))
        await db.commit()
    pay_text = "💵 Наличные" if payment == "cash" else "💳 Картой"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, driver_lat, driver_lon FROM users WHERE user_id=?", (call.from_user.id,))
        drow = await cur.fetchone()
    car_brand = drow[0] if drow and drow[0] else "не указана"
    car_plate = drow[1] if drow and drow[1] else "не указан"
    dlat = drow[2] if drow else None
    dlon = drow[3] if drow else None
    if dlat and dlon:
        dist_to_client = haversine(dlat, dlon, flat, flon)
        eta_driver = estimate_minutes(dist_to_client)
    else:
        eta_driver = None
    ride_dist = haversine(flat, flon, tlat, tlon)
    eta_ride = estimate_minutes(ride_dist)
    eta_driver_text = str(eta_driver) + " мин" if eta_driver else "неизвестно"
    eta_ride_text = str(eta_ride) + " мин" if eta_ride else "неизвестно"
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
                    await call.bot.send_message(referrer_id, "🎉 <b>Бонус!</b>\n\nВы привели " + str(REF_TARGET) + " друзей!\n🎁 +" + str(REF_BONUS_DAYS) + " дня подписки!", parse_mode="HTML")
                except Exception:
                    pass
            await db.commit()
    await call.message.edit_text("✅ <b>Вы приняли заказ #" + str(order_id) + "</b>\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ До клиента: <b>" + eta_driver_text + "</b>\n⏳ Поездка: <b>" + eta_ride_text + "</b>", parse_mode="HTML")
    await call.bot.send_location(call.from_user.id, latitude=flat, longitude=flon)
    await call.bot.send_message(call.from_user.id, "📍 <b>Место клиента</b>\n\nНавигатор ниже 👇", parse_mode="HTML")
    await call.bot.send_message(call.from_user.id, "🚕 <a href='" + nav_link(flat, flon, tlat, tlon) + "'>Открыть маршрут в Яндекс.Картах</a>", parse_mode="HTML", disable_web_page_preview=True)
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершить поездку", callback_data="finish:" + str(order_id))
    await call.bot.send_message(call.from_user.id, "Когда завершите:", reply_markup=builder.as_markup())
    await call.bot.send_message(client_id, "🚗 <b>Водитель принял заказ #" + str(order_id) + "</b>\n\n🚙 " + car_brand + "\n🔢 " + car_plate + "\n\n💰 " + str(price) + " сомони\n💳 " + pay_text + "\n\n⏱️ Подъедет через: <b>" + eta_driver_text + "</b>\n⏳ Поездка: <b>" + eta_ride_text + "</b>", parse_mode="HTML")
    await call.answer("Заказ принят")

@router.callback_query(F.data.startswith("client_cancel:"))
async def client_cancel(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, driver_id FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[0] not in ("pending", "accepted"):
            await call.answer("Нельзя отменить", show_alert=True)
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
            await call.answer("Заказ не найден", show_alert=True)
            return
        client_id, driver_id, status = row
        if status != "accepted":
            await call.answer("Уже завершён", show_alert=True)
            return
        await db.execute("UPDATE orders SET status='finished' WHERE id=?", (order_id,))
        await db.execute("UPDATE users SET rides=rides+1 WHERE user_id=?", (driver_id,))
        await db.commit()
    await call.message.edit_text("✅ Поездка завершена. Спасибо!")
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data="rate:" + str(order_id) + ":" + str(i))
    builder.adjust(5)
    await call.bot.send_message(client_id, "🏁 Поездка <b>#" + str(order_id) + "</b> завершена!\n\nОцените водителя:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("rate:"))
async def rate_driver(call: CallbackQuery):
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
    await call.message.edit_text("Спасибо за оценку: " + "⭐" * score)
    try:
        await call.bot.send_message(driver_id, "⭐ Вам поставили " + str(score) + "/5")
    except Exception:
        pass
    await call.answer()

@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, price, status, tariff FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
        rows = await cur.fetchall()
    if not rows:
        await message.answer("У вас ещё не было заказов.")
        return
    emoji = {"pending": "⏳", "accepted": "🚗", "finished": "✅", "cancelled": "❌"}
    text = "📋 <b>Последние заказы:</b>\n\n"
    for oid, price, status, tariff in rows:
        text += emoji.get(status, "?") + " #" + str(oid) + " — " + TARIFFS[tariff]["name"] + " — " + str(price) + " сомони\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚠️ Пожаловаться")
async def complaint_start(message: Message, state: FSMContext):
    await state.set_state(Complaint.text)
    await message.answer("⚠️ <b>Жалоба</b>\n\nОпишите проблему одним сообщением. Админ получит её и ответит.", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

@router.message(Complaint.text)
async def complaint_send(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT role, phone FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        role = row[0] if row and row[0] else "неизвестно"
        phone = row[1] if row and row[1] else "—"
        cur = await db.execute("INSERT INTO complaints(from_id, from_role, text) VALUES(?,?,?)", (uid, role, text))
        complaint_id = cur.lastrowid
        await db.commit()
    await state.clear()
    if ADMIN_ID:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="✉️ Ответить", callback_data="reply_compl:" + str(complaint_id))
            builder.adjust(1)
            uname = "@" + message.from_user.username if message.from_user.username else "—"
            await message.bot.send_message(ADMIN_ID, "⚠️ <b>Жалоба #" + str(complaint_id) + "</b>\n\n👤 " + message.from_user.full_name + "\n🔗 " + uname + "\n📱 " + phone + "\n🎭 " + role + "\n🆔 <code>" + str(uid) + "</code>\n\n📝 " + text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception as e:
            logging.warning("Ошибка: " + str(e))
    await message.answer("✅ Жалоба отправлена админу.", reply_markup=main_menu())

@router.callback_query(F.data.startswith("reply_compl:"))
async def admin_reply_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    complaint_id = int(call.data.split(":")[1])
    await state.update_data(complaint_id=complaint_id)
    await state.set_state(AdminReply.waiting)
    await call.message.answer("✍️ Напишите ответ на жалобу #" + str(complaint_id) + ":")
    await call.answer()

@router.message(AdminReply.waiting)
async def admin_reply_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    complaint_id = data.get("complaint_id")
    if not complaint_id:
        await state.clear()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT from_id FROM complaints WHERE id=?", (complaint_id,))
        row = await cur.fetchone()
        if not row:
            await message.answer("Жалоба не найдена")
            await state.clear()
            return
        user_id = row[0]
        await db.execute("UPDATE complaints SET answer=?, status='answered' WHERE id=?", (message.text, complaint_id))
        await db.commit()
    try:
        await message.bot.send_message(user_id, "✉️ <b>Ответ на жалобу #" + str(complaint_id) + "</b>\n\n" + message.text, parse_mode="HTML")
        await message.answer("✅ Отправлено.")
    except Exception:
        await message.answer("⚠️ Не смог отправить.")
    await state.clear()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=admin_menu(), parse_mode="HTML")

@router.message(F.text == "🔙 Выйти")
async def admin_exit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Выход.", reply_markup=main_menu())

@router.message(F.text == "📊 Статистика")
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
    text = "📊 <b>Статистика</b>\n\n"
    text += "👤 Клиентов: <b>" + str(clients) + "</b>\n"
    text += "🚗 Водителей: <b>" + str(drivers) + "</b>\n"
    text += "📦 Заказов: <b>" + str(total) + "</b>\n"
    text += "✅ Завершено: <b>" + str(fin) + "</b>\n"
    text += "❌ Отменено: <b>" + str(can) + "</b>\n"
    text += "💰 Оборот: <b>" + str(rev) + " сомони</b>\n"
    text += "💵 Комиссия 10%: <b>" + str(int(rev * 0.1)) + " сомони</b>\n"
    text += "⚠️ Новых жалоб: <b>" + str(comp) + "</b>"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🚗 Водители")
async def admin_drivers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone, online, rating, rides, car_brand, car_plate FROM users WHERE role='driver' ORDER BY rides DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Водителей нет.")
        return
    text = "🚗 <b>Водители</b>\n\n"
    for uid, phone, online, rating, rides, brand, plate in rows:
        on = "🟢" if online else "⚪"
        car = (brand or "—") + " / " + (plate or "—")
        text += on + " <code>" + str(uid) + "</code> | " + str(phone) + "\n"
        text += "   🚙 " + car + " | ⭐ " + str(round(rating, 1)) + " | 🚕 " + str(rides) + "\n\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👤 Клиенты")
async def admin_clients(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone FROM users WHERE role='client' ORDER BY created_at DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Клиентов нет.")
        return
    text = "👤 <b>Клиенты (" + str(len(rows)) + ")</b>\n\n"
    for uid, phone in rows:
        text += "<code>" + str(uid) + "</code> | " + str(phone) + "\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📦 Заказы")
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, client_id, driver_id, price, status FROM orders ORDER BY id DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    emoji = {"pending": "⏳", "accepted": "🚗", "finished": "✅", "cancelled": "❌"}
    text = "📦 <b>Заказы</b>\n\n"
    for oid, cid, did, price, status in rows:
        text += emoji.get(status, "?") + " #" + str(oid) + " | " + str(price) + " сомони\n"
        text += "   К: <code>" + str(cid) + "</code> | В: <code>" + str(did or "—") + "</code>\n\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚠️ Жалобы")
async def admin_complaints(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, from_id, from_role, text FROM complaints WHERE status='new' ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("✅ Новых жалоб нет.")
        return
    for cid, from_id, role, text in rows:
        builder = InlineKeyboardBuilder()
        builder.button(text="✉️ Ответить", callback_data="reply_compl:" + str(cid))
        builder.adjust(1)
        await message.answer("⚠️ <b>Жалоба #" + str(cid) + "</b>\n\nОт: <code>" + str(from_id) + "</code> (" + role + ")\n\n" + text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message(F.text == "💳 Заявки")
async def admin_sub_requests(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, driver_id FROM sub_requests WHERE status='pending' ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("✅ Заявок нет.")
        return
    for req_id, driver_id in rows:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data="sub_ok:" + str(driver_id))
        builder.button(text="❌ Отклонить", callback_data="sub_no:" + str(driver_id))
        builder.adjust(2)
        await message.answer("💳 Заявка от <code>" + str(driver_id) + "</code>", reply_markup=builder.as_markup(), parse_mode="HTML")

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
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())