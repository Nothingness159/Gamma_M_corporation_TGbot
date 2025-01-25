from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import pandas as pd
import asyncio

# Константы
API_TOKEN = "7925472616:AAG7YFA54h8llVbOjJuBrVvH1igpfhKxhD4"
ADMIN_ID = 857663686  # Замените на ID администратора
DATA_FILE = "Pantone.xlsx"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура для админ-панели
keyboard = [
    [
        KeyboardButton(text="Добавить строку"),
        KeyboardButton(text="Редактировать строку")
    ]
]
admin_keyboard = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Загрузка данных из Excel
try:
    df = pd.read_excel(DATA_FILE)
except FileNotFoundError:
    df = pd.DataFrame(columns=["Column1", "Column2", "Column3", "Column4"])


# Состояния
class AddRow(StatesGroup):
    waiting_for_row_data = State()


class EditRow(StatesGroup):
    waiting_for_row_index = State()
    waiting_for_new_data = State()


# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Добро пожаловать в панель администратора!\nОна позволяет редактировать базу данных с рабочим инвентарем.", reply_markup=admin_keyboard)
    else:
        await message.reply("У вас нет доступа к этой панели.")


# Добавление строки
@dp.message(lambda msg: msg.text == "Добавить строку")
async def add_row(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Введите данные для строки(Название, вес, расположение по вертикали, горизонтали)через запятую:")
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
