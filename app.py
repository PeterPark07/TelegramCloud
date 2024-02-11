import os
from flask import Flask, request
from database import log
import telebot
import time
import random

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

#Handler for document messages
@bot.message_handler(content_types=['document'])
def handle_document(message):
    document = message.document

    # Extract information from the document
    file_id = document.file_id
    file_size = document.file_size
    file_type = document.mime_type
    file_name = document.file_name if document.file_name else "Not available"

    # Log information in MongoDB
    log_entry = {
        "file_id": file_id,
        "file_size": file_size,
        "file_type": file_type,
        "file_name": file_name,
        "timestamp": time.time(),
        "random_number": random.randint(1, 1000)  # Adjust range as needed
    }
    log.insert_one(log_entry)

    # Create response message with the assigned random number
    response_text = f"File ID: {file_id}\nFile Size: {file_size} bytes\nFile Type: {file_type}\nFile Name: {file_name}\n"
    response_text += f"Use /file{log_entry['random_number']} to retrieve this file later."
    bot.reply_to(message, response_text)


@bot.message_handler(func=lambda message: message.text.startswith('/file'))
def handle_file_request(message):
    try:
        random_number = int(message.text.split('/file')[1])
        file_entry = log.find_one({"random_number": random_number})

        if file_entry:
            file_id = file_entry["file_id"]
            bot.send_document(message.chat.id, file_id)
        else:
            bot.reply_to(message, "File not found.")
    except (ValueError, IndexError):
        bot.reply_to(message, "Invalid command format. Use /file<n> to retrieve a file.")

