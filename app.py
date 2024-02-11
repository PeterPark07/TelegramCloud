
import os
from flask import Flask, request
import telebot
import time

app = Flask(__name__)
bot = telebot.TeleBot(os.getenv('bot'), threaded=False)

# Bot route to handle incoming messages
@app.route('/bot', methods=['POST'])
def telegram():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200

# Handler for the '/start' command
@bot.message_handler(commands=['start'])
def start_command(message):
    response_text = "Hello! Welcome to this bot!\n\n"
    response_text += "For help, use the command /help."
    bot.reply_to(message, response_text)

# Handler for the '/help' command
@bot.message_handler(commands=['help'])
def help_command(message):
    response_text = "Here are the available commands:\n\n"
    response_text += "/start - Start the bot.\n"
    response_text += "/help - Show this help message.\n"
    bot.reply_to(message, response_text)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    document = message.document

    file_id = document.file_id
    file_size = document.file_size
    file_type = document.mime_type
    file_name = document.file_name if document.file_name else "Not available"

    response_text = f"File ID: {file_id}\nFile Size: {file_size} bytes\nFile Type: {file_type}\nFile Name: {file_name}"
    bot.reply_to(message, response_text)


# Handler for when a file is sent
@bot.message_handler(content_types=['photo', 'video', 'audio'])
def handle_file(message):
    file_type = message.content_type # Extracting the type of file
    response_text = f"Received a {file_type} file!"
    bot.reply_to(message, response_text)


