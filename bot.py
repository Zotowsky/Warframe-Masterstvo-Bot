import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

def init_db():
    conn = sqlite3.connect('warframe.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS weapons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  name TEXT,
                  level INTEGER,
                  forma_count INTEGER,
                  mastered BOOLEAN,
                  timestamp DATETIME)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS warframes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  name TEXT,
                  level INTEGER,
                  forma_count INTEGER,
                  mastered BOOLEAN,
                  timestamp DATETIME)''')
    
    conn.commit()
    conn.close()

ADD_WEAPON, ADD_WARFRAME = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для отслеживания прокачки в Warframe.\n"
        "Используй /help для списка команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Доступные команды:
    /add_weapon - Добавить оружие в трекер
    /add_warframe - Добавить варфрейм в трекер
    /my_weapons - Показать ваше оружие
    /my_warframes - Показать ваши варфреймы
    /stats - Показать статистику
    """
    await update.message.reply_text(help_text)

async def add_weapon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название оружия:")
    return ADD_WEAPON

async def add_weapon_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weapon_name = update.message.text
    context.user_data['weapon_name'] = weapon_name
    context.user_data['item_type'] = 'weapon'
    
    keyboard = [
        [InlineKeyboardButton("30", callback_data='30')],
        [InlineKeyboardButton("0", callback_data='0'),
         InlineKeyboardButton("5", callback_data='5'),
         InlineKeyboardButton("10", callback_data='10'),
         InlineKeyboardButton("15", callback_data='15'),
         InlineKeyboardButton("20", callback_data='20'),
         InlineKeyboardButton("25", callback_data='25')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Выберите текущий уровень для {weapon_name}:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def add_warframe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название варфрейма:")
    return ADD_WARFRAME

async def add_warframe_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    warframe_name = update.message.text
    context.user_data['warframe_name'] = warframe_name
    context.user_data['item_type'] = 'warframe'
    
    keyboard = [
        [InlineKeyboardButton("30", callback_data='30')],
        [InlineKeyboardButton("0", callback_data='0'),
         InlineKeyboardButton("5", callback_data='5'),
         InlineKeyboardButton("10", callback_data='10'),
         InlineKeyboardButton("15", callback_data='15'),
         InlineKeyboardButton("20", callback_data='20'),
         InlineKeyboardButton("25", callback_data='25')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Выберите текущий уровень для {warframe_name}:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    level = int(query.data)
    context.user_data['item_level'] = level
    
    keyboard = [
        [InlineKeyboardButton("0", callback_data='forma_0'),
         InlineKeyboardButton("1", callback_data='forma_1'),
         InlineKeyboardButton("2", callback_data='forma_2'),
         InlineKeyboardButton("3+", callback_data='forma_3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    item_type = context.user_data.get('item_type', 'предмета')
    item_name = context.user_data.get(f'{item_type}_name', 'Неизвестный предмет')
    
    await query.edit_message_text(
        f"{item_name} - уровень {level}\n"
        "Сколько форм установлено?",
        reply_markup=reply_markup
    )

async def forma_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    forma_count = int(query.data.split('_')[1])
    item_type = context.user_data.get('item_type')
    
    if item_type == 'weapon':
        item_name = context.user_data.get('weapon_name', 'Неизвестное оружие')
        table = 'weapons'
    else:
        item_name = context.user_data.get('warframe_name', 'Неизвестный варфрейм')
        table = 'warframes'
    
    level = context.user_data.get('item_level', 0)
    mastered = level == 30
    
    conn = sqlite3.connect('warframe.db')
    c = conn.cursor()
    c.execute(f'''INSERT INTO {table} 
                 (user_id, name, level, forma_count, mastered, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?)''',
                 (query.from_user.id, item_name, level, forma_count, mastered, datetime.now()))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        f"{'Варфрейм' if item_type == 'warframe' else 'Оружие'} {item_name} добавлено!\n"
        f"Уровень: {level}\n"
        f"Формы: {forma_count}\n"
        f"Освоено: {'Да' if mastered else 'Нет'}"
    )

async def my_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('warframe.db')
    c = conn.cursor()
    c.execute('''SELECT name, level, forma_count, mastered FROM weapons 
                  WHERE user_id=? ORDER BY name''',
                  (update.effective_user.id,))
    weapons = c.fetchall()
    conn.close()
    
    if not weapons:
        await update.message.reply_text("У вас нет оружия в трекере.")
        return
    
    response = "🔫 Ваше оружие:\n\n"
    for name, level, forma, mastered in weapons:
        mastered_status = "✅" if mastered else "❌"
        response += f"<b>{name}</b>\nУр. {level}, Формы: {forma}, Мастер: {mastered_status}\n\n"
    
    await update.message.reply_text(response, parse_mode='HTML')


async def my_warframes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('warframe.db')
    c = conn.cursor()
    c.execute('''SELECT name, level, forma_count, mastered FROM warframes 
                  WHERE user_id=? ORDER BY name''',
                  (update.effective_user.id,))
    warframes = c.fetchall()
    conn.close()
    
    if not warframes:
        await update.message.reply_text("У вас нет варфреймов в трекере.")
        return
    
    response = "Ваши варфреймы:\n\n"
    for name, level, forma, mastered in warframes:
        mastered_status = "✅" if mastered else "❌"
        response += f"<b>{name}</b>\nУр. {level}, Формы: {forma}, Мастер: {mastered_status}\n\n"
    
    await update.message.reply_text(response, parse_mode='HTML')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('warframe.db')
    c = conn.cursor()
    
    c.execute('''SELECT COUNT(*) FROM weapons WHERE user_id=? AND mastered=1''',
              (update.effective_user.id,))
    mastered_weapons = c.fetchone()[0]
    c.execute('''SELECT COUNT(DISTINCT name) FROM weapons WHERE user_id=?''',
              (update.effective_user.id,))
    total_weapons = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(*) FROM warframes WHERE user_id=? AND mastered=1''',
              (update.effective_user.id,))
    mastered_warframes = c.fetchone()[0]
    c.execute('''SELECT COUNT(DISTINCT name) FROM warframes WHERE user_id=?''',
              (update.effective_user.id,))
    total_warframes = c.fetchone()[0]
    
    conn.close()
    
    response = (
        " Ваша статистика:\n\n"
        f"Оружие: {mastered_weapons}/{total_weapons} освоено\n"
        f"Варфреймы: {mastered_warframes}/{total_warframes} освоено"
    )
    
    await update.message.reply_text(response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Ошибка при обработке запроса: {context.error}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка. Пожалуйста, попробуйте позже."
    )

def main():
    init_db()
    
    application = Application.builder().token("8288047174:AAEJ4EYtA3irKT-0VbqenyTyaU7xTZzXVzo").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_weapons", my_weapons))
    application.add_handler(CommandHandler("my_warframes", my_warframes))
    application.add_handler(CommandHandler("stats", stats))
    
    conv_handler_weapon = ConversationHandler(
        entry_points=[CommandHandler("add_weapon", add_weapon_start)],
        states={
            ADD_WEAPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_weapon_name)],
        },
        fallbacks=[]
    )
    
    conv_handler_warframe = ConversationHandler(
        entry_points=[CommandHandler("add_warframe", add_warframe_start)],
        states={
            ADD_WARFRAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_warframe_name)],
        },
        fallbacks=[]
    )
    
    application.add_handler(conv_handler_weapon)
    application.add_handler(conv_handler_warframe)
    
    application.add_handler(CallbackQueryHandler(level_choice, pattern='^[0-9]+$'))
    application.add_handler(CallbackQueryHandler(forma_choice, pattern='^forma_'))
    
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()