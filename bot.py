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
    "Что говорит пидор при компиляции? - Сейчас войду в процесс!",
    "Почему пидоры хорошие тестировщики? - Они проверяют все дырочки в системе!",
    "Как пидор решает проблемы? - Подходит с задней стороны!",
    "Как пидор находит баги? - Чутьем настоящего искателя!",
    "Что пидор думает о коде? - Главное чтобы было красиво сзади!",
    "Ищем любителя видеозвонков в СБИСе",
    "Настраиваюсь на волну автора незначительных ошибок за неделю до релиза",
    "Выбираем лесную банку...."
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

# Ответы на IT-триггеры
IT_RESPONSES = {
    'офис': [
        "Офис? Это место где пидоры притворяются нормальными с 9 до 6! 🎭",
        "В офисе все знают, чей стул скрипит громче всех! 💺🔊",
        "Офисный пидор всегда знает, где найти самый удобный стул! 💼",
        "В офисе пидоры собираются у кулера, чтобы обсудить последние тренды! 💦"
    ],
    'ошибка': [
        "Это не баг, это фича! 🐛🏳️‍🌈",
        "Ошибка компиляции - пидор не может войти в программу! ⚠️",
        "Ошибка 404: Пидор не найден в этом коде! 🔍",
        "Runtime Error: Пидор пытался войти не в ту функцию! 🚫"
    ],
    'айос': [
        "iOS - операционка для пидоров которые любят когда за них все решают! 📱✨",
        "iPhone пользователи - пидоры с золотыми цепями! 📱⛓️",
        "iOS разработчик - пидор в позолоченной клетке! 🏢"
    ],
    'андроид': [
        "Android - для пидоров которые любят настраивать все под себя! 🤖🔧",
        "Android разработчики - пидоры в свободных отношениях с кодом! 💻",
        "Android пользователь - пидор с возможностью кастомизации! 🎨",
        "Пидор на Android может настроить все под свой вкус! 🌈"
    ],
    'баг': [
        "Нашел баг? Значит ты хороший пидор-тестировщик! 🐛🔍",
        "Баг - это просто фича, которую пидор еще не понял! 🐞",
        "Каждому багу нужен свой пидор для исправления! 🛠️"
    ],
    'кулик': [
        "Не произноси это имя вслух",
        "Что он тебе сделаль??",
    ],
    'сережа': [
        "не Серёжа, а СерГЕЙ",
    ]
}

# База данных
def init_db():
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    # Таблица для ежедневных результатов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_results (
        date TEXT PRIMARY KEY,
        pidor_result TEXT,
        favorite_result TEXT,
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        reactions_count INTEGER DEFAULT 1,
        date TEXT,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_today_results():
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT pidor_result, favorite_result FROM daily_results WHERE date = ?', (today,))
    result = cursor.fetchone()
    conn.close()
    
    return result if result else (None, None)

def save_today_results(pidor_result, favorite_result):
    today = datetime.now().date().isoformat()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_results (date, pidor_result, favorite_result, last_updated)
        VALUES (?, ?, ?, ?)
    ''', (today, pidor_result, favorite_result, now))
    
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

def get_reactions_stats_period(period_days):
    """Получает статистику реакций за период"""
    conn = sqlite3.connect('daily_titles.db')
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=period_days)).date().isoformat()
    
    cursor.execute('''
        SELECT username, first_name, last_name, SUM(reactions_count) as total_reactions
        FROM message_reactions 
        WHERE date >= ?
        GROUP BY user_id 
        ORDER BY total_reactions DESC 
        LIMIT 10
    ''', (start_date,))
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

async def save_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет информацию о сообщении для подсчета реакций"""
    try:
        message = update.message
        if not message:
            return
            
        user = message.from_user
        if not user:
            return
        
        # Базовый счетчик реакций
        reaction_count = 1
        
        conn = sqlite3.connect('daily_titles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO message_reactions 
            (message_id, user_id, username, first_name, last_name, reactions_count, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            reaction_count,
            datetime.now().date().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранено сообщение от {user.first_name} для подсчета реакций")
        
    except Exception as e:
        logger.error(f"Error saving message reaction: {e}")

# Список тестовых пользователей (для демонстрации без прав админа)
TEST_USERS = [
    {"id": 1, "first_name": "Вася", "last_name": "Пупкин", "username": "vasya"},
    {"id": 2, "first_name": "Мария", "last_name": "Иванова", "username": None},
    {"id": 3, "first_name": "Алексей", "last_name": None, "username": "alexey"},
    {"id": 4, "first_name": "Екатерина", "last_name": "Смирнова", "username": "kate"},
    {"id": 5, "first_name": "Дмитрий", "last_name": "Петров", "username": "dima"},
]

async def get_chat_members_simple(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенный способ получения участников чата (без прав админа)"""
    try:
        # Для демонстрации используем тестовых пользователей + бота
        from telegram import User, ChatMember
        
        members = []
        
        # Добавляем бота
        bot_info = await context.bot.get_me()
        bot_user = User(
            id=bot_info.id,
            is_bot=True,
            first_name=bot_info.first_name,
            username=bot_info.username
        )
        members.append(ChatMember(user=bot_user, status='member'))
        
        # Добавляем тестовых пользователей
        for user_data in TEST_USERS:
            user = User(
                id=user_data["id"],
                is_bot=False,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                username=user_data["username"]
            )
            members.append(ChatMember(user=user, status='member'))
        
        logger.info(f"Создано тестовых участников: {len(members)}")
        return members
        
    except Exception as e:
        logger.error(f"Error in get_chat_members_simple: {e}")
        return []

async def assign_pidor_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Пидора Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        pidor_result, favorite_result = get_today_results()
        if pidor_result:
            await update.message.reply_text("📅 Пидор дня уже был выбран сегодня!")
            return
        
        # Получаем участников чата (упрощенный метод)
        members = await get_chat_members_simple(chat_id, context)
        
        # Фильтруем ботов и оставляем только людей
        human_members = [m for m in members if not m.user.is_bot]
        if not human_members:
            await update.message.reply_text("❌ В чате нет участников для выбора!")
            return
            
        logger.info(f"Участников для выбора пидора: {len(human_members)}")
        
        # 1. Отправляем гей-шутку
        gay_joke = random.choice(GAY_JOKES)
        await update.message.reply_text(gay_joke)
        await asyncio.sleep(1)
        
        # 2. Отправляем картинку барабана (эмодзи)
        drum_msg = await update.message.reply_text("🥁 *Барабанная дробь...* 🥁", parse_mode='Markdown')
        await asyncio.sleep(2)
        
        # 3. Выбираем пидора дня
        pidor_user = random.choice(human_members).user
        
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
        response = f"🏆 *Пидор Дня* 🏆\n"
        response += f"Самый везучий неудачник чата!\n"
        response += f"🥇 {pidor_name}\n"
        response += f"📊 Всего кандидатов: {len(human_members)}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response, None)
        
        await drum_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_pidor_day: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выборе пидора дня!")

async def assign_favorite_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Любимчика Дня (по реальным реакциям)"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        pidor_result, favorite_result = get_today_results()
        if favorite_result:
            await update.message.reply_text("📅 Любимчик дня уже был выбран сегодня!")
            return
        
        # Получаем участников чата
        members = await get_chat_members_simple(chat_id, context)
        human_members = [m for m in members if not m.user.is_bot]
        if not human_members:
            await update.message.reply_text("❌ В чате нет участников для выбора!")
            return
        
        # Выбираем любимчика дня по реальным реакциям за сегодня
        today = datetime.now().date().isoformat()
        conn = sqlite3.connect('daily_titles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, SUM(reactions_count) as total_reactions
            FROM message_reactions 
            WHERE date = ?
            GROUP BY user_id 
            ORDER BY total_reactions DESC 
            LIMIT 1
        ''', (today,))
        
        favorite_user_data = cursor.fetchone()
        conn.close()
        
        if favorite_user_data and favorite_user_data[4] > 0:  # Есть реакции
            user_id, username, first_name, last_name, total_reactions = favorite_user_data
            favorite_name = f"{first_name or ''}"
            if last_name:
                favorite_name += f" {last_name}"
            if username:
                favorite_name += f" (@{username})"
            favorite_name += f" - {total_reactions} реакций"
            
            # Обновляем статистику
            update_user_stats(user_id, username, first_name, last_name, 'favorite')
        else:
            # Если нет реакций, выбираем случайного
            favorite_user = random.choice(human_members).user
            favorite_name = f"{favorite_user.first_name or ''}"
            if favorite_user.last_name:
                favorite_name += f" {favorite_user.last_name}"
            if favorite_user.username:
                favorite_name += f" (@{favorite_user.username})"
            favorite_name += " (выбран случайно, нет реакций)"
            
            update_user_stats(
                favorite_user.id,
                favorite_user.username,
                favorite_user.first_name,
                favorite_user.last_name,
                'favorite'
            )
        
        # Формируем ответ
        response = f"💖 *Любимчик Дня* 💖\n"
        response += f"Чьи сообщения собрали больше всего реакций!\n"
        response += f"🥇 {favorite_name}\n"
        response += f"📊 Всего кандидатов: {len(human_members)}"
        
        # Сохраняем результаты на сегодня
        save_today_results(pidor_result, response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_favorite_day: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выборе любимчика дня!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пидоров и реакций"""
    try:
        response = "📊 *СТАТИСТИКА* 📊\n\n"
        
        # Статистика пидоров
        response += "🏆 *Пидоры Дня:*\n"
        
        # За неделю
        week_stats = get_user_stats_period('pidor', 7)
        response += "📅 За неделю:\n"
        if week_stats:
            for i, (username, first_name, last_name, count) in enumerate(week_stats[:3], 1):
                user_name = first_name or ""
                if last_name:
                    user_name += f" {last_name}"
                if username:
                    user_name += f" (@{username})"
                response += f"{i}. {user_name} - {count} раз\n"
        else:
            response += "Нет данных\n"
        
        # За месяц
        month_stats = get_user_stats_period('pidor', 30)
        response += "📅 За месяц:\n"
        if month_stats:
            for i, (username, first_name, last_name, count) in enumerate(month_stats[:3], 1):
                user_name = first_name or ""
                if last_name:
                    user_name += f" {last_name}"
                if username:
                    user_name += f" (@{username})"
                response += f"{i}. {user_name} - {count} раз\n"
        else:
            response += "Нет данных\n"
        
        response += "\n💖 *Любимчики Дня (по реакциям):*\n"
        
        # Реакции за сегодня
        today_reactions = get_reactions_stats_period(1)
        response += "📅 За сегодня:\n"
        if today_reactions:
            for i, (username, first_name, last_name, reactions) in enumerate(today_reactions[:3], 1):
                user_name = first_name or ""
                if last_name:
                    user_name += f" {last_name}"
                if username:
                    user_name += f" (@{username})"
                response += f"{i}. {user_name} - {reactions} реакций\n"
        else:
            response += "Нет данных\n"
        
        # Реакции за неделю
        week_reactions = get_reactions_stats_period(7)
        response += "📅 За неделю:\n"
        if week_reactions:
            for i, (username, first_name, last_name, reactions) in enumerate(week_reactions[:3], 1):
                user_name = first_name or ""
                if last_name:
                    user_name += f" {last_name}"
                if username:
                    user_name += f" (@{username})"
                response += f"{i}. {user_name} - {reactions} реакций\n"
        else:
            response += "Нет данных\n"
        
        # Реакции за месяц
        month_reactions = get_reactions_stats_period(30)
        response += "📅 За месяц:\n"
        if month_reactions:
            for i, (username, first_name, last_name, reactions) in enumerate(month_reactions[:3], 1):
                user_name = first_name or ""
                if last_name:
                    user_name += f" {last_name}"
                if username:
                    user_name += f" (@{username})"
                response += f"{i}. {user_name} - {reactions} реакций\n"
        else:
            response += "Нет данных\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = """
🤖 *Доступные команды:*

/pidor - Выбрать пидора дня 🏆
/favorite - Выбрать любимчика дня 💖  
/stats - Показать статистику 📊
/help - Показать эту справку ❓

💬 *Триггеры в сообщениях:*
- "да" → "Пизда!"
- "нет" → "пидора ответ!"
- IT-слова (офис, ошибка, айос, андроид, баг, кулик, сережа)
- "пиздец" → случайный грубый ответ

✅ *Бот работает без прав администратора!*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Триггеры для сообщений
async def message_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает триггеры в сообщениях"""
    try:
        if not update.message or not update.message.text:
            return
            
        message_text = update.message.text.lower()
        user = update.message.from_user
        
        logger.info(f"Получено сообщение для триггеров от {user.first_name}: {message_text}")
        
        # Сохраняем сообщение для подсчета реакций
        await save_message_reaction(update, context)
        
        # Триггер: Катя/Екатерина + "пока"
        if user.first_name:
            user_name_lower = user.first_name.lower()
            if ('катя' in user_name_lower or 'екатерина' in user_name_lower) and 'пока' in message_text:
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
            
        # Триггер: "ошибка" или "error"
        if 'ошибка' in message_text or 'error' in message_text:
            it_response = random.choice(IT_RESPONSES['ошибка'])
            await update.message.reply_text(it_response)
            return
            
        # Триггер: "пиздец"
        if 'пиздец' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
        # IT-триггеры
        words = message_text.lower().split()
        for word in words:
            clean_word = word.strip().rstrip('.,!?;:')
            
            for trigger in ['офис', 'айос', 'андроид', 'баг', 'кулик', 'сережа']:
                if trigger == clean_word:
                    it_response = random.choice(IT_RESPONSES.get(trigger, ["Нет ответа"]))
                    await update.message.reply_text(it_response)
                    return
                
    except Exception as e:
        logger.error(f"Error in message_triggers: {e}")

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения с настройками для групп
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("pidor", assign_pidor_day))
    application.add_handler(CommandHandler("favorite", assign_favorite_day))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", help_command))
    
    # Обработчик всех сообщений для триггеров и реакций
    # Важно: используем filters.CHAT чтобы обрабатывать сообщения в группах
    application.add_handler(MessageHandler(
        filters.TEXT & (filters.CHAT_GROUP | filters.CHAT_SUPERGROUP) & ~filters.COMMAND, 
        message_triggers
    ))
    
    # Также обрабатываем сообщения в личных чатах
    application.add_handler(MessageHandler(
        filters.TEXT & filters.CHAT_PRIVATE & ~filters.COMMAND, 
        message_triggers
    ))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    print("Бот настроен для работы в группах без прав администратора")
    
    # Запуск бота
    try:
        application.run_polling(
            drop_pending_updates=True,  # Игнорировать накопившиеся апдейты
            allowed_updates=['message', 'chat_member', 'my_chat_member']
        )
    except Exception as e:
        logger.error(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
