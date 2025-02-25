import logging
import asyncio
import os
import datetime
import pandas as pd
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import timezone
from aiogram.types import FSInputFile
import ollama
import json

# Загрузка FAQ (JSON файл) в память
def load_faq():
    with open("faq.json", "r", encoding="utf-8") as file:
        return json.load(file)

faq_data = load_faq()

# Функция для поиска ответа в JSON
def get_answer_from_faq(user_input):
    for item in faq_data:
        # Проверка на оба возможных ключа
        question = item.get("question") or item.get("input")

        if question and question.lower() in user_input.lower():
            return item.get("answer") or item.get("output")
    return None


# =======================
# Конфигурация
# =======================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")



if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не установлен в .env!")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI не установлен в .env!")

# =======================
# Логирование
# =======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =======================
# Проверка зависимости openpyxl
# =======================
try:
    import openpyxl
except ImportError:
    raise ImportError("❌ OpenPyXL не установлен! Установите: pip install openpyxl")

# =======================
# Инициализация бота и базы данных
# =======================
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher()
router = Router()

# Подключение к MongoDB
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["service_desk"]
    requests_collection = db["requests"]
    logger.info("✅ Подключение к MongoDB установлено")
except Exception as e:
    logger.error(f"❌ Ошибка подключения к MongoDB: {e}")
    exit(1)


# =======================
# Определение состояний FSM
# =======================
class RequestForm(StatesGroup):
    waiting_for_request = State()


# =======================
# Основное меню (клавиатура)
# =======================
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📩 Отправить запрос")],
        [KeyboardButton(text="📋 Просмотр отчета")],
        [KeyboardButton(text="📈 Экспортировать отчет")],
        [KeyboardButton(text="📊 Показатели КПД")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)


# =======================
# Хендлер команды /start
# =======================
@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    start_text = (
        "👋 *Добро пожаловать в Service Desk Bot!*\n\n"
        "💡 Этот бот поможет вам управлять заявками и получать отчеты.\n"
        "Выберите действие из меню ниже или используйте команду `/help`, чтобы узнать больше."
    )
    await message.answer(start_text, reply_markup=main_menu_kb, parse_mode="Markdown")


# =======================
# Хендлер команды /help
# =======================
@router.message(F.text == "/help")
async def cmd_help(message: types.Message):
    help_text = (
        "ℹ *Доступные команды и кнопки:*\n\n"
        "📩 *Отправить запрос* — создать новую заявку.\n"
        "📋 *Мои заявки* — посмотреть ваши заявки.\n"
        "📈 *Экспортировать отчет* — выгрузить отчет в Excel.\n"
        "📊 *Показатели КПД* — статистика обработки заявок.\n\n"
        "💡 Также доступны текстовые команды:\n"
        "🔹 `/my_requests` — список ваших заявок.\n"
        "🔹 `/update_status <id> <статус>` — обновить статус заявки.\n"
        "    *Доступные статусы:* `В обработке`, `Обработано`, `Завершено`. Пример: `/update_status 65fc3a1b2f9a3c7f0c1d4a12 Обработано`\n"
        "🔹 `/export` — скачать отчет.\n"
        "🔹 `/kpi` — посмотреть показатели КПД.\n"
        "🔹 `/cancel` — отменить ввод заявки.\n\n"
        "📌 *Вы можете использовать кнопки ниже для быстрого доступа к функциям!*"
    )
    await message.answer(help_text, parse_mode="Markdown")




# =======================
# Прием запроса пользователя
# =======================
@router.message(F.text == "📩 Отправить запрос")
async def send_request(message: types.Message, state: FSMContext):
    await state.set_state(RequestForm.waiting_for_request)
    await message.answer("✏ Пожалуйста, введите текст запроса:")

@router.message(F.text == "/my_requests")
async def my_requests(message: types.Message):
    # Указываем, какие поля мы хотим получить (например, все поля)
    user_requests = list(
        requests_collection.find(
            {},  # Фильтр по user_id
            {"_id": 1, "text": 1, "status": 1, "created_at": 1}  # Проекция (какие поля вернуть)
        )
    )

    if not user_requests:
        await message.answer("📭 У вас пока нет созданных заявок.")
        return

    request_lines = [
        f"🔹 ID: `{str(req['_id'])}`\nТекст: {req['text']}\nСтатус: *{req['status']}*\nДата: {req['created_at'].strftime('%Y-%m-%d %H:%M')}"
        for req in user_requests
    ]

    await message.answer("\n\n".join(request_lines), parse_mode="Markdown")


@router.message(F.text == "/cancel")
async def cancel_request(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Ввод заявки отменен.", reply_markup=main_menu_kb)


from bson import ObjectId


@router.message(F.text.startswith("/update_status"))
async def update_status(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❌ Формат команды: `/update_status <id> <статус>`", parse_mode="Markdown")
            return

        request_id, new_status = parts[1], " ".join(parts[2:])

        # Проверяем, является ли request_id валидным ObjectId
        try:
            request_id = ObjectId(request_id)
        except Exception:
            await message.answer("❌ Некорректный ID заявки.")
            return

        result = requests_collection.update_one({"_id": request_id}, {"$set": {"status": new_status}})

        if result.matched_count == 0:
            await message.answer("❌ Запрос с таким ID не найден.")
        else:
            status_message = f"✅ Статус заявки `{request_id}` обновлен на: *{new_status}*"

            # Если заявка завершена, добавить упоминание
            if new_status.lower() in ["обработано", "завершено", "закрыто"]:
                status_message += "\n✅ Эта заявка теперь считается обработанной."

            await message.answer(status_message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении статуса: {e}")
        await message.answer("❌ Произошла ошибка при обновлении статуса.")


@router.message(RequestForm.waiting_for_request, F.text)
async def process_request(message: types.Message, state: FSMContext):
    request_text = message.text
    request_data = {
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Аноним",
        "text": request_text,
        "status": "В обработке",
        "created_at": datetime.datetime.now(timezone.utc)
    }
    result = requests_collection.insert_one(request_data)
    logger.info(f"✅ Запрос зарегистрирован с id: {result.inserted_id}")
    await message.answer("✅ Ваш запрос успешно зарегистрирован! Спасибо.")
    await state.clear()


# =======================
# Просмотр отчета (сводка по запросам)
# =======================
@router.message(F.text == "📋 Просмотр отчета")
async def view_report(message: types.Message):
    requests = list(
        requests_collection.find({}, {"_id": 0, "username": 1, "text": 1, "status": 1, "created_at": 1}).sort(
            "created_at", -1))
    if not requests:
        await message.answer("📭 На данный момент запросов нет.")
        return

    report_lines = []
    for req in requests[-100:]:
        created_str = req["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(req["created_at"],
                                                                                 datetime.datetime) else str(
            req["created_at"])
        report_lines.append(f"🔹 {req['username']}: {req['text']}\nСтатус: {req['status']}, {created_str}")

    report_text = "\n\n".join(report_lines)
    await message.answer(report_text)



# =======================
# Экспорт отчета в Excel
# =======================



@router.message(F.text == "📈 Экспортировать отчет")
async def export_report(message: types.Message):
    requests = list(requests_collection.find({}, {"_id": 0, "username": 1, "text": 1, "status": 1, "created_at": 1}))
    if not requests:
        await message.answer("❌ Нет данных для экспорта.")
        return

    df = pd.DataFrame(requests)
    df["created_at"] = df["created_at"].apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if isinstance(x, datetime.datetime) else str(x))

    file_name = "service_desk_report.xlsx"
    try:
        df.to_excel(file_name, index=False)
        excel_file = FSInputFile(file_name)
        await message.answer_document(excel_file, caption="📂 Ваш отчет в формате Excel.")
    except Exception as e:
        logger.error(f"❌ Ошибка при экспорте: {e}")
        await message.answer("❌ Произошла ошибка при экспорте отчета.")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)  # Удаляем файл даже если произошла ошибка

@router.message(F.text == "❓ Помощь")
async def help_command(message: types.Message):
    # Вызываем команду /help
    await message.bot.send_message(message.chat.id, "/help", reply_markup=main_menu_kb)

# =======================
# Расчет КПД (административные показатели)
# =======================
@router.message(F.text == "📊 Показатели КПД")
async def kpi_report(message: types.Message):
    total_requests = requests_collection.count_documents({})
    processed_requests = requests_collection.count_documents({"status": {"$in": ["Обработано", "Готово", "Закрыто"]}})
    kpi_percentage = (processed_requests / total_requests * 100) if total_requests > 0 else 0
    await message.answer(f"📊 КПД: {kpi_percentage:.2f}%", parse_mode="Markdown")




# =======================
# Фолбэк-хендлер
# =======================




@router.message()
async def ollama_fallback_handler(message: types.Message):
    user_input = message.text

    # Сначала ищем ответ в FAQ
    faq_answer = get_answer_from_faq(user_input)

    if faq_answer:
        # Если нашли ответ в FAQ
        await message.answer(f"🤖 {faq_answer}")
    else:
        # Если не нашли, обращаемся к Ollama
        try:
            # Отправляем запрос в Ollama
            response = ollama.generate(
                model="llama3.2",
                prompt=user_input,
                system="Ты — русскоязычный бот Service Desk. Ты должен отвечать только на русском языке. "
                   "Ты должен помогать пользователям разобраться с командами и функционалом бота. "
                   "Если пользователь не понимает, как создать заявку, объясни, что нужно нажать кнопку 📩 'Отправить запрос' в меню или "
                   "ввести текст заявки вручную после команды. "
                   "Если пользователь спрашивает, как посмотреть заявки, предложи нажать кнопку 📋 'Мои заявки' или использовать команду `/my_requests`. "
                   "Для обновления статуса заявки используется команда `/update_status <id> <статус>`, "
                   "а для выгрузки отчета в Excel — кнопка 📈 'Экспортировать отчет' или команда `/export`. "
                   "Также можно посмотреть статистику с помощью 📊 'Показатели КПД' или команды `/kpi`. "
                   "Если пользователь отправил текст, который не является командой, попробуй ответить на его вопрос. "
                   "При необходимости помогай с работой с ботом и MongoDB."
            )

            # Получаем ответ от модели
            ollama_answer = response['response']
            await message.answer(f"🤖 {ollama_answer}")

        except Exception as e:
            logger.error(f"❌ Ошибка при запросе к Ollama: {e}")
            await message.answer("❌ Ошибка при обработке запроса. Попробуйте позже.")

# =======================
# Запуск бота
# =======================
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())