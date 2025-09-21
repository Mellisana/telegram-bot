import os
import random
import logging
import sqlite3
import datetime
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен из файла
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Гейские подколы для пидора дня
GAY_JOKES = [
    "Как пидоры называют свой выходной? - День открытых дверей!",
    "Почему пидоры хорошие программисты? Потому что они любят обрабатывать исключения!",
    "Что общего между пидором и пиццей? Оба любят, когда их укладывают на стол!",
    "Почему пидоры любят базы данных? - Там можно найти много интересных связей!",
    "Как пидор решает проблемы? - Подходит с задней стороны!",
]

# Грубые ответы для триггеров
RUDE_RESPONSES = [
    "Пиздец конечно, но мне похуй!",
    "Ну вот опять этот пиздец начался...",
    "Иди нахуй, я занят более важной хуйней!",
    "Пиздец как всё заебало!",
    "Опять этот хуевый пиздец..."
]

# Ответы на IT-триггеры (по 15+ для каждого)
IT_RESPONSES = {
    'офис': [
    
    ],
    'ошибка': [
        "Ошибка? Это не баг, это фича! 🐛🏳️‍🌈",
        "Deadlock - два пидора не могут решить кто сверху! ⚖️",
        "Buffer overflow - пидор не знает меры! 🎪",
        "Fatal error - пидор довел систему до оргазма! 💀"
    ],
    'айос': [
        "iOS - операционка для пидоров которые любят когда за них все решают! 📱✨",
    ],
    'андроид': [
        "Android - для пидоров которые любят настраивать все под себя! 🤖🔧",
        "Android разработчики - пидоры в свободных отношениях с кодом! 💻",
    ]
}

# ТИТУЛЫ ДЛЯ ЕЖЕДНЕВНОГО ВЫБОРА
TITLES = {
    'pidor': {
        'title': '🏆 Пидор Дня',
        'description': 'Самый везучий неудачник чата!',
        'emoji': '🏆'
    },
    'favorite': {
        'title': '💖 Любимчик Дня', 
        'description': 'Чьи сообщения собрали больше всего реакций!',
        'emoji': '💖'
    },
}

# База данных
def init_db():
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Таблица для ежедневных результатов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_results (
        date TEXT PRIMARY KEY,
        results TEXT,
        last_updated TEXT
    )
    ''')
    
    # Таблица для статистики пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        title_type TEXT,
        count INTEGER DEFAULT 0,
        last_awarded TEXT,
        PRIMARY KEY (user_id, title_type)
    )
    ''')
    
    # Таблица для отслеживания реакций
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_reactions (
        message_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        reactions_count INTEGER DEFAULT 0,
        date TEXT
    )
    ''')
    
    # Таблица для отслеживания предсказаний тестировщика
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tester_predictions (
        user_id INTEGER PRIMARY KEY,
        last_prediction_date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_today_results():
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT results FROM daily_results WHERE date = ?', (today,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def save_today_results(results):
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_results (date, results, last_updated)
        VALUES (?, ?, ?)
    ''', (today, results, now))
    
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, first_name, last_name, title_type):
    today = datetime.now().date().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, first_name, last_name, title_type, count, last_awarded)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT count FROM user_stats WHERE user_id = ? AND title_type = ?), 0) + 1, ?)
    ''', (user_id, username, first_name, last_name, title_type, user_id, title_type, today))
    
    conn.commit()
    conn.close()

def get_user_stats_period(title_type, period_days):
    """Получает статистику за определенный период"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=period_days)).date().isoformat()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ? AND last_awarded >= ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type, start_date))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_all_time_stats(title_type):
    """Получает статистику за все время"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type,))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_random_users(chat_members, count=1):
    """Выбирает случайных пользователей из списка"""
    human_members = [m for m in chat_members if not m.user.is_bot]
    return random.sample(human_members, min(count, len(human_members)))

def get_top_user_by_reactions():
    """Получает пользователя с наибольшим количеством реакций"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Получаем пользователя с максимальным количеством реакций за сегодня
    today = datetime.now().date().isoformat()
    cursor.execute('''
        SELECT user_id, username, first_name, last_name, SUM(reactions_count) as total_reactions
        FROM message_reactions 
        WHERE date = ?
        GROUP BY user_id 
        ORDER BY total_reactions DESC 
        LIMIT 1
    ''', (today,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def can_user_get_prediction(user_id):
    """Проверяет, может ли пользователь получить предсказание сегодня"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT last_prediction_date FROM tester_predictions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] == today:
        conn.close()
        return False
    
    cursor.execute('''
        INSERT OR REPLACE INTO tester_predictions (user_id, last_prediction_date)
        VALUES (?, ?)
    ''', (user_id, today))
    
    conn.commit()
    conn.close()
    return True

async def save_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет информацию о сообщении и его реакциях"""
    try:
        message = update.message
        user = message.from_user
        
        # Подсчитываем общее количество реакций
        reaction_count = 0
        if message.reactions:
            for reaction in message.reactions:
                reaction_count += reaction.count
        
        conn = sqlite3.connect('daily_titles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO message_reactions 
            (message_id, user_id, username, first_name, last_name, reactions_count, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            reaction_count,
            datetime.now().date().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error saving message reaction: {e}")

async def get_chat_members(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Получает всех участников чата (не только админов)"""
    try:
        # Получаем список всех участников чата
        members = []
        async for member in context.bot.get_chat_members(chat_id):
            members.append(member)
        return members
    except Exception as e:
        logger.error(f"Error getting chat members: {e}")
        # Если не получается получить всех участников, возвращаем админов как fallback
        return await context.bot.get_chat_administrators(chat_id)

async def assign_pidor_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Пидора Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Пидор Дня' in today_results:
            await update.message.reply_text("📅 Пидор дня уже был выбран сегодня!")
            return
        
        # Получаем всех участников чата
        members = await get_chat_members(chat_id, context)
        
        # 1. Отправляем гей-шутку
        gay_joke = random.choice(GAY_JOKES)
        await update.message.reply_text(gay_joke)
        
        # 2. Отправляем картинку барабана (эмодзи)
        await update.message.reply_text("🥁 *Барабанная дробь...* 🥁", parse_mode='Markdown')
        
        # 3. Выбираем пидора дня
        pidor_users = get_random_users(members, 1)
        pidor_user = pidor_users[0].user
        
        # Обновляем статистику для пидора дня
        update_user_stats(
            pidor_user.id, 
            pidor_user.username, 
            pidor_user.first_name, 
            pidor_user.last_name, 
            'pidor'
        )
        
        # Формируем результат
        pidor_name = f"{pidor_user.first_name or ''}"
        if pidor_user.last_name:
            pidor_name += f" {pidor_user.last_name}"
        if pidor_user.username:
            pidor_name += f" (@{pidor_user.username})"
        
        # Формируем ответ
        response = f"🏆 *{TITLES['pidor']['title']}* 🏆\n"
        response += f"{TITLES['pidor']['description']}\n"
        response += f"🥇 {pidor_name}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_pidor_day: {e}")
        await update.message.reply_text("Произошла ошибка при выборе пидора дня!")

async def assign_favorite_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Любимчика Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Любимчик Дня' in today_results:
            await update.message.reply_text("📅 Любимчик дня уже был выбран сегодня!")
            return
        
        # Получаем всех участников чата
        members = await get_chat_members(chat_id, context)
        
        # Выбираем любимчика дня (по реакциям)
        favorite_user_data = get_top_user_by_reactions()
        
        # Если нет данных о реакциях, выбираем случайного
        if not favorite_user_data:
            favorite_users = get_random_users(members, 1)
            favorite_user = favorite_users[0].user
            favorite_name = f"{favorite_user.first_name or ''}"
            if favorite_user.last_name:
                favorite_name += f" {favorite_user.last_name}"
            if favorite_user.username:
                favorite_name += f" (@{favorite_user.username})"
            favorite_name += " (выбран случайно)"
        else:
            user_id, username, first_name, last_name, total_reactions = favorite_user_data
            favorite_name = f"{first_name or ''}"
            if last_name:
                favorite_name += f" {last_name}"
            if username:
                favorite_name += f" (@{username})"
            favorite_name += f" - {total_reactions} реакций"
        
        # Формируем ответ
        response = f"💖 *{TITLES['favorite']['title']}* 💖\n"
        response += f"{TITLES['favorite']['description']}\n"
        response += f"🥇 {favorite_name}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_favorite_day: {e}")
        await update.message.reply_text("Произошла ошибка при выборе любимчика дня!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пидоров и любимчиков за неделю, месяц и все время"""
    try:
        response = "📊 *СТАТИСТИКА ТИТУЛОВ* 📊\n\n"
        
        for title_type, title_info in TITLES.items():
            response += f"{title_info['emoji']} *{title_info['title']}* {title_info['emoji']}\n"
            
            # За неделю
            week_stats = get_user_stats_period(title_type, 7)
            response += "📅 *За неделю:*\n"
            if week_stats:
                for i, (username, first_name, last_name, count) in enumerate(week_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За месяц
            month_stats = get_user_stats_period(title_type, 30)
            response += "📅 *За месяц:*\n"
            if month_stats:
                for i, (username, first_name, last_name, count) in enumerate(month_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За все время
            all_time_stats = get_all_time_stats(title_type)
            response += "📅 *За все время:*\n"
            if all_time_stats:
                for i, (username, first_name, last_name, count) in enumerate(all_time_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            response += "\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики!")

async def tester_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для предсказания тестировщика дня"""
    try:
        user = update.message.from_user
        
        if not can_user_get_prediction(user.id):
            await update.message.reply_text("Вы уже получали предсказание сегодня! Попробуйте завтра.")
            return
        
        # Получаем участников чата
        chat_id = update.effective_chat.id
        members = await get_chat_members(chat_id, context)
        
        # Выбираем случайного тестировщика
        tester_users = get_random_users(members, 1)
        tester_user = tester_users[0].user
        
        tester_name = f"{tester_user.first_name or ''}"
        if tester_user.last_name:
            tester_name += f" {tester_user.last_name}"
        if tester_user.username:
            tester_name += f" (@{tester_user.username})"
        
        response = f"🔮 *ПРЕДСКАЗАНИЕ ТЕСТИРОВЩИКА ДНЯ* 🔮\n\n"
        response += f"Мой хрустальный шар говорит...\n"
        response += f"Сегодняшний тестировщик дня: {tester_name}!\n\n"
        response += "Пусть баги горят, а тесты проходят! 🐛🔥"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in tester_day_command: {e}")
        await update.message.reply_text("Произошла ошибка при предсказании тестировщика дня!")

# Триггеры для сообщений
async def message_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает триггеры в сообщениях"""
    try:
        message_text = update.message.text.lower()
        user = update.message.from_user
        
        # Сохраняем реакции сообщения
        await save_message_reaction(update, context)
        
        # Триггер: Катя/Екатерина + "пока"
        if user.first_name and ('катя' in user.first_name.lower() or 'екатерина' in user.first_name.lower()):
            if 'пока' in message_text:
                await update.message.reply_text("Пока Кать! 👋")
                return
        
        # Триггер: "да" -> "Пизда"
        if message_text.strip() == 'да':
            await update.message.reply_text("Пизда! 😏")
            return
        
        # Триггер: "нет" -> "пидора ответ"
        if message_text.strip() == 'нет':
            await update.message.reply_text("пидора ответ! 🏳️‍🌈")
            return
            
        # Триггер: "ошибка" -> IT ответ
        if 'ошибка' in message_text or 'error' in message_text:
            it_response = random.choice(IT_RESPONSES['ошибка'])
            await update.message.reply_text(it_response)
            return
            
        # Триггер: "пиздец" -> грубый ответ
        if 'пиздец' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
        # IT-триггеры
        for trigger_word in ['офис', 'айос', 'андроид']:
            if trigger_word in message_text:
                it_response = random.choice(IT_RESPONSES[trigger_word])
                await update.message.reply_text(it_response)
                return
                
    except Exception as e:
        logger.error(f"Error in message_triggers: {e}")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("pidor", assign_pidor_day))
    application.add_handler(CommandHandler("favorite", assign_favorite_day))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("tester", tester_day_command))
    
    # Обработчик всех сообщений для триггеров и реакций
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_triggers))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    application.run_polling()

if __name__ == "__main__":
    main()ом и пиццей? Оба любят, когда их укладывают на стол!",
]

# Грубые ответы для триггеров
RUDE_RESPONSES = [
    "Да иди ты нахуй со своими проблемами!",
    "Пиздец конечно, но мне похуй!",
    "Ну вот опять этот пиздец начался...",
    "Иди нахуй, я занят более важной хуйней!",
    "Пиздец как всё заебало!",
    "Опять этот хуевый пиздец..."
]

# ТИТУЛЫ ДЛЯ ЕЖЕДНЕВНОГО ВЫБОРА
TITLES = {
    'pidor': {
        'title': '🏆 Пидор Дня',
        'description': 'Самый везучий неудачник чата!',
        'emoji': '🏆'
    },
    'favorite': {
        'title': '💖 Любимчик Дня', 
        'description': 'Чьи сообщения собрали больше всего реакций!',
        'emoji': '💖'
    },
}

# База данных
def init_db():
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Таблица для ежедневных результатов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_results (
        date TEXT PRIMARY KEY,
        results TEXT,
        last_updated TEXT
    )
    ''')
    
    # Таблица для статистики пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        title_type TEXT,
        count INTEGER DEFAULT 0,
        last_awarded TEXT,
        PRIMARY KEY (user_id, title_type)
    )
    ''')
    
    # Таблица для отслеживания реакций
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_reactions (
        message_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        reactions_count INTEGER DEFAULT 0,
        date TEXT
    )
    ''')
    
    # Таблица для отслеживания предсказаний тестировщика
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tester_predictions (
        user_id INTEGER PRIMARY KEY,
        last_prediction_date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_today_results():
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT results FROM daily_results WHERE date = ?', (today,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def save_today_results(results):
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_results (date, results, last_updated)
        VALUES (?, ?, ?)
    ''', (today, results, now))
    
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, first_name, last_name, title_type):
    today = datetime.now().date().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, first_name, last_name, title_type, count, last_awarded)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT count FROM user_stats WHERE user_id = ? AND title_type = ?), 0) + 1, ?)
    ''', (user_id, username, first_name, last_name, title_type, user_id, title_type, today))
    
    conn.commit()
    conn.close()

def get_user_stats_period(title_type, period_days):
    """Получает статистику за определенный период"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=period_days)).date().isoformat()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ? AND last_awarded >= ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type, start_date))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_all_time_stats(title_type):
    """Получает статистику за все время"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type,))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_random_users(chat_members, count=1):
    """Выбирает случайных пользователей из списка"""
    human_members = [m for m in chat_members if not m.user.is_bot]
    return random.sample(human_members, min(count, len(human_members)))

def get_top_user_by_reactions():
    """Получает пользователя с наибольшим количеством реакций"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Получаем пользователя с максимальным количеством реакций за сегодня
    today = datetime.now().date().isoformat()
    cursor.execute('''
        SELECT user_id, username, first_name, last_name, SUM(reactions_count) as total_reactions
        FROM message_reactions 
        WHERE date = ?
        GROUP BY user_id 
        ORDER BY total_reactions DESC 
        LIMIT 1
    ''', (today,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def can_user_get_prediction(user_id):
    """Проверяет, может ли пользователь получить предсказание сегодня"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT last_prediction_date FROM tester_predictions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] == today:
        conn.close()
        return False
    
    cursor.execute('''
        INSERT OR REPLACE INTO tester_predictions (user_id, last_prediction_date)
        VALUES (?, ?)
    ''', (user_id, today))
    
    conn.commit()
    conn.close()
    return True

async def save_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет информацию о сообщении и его реакциях"""
    try:
        message = update.message
        user = message.from_user
        
        # Подсчитываем общее количество реакций
        reaction_count = 0
        if message.reactions:
            for reaction in message.reactions:
                reaction_count += reaction.count
        
        conn = sqlite3.connect('daily_titles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO message_reactions 
            (message_id, user_id, username, first_name, last_name, reactions_count, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            reaction_count,
            datetime.now().date().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error saving message reaction: {e}")

async def assign_daily_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основная функция назначения ежедневных титулов"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results:
            await update.import os
import random
import logging
import sqlite3
import datetime
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен из файла
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Гейские подколы для пидора дня
GAY_JOKES = [
    "Как пидоры называют свой выходной? - День открытых дверей!",
    "Почему пидоры хорошие программисты? Потому что они любят обрабатывать исключения!",
    "Что общего между пидором и пиццей? Оба любят, когда их укладывают на стол!",
]

# Грубые ответы для триггеров
RUDE_RESPONSES = [
    "Да иди ты нахуй со своими проблемами!",
    "Пиздец конечно, но мне похуй!",
    "Ну вот опять этот пиздец начался...",
    "Иди нахуй, я занят более важной хуйней!",
    "Пиздец как всё заебало!",
    "Опять этот хуевый пиздец..."
]

# ТИТУЛЫ ДЛЯ ЕЖЕДНЕВНОГО ВЫБОРА
TITLES = {
    'pidor': {
        'title': '🏆 Пидор Дня',
        'description': 'Самый везучий неудачник чата!',
        'emoji': '🏆'
    },
    'favorite': {
        'title': '💖 Любимчик Дня', 
        'description': 'Чьи сообщения собрали больше всего реакций!',
        'emoji': '💖'
    },
}

# База данных
def init_db():
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Таблица для ежедневных результатов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_results (
        date TEXT PRIMARY KEY,
        results TEXT,
        last_updated TEXT
    )
    ''')
    
    # Таблица для статистики пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        title_type TEXT,
        count INTEGER DEFAULT 0,
        last_awarded TEXT,
        PRIMARY KEY (user_id, title_type)
    )
    ''')
    
    # Таблица для отслеживания реакций
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_reactions (
        message_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        reactions_count INTEGER DEFAULT 0,
        date TEXT
    )
    ''')
    
    # Таблица для отслеживания предсказаний тестировщика
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tester_predictions (
        user_id INTEGER PRIMARY KEY,
        last_prediction_date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_today_results():
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT results FROM daily_results WHERE date = ?', (today,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def save_today_results(results):
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_results (date, results, last_updated)
        VALUES (?, ?, ?)
    ''', (today, results, now))
    
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, first_name, last_name, title_type):
    today = datetime.now().date().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, first_name, last_name, title_type, count, last_awarded)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT count FROM user_stats WHERE user_id = ? AND title_type = ?), 0) + 1, ?)
    ''', (user_id, username, first_name, last_name, title_type, user_id, title_type, today))
    
    conn.commit()
    conn.close()

def get_user_stats_period(title_type, period_days):
    """Получает статистику за определенный период"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=period_days)).date().isoformat()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ? AND last_awarded >= ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type, start_date))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_all_time_stats(title_type):
    """Получает статистику за все время"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, first_name, last_name, COUNT(*) as count
        FROM user_stats 
        WHERE title_type = ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (title_type,))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def get_random_users(chat_members, count=1):
    """Выбирает случайных пользователей из списка"""
    human_members = [m for m in chat_members if not m.user.is_bot]
    return random.sample(human_members, min(count, len(human_members)))

def get_top_user_by_reactions():
    """Получает пользователя с наибольшим количеством реакций"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Получаем пользователя с максимальным количеством реакций за сегодня
    today = datetime.now().date().isoformat()
    cursor.execute('''
        SELECT user_id, username, first_name, last_name, SUM(reactions_count) as total_reactions
        FROM message_reactions 
        WHERE date = ?
        GROUP BY user_id 
        ORDER BY total_reactions DESC 
        LIMIT 1
    ''', (today,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def can_user_get_prediction(user_id):
    """Проверяет, может ли пользователь получить предсказание сегодня"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT last_prediction_date FROM tester_predictions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] == today:
        conn.close()
        return False
    
    cursor.execute('''
        INSERT OR REPLACE INTO tester_predictions (user_id, last_prediction_date)
        VALUES (?, ?)
    ''', (user_id, today))
    
    conn.commit()
    conn.close()
    return True

async def save_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет информацию о сообщении и его реакциях"""
    try:
        message = update.message
        user = message.from_user
        
        # Подсчитываем общее количество реакций
        reaction_count = 0
        if message.reactions:
            for reaction in message.reactions:
                reaction_count += reaction.count
        
        conn = sqlite3.connect('daily_titles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO message_reactions 
            (message_id, user_id, username, first_name, last_name, reactions_count, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            reaction_count,
            datetime.now().date().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error saving message reaction: {e}")

async def get_chat_members(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Получает всех участников чата (не только админов)"""
    try:
        # Получаем список всех участников чата
        members = []
        async for member in context.bot.get_chat_members(chat_id):
            members.append(member)
        return members
    except Exception as e:
        logger.error(f"Error getting chat members: {e}")
        # Если не получается получить всех участников, возвращаем админов как fallback
        return await context.bot.get_chat_administrators(chat_id)

async def assign_pidor_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Пидора Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Пидор Дня' in today_results:
            await update.message.reply_text("📅 Пидор дня уже был выбран сегодня!")
            return
        
        # Получаем всех участников чата
        members = await get_chat_members(chat_id, context)
        
        # 1. Отправляем гейскую шутку
        gay_joke = random.choice(GAY_JOKES)
        await update.message.reply_text(gay_joke)
        
        # 2. Отправляем картинку барабана (эмодзи)
        await update.message.reply_text("🥁 *Барабанная дробь...* 🥁", parse_mode='Markdown')
        
        # 3. Выбираем пидора дня
        pidor_users = get_random_users(members, 1)
        pidor_user = pidor_users[0].user
        
        # Обновляем статистику для пидора дня
        update_user_stats(
            pidor_user.id, 
            pidor_user.username, 
            pidor_user.first_name, 
            pidor_user.last_name, 
            'pidor'
        )
        
        # Формируем результат
        pidor_name = f"{pidor_user.first_name or ''}"
        if pidor_user.last_name:
            pidor_name += f" {pidor_user.last_name}"
        if pidor_user.username:
            pidor_name += f" (@{pidor_user.username})"
        
        # Формируем ответ
        response = f"🏆 *{TITLES['pidor']['title']}* 🏆\n"
        response += f"{TITLES['pidor']['description']}\n"
        response += f"🥇 {pidor_name}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_pidor_day: {e}")
        await update.message.reply_text("Произошла ошибка при выборе пидора дня!")

async def assign_favorite_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Любимчика Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Любимчик Дня' in today_results:
            await update.message.reply_text("📅 Любимчик дня уже был выбран сегодня!")
            return
        
        # Получаем всех участников чата
        members = await get_chat_members(chat_id, context)
        
        # Выбираем любимчика дня (по реакциям)
        favorite_user_data = get_top_user_by_reactions()
        
        # Если нет данных о реакциях, выбираем случайного
        if not favorite_user_data:
            favorite_users = get_random_users(members, 1)
            favorite_user = favorite_users[0].user
            favorite_name = f"{favorite_user.first_name or ''}"
            if favorite_user.last_name:
                favorite_name += f" {favorite_user.last_name}"
            if favorite_user.username:
                favorite_name += f" (@{favorite_user.username})"
            favorite_name += " (выбран случайно)"
        else:
            user_id, username, first_name, last_name, total_reactions = favorite_user_data
            favorite_name = f"{first_name or ''}"
            if last_name:
                favorite_name += f" {last_name}"
            if username:
                favorite_name += f" (@{username})"
            favorite_name += f" - {total_reactions} реакций"
        
        # Формируем ответ
        response = f"💖 *{TITLES['favorite']['title']}* 💖\n"
        response += f"{TITLES['favorite']['description']}\n"
        response += f"🥇 {favorite_name}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_favorite_day: {e}")
        await update.message.reply_text("Произошла ошибка при выборе любимчика дня!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пидоров и любимчиков за неделю, месяц и все время"""
    try:
        response = "📊 *СТАТИСТИКА ТИТУЛОВ* 📊\n\n"
        
        for title_type, title_info in TITLES.items():
            response += f"{title_info['emoji']} *{title_info['title']}* {title_info['emoji']}\n"
            
            # За неделю
            week_stats = get_user_stats_period(title_type, 7)
            response += "📅 *За неделю:*\n"
            if week_stats:
                for i, (username, first_name, last_name, count) in enumerate(week_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За месяц
            month_stats = get_user_stats_period(title_type, 30)
            response += "📅 *За месяц:*\n"
            if month_stats:
                for i, (username, first_name, last_name, count) in enumerate(month_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За все время
            all_time_stats = get_all_time_stats(title_type)
            response += "📅 *За все время:*\n"
            if all_time_stats:
                for i, (username, first_name, last_name, count) in enumerate(all_time_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            response += "\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики!")

async def tester_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для предсказания тестировщика дня"""
    try:
        user = update.message.from_user
        
        if not can_user_get_prediction(user.id):
            await update.message.reply_text("Вы уже получали предсказание сегодня! Попробуйте завтра.")
            return
        
        # Получаем участников чата
        chat_id = update.effective_chat.id
        members = await get_chat_members(chat_id, context)
        
        # Выбираем случайного тестировщика
        tester_users = get_random_users(members, 1)
        tester_user = tester_users[0].user
        
        tester_name = f"{tester_user.first_name or ''}"
        if tester_user.last_name:
            tester_name += f" {tester_user.last_name}"
        if tester_user.username:
            tester_name += f" (@{tester_user.username})"
        
        response = f"🔮 *ПРЕДСКАЗАНИЕ ТЕСТИРОВЩИКА ДНЯ* 🔮\n\n"
        response += f"Мой хрустальный шар говорит...\n"
        response += f"Сегодняшний тестировщик дня: {tester_name}!\n\n"
        response += "Пусть баги горят, а тесты проходят! 🐛🔥"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in tester_day_command: {e}")
        await update.message.reply_text("Произошла ошибка при предсказании тестировщика дня!")

# Триггеры для сообщений
async def message_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает триггеры в сообщениях"""
    try:
        message_text = update.message.text.lower()
        user = update.message.from_user
        
        # Сохраняем реакции сообщения
        await save_message_reaction(update, context)
        
        # Триггер: Катя/Екатерина + "пока"
        if user.first_name and ('катя' in user.first_name.lower() or 'екатерина' in user.first_name.lower()):
            if 'пока' in message_text:
                await update.message.reply_text("Пока Кать! 👋")
                return
        
        # Триггер: "да" -> "Пизда"
        if message_text.strip() == 'да':
            await update.message.reply_text("Пизда! 😏")
            return
        
        # Триггер: "нет" -> "пидора ответ"
        if message_text.strip() == 'нет':
            await update.message.reply_text("пидора ответ! 🏳️‍🌈")
            return
            
        # Триггер: "ошибка" -> грубый ответ
        if 'ошибка' in message_text or 'error' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
        # Триггер: "пиздец" -> грубый ответ
        if 'пиздец' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
    except Exception as e:
        logger.error(f"Error in message_triggers: {e}")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("pidor", assign_pidor_day))
    application.add_handler(CommandHandler("favorite", assign_favorite_day))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("tester", tester_day_command))
    
    # Обработчик всех сообщений для триггеров и реакций
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_triggers))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    application.run_polling()

if __name__ == "__main__":
    main()message.reply_text("📅 Сегодняшние титулы уже были назначены!\n\n" + today_results)
            return
        
        # Получаем участников чата
        members = await context.bot.get_chat_administrators(chat_id)
        
        # 1. Отправляем гейскую шутку
        gay_joke = random.choice(GAY_JOKES)
        await update.message.reply_text(gay_joke)
        
        # 2. Отправляем картинку барабана (эмодзи)
        await update.message.reply_text("🥁 *Барабанная дробь...* 🥁", parse_mode='Markdown')
        
        # 3. Выбираем пидора дня
        pidor_users = get_random_users(members, 1)
        pidor_user = pidor_users[0].user
        
        # 4. Выбираем любимчика дня (по реакциям)
        favorite_user_data = get_top_user_by_reactions()
        
        # Если нет данных о реакциях, выбираем случайного
        if not favorite_user_data:
            favorite_users = get_random_users(members, 1)
            favorite_user = favorite_users[0].user
            favorite_name = f"{favorite_user.first_name or ''}"
            if favorite_user.last_name:
                favorite_name += f" {favorite_user.last_name}"
            if favorite_user.username:
                favorite_name += f" (@{favorite_user.username})"
        else:
            user_id, username, first_name, last_name, total_reactions = favorite_user_data
            favorite_name = f"{first_name or ''}"
            if last_name:
                favorite_name += f" {last_name}"
            if username:
                favorite_name += f" (@{username})"
            favorite_name += f" - {total_reactions} реакций"
        
        # Обновляем статистику для пидора дня
        update_user_stats(
            pidor_user.id, 
            pidor_user.username, 
            pidor_user.first_name, 
            pidor_user.last_name, 
            'pidor'
        )
        
        # Формируем результат
        pidor_name = f"{pidor_user.first_name or ''}"
        if pidor_user.last_name:
            pidor_name += f" {pidor_user.last_name}"
        if pidor_user.username:
            pidor_name += f" (@{pidor_user.username})"
        
        # Формируем красивый ответ
        response = "🎉 *ЕЖЕДНЕВНЫЕ ТИТУЛЫ* 🎉\n\n"
        
        # Пидор дня
        response += f"🏆 *{TITLES['pidor']['title']}* 🏆\n"
        response += f"{TITLES['pidor']['description']}\n"
        response += f"🥇 {pidor_name}\n\n"
        
        # Любимчик дня
        response += f"💖 *{TITLES['favorite']['title']}* 💖\n"
        response += f"{TITLES['favorite']['description']}\n"
        response += f"🥇 {favorite_name}\n\n"
        
        response += "🏆 Поздравляем победителей! 🏆"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_daily_titles: {e}")
        await update.message.reply_text("Произошла ошибка при назначении титулов!")

async def daily_titles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для вызова ежедневных титулов"""
    await assign_daily_titles(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пидоров и любимчиков за неделю, месяц и все время"""
    try:
        response = "📊 *СТАТИСТИКА ТИТУЛОВ* 📊\n\n"
        
        for title_type, title_info in TITLES.items():
            response += f"{title_info['emoji']} *{title_info['title']}* {title_info['emoji']}\n"
            
            # За неделю
            week_stats = get_user_stats_period(title_type, 7)
            response += "📅 *За неделю:*\n"
            if week_stats:
                for i, (username, first_name, last_name, count) in enumerate(week_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За месяц
            month_stats = get_user_stats_period(title_type, 30)
            response += "📅 *За месяц:*\n"
            if month_stats:
                for i, (username, first_name, last_name, count) in enumerate(month_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            # За все время
            all_time_stats = get_all_time_stats(title_type)
            response += "📅 *За все время:*\n"
            if all_time_stats:
                for i, (username, first_name, last_name, count) in enumerate(all_time_stats[:3], 1):
                    user_name = first_name or ""
                    if last_name:
                        user_name += f" {last_name}"
                    if username:
                        user_name += f" (@{username})"
                    response += f"{i}. {user_name} - {count} раз(а)\n"
            else:
                response += "Нет данных\n"
            
            response += "\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики!")

async def tester_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для предсказания тестировщика дня"""
    try:
        user = update.message.from_user
        
        if not can_user_get_prediction(user.id):
            await update.message.reply_text("Вы уже получали предсказание сегодня! Попробуйте завтра.")
            return
        
        # Получаем участников чата
        chat_id = update.effective_chat.id
        members = await context.bot.get_chat_administrators(chat_id)
        
        # Выбираем случайного тестировщика
        tester_users = get_random_users(members, 1)
        tester_user = tester_users[0].user
        
        tester_name = f"{tester_user.first_name or ''}"
        if tester_user.last_name:
            tester_name += f" {tester_user.last_name}"
        if tester_user.username:
            tester_name += f" (@{tester_user.username})"
        
        response = f"🔮 *ПРЕДСКАЗАНИЕ ТЕСТИРОВЩИКА ДНЯ* 🔮\n\n"
        response += f"Мой хрустальный шар говорит...\n"
        response += f"Сегодняшний тестировщик дня: {tester_name}!\n\n"
        response += "Пусть баги горят, а тесты проходят! 🐛🔥"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in tester_day_command: {e}")
        await update.message.reply_text("Произошла ошибка при предсказании тестировщика дня!")

# Триггеры для сообщений
async def message_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает триггеры в сообщениях"""
    try:
        message_text = update.message.text.lower()
        user = update.message.from_user
        
        # Сохраняем реакции сообщения
        await save_message_reaction(update, context)
        
        # Триггер: Катя/Екатерина + "пока"
        if user.first_name and ('катя' in user.first_name.lower() or 'екатерина' in user.first_name.lower()):
            if 'пока' in message_text:
                await update.message.reply_text("Пока Кать! 👋")
                return
        
        # Триггер: "да" -> "Пизда"
        if message_text.strip() == 'да':
            await update.message.reply_text("Пизда! 😏")
            return
        
        # Триггер: "нет" -> "пидора ответ"
        if message_text.strip() == 'нет':
            await update.message.reply_text("пидора ответ! 🏳️‍🌈")
            return
            
        # Триггер: "ошибка" -> грубый ответ
        if 'ошибка' in message_text or 'error' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
        # Триггер: "пиздец" -> грубый ответ
        if 'пиздец' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
    except Exception as e:
        logger.error(f"Error in message_triggers: {e}")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("daily", daily_titles_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("tester", tester_day_command))
    
    # Обработчик всех сообщений для триггеров и реакций
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_triggers))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    application.run_polling()

if __name__ == "__main__":
    main()


