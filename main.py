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
CARD_NUMBER = "013585959"
CARD_BANK = "Душанбе Сити (DC)"

BTN_CLIENT = "Я клиент"
BTN_DRIVER = "Я водитель"
BTN_COMPLAINT = "Пожаловаться"
BTN_CHANGE = "Сменить роль"
BTN_ORDER = "Заказать такси"
BTN_HISTORY = "История"
BTN_REF = "Приведи друга"
BTN_ONLINE = "Я на линии"
BTN_OFFLINE = "Уйти с линии"
BTN_SUB = "Подписка"
BTN_CAR = "Моя машина"
BTN_REVIEW = "Отзывы"
BTN_PROMO = "Промокоды"
BTN_SUBREQ = "Заявки"
BTN_DRIVERS = "Водители"
BTN_CLIENTS = "Клиенты"
BTN_ORDERS = "Заказы"
BTN_COMPLAINTS = "Жалобы"
BTN_STATS = "Статистика"
BTN_EXIT = "Выйти"

logging.basicConfig(level=logging.INFO)

TARIFFS = {
    "economy":  {"name": "Эконом",  "base": 10, "rate": 3},
    "comfort":  {"name": "Комфорт", "base": 15, "rate": 4},
    "business": {"name": "Бизнес",  "base": 25, "rate": 7},
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
    location = State()

class OrderFlow(StatesGroup):
    from_loc = State()
    to_loc = State()
    tariff = State()
    payment = State()
    promo = State()
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
        keyboard=[[KeyboardButton(text="Отправить номер", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def loc_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить геолокацию", request_location=True)]],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
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

def chat_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Выйти из чата")],
        ],
        resize_keyboard=True
    )

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CLIENT)],
            [KeyboardButton(text=BTN_DRIVER)],
            [KeyboardButton(text=BTN_COMPLAINT)],
        ],
        resize_keyboard=True
    )

def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ORDER)],
            [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_REF)],
            [KeyboardButton(text=BTN_COMPLAINT), KeyboardButton(text=BTN_CHANGE)],
        ],
        resize_keyboard=True
    )

def driver_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ONLINE), KeyboardButton(text=BTN_OFFLINE)],
            [KeyboardButton(text=BTN_SUB), KeyboardButton(text=BTN_CAR)],
            [KeyboardButton(text=BTN_REF), KeyboardButton(text=BTN_COMPLAINT)],
            [KeyboardButton(text=BTN_CHANGE)],
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_DRIVERS), KeyboardButton(text=BTN_CLIENTS)],
            [KeyboardButton(text=BTN_ORDERS), KeyboardButton(text=BTN_COMPLAINTS)],
            [KeyboardButton(text=BTN_SUBREQ), KeyboardButton(text=BTN_PROMO)],
            [KeyboardButton(text=BTN_REVIEW), KeyboardButton(text=BTN_EXIT)],
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
            sub_until TIMESTAMP,
            referred_by INTEGER,
            ref_count INTEGER DEFAULT 0, ref_activated INTEGER DEFAULT 0,
            car_brand TEXT, car_plate TEXT, car_class TEXT,
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
        """)
        for col in ["first_name TEXT", "last_name TEXT", "car_class TEXT"]:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN " + col)
            except Exception:
                pass
        for col in ["promo TEXT DEFAULT ''", "discount INTEGER DEFAULT 0", "review TEXT DEFAULT ''"]:
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
                            await message.bot.send_message(referrer_id, "По вашей ссылке зарегистрировался новый пользователь!")
                        except Exception:
                            pass
        except Exception:
            pass
    if not await is_registered(uid):
        await state.set_state(Reg.phone)
        await message.answer("Добро пожаловать в Такси-бот!\n\nШаг 1/3: Отправьте свой номер телефона:", reply_markup=phone_kb())
        return
    await message.answer("С возвращением! Выберите роль:", reply_markup=main_menu())

@router.message(Reg.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    uid = message.from_user.id
    phone = message.contact.phone_number
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id, phone) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone", (uid, phone))
        await db.commit()
    await state.set_state(Reg.first_name)
    await message.answer("Номер сохранён.\n\nШаг 2/3: Напишите своё имя:", reply_markup=ReplyKeyboardRemove())

@router.message(Reg.phone)
async def reg_phone_wrong(message: Message):
    await message.answer("Нажмите кнопку Отправить номер внизу.")

@router.message(Reg.first_name)
async def reg_first_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()[:50]
    if not name:
        await message.answer("Напишите имя текстом.")
        return
    await state.update_data(first_name=name)
    await state.set_state(Reg.last_name)
    await message.answer("Имя: " + name + "\n\nШаг 3/3: Напишите свою фамилию:")

@router.message(Reg.last_name)
async def reg_last_name(message: Message, state: FSMContext):
    last = (message.text or "").strip()[:50]
    if not last:
        await message.answer("Напишите фамилию текстом.")
        return
    data = await state.get_data()
    uid = message.from_user.id
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
            await message.bot.send_message(ADMIN_ID, "Новый пользователь\n\nИмя: " + data["first_name"] + " " + last + "\nUsername: " + uname + "\nТелефон: " + phone + "\nID: " + str(uid))
        except Exception:
            pass
    await message.answer("Регистрация завершена!\n\n" + data["first_name"] + " " + last + "\n" + phone + "\n\nВыберите роль:", reply_markup=main_menu())

@router.message(F.text == BTN_CLIENT)
async def role_client(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("Сначала /start и регистрация.")
        return
    await set_role(message.from_user.id, "client")
    await message.answer("Вы вошли как клиент.", reply_markup=client_menu())

@router.message(F.text == BTN_DRIVER)
async def role_driver(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("Сначала /start и регистрация.")
        return
    await set_role(message.from_user.id, "driver")
    await set_online(message.from_user.id, 0)
    sub_ok = await has_subscription(message.from_user.id)
    sub_text = "Подписка активна" if sub_ok else "Подписки нет - оплатите " + str(SUB_PRICE) + " сомони"
    await message.answer("Вы вошли как водитель.\n\n" + sub_text + "\n\nНажмите Я на линии.", reply_markup=driver_menu())

@router.message(F.text == BTN_CHANGE)
async def change_role(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите роль:", reply_markup=main_menu())

@router.message(F.text == BTN_SUB)
async def sub_info(message: Message):
    uid = message.from_user.id
    sub_ok = await has_subscription(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sub_until FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    if sub_ok and row and row[0]:
        until = datetime.fromisoformat(row[0]).strftime("%d.%m.%Y %H:%M")
        text = "Подписка активна\nДо: " + until
    else:
        text = "Подписки нет\n\nСтоимость: " + str(SUB_PRICE) + " сомони/день"
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплатить " + str(SUB_PRICE) + " сомони", callback_data="sub_pay")
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
    text = "Оплата подписки\n\nСумма: " + str(SUB_PRICE) + " сомони\nКарта: " + CARD_NUMBER + "\nБанк: " + CARD_BANK + "\n\n1. Переведите " + str(SUB_PRICE) + " сомони на карту\n2. Отправьте скриншот чека сюда (как фото)"
    await call.message.edit_text(text)
    if ADMIN_ID:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="Отклонить", callback_data="sub_no:" + str(uid))
            builder.adjust(1)
            await call.bot.send_message(ADMIN_ID, "Заявка на подписку\n\nID: " + str(uid), reply_markup=builder.as_markup())
        except Exception:
            pass
    await state.set_state(SubPayment.receipt)
    await call.answer()

@router.message(SubPayment.receipt, F.photo)
async def sub_receipt_photo(message: Message, state: FSMContext):
    uid = message.from_user.id
    photo_id = message.photo[-1].file_id
    await state.clear()
    if ADMIN_ID:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="Подтвердить", callback_data="sub_ok:" + str(uid))
            builder.button(text="Отклонить", callback_data="sub_no:" + str(uid))
            builder.adjust(2)
            await message.bot.send_photo(ADMIN_ID, photo=photo_id, caption="Чек об оплате\n\nID: " + str(uid), reply_markup=builder.as_markup())
        except Exception as e:
            logging.warning("Error: " + str(e))
    await message.answer("Чек отправлен админу!", reply_markup=driver_menu())

@router.message(SubPayment.receipt)
async def sub_receipt_wrong(message: Message):
    await message.answer("Отправьте фото чека.")

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
        await call.bot.send_message(uid, "Подписка активирована!\nДо: " + until.strftime("%d.%m.%Y %H:%M"))
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="Подписка выдана: " + str(uid))
        else:
            await call.message.edit_text("Подписка выдана: " + str(uid))
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
        await call.bot.send_message(uid, "Заявка отклонена.")
    except Exception:
        pass
    try:
        if call.message.photo:
            await call.message.edit_caption(caption="Отклонено: " + str(uid))
        else:
            await call.message.edit_text("Отклонено: " + str(uid))
    except Exception:
        pass
    await call.answer()

@router.message(F.text == BTN_REF)
async def ref_info(message: Message):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT ref_count, ref_activated FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    count = row[0] if row else 0
    activated = row[1] if row else 0
    bot_info = await message.bot.get_me()
    ref_link = "https://t.me/" + bot_info.username + "?start=ref_" + str(uid)
    text = "Приведи друга\n\nПригласите " + str(REF_TARGET) + " друзей и получите " + str(REF_BONUS_DAYS) + " дня подписки!\n\nПриглашено: " + str(count) + "\nАктивировано: " + str(activated) + "\n\nВаша ссылка:\n" + ref_link
    await message.answer(text)

@router.message(F.text == BTN_CAR)
async def my_car(message: Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    brand = row[0] if row and row[0] else "не указана"
    plate = row[1] if row and row[1] else "не указан"
    cls = row[2] if row and row[2] else "не указан"
    await state.set_state(DriverReg.car_brand)
    await message.answer("Ваша машина\n\nМарка: " + brand + "\nНомер: " + plate + "\nКласс: " + cls + "\n\nВведите новую марку:", reply_markup=ReplyKeyboardRemove())

@router.message(F.text == BTN_ONLINE)
async def go_online(message: Message, state: FSMContext):
    if not await has_subscription(message.from_user.id):
        await message.answer("Нет подписки. Стоимость: " + str(SUB_PRICE) + " сомони/день")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
    if not row or not row[0] or not row[1] or not row[2]:
        await state.set_state(DriverReg.car_brand)
        await message.answer("Укажите марку автомобиля:", reply_markup=ReplyKeyboardRemove())
        return
    await state.set_state(DriverReg.location)
    await message.answer("Машина: " + row[0] + " " + row[1] + " (" + row[2] + ")\n\nОтправьте геолокацию:", reply_markup=loc_kb())

@router.message(DriverReg.car_brand)
async def drv_brand(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=driver_menu())
        return
    brand = (message.text or "").strip()[:50]
    if not brand:
        await message.answer("Напишите марку.")
        return
    await state.update_data(car_brand=brand)
    await state.set_state(DriverReg.car_plate)
    await message.answer("Укажите номер (например 01 TJ 777 AA):", reply_markup=cancel_kb())

@router.message(DriverReg.car_plate)
async def drv_plate(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=driver_menu())
        return
    plate = (message.text or "").strip()[:20]
    if not plate:
        await message.answer("Напишите номер.")
        return
    await state.update_data(car_plate=plate)
    await state.set_state(DriverReg.car_class)
    await message.answer("Выберите класс машины:", reply_markup=class_kb())

@router.message(DriverReg.car_class, F.text.in_(CAR_CLASSES))
async def drv_class(message: Message, state: FSMContext):
    cls = message.text
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET car_brand=?, car_plate=?, car_class=? WHERE user_id=?", (data.get("car_brand", ""), data.get("car_plate", ""), cls, message.from_user.id))
        await db.commit()
    await state.set_state(DriverReg.location)
    await message.answer("Сохранено.\n\nОтправьте геолокацию:", reply_markup=loc_kb())

@router.message(DriverReg.car_class)
async def drv_class_wrong(message: Message):
    await message.answer("Выберите класс из кнопок ниже.", reply_markup=class_kb())

@router.message(DriverReg.location, F.location)
async def drv_location(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET driver_lat=?, driver_lon=?, online=1 WHERE user_id=?", (message.location.latitude, message.location.longitude, message.from_user.id))
        await db.commit()
    await state.clear()
    await message.answer("Вы на линии. Ожидайте заказы.", reply_markup=driver_menu())

@router.message(DriverReg.location)
async def drv_location_wrong(message: Message):
    await message.answer("Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(F.text == BTN_OFFLINE)
async def go_offline(message: Message):
    await set_online(message.from_user.id, 0)
    await message.answer("Вы ушли с линии.", reply_markup=driver_menu())

@router.message(F.text == BTN_ORDER)
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderFlow.from_loc)
    await message.answer("Откуда едем?", reply_markup=loc_kb())

@router.message(OrderFlow.from_loc, F.location)
async def from_loc(message: Message, state: FSMContext):
    await state.update_data(from_lat=message.location.latitude, from_lon=message.location.longitude)
    await state.set_state(OrderFlow.to_loc)
    await message.answer("Куда едем?", reply_markup=loc_kb())

@router.message(OrderFlow.to_loc, F.location)
async def to_loc(message: Message, state: FSMContext):
    data = await state.get_data()
    dist = haversine(data["from_lat"], data["from_lon"], message.location.latitude, message.location.longitude)
    if dist < 0.1:
        await message.answer("Слишком близко.")
        return
    await state.update_data(to_lat=message.location.latitude, to_lon=message.location.longitude, distance=dist)
    eta = estimate_minutes(dist)
    builder = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        price = int(t["base"] + t["rate"] * dist)
        builder.button(text=t["name"] + " - " + str(price) + " сомони", callback_data="tariff:" + key)
    builder.adjust(1)
    await state.set_state(OrderFlow.tariff)
    await message.answer("Расстояние: " + str(round(dist, 1)) + " км\nВремя: " + str(eta) + " мин\n\nВыберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(OrderFlow.tariff, F.data.startswith("tariff:"))
async def choose_tariff(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    data = await state.get_data()
    price = int(TARIFFS[key]["base"] + TARIFFS[key]["rate"] * data["distance"])
    await state.update_data(tariff=key, price=price)
    builder = InlineKeyboardBuilder()
    builder.button(text="Наличные", callback_data="pay:cash")
    builder.button(text="Картой", callback_data="pay:card")
    builder.adjust(2)
    await state.set_state(OrderFlow.payment)
    await call.message.edit_text(TARIFFS[key]["name"] + "\nЦена: " + str(price) + " сомони\n\nОплата?", reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(OrderFlow.payment, F.data.startswith("pay:"))
async def choose_payment(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(payment=method)
    builder = InlineKeyboardBuilder()
    builder.button(text="Есть промокод", callback_data="promo_yes")
    builder.button(text="Пропустить", callback_data="promo_skip")
    builder.adjust(2)
    await state.set_state(OrderFlow.promo)
    await call.message.edit_text("У вас есть промокод?", reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(OrderFlow.promo, F.data == "promo_yes")
async def promo_yes(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Напишите промокод:")
    await call.answer()

@router.message(OrderFlow.promo, F.text)
async def promo_apply(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT discount, uses, max_uses, active FROM promos WHERE code=?", (code,))
        row = await cur.fetchone()
    if not row or not row[3]:
        await message.answer("Промокод не найден.")
        return
    discount, uses, max_uses, active = row
    if uses >= max_uses:
        await message.answer("Исчерпан.")
        return
    data = await state.get_data()
    new_price = max(0, int(data["price"] * (100 - discount) / 100))
    await state.update_data(promo=code, discount=discount, price=new_price)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promos SET uses = uses + 1 WHERE code=?", (code,))
        await db.commit()
    await show_confirm(message, state)

@router.callback_query(OrderFlow.promo, F.data == "promo_skip")
async def promo_skip(call: CallbackQuery, state: FSMContext):
    await show_confirm(call.message, state)
    await call.answer()

async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    pay_text = "Наличные" if data.get("payment") == "cash" else "Картой"
    promo_text = ""
    if data.get("promo"):
        promo_text = "\nПромокод: " + data["promo"]
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="confirm_order")
    builder.button(text="Отмена", callback_data="cancel_order")
    builder.adjust(2)
    await state.set_state(OrderFlow.confirm)
    await message.answer(TARIFFS[data["tariff"]]["name"] + "\nЦена: " + str(data["price"]) + " сомони\nОплата: " + pay_text + promo_text + "\n\nПодтвердить?", reply_markup=builder.as_markup())

@router.callback_query(OrderFlow.confirm, F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Отменено.")
    await call.message.answer("В меню.", reply_markup=client_menu())
    await call.answer()

@router.callback_query(OrderFlow.confirm, F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders(client_id, from_lat, from_lon, to_lat, to_lon, distance, price, tariff, payment, promo, discount) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (call.from_user.id, data["from_lat"], data["from_lon"], data["to_lat"], data["to_lon"], data["distance"], data["price"], data["tariff"], data.get("payment", "cash"), data.get("promo", ""), data.get("discount", 0)))
        order_id = cur.lastrowid
        await db.commit()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить заказ", callback_data="client_cancel:" + str(order_id))
    pay_text = "Наличные" if data.get("payment") == "cash" else "Картой"
    eta = estimate_minutes(data["distance"])
    await call.message.edit_text("Заказ #" + str(order_id) + " создан!\n\nЦена: " + str(data["price"]) + " сомони\nОплата: " + pay_text + "\nВремя: " + str(eta) + " мин\n\nИщем водителя...")
    await call.message.answer("Ожидайте:", reply_markup=builder.as_markup())
    await notify_drivers(call.bot, order_id, data)
    await call.answer()

async def notify_drivers(bot: Bot, order_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE role='driver' AND online=1")
        drivers = await cur.fetchall()
    if not drivers:
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="Принять заказ", callback_data="accept:" + str(order_id))
    pay_text = "Наличные" if data.get("payment") == "cash" else "Картой"
    text = "Новый заказ #" + str(order_id) + "\n\n" + TARIFFS[data["tariff"]]["name"] + "\nОплата: " + pay_text + "\nРасстояние: " + str(round(data["distance"], 1)) + " км\nЦена: " + str(data["price"]) + " сомони"
    for (uid,) in drivers:
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
        if status != "pending":
            await call.answer("Уже занят", show_alert=True)
            return
        await db.execute("UPDATE orders SET driver_id=?, status='accepted' WHERE id=?", (call.from_user.id, order_id))
        await db.commit()
    pay_text = "Наличные" if payment == "cash" else "Картой"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT car_brand, car_plate, car_class, driver_lat, driver_lon, phone, first_name, last_name FROM users WHERE user_id=?", (call.from_user.id,))
        drow = await cur.fetchone()
        cur = await db.execute("SELECT phone, first_name, last_name FROM users WHERE user_id=?", (client_id,))
        crow = await cur.fetchone()
    car_brand = drow[0] if drow and drow[0] else "-"
    car_plate = drow[1] if drow and drow[1] else "-"
    car_class = drow[2] if drow and drow[2] else "-"
    driver_phone = drow[5] if drow else "-"
    driver_name = ((drow[6] or "") + " " + (drow[7] or "")).strip() if drow else "Водитель"
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
                    await call.bot.send_message(referrer_id, "Бонус! +" + str(REF_BONUS_DAYS) + " дня подписки!")
                except Exception:
                    pass
            await db.commit()
    await call.message.edit_text("Вы приняли заказ #" + str(order_id) + "\n\nЦена: " + str(price) + " сомони\nОплата: " + pay_text + "\n\nДо клиента: " + eta_driver_text + "\nПоездка: " + eta_ride_text + "\n\nКлиент: " + client_name + "\nТел: " + str(client_phone))
    await call.bot.send_location(call.from_user.id, latitude=flat, longitude=flon)
    await call.bot.send_message(call.from_user.id, "Маршрут: " + nav_link(flat, flon, tlat, tlon))
    dkb = InlineKeyboardBuilder()
    dkb.button(text="Я выехал", callback_data="drv_status:on_way:" + str(order_id))
    dkb.button(text="Я рядом", callback_data="drv_status:near:" + str(order_id))
    dkb.button(text="Я приехал", callback_data="drv_status:arrived:" + str(order_id))
    dkb.button(text="Чат с клиентом", callback_data="chat_start:" + str(order_id))
    dkb.button(text="Позвонить", url="tel:" + str(client_phone))
    dkb.button(text="Завершить поездку", callback_data="finish:" + str(order_id))
    dkb.adjust(1)
    await call.bot.send_message(call.from_user.id, "Управление:", reply_markup=dkb.as_markup())
    ckb = InlineKeyboardBuilder()
    ckb.button(text="Чат с водителем", callback_data="chat_start:" + str(order_id))
    ckb.button(text="Позвонить", url="tel:" + str(driver_phone))
    ckb.button(text="Где водитель", callback_data="where_driver:" + str(order_id))
    ckb.adjust(1)
    await call.bot.send_message(client_id, "Водитель принял заказ #" + str(order_id) + "\n\n" + driver_name + "\nТел: " + str(driver_phone) + "\n\n" + car_brand + " (" + car_class + ")\n" + car_plate + "\n\nЦена: " + str(price) + " сомони\nОплата: " + pay_text + "\n\nПодъедет через: " + eta_driver_text + "\nПоездка: " + eta_ride_text)
    await call.bot.send_message(client_id, "Действия:", reply_markup=ckb.as_markup())
    await call.answer("Заказ принят")

@router.callback_query(F.data.startswith("drv_status:"))
async def drv_status(call: CallbackQuery):
    parts = call.data.split(":")
    status_type = parts[1]
    order_id = int(parts[2])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
    if not row or row[1] not in ("accepted", "arrived", "started"):
        await call.answer("Заказ не активен", show_alert=True)
        return
    client_id = row[0]
    texts = {
        "on_way": "Водитель выехал к вам!",
        "near": "Водитель уже рядом!",
        "arrived": "Водитель приехал! Выходите к машине.",
    }
    if status_type in texts:
        try:
            await call.bot.send_message(client_id, texts[status_type])
        except Exception:
            pass
    if status_type == "arrived":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='arrived' WHERE id=?", (order_id,))
            await db.commit()
    await call.answer("Отправлено клиенту")

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
        await call.answer("Локация водителя отправлена")
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
        await call.answer("Вы не участник заказа", show_alert=True)
        return
    await state.set_state(ChatMode.chatting)
    await state.update_data(order_id=order_id, partner_id=partner_id)
    await call.message.answer("Чат открыт. Пишите сообщения.\n\nДля выхода нажмите Выйти из чата.", reply_markup=chat_kb())
    await call.answer()

@router.message(ChatMode.chatting, F.text == "Выйти из чата")
async def chat_exit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Чат закрыт.", reply_markup=main_menu())

@router.message(ChatMode.chatting, F.location)
async def chat_location(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    if not partner_id:
        await state.clear()
        return
    try:
        await message.bot.send_message(partner_id, "Локация от собеседника:")
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
    role_text = "Водитель" if role == "driver" else "Клиент"
    try:
        await message.bot.send_message(partner_id, role_text + " - " + name + ":\n\n" + message.text)
        await message.answer("Отправлено", reply_markup=chat_kb())
    except Exception:
        await message.answer("Не удалось доставить", reply_markup=chat_kb())

@router.callback_query(F.data.startswith("client_cancel:"))
async def client_cancel(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, driver_id FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row or row[0] not in ("pending", "accepted", "arrived", "started"):
            await call.answer("Нельзя", show_alert=True)
            return
        status, driver_id = row
        await db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        await db.commit()
    await call.message.edit_text("Заказ отменён.")
    if driver_id:
        try:
            await call.bot.send_message(driver_id, "Клиент отменил заказ #" + str(order_id))
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
        await db.execute("UPDATE users SET rides=rides+1 WHERE user_id=?", (driver_id,))
        await db.commit()
    await call.message.edit_text("Поездка завершена.")
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="*" * i, callback_data="rate:" + str(order_id) + ":" + str(i))
    builder.adjust(5)
    await call.bot.send_message(client_id, "Поездка #" + str(order_id) + " завершена!\n\nОцените водителя:", reply_markup=builder.as_markup())
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
    await call.message.edit_text("Спасибо! " + str(score) + " звезд\n\nНапишите отзыв (или - чтобы пропустить):")
    await call.answer()

@router.message(Review.text)
async def review_save(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()
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
                await message.bot.send_message(driver_id, "Новый отзыв\n\nОт: " + name + "\n\n" + text[:300])
            except Exception:
                pass
        await message.answer("Отзыв сохранён. Спасибо!", reply_markup=main_menu())
    else:
        await message.answer("Спасибо за оценку!", reply_markup=main_menu())

@router.message(F.text == BTN_HISTORY)
async def my_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, price, status, tariff FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 20", (message.from_user.id,))
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    text = "История поездок\n\n"
    total = 0
    for oid, price, status, tariff in rows:
        text += "#" + str(oid) + " " + TARIFFS[tariff]["name"] + " " + str(price) + " сомони (" + status + ")\n"
        if status == "finished":
            total += price
    text += "\nВсего потрачено: " + str(total) + " сомони"
    await message.answer(text)

@router.message(F.text == BTN_COMPLAINT)
async def complaint_start(message: Message, state: FSMContext):
    await state.set_state(Complaint.text)
    await message.answer("Опишите проблему:", reply_markup=ReplyKeyboardRemove())

@router.message(Complaint.text)
async def complaint_send(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
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
            b.button(text="Ответить", callback_data="reply_compl:" + str(cid))
            b.adjust(1)
            await message.bot.send_message(ADMIN_ID, "Жалоба #" + str(cid) + "\n\n" + name + "\nТел: " + str(phone) + "\nРоль: " + role + "\nID: " + str(uid) + "\n\n" + text, reply_markup=b.as_markup())
        except Exception:
            pass
    await message.answer("Отправлено.", reply_markup=main_menu())

@router.callback_query(F.data.startswith("reply_compl:"))
async def admin_reply_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Только админ", show_alert=True)
        return
    cid = int(call.data.split(":")[1])
    await state.update_data(complaint_id=cid)
    await state.set_state(AdminReply.waiting)
    await call.message.answer("Ответ:")
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
        await message.bot.send_message(uid, "Ответ на жалобу #" + str(cid) + "\n\n" + message.text)
        await message.answer("Отправлено.")
    except Exception:
        await message.answer("Не доставлено.")
    await state.clear()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Админ-панель", reply_markup=admin_menu())

@router.message(F.text == BTN_EXIT)
async def admin_exit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Выход.", reply_markup=main_menu())

@router.message(F.text == BTN_STATS)
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
    text = "Статистика\n\nКлиентов: " + str(clients) + "\nВодителей: " + str(drivers) + "\nЗаказов: " + str(total) + "\nЗавершено: " + str(fin) + "\nОтменено: " + str(can) + "\nОборот: " + str(rev) + " сомони\nКомиссия 10%: " + str(int(rev * 0.1)) + " сомони\nЖалоб: " + str(comp)
    await message.answer(text)

@router.message(F.text == BTN_DRIVERS)
async def admin_drivers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone, first_name, last_name, online, rating, rides, car_brand, car_plate, car_class FROM users WHERE role='driver' ORDER BY rides DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Водителей нет.")
        return
    text = "Водители\n\n"
    for uid, phone, fn, ln, online, rating, rides, brand, plate, cls in rows:
        on = "ON" if online else "OFF"
        name = ((fn or "") + " " + (ln or "")).strip()
        text += on + " " + name + "\nТел: " + str(phone) + "\n" + str(brand or "-") + " " + str(plate or "-") + " (" + str(cls or "-") + ")\nРейтинг: " + str(round(rating, 1)) + " Поездок: " + str(rides) + "\n\n"
    await message.answer(text)

@router.message(F.text == BTN_CLIENTS)
async def admin_clients(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, phone, first_name, last_name FROM users WHERE role='client' ORDER BY created_at DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Клиентов нет.")
        return
    text = "Клиенты\n\n"
    for uid, phone, fn, ln in rows:
        name = ((fn or "") + " " + (ln or "")).strip() or "-"
        text += name + " - " + str(phone) + "\n"
    await message.answer(text)

@router.message(F.text == BTN_ORDERS)
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, client_id, driver_id, price, status FROM orders ORDER BY id DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заказов нет.")
        return
    text = "Заказы\n\n"
    for oid, cid, did, price, status in rows:
        text += "#" + str(oid) + " " + str(price) + " сомони " + status + " К:" + str(cid) + " В:" + str(did or "-") + "\n"
    await message.answer(text)

@router.message(F.text == BTN_COMPLAINTS)
async def admin_complaints(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, from_id, from_role, text FROM complaints WHERE status='new' ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Жалоб нет.")
        return
    for cid, fid, role, text in rows:
        b = InlineKeyboardBuilder()
        b.button(text="Ответить", callback_data="reply_compl:" + str(cid))
        b.adjust(1)
        await message.answer("Жалоба #" + str(cid) + " от " + str(fid) + " (" + role + "):\n\n" + text, reply_markup=b.as_markup())

@router.message(F.text == BTN_SUBREQ)
async def admin_sub_requests(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, driver_id FROM sub_requests WHERE status='pending' ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Заявок нет.")
        return
    for _, driver_id in rows:
        b = InlineKeyboardBuilder()
        b.button(text="Подтвердить", callback_data="sub_ok:" + str(driver_id))
        b.button(text="Отклонить", callback_data="sub_no:" + str(driver_id))
        b.adjust(2)
        await message.answer("Заявка от " + str(driver_id), reply_markup=b.as_markup())

@router.message(F.text == BTN_PROMO)
async def admin_promos(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT code, discount, uses, max_uses, active FROM promos ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
    text = "Промокоды\n\n"
    if not rows:
        text += "Нет промокодов.\n"
    else:
        for code, disc, uses, mx, act in rows:
            text += ("OK" if act else "X") + " " + code + " - " + str(disc) + "% (" + str(uses) + "/" + str(mx) + ")\n"
    text += "\nЧтобы создать - /newpromo"
    await message.answer(text)

@router.message(Command("newpromo"))
async def new_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(PromoCreate.code)
    await message.answer("Код промокода:")

@router.message(PromoCreate.code)
async def promo_set_code(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()[:20]
    if not code:
        await message.answer("Введите код.")
        return
    await state.update_data(code=code)
    await state.set_state(PromoCreate.discount)
    await message.answer("Скидка в % (1-99):")

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
            await message.answer("Промокод " + data["code"] + " - " + str(disc) + "%")
        except Exception:
            await message.answer("Уже существует.")
    await state.clear()

@router.message(F.text == BTN_REVIEW)
async def admin_reviews(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, driver_id, rating, review FROM orders WHERE review != '' ORDER BY id DESC LIMIT 15")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Отзывов пока нет.")
        return
    text = "Последние отзывы\n\n"
    for oid, did, rating, review in rows:
        text += "Заказ #" + str(oid) + " Водитель: " + str(did) + " Оценка: " + str(rating) + "\n"
        text += review[:150] + "\n\n"
    await message.answer(text)

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