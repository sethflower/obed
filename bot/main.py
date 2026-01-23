from __future__ import annotations

import asyncio
import datetime as dt
import logging
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.calendar_ui import CALENDAR_PREFIX, NAV_PREFIX, CalendarRange, build_calendar
from bot.config import BOT_TOKEN, DB_PATH
from bot.db import OrderRepository

logging.basicConfig(level=logging.INFO)


DEPARTMENTS = [
    "Склад (1 этаж)",
    "Склад (2 этаж)",
    "Склад (приём товара)",
    "Сервис",
    "Охрана",
    "Хоз. отдел",
]


@dataclass
class OrderData:
    department: str | None = None
    order_date: dt.date | None = None


class OrderStates(StatesGroup):
    department = State()
    date = State()
    quantity = State()


async def start_handler(message: Message) -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Сделать заказ")]],
        resize_keyboard=True,
    )
    await message.answer(
        "Привет! Я помогу оформить заказ обедов. Нажмите «Сделать заказ».",
        reply_markup=keyboard,
    )


async def make_order_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(OrderStates.department)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=dept, callback_data=f"dept:{dept}")]
            for dept in DEPARTMENTS
        ]
    )
    await message.answer("Выберите отдел:", reply_markup=keyboard)


async def department_handler(callback: CallbackQuery, state: FSMContext) -> None:
    department = callback.data.split(":", 1)[1]
    await state.update_data(order=OrderData(department=department))
    await state.set_state(OrderStates.date)

    today = dt.date.today()
    date_range = CalendarRange(min_date=today, max_date=today + dt.timedelta(days=180))
    calendar_markup = build_calendar(today.year, today.month, date_range)

    await callback.message.edit_text(
        f"Отдел: {department}\nВыберите дату:",
        reply_markup=calendar_markup,
    )
    await callback.answer()


async def calendar_navigation_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = callback.data.split(":", 1)[1]
    year_str, month_str = data.split("-")
    year, month = int(year_str), int(month_str)

    today = dt.date.today()
    date_range = CalendarRange(min_date=today, max_date=today + dt.timedelta(days=180))
    calendar_markup = build_calendar(year, month, date_range)

    await callback.message.edit_reply_markup(reply_markup=calendar_markup)
    await callback.answer()


async def calendar_date_handler(callback: CallbackQuery, state: FSMContext) -> None:
    date_str = callback.data.split(":", 1)[1]
    selected_date = dt.date.fromisoformat(date_str)

    data = await state.get_data()
    order_data: OrderData = data.get("order", OrderData())
    order_data.order_date = selected_date
    await state.update_data(order=order_data)

    await state.set_state(OrderStates.quantity)
    await callback.message.edit_text(
        f"Дата: {selected_date.strftime('%d.%m.%Y')}\n"
        "Введите количество ланчей (можно с + или -):"
    )
    await callback.answer()


async def quantity_handler(message: Message, state: FSMContext, repo: OrderRepository) -> None:
    try:
        delta = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Введите число, например 10, -2 или +3.")
        return

    data = await state.get_data()
    order_data: OrderData = data.get("order", OrderData())
    if not order_data.department or not order_data.order_date:
        await message.answer("Что-то пошло не так. Попробуйте заново /start.")
        await state.clear()
        return

    await repo.add_order(
        user_id=message.from_user.id,
        department=order_data.department,
        order_date=order_data.order_date,
        delta=delta,
    )
    total = await repo.get_total_for_department(order_data.department, order_data.order_date)

    await message.answer(
        "Заявка принята ✅\n"
        f"Отдел: {order_data.department}\n"
        f"Дата: {order_data.order_date.strftime('%d.%m.%Y')}\n"
        f"Текущее количество ланчей: {total}"
    )
    await state.clear()


async def ignore_callback(callback: CallbackQuery) -> None:
    await callback.answer()


async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Операция отменена. Нажмите «Сделать заказ».")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    repo = OrderRepository(DB_PATH)
    await repo.connect()

    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.message.register(start_handler, Command("start"))
    dispatcher.message.register(cancel_handler, Command("cancel"))
    dispatcher.message.register(make_order_handler, F.text == "Сделать заказ")
    dispatcher.callback_query.register(department_handler, F.data.startswith("dept:"))
    dispatcher.callback_query.register(calendar_navigation_handler, F.data.startswith(NAV_PREFIX))
    dispatcher.callback_query.register(calendar_date_handler, F.data.startswith(CALENDAR_PREFIX))
    dispatcher.callback_query.register(ignore_callback, F.data == "ignore")
    dispatcher.message.register(quantity_handler, OrderStates.quantity)

    try:
        await dispatcher.start_polling(bot, repo=repo)
    finally:
        await repo.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
