import asyncio
import math
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER"
ADMIN_ID = 0  # твой Telegram ID (узнать: @userinfobot). 0 = отключено
DB_PATH = "taxi.db"

logging.basicConfig(level=logging.INFO)

TARIFFS = {
    "economy":  {"name": "🚕 Эконом",  "base": 100, "rate": 30},
    "comfort":  {"name": "🚙 Комфорт", "base": 150, "rate": 45},
    "business": {"name": "🚘 Бизнес",  "base": 250, "rate": 70},
}

router = Router()

# ============ СОСТОЯНИЯ ============
class OrderFlow(StatesGroup):
    from_loc = State()
    to_loc = State()
    tariff = State()
    confirm = State()

class Rating(StatesGroup):
    wait_score = State()

# ============ УТИЛИТЫ ============
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def loc_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True
    )

def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Заказать такси")],
            [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="🔄 Сменить роль")],
        ],
        resize_keyboard=True
    )

def driver_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Я на линии"), KeyboardButton(text="🔴 Уйти с линии")],
            [KeyboardButton(text="🔄 Сменить роль")],
        ],
        resize_keyboard=True
    )

# ============ БД ============
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            role TEXT,
            online INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0,
            rides INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            driver_id INTEGER,
            from_lat REAL, from_lon REAL,
            to_lat REAL, to_lon REAL,
            distance REAL, price INTEGER, tariff TEXT,
            status TEXT DEFAULT 'pending',
            rating INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.commit()

async def set_role(uid, role):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users(user_id, role) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role",
            (uid, role)
        )
        await db.commit()

async def set_online(uid, val):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET online=? WHERE user_id=?", (val, uid))
        await db.commit()

# ============ СТАРТ ============
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await set_role(message.from_user.id, None)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Я клиент")],
            [KeyboardButton(text="🚗 Я водитель")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "👋 Добро пожаловать в Такси-бот!\n\n"
        "Выберите роль:\n"
        "🚕 <b>Клиент</b> — заказывает поездки\n"
        "🚗 <b>Водитель</b> — принимает заказы",
        reply_markup=kb, parse_mode="HTML"
    )

@router.message(F.text == "🚕 Я клиент")
async def role_client(message: Message):
    await set_role(message.from_user.id, "client")
    await message.answer("✅ Вы вошли как <b>клиент</b>.", reply_markup=client_menu(), parse_mode="HTML")

@router.message(F.text == "🚗 Я водитель")
async def role_driver(message: Message):
    await set_role(message.from_user.id, "driver")
    await set_online(message.from_user.id, 0)
    await message.answer(
        "✅ Вы вошли как <b>водитель</b>.\n\n"
        "Нажмите «🟢 Я на линии», чтобы начать получать заказы.",
        reply_markup=driver_menu(), parse_mode="HTML"
    )

@router.message(F.text == "🔄 Сменить роль")
async def change_role(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message, state)

# ============ ВОДИТЕЛЬ: ВКЛ/ВЫКЛ ============
@router.message(F.text == "🟢 Я на линии")
async def go_online(message: Message):
    await set_online(message.from_user.id, 1)
    await message.answer("🟢 Вы на линии. Ожидайте заказы.", reply_markup=driver_menu())

@router.message(F.text == "🔴 Уйти с линии")
async def go_offline(message: Message):
    await set_online(message.from_user.id, 0)
    await message.answer("🔴 Вы ушли с линии.", reply_markup=driver_menu())

# ============ СОЗДАНИЕ ЗАКАЗА ============
@router.message(F.text == "🚕 Заказать такси")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderFlow.from_loc)
    await message.answer("📍 Откуда едем? Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(OrderFlow.from_loc, F.location)
async def from_loc(message: Message, state: FSMContext):
    await state.update_data(from_lat=message.location.latitude,
                            from_lon=message.location.longitude)
    await state.set_state(OrderFlow.to_loc)
    await message.answer("🎯 Куда едем? Отправьте геолокацию.", reply_markup=loc_kb())

@router.message(OrderFlow.to_loc, F.location)
async def to_loc(message: Message, state: FSMContext):
    data = await state.get_data()
    dist = haversine(data["from_lat"], data["from_lon"],
                     message.location.latitude, message.location.longitude)
    if dist < 0.1:
        await message.answer("⚠️ Слишком близко. Отправьте другую точку.")
        return
    await state.update_data(to_lat=message.location.latitude,
                            to_lon=message.location.longitude,
                            distance=dist)

    builder = InlineKeyboardBuilder()
    for key, t in TARIFFS.items():
        price = int(t["base"] + t["rate"] * dist)
        builder.button(text=f"{t['name']} — {price} ₽", callback_data=f"tariff:{key}")
    builder.adjust(1)

    await state.set_state(OrderFlow.tariff)
    await message.answer(
        f"📏 Расстояние: ~{dist:.1f} км\n\nВыберите тариф:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(OrderFlow.tariff, F.data.startswith("tariff:"))
async def choose_tariff(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    data = await state.get_data()
    price = int(TARIFFS[key]["base"] + TARIFFS[key]["rate"] * data["distance"])
    await state.update_data(tariff=key, price=price)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.adjust(2)

    await state.set_state(OrderFlow.confirm)
    await call.message.edit_text(
        f"🚕 Тариф: <b>{TARIFFS[key]['name']}</b>\n"
        f"📏 Расстояние: ~{data['distance']:.1f} км\n"
        f"💰 Цена: <b>{price} ₽</b>\n\nПодтверждаете заказ?",
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )
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
        cur = await db.execute(
            """INSERT INTO orders(client_id, from_lat, from_lon, to_lat, to_lon,
                                  distance, price, tariff)
               VALUES(?,?,?,?,?,?,?,?)""",
            (call.from_user.id, data["from_lat"], data["from_lon"],
             data["to_lat"], data["to_lon"], data["distance"],
             data["price"], data["tariff"])
        )
        order_id = cur.lastrowid
        await db.commit()

    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заказ", callback_data=f"client_cancel:{order_id}")

    await call.message.edit_text(
        f"✅ Заказ <b>#{order_id}</b> создан!\n"
        f"💰 Цена: {data['price']} ₽\n\n"
        f"🔍 Ищем водителя…",
        parse_mode="HTML"
    )
    await call.message.answer("Ожидайте. Можно отменить:", reply_markup=builder.as_markup())
    await notify_drivers(call.bot, order_id, data)
    await call.answer()

# ============ ОПОВЕЩЕНИЕ ВОДИТЕЛЕЙ ============
async def notify_drivers(bot: Bot, order_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE role='driver' AND online=1")
        drivers = await cur.fetchall()

    if not drivers:
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Принять заказ", callback_data=f"accept:{order_id}")

    text = (f"🔔 <b>Новый заказ #{order_id}</b>\n"
            f"Тариф: {TARIFFS[data['tariff']]['name']}\n"
            f"📏 ~{data['distance']:.1f} км\n"
            f"💰 <b>{data['price']} ₽</b>")

    for (uid,) in drivers:
        try:
            await bot.send_message(uid, text,
                                   reply_markup=builder.as_markup(),
                                   parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Не смог отправить {uid}: {e}")

# ============ ПРИНЯТИЕ ЗАКАЗА ============
@router.callback_query(F.data.startswith("accept:"))
async def accept_order(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status, client_id, price, from_lat, from_lon, to_lat, to_lon FROM orders WHERE id=?",
                               (order_id,))
        row = await cur.fetchone()
        if not row:
            await call.answer("Заказ не найден", show_alert=True)
            return
        status, client_id, price, flat, flon, tlat, tlon = row
        if status != "pending":
            await call.answer("⚠️ Заказ уже занят", show_alert=True)
            return
        await db.execute("UPDATE orders SET driver_id=?, status='accepted' WHERE id=?",
                         (call.from_user.id, order_id))
        await db.commit()

    await call.message.edit_text(f"✅ Вы приняли заказ <b>#{order_id}</b>. Цена {price} ₽.", parse_mode="HTML")

    # клиенту — геолокация водителя не нужна, но передадим точки
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершить поездку", callback_data=f"finish:{order_id}")

    await call.bot.send_message(
        client_id,
        f"🚗 Водитель принял ваш заказ <b>#{order_id}</b>!\n"
        f"Цена: {price} ₽\n\nОжидайте прибытия.",
        parse_mode="HTML"
    )
    await call.bot.send_message(
        call.from_user.id,
        "Когда завершите поездку — нажмите кнопку:",
        reply_markup=builder.as_markup()
    )
    await call.answer("Заказ принят")

# ============ ОТМЕНА КЛИЕНТОМ ============
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
            await call.bot.send_message(driver_id, f"⚠️ Клиент отменил заказ #{order_id}.")
        except Exception:
            pass
    await call.answer()

# ============ ЗАВЕРШЕНИЕ ПОЕЗДКИ ============
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

    # оценка
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data=f"rate:{order_id}:{i}")
    builder.adjust(5)
    await call.bot.send_message(
        client_id,
        f"Поездка <b>#{order_id}</b> завершена!\nОцените водителя:",
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )
    await call.answer()

# ============ РЕЙТИНГ ============
@router.callback_query(F.data.startswith("rate:"))
async def rate_driver(call: CallbackQuery):
    _, order_id, score = call.data.split(":")
    order_id, score = int(order_id), int(score)
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

    await call.message.edit_text(f"Спасибо за оценку: {'⭐' * score}")
    try:
        await call.bot.send_message(driver_id, f"⭐ Вам поставили {score}/5 за заказ #{order_id}.")
    except Exception:
        pass
    await call.answer()

# ============ МОИ ЗАКАЗЫ ============
@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, price, status, tariff FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 5",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()

    if not rows:
        await message.answer("У вас ещё не было заказов.")
        return

    emoji = {"pending": "⏳", "accepted": "🚗", "finished": "✅", "cancelled": "❌"}
    text = "📋 <b>Последние заказы:</b>\n\n"
    for oid, price, status, tariff in rows:
        text += f"{emoji.get(status, '?')} #{oid} — {TARIFFS[tariff]['name']} — {price} ₽\n"
    await message.answer(text, parse_mode="HTML")

# ============ АДМИН ============
@router.message(Command("stats"))
async def stats(message: Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='client'")
        clients = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='driver'")
        drivers = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        orders = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM orders WHERE status='finished'")
        finished = (await cur.fetchone())[0]
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Клиентов: {clients}\n"
        f"🚗 Водителей: {drivers}\n"
        f"📦 Заказов: {orders}\n"
        f"✅ Завершено: {finished}",
        parse_mode="HTML"
    )

# ============ ЗАПУСК ============
async def main():
    await init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("🤖 Бот запущен. Не закрывай это окно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())