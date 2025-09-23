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
    if not human_members:
        return []
    return random.sample(human_members, min(count, len(human_members)))

def get_top_user_by_reactions():
    """Получает пользователя с наибольшим количеством реакций за сегодня"""
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

async def save_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет информацию о сообщении и его реакциях"""
    try:
        message = update.message
        if not message:
            return
            
        user = message.from_user
        if not user:
            return
        
        # Базовый счетчик реакций (можно расширить логикой подсчета реальных реакций)
        reaction_count = 1  # Каждое сообщение получает минимум 1 "реакцию"
        
        # Дополнительные реакции за replies
        if message.reply_to_message:
            reaction_count += 2  # Ответ на сообщение = +2 реакции
        
        # Логируем для отладки
        logger.info(f"Сообщение от {user.first_name}: reactions_count = {reaction_count}")
        
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

async def get_all_chat_members(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Получает ВСЕХ участников чата (используем администраторов как fallback)"""
    try:
        members = []
        
        # Пытаемся получить всех участников чата
        try:
            async for member in context.bot.get_chat_members(chat_id):
                members.append(member)
            logger.info(f"✅ Успешно получено всех участников: {len(members)}")
        except Exception as e:
            logger.warning(f"Не удалось получить всех участников: {e}")
            # Fallback - получаем администраторов
            try:
                admin_members = await context.bot.get_chat_administrators(chat_id)
                members.extend(admin_members)
                logger.info(f"✅ Получено администраторов: {len(members)}")
            except Exception as admin_error:
                logger.error(f"❌ Не удалось получить даже администраторов: {admin_error}")
                return []
        
        return members
        
    except Exception as e:
        logger.error(f"Error getting chat members: {e}")
        return []

async def assign_pidor_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Пидора Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Пидор Дня' in today_results:
            await update.message.reply_text("📅 Пидор дня уже был выбран сегодня!")
            return
        
        # Получаем ВСЕХ участников чата
        members = await get_all_chat_members(chat_id, context)
        if not members:
            await update.message.reply_text("❌ Не удалось получить список участников чата! Убедитесь, что бот имеет права администратора.")
            return
        
        logger.info(f"Получено участников для выбора пидора: {len(members)}")
        
        # Фильтруем ботов и оставляем только людей
        human_members = [m for m in members if not m.user.is_bot]
        if not human_members:
            await update.message.reply_text("❌ В чате нет подходящих участников (все боты?)!")
            return
            
        logger.info(f"Человеческих участников после фильтрации: {len(human_members)}")
        
        # 1. Отправляем гей-шутку
        gay_joke = random.choice(GAY_JOKES)
        await update.message.reply_text(gay_joke)
        await asyncio.sleep(1)
        
        # 2. Отправляем картинку барабана (эмодзи)
        drum_msg = await update.message.reply_text("🥁 *Барабанная дробь...* 🥁", parse_mode='Markdown')
        await asyncio.sleep(2)  # Пауза для драматизма
        
        # 3. Выбираем пидора дня из ВСЕХ участников
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
        save_today_results(response)
        
        await drum_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_pidor_day: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выборе пидора дня!")

async def assign_favorite_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение Любимчика Дня"""
    try:
        chat_id = update.effective_chat.id
        
        # Проверяем, не выполнялась ли сегодня уже этой команды
        today_results = get_today_results()
        if today_results and 'Любимчик Дня' in today_results:
            await update.message.reply_text("📅 Любимчик дня уже был выбран сегодня!")
            return
        
        # Получаем ВСЕХ участников чата
        members = await get_all_chat_members(chat_id, context)
        if not members:
            await update.message.reply_text("❌ Не удалось получить список участников чата!")
            return
        
        # Фильтруем ботов
        human_members = [m for m in members if not m.user.is_bot]
        if not human_members:
            await update.message.reply_text("❌ В чате нет подходящих участников!")
            return
        
        # Выбираем любимчика дня (по реакциям из ВСЕХ сообщений за день)
        favorite_user_data = get_top_user_by_reactions()
        
        # Если нет данных о реакциях, выбираем случайного из всех участников
        if not favorite_user_data:
            favorite_user = random.choice(human_members).user
            favorite_name = f"{favorite_user.first_name or ''}"
            if favorite_user.last_name:
                favorite_name += f" {favorite_user.last_name}"
            if favorite_user.username:
                favorite_name += f" (@{favorite_user.username})"
            favorite_name += " (выбран случайно)"
            
            # Обновляем статистику
            update_user_stats(
                favorite_user.id,
                favorite_user.username,
                favorite_user.first_name,
                favorite_user.last_name,
                'favorite'
            )
        else:
            user_id, username, first_name, last_name, total_reactions = favorite_user_data
            favorite_name = f"{first_name or ''}"
            if last_name:
                favorite_name += f" {last_name}"
            if username:
                favorite_name += f" (@{username})"
            favorite_name += f" - {total_reactions} реакций"
            
            # Обновляем статистику
            update_user_stats(user_id, username, first_name, last_name, 'favorite')
        
        # Формируем ответ
        response = f"💖 *Любимчик Дня* 💖\n"
        response += f"Чьи сообщения собрали больше всего реакций!\n"
        response += f"🥇 {favorite_name}\n"
        response += f"📊 Всего кандидатов: {len(human_members)}"
        
        # Сохраняем результаты на сегодня
        save_today_results(response)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in assign_favorite_day: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выборе любимчика дня!")

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

⚠️ *Для работы бота нужны права администратора!*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для отладки - показать участников чата"""
    try:
        chat_id = update.effective_chat.id
        members = await get_all_chat_members(chat_id, context)
        
        if not members:
            await update.message.reply_text("❌ Не удалось получить список участников!")
            return
        
        human_members = [m for m in members if not m.user.is_bot]
        
        response = f"👥 *ИНФОРМАЦИЯ О ЧАТЕ* 👥\n\n"
        response += f"Всего участников: {len(members)}\n"
        response += f"Людей (не ботов): {len(human_members)}\n\n"
        response += f"*Список участников:*\n"
        
        for i, member in enumerate(human_members[:15], 1):  # Показываем первых 15
            user = member.user
            name = f"{user.first_name or ''}"
            if user.last_name:
                name += f" {user.last_name}"
            if user.username:
                name += f" (@{user.username})"
            response += f"{i}. {name}\n"
        
        if len(human_members) > 15:
            response += f"\n... и еще {len(human_members) - 15} участников"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in members_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении информации о чате")

# Триггеры для сообщений
async def message_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает триггеры в сообщениях (независимо от регистра)"""
    try:
        if not update.message or not update.message.text:
            return
            
        message_text = update.message.text.lower()
        user = update.message.from_user
        
        logger.info(f"Получено сообщение от {user.first_name}: {message_text}")
        
        # Сохраняем реакции сообщения (для любимчика дня)
        await save_message_reaction(update, context)
        
        # Триггер: Катя/Екатерина + "пока" (независимо от регистра)
        if user.first_name:
            user_name_lower = user.first_name.lower()
            if ('катя' in user_name_lower or 'екатерина' in user_name_lower) and 'пока' in message_text:
                await update.message.reply_text("Пока Кать! 👋")
                return
        
        # Триггер: "да" -> "Пизда" (точное совпадение)
        if message_text.strip() == 'да':
            await update.message.reply_text("Пизда! 😏")
            return
        
        # Триггер: "нет" -> "пидора ответ" (точное совпадение)
        if message_text.strip() == 'нет':
            await update.message.reply_text("пидора ответ! 🏳️‍🌈")
            return
            
        # Триггер: "ошибка" или "error" -> IT ответ
        if 'ошибка' in message_text or 'error' in message_text:
            it_response = random.choice(IT_RESPONSES['ошибка'])
            await update.message.reply_text(it_response)
            return
            
        # Триггер: "пиздец" -> грубый ответ
        if 'пиздец' in message_text:
            rude_response = random.choice(RUDE_RESPONSES)
            await update.message.reply_text(rude_response)
            return
            
        # IT-триггеры - проверяем каждое слово отдельно (независимо от регистра)
        words = message_text.lower().split()
        for word in words:
            # Очищаем слово от знаков препинания
            clean_word = word.strip().rstrip('.,!?;:')
            
            # Проверяем все возможные триггеры
            for trigger in ['офис', 'ошибка', 'айос', 'андроид', 'баг', 'кулик', 'сережа']:
                if trigger in clean_word:
                    it_response = random.choice(IT_RESPONSES.get(trigger, ["Нет ответа для этого триггера"]))
                    await update.message.reply_text(it_response)
                    return
                
    except Exception as e:
        logger.error(f"Error in message_triggers: {e}")

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("pidor", assign_pidor_day))
    application.add_handler(CommandHandler("favorite", assign_favorite_day))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", help_command))
    application.add_handler(CommandHandler("members", members_command))
    
    # Обработчик всех сообщений для триггеров и реакций
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_triggers))
    
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    
    # Запуск бота
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
