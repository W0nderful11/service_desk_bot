# Service Desk Telegram Bot  

Этот бот помогает управлять заявками в Service Desk, хранить их в MongoDB и экспортировать в Excel.  

## Функционал  
- Отправить запрос — создание заявки.  
- Просмотр отчета — просмотр последних 10 заявок.  
- Экспортировать отчет — выгрузка данных в Excel.  
- Показатели КПД — анализ эффективности обработки заявок.  

## Установка  

1. Клонируйте репозиторий:  
   ```
   git clone https://github.com/your-repo/service-desk-bot.git
   cd service-desk-bot
   ```
2. Создайте виртуальное окружение:  
   ```
   python3 -m venv .venv
   ```
3. Активируйте виртуальное окружение:  
   - macOS/Linux:  
     ```
     source .venv/bin/activate
     ```
   - Windows:  
     ```
     .venv\Scripts\activate
     ```
4. Установите зависимости:  
   ```
   pip install -r requirements.txt
   ```

## Настройка переменных окружения  
Создайте файл `.env` и добавьте в него:  
```
TELEGRAM_BOT_TOKEN=your_bot_token
MONGO_URI=mongodb+srv://your_mongo_uri
```

## Запуск бота  
```
python test.py
```

## Требования  
- Python 3.10+  
- Aiogram 3.x  
- MongoDB Atlas  
- Pandas  
- OpenPyXL (для экспорта в Excel)  

## Используемый стек  
- Aiogram 3 — управление ботом.  
- MongoDB — база данных.  
- Pandas — обработка данных.  
- OpenPyXL — работа с Excel.  

## API команд  
| Команда | Описание |  
|---------|----------|  
| /start | Запуск бота и меню |  
| /help | Описание доступных команд |  
| 📩 Отправить запрос | Добавить новый запрос |  
| 📋 Просмотр отчета | Посмотреть последние 10 заявок |  
| 📈 Экспортировать отчет | Скачать заявки в Excel |  
| 📊 Показатели КПД | Анализ эффективности |  

## Структура проекта  
```
📁 service-desk-bot/  
│── 📄 test.py          # Основной код бота  
│── 📄 .env             # Файл с переменными окружения  
│── 📄 requirements.txt # Список зависимостей  
│── 📄 README.md        # Этот файл  
```

## Разработчик  
Автор: Atembek  Shaimerden  
github: w0nderful11 # service_desk_bot
