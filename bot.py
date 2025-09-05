import os
import random
import logging
import sqlite3
import datetime
from datetime import timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен из файла
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# НАСТРОЙКИ БОТА
BOT_CONFIG = {
    'users_to_select': 3,      # Сколько человек выбирать (1, 2, 3...)
    'joke_before_tag': True,   # True = шутка потом пользователь, False = пользователь потом шутка
    'show_stats': True         # Показывать статистику при выборе
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Список перед именем
GAY_JOKES = [
    "Почему геи не боятся привидений? Потому что они уже видели выходцы из шкафов!",
]

# Фразы на триггер "пиздец"
PIZDEC_PHRASES = [
    "Да уж, это действительно пиздец...",
    "Пиздец? Это только начало!",
]

# Предсказания Таро для тестировщиков
TARO = [
    "✨ Карта Солнце: Сегодня все баги сами пофиксятся",
    "🌙 Карта Луна: Автотесты пройдут",
    "⭐ Карта Звезда: Найдешь баг, который все искали годами",
    "💖 Карта Влюбленные: Все ошибки поправятся с первого раза",
    "🏆 Карта Сила: Облако не ебланит",
    "🎉 Карта Колесо Фортуны: День без значительных ошибок",
    "🌅 Карта Мир: Все тесты упали по ошибкам в самих тестах",
    "💰 Карта Император: Релиз будет вовремя",
    "🔧 Карта Маг: Все магически само заработает",
    "📊 Карта Правосудие: Ничего не будет ВОСить неделю",
    "☠️ Карта Смерть: Ошибка с боя",
    "🔥 Карта Башня: Весь день будут значительные ошибки ",
    "👻 Карта Отшельник: Застрянешь на одном баге на 8 часов",
    "💀 Карта Дьявол: Все будет разъебано по проекту",
    "🌪️ Карта Суд: С логами не повторишь Ашибку",
    "⛈️ Карта Повешенный: будешь искать макет пол дня",
    "🕷️ Карта Императрица: 'срочная' фича!",
]

# Мемы на "Ошибка" для IT
ERROR_MEMES = [
    "У меня не повторяется",
    "Это не ошибка, это undocumented feature!",
    "Ошибка - это когда expected != actual, а в жизни expected != expected",
    "Мой код работает? Не знаю, я его не тестировал 🤷‍♂️",
    "Всё работает! (на моей машине работает)",
    "Это не баг, это фича!",
]

# База данных
def init_db():
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        count_day INTEGER DEFAULT 0,
        count_week INTEGER DEFAULT 0,
        count_total INTEGER DEFAULT 0,
        last_selected_date TEXT
    )
    ''')
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, first_name, last_name):
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    
    cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute('''
            UPDATE user_stats 
            SET count_total = count_total + 1,
                username = ?, first_name = ?, last_name = ?,
                last_selected_date = ?
            WHERE user_id = ?
        ''', (username, first_name, last_name, today, user_id))
    else:
        cursor.execute('''
            INSERT INTO user_stats (user_id, username, first_name, last_name, count_total, last_selected_date)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (user_id, username, first_name, last_name, today))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT count_total FROM user_stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Команда /rainbow
async def rainbow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        members = await context.bot.get_chat_administrators(chat_id)
        human_members = [m for m in members if not m.user.is_bot]
        
        if not human_members:
            await update.message.reply_text("Не могу найти участников для выбора!")
            return
        
        # Выбираем несколько пользователей согласно настройкам
        selected_members = random.sample(human_members, min(BOT_CONFIG['users_to_select'], len(human_members)))
        
        response = ""
        
        # Сначала шутка, потом пользователи
        if BOT_CONFIG['joke_before_tag']:
            joke = random.choice(GAY_JOKES)
            response += f"{joke}\n\n"
            
            for member in selected_members:
                user = member.user
                update_user_stats(user.id, user.username, user.first_name, user.last_name)
                user_name = f"{user.first_name}"
                if user.last_name:
                    user_name += f" {user.last_name}"
                if user.username:
                    user_name += f" (@{user.username})"
                response += f"🎲 {user_name}\n"
        
        # Сначала пользователи, потом шутка
        else:
            for member in selected_members:
                user = member.user
                update_user_stats(user.id, user.username, user.first_name, user.last_name)
                user_name = f"{user.first_name}"
                if user.last_name:
                    user_name += f" {user.last_name}"
                if user.username:
                    user_name += f" (@{user.username})"
                response += f"🎲 {user_name}\n"
            
            joke = random.choice(GAY_JOKES)
            response += f"\n{joke}"
        
        # Добавляем статистику если включено
        if BOT_CONFIG['show_stats']:
            for member in selected_members:
                user = member.user
                stats = get_user_stats(user.id)
                response += f"\n📊 {user.first_name} выбирали: {stats} раз(а)"
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error in rainbow_command: {e}")
        await update.message.reply_text("Произошла ошибка при выполнении команды!")

# Команда /stats
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        total = get_user_stats(user_id)
        
        response = f"📊 Ваша статистика:\nЗа все время: {total} раз(а)"
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики!")

# Команда /taro
async def taro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prediction = random.choice(TARO)
    await update.message.reply_text(f"🔮 Ваше предсказание на сегодня:\n{prediction}")

# Триггер "пиздец"
async def pizdec_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phrase = random.choice(PIZDEC_PHRASES)
    await update.message.reply_text(phrase)

# Триггер "Ошибка"
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meme = random.choice(ERROR_MEMES)
    await update.message.reply_text(meme)

# Триггер "Катя/Екатерина + пока"
async def katya_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.first_name and ('катя' in user.first_name.lower() or 'екатерина' in user.first_name.lower()):
        if 'пока' in update.message.text.lower():
            await update.message.reply_text("Пока Кать! 👋")

# Главная функция
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("rainbow", rainbow_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("taro", taro_command))
    
    # Триггеры
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)пиздец"), pizdec_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)ошибка"), error_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)пока"), katya_handler))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    application.run_polling()

if __name__ == "__main__":
    main()