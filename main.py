from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import pandas as pd
import asyncio

# Константы
API_TOKEN = "7925472616:AAG7YFA54h8llVbOjJuBrVvH1igpfhKxhD4"
ADMIN_ID = 23334334323  # Замените на ID администратора
DATA_FILE = "Pantone.xlsx"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Загрузка данных из Excel
try:
    df = pd.read_excel(DATA_FILE)
except FileNotFoundError:
    df = pd.DataFrame(columns=["Название", "Вес", "Вертикаль", "Горизонталь"])
except Exception as e:
    df = pd.DataFrame(columns=["Название", "Вес", "Вертикаль", "Горизонталь"])
    print(f"Ошибка при чтении файла: {e}")

# Состояния
class AddRow(StatesGroup):
    waiting_for_row_data = State()

class EditRow(StatesGroup):
    waiting_for_row_index = State()
    waiting_for_new_data = State()

class PaintSearch(StatesGroup):
    waiting_for_paint_name = State()
    waiting_for_weight_update = State()

# Клавиатуры
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить строку"), KeyboardButton(text="Редактировать строку")],
    ],
    resize_keyboard=True,
)

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Склад номер 1"), KeyboardButton(text="Склад номер 2")],
    ],
    resize_keyboard=True,
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Назад")]],
    resize_keyboard=True,
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Склад номер 1"), KeyboardButton(text="Склад номер 2")]],
    resize_keyboard=True,
)

# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        # Отправляем админ-клавиатуру и сообщение
        await message.reply(
            "Добро пожаловать в панель администратора!\n"
            "Она позволяет редактировать базу данных с рабочим инвентарем.",
            reply_markup=admin_keyboard,
        )
    else:
        await message.reply(
            "Выберите нужный вам склад",
            reply_markup=user_keyboard,
        )

# Обработчик выбора склада
@dp.message(lambda message: message.text == "Склад номер 1" or message.text == "Склад номер 2")
async def choose_warehouse(message: types.Message):
    if message.text == "Склад номер 1":
        await message.reply("Вы выбрали Склад номер 1. Что хотите сделать?", reply_markup=admin_keyboard)
    elif message.text == "Склад номер 2":
        await message.reply("Вы выбрали Склад номер 2. Что хотите сделать?", reply_markup=admin_keyboard)

# Обработчик поиска краски
@dp.message(StateFilter(PaintSearch.waiting_for_paint_name))
async def search_paint(message: types.Message, state: FSMContext):
    global df
    paint_name = message.text

    if paint_name == "Назад":
        await state.clear()
        await message.reply("Выберите склад:", reply_markup=main_keyboard)
        return

    matching_rows = df[df["Название"].str.contains(paint_name, case=False, na=False)]

    if matching_rows.empty:
        await message.reply("Краска не найдена. Попробуйте снова.")
    else:
        buttons = []
        for index, row in matching_rows.iterrows():
            button_text = f"{row['Название']} - {row['Вес']} кг (В: {row['Вертикаль']}, Г: {row['Горизонталь']})"
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"edit_{index}")])

        inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Найдены следующие краски:", reply_markup=inline_kb)

# Обработчик нажатия на кнопку для редактирования
@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_paint(callback_query: types.CallbackQuery, state: FSMContext):
    global df
    row_index = int(callback_query.data.split("_")[1])
    row = df.iloc[row_index]

    await state.update_data(row_index=row_index)
    await callback_query.message.reply(
        f"Редактирование:\nНазвание: {row['Название']}\nВес: {row['Вес']} кг\nВертикаль: {row['Вертикаль']}\nГоризонталь: {row['Горизонталь']}\nВведите новый вес (или 0 для удаления):",
        reply_markup=back_keyboard
    )
    await state.set_state(PaintSearch.waiting_for_weight_update)

# Обработчик изменения веса
@dp.message(StateFilter(PaintSearch.waiting_for_weight_update))
async def update_weight(message: types.Message, state: FSMContext):
    global df

    if message.text == "Назад":
        await state.clear()
        await message.reply("Выберите склад:", reply_markup=main_keyboard)
        return

    try:
        new_weight = float(message.text)
        user_data = await state.get_data()
        row_index = user_data["row_index"]

        if new_weight == 0:
            df = df.drop(index=row_index).reset_index(drop=True)
            df.to_excel(DATA_FILE, index=False)
            await state.clear()
            await message.reply("Краска удалена.", reply_markup=main_keyboard)
        else:
            df.at[row_index, "Вес"] = new_weight
            df.to_excel(DATA_FILE, index=False)
            await state.clear()
            await message.reply("Вес обновлен.", reply_markup=main_keyboard)
    except ValueError:
        await message.reply("Ошибка: введите корректное число.")

# Добавление строки
@dp.message(lambda msg: msg.text == "Добавить строку")
async def add_row(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Введите данные для строки (Название, вес, расположение по вертикали, горизонтали) через запятую:")
        await state.set_state(AddRow.waiting_for_row_data)
    else:
        await message.reply("У вас нет доступа к этой функции.")

@dp.message(StateFilter(AddRow.waiting_for_row_data))
async def process_row_data(message: types.Message, state: FSMContext):
    try:
        data = message.text.split(",")
        if len(data) != 4:
            await message.reply("Ошибка: необходимо ввести 4 значения через запятую.")
            return

        global df
        df.loc[len(df)] = data
        df.to_excel(DATA_FILE, index=False)
        await state.clear()
        await message.reply("Строка добавлена!", reply_markup=admin_keyboard)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

# Редактирование строки
@dp.message(lambda msg: msg.text == "Редактировать строку")
async def edit_row(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        rows = df.to_string(index=True)
        await message.reply(f"Выберите строку для редактирования (введите номер строки):\n{rows}")
        await state.set_state(EditRow.waiting_for_row_index)
    else:
        await message.reply("У вас нет доступа к этой функции.")

@dp.message(StateFilter(EditRow.waiting_for_row_index))
async def process_row_index(message: types.Message, state: FSMContext):
    try:
        row_index = int(message.text)
        if row_index < 0 or row_index >= len(df):
            await message.reply("Ошибка: номер строки вне диапазона.")
            return

        await state.update_data(row_index=row_index)
        await message.reply("Введите новые данные для строки (через запятую):")
        await state.set_state(EditRow.waiting_for_new_data)
    except ValueError:
        await message.reply("Ошибка: необходимо ввести корректный номер строки.")

@dp.message(StateFilter(EditRow.waiting_for_new_data))
async def process_new_data(message: types.Message, state: FSMContext):
    try:
        data = message.text.split(",")
        if len(data) != 4:
            await message.reply("Ошибка: необходимо ввести 4 значения через запятую.")
            return

        user_data = await state.get_data()
        row_index = user_data["row_index"]

        global df
        df.iloc[row_index] = data
        df.to_excel(DATA_FILE, index=False)
        await state.clear()
        await message.reply("Строка обновлена!", reply_markup=admin_keyboard)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

# Основной цикл бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
