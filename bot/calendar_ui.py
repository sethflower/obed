from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALENDAR_PREFIX = "cal"
NAV_PREFIX = "cal_nav"

WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


@dataclass(frozen=True)
class CalendarRange:
    min_date: dt.date
    max_date: dt.date


def _month_label(year: int, month: int) -> str:
    month_name = dt.date(year, month, 1).strftime("%B")
    return f"{month_name.capitalize()} {year}"


def build_calendar(year: int, month: int, date_range: CalendarRange) -> InlineKeyboardMarkup:
    cal = calendar.Calendar(firstweekday=0)
    keyboard: list[list[InlineKeyboardButton]] = []

    keyboard.append([InlineKeyboardButton(text=_month_label(year, month), callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(text=label, callback_data="ignore") for label in WEEKDAY_LABELS])

    for week in cal.monthdayscalendar(year, month):
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue
            day_date = dt.date(year, month, day)
            if day_date < date_range.min_date or day_date > date_range.max_date:
                row.append(InlineKeyboardButton(text=str(day), callback_data="ignore"))
            else:
                row.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"{CALENDAR_PREFIX}:{day_date.isoformat()}",
                    )
                )
        keyboard.append(row)

    nav_row: list[InlineKeyboardButton] = []
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)

    if dt.date(prev_year, prev_month, 1) >= date_range.min_date.replace(day=1):
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"{NAV_PREFIX}:{prev_year}-{prev_month:02d}",
            )
        )

    if dt.date(next_year, next_month, 1) <= date_range.max_date.replace(day=1):
        nav_row.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"{NAV_PREFIX}:{next_year}-{next_month:02d}",
            )
        )

    if nav_row:
        keyboard.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    new_month = month + delta
    new_year = year + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    return new_year, new_month
