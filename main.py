import logging
import os
import pandas as pd
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
log_directory = "logs"
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, "bot.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# Константы
API_TOKEN = "7925472616:AAG7YFA54h8llVbOjJuBrVvH1igpfhKxhD4"
ADMIN_ID = 12121212
DATA_FILE = "Pantone.xlsx"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Загрузка данных из Excel
def load_data():
    if not os.path.exists(DATA_FILE):
        logger.warning(f"Файл {DATA_FILE} не найден. Создана пустая база данных.")
        return pd.DataFrame(columns=["Номер", "Вес", "Вертикаль", "Горизонталь"])

    try:
        return pd.read_excel(DATA_FILE)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {DATA_FILE}: {e}")
        return pd.DataFrame(columns=["Номер", "Вес", "Вертикаль", "Горизонталь"])

df = load_data()

# Состояния
class PaintSearch(StatesGroup):
    waiting_for_paint_name = State()
    waiting_for_weight_update = State()

# Клавиатуры
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Добавить строку"), KeyboardButton(text="Редактировать строку")]],
    resize_keyboard=True,
)

setting_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Найти расположение краски"), KeyboardButton(text="Назад")]],
    resize_keyboard=True,
)

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Склад номер 1"), KeyboardButton(text="Склад номер 2")]],
    resize_keyboard=True,
)

# Обработчики команд
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Добро пожаловать в панель администратора!\nВы можете редактировать базу данных.", reply_markup=admin_keyboard)
        logger.info(f"Администратор {message.from_user.id} вошёл в панель.")
    else:
        await message.reply("Выберите нужный вам склад.", reply_markup=user_keyboard)
        logger.info(f"Пользователь {message.from_user.id} начал работу.")

@dp.message(lambda message: message.text in ["Склад номер 1", "Склад номер 2", "Назад"])
async def choose_warehouse(message: types.Message):
    if message.text == "Склад номер 1":
        await message.reply("Вы выбрали Склад номер 1. Что хотите сделать?", reply_markup=setting_keyboard)
    elif message.text == "Склад номер 2":
        await message.reply("Вы выбрали Склад номер 2. Что хотите сделать?", reply_markup=setting_keyboard)
    elif message.text == "Назад":
        await message.reply("Вы вернулись к выбору склада.", reply_markup=user_keyboard)
    logger.info(f"Пользователь {message.from_user.id} выбрал опцию: {message.text}")

@dp.message(lambda msg: msg.text == "Найти расположение краски")
async def search_paint_initiate(message: types.Message, state: FSMContext):
    await message.reply("Введите номер краски:")
    await state.set_state(PaintSearch.waiting_for_paint_name)
    logger.info(f"Пользователь {message.from_user.id} начал поиск краски.")
@dp.message(StateFilter(PaintSearch.waiting_for_paint_name))
async def search_paint(message: types.Message, state: FSMContext):
    paint_number = message.text.strip()  # Получаем номер краски

    # Проверяем, есть ли краска с таким номером в базе данных
    paint_row = df[df["Номер"] == paint_number]

    if paint_row.empty:
        # Если краска не найдена
        await message.reply(f"Краска с номером {paint_number} не найдена. Попробуйте снова или нажмите 'Назад'.")
        await state.set_state(PaintSearch.waiting_for_paint_name)  # Ожидаем повторный ввод
    else:
        # Если краска найдена
        paint_info = paint_row.iloc[0]
        paint_name = paint_info["Номер"]
        paint_weight = paint_info["Вес"]
        paint_vertical = paint_info["Вертикаль"]
        paint_horizontal = paint_info["Горизонталь"]

        # Отправляем информацию о краске и кнопки для действий
        await message.reply(
            f"Информация о краске №{paint_name}:\n"
            f"Вес: {paint_weight} кг\n"
            f"Вертикаль: {paint_vertical}\n"
            f"Горизонталь: {paint_horizontal}\n\n"
            "Что хотите сделать?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Взять", callback_data=f"take_{paint_name}")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_search")]
                ]
            )
        )
        logger.info(f"Пользователь {message.from_user.id} нашел краску №{paint_name}.")

        # Обновляем состояние с номером найденной краски
        await state.update_data(selected_paint=paint_name)
        await state.set_state(PaintSearch.waiting_for_weight_update)


@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def take_paint(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        row_index = int(callback_query.data.split("_")[1])
        row = df.iloc[row_index]

        # Сохраняем выбранный номер краски в состоянии
        selected_paint = await state.get_data()
        if 'selected_paints' not in selected_paint:
            selected_paint['selected_paints'] = []
        selected_paint['selected_paints'].append(row['Номер'])
        await state.update_data(selected_paints=selected_paint['selected_paints'])

        # Отправляем сообщение с вопросом: "Нужна ли еще краска?"
        question_text = f"Вы выбрали краску №{row['Номер']}.\nНужна ли еще краска?"
        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="more_paint_yes"),
                 InlineKeyboardButton(text="Нет", callback_data="more_paint_no"),
                 InlineKeyboardButton(text="Вернуть краску", callback_data="return_paint")]
            ]
        )

        await callback_query.message.answer(question_text, reply_markup=inline_kb)
        logger.info(f"Пользователь {callback_query.from_user.id} выбрал краску №{row['Номер']}")
    except Exception as e:
        await callback_query.message.reply(f"Ошибка при обработке запроса: {e}")
        logger.error(f"Ошибка при обработке запроса: {e}")

@dp.callback_query(lambda c: c.data == "more_paint_yes")
async def more_paint_yes(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.reply("Введите номер краски:")
    await state.set_state(PaintSearch.waiting_for_paint_name)
    logger.info(f"Пользователь {callback_query.from_user.id} хочет выбрать еще краску.")

@dp.callback_query(lambda c: c.data == "more_paint_no")
async def more_paint_no(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    selected_paints = user_data.get('selected_paints', [])

    if selected_paints:
        await callback_query.message.answer("Вы выбрали краски. Теперь их можно вернуть. Нажмите 'Вернуть краску'.")
        await return_paint(callback_query, state)
    else:
        await callback_query.message.answer("Вы не выбрали краски.")
        await state.finish()

@dp.callback_query(lambda c: c.data == "return_paint")
async def return_paint(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    selected_paints = user_data.get('selected_paints', [])

    if not selected_paints:
        await callback_query.message.answer("Вы еще не выбрали краски для возврата.")
        return

    buttons = [[InlineKeyboardButton(text=paint, callback_data=f"return_{paint}") for paint in selected_paints]]
    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback_query.message.answer("Выберите краску для возврата:", reply_markup=inline_kb)
    logger.info(f"Пользователь {callback_query.from_user.id} открыл меню возврата краски.")

@dp.callback_query(lambda c: c.data.startswith("return_"))
async def return_selected_paint(callback_query: types.CallbackQuery, state: FSMContext):
    paint_number = callback_query.data.split("_")[1]

    # Обновление состояния для выбранной краски
    await state.update_data(returning_paint=paint_number)
    await callback_query.message.answer(f"Введите оставшийся вес краски №{paint_number} (если 0, то краска будет удалена):")
    await state.set_state(PaintSearch.waiting_for_weight_update)

    logger.info(f"Пользователь {callback_query.from_user.id} выбрал краску для возврата: {paint_number}")


@dp.message(StateFilter(PaintSearch.waiting_for_weight_update))
async def handle_return_weight(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    paint_number = user_data.get("returning_paint")

    if not paint_number:
        await message.reply("Ошибка: не выбран номер краски.")
        return

    try:
        remaining_weight = float(message.text)
        paint_row = df[df["Номер"] == paint_number]

        if paint_row.empty:
            await message.reply("Краска не найдена в базе данных.")
            return

        if remaining_weight == 0:
            df.drop(paint_row.index, inplace=True)
            await message.reply(f"Краска №{paint_number} удалена из базы данных.")
        else:
            df.loc[df["Номер"] == paint_number, "Вес"] = remaining_weight
            await message.reply(f"Оставшийся вес краски №{paint_number} обновлен.")

        df.to_excel(DATA_FILE, index=False)
        await state.finish()

    except ValueError:
        await message.reply("Ошибка: введите корректное число для веса.")
        logger.error(f"Ошибка при вводе веса: {message.text}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
