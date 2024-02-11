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

# Handler for document messages
@bot.message_handler(content_types=['document'])
def handle_document(message):
    document = message.document

    # Extract information from the document
    file_id = document.file_id
    file_size = document.file_size
    file_type = document.mime_type
    file_name = document.file_name if document.file_name else "Not available"

    # Generate a unique identifier combining file ID and random number
    unique_identifier = f"{file_id[-6:]}_{random.randint(1, 1000)}"

    # Log information in MongoDB
    log_entry = {
        "file_id": file_id,
        "file_size": file_size,
        "file_type": file_type,
        "file_name": file_name,
        "timestamp": time.time(),
        "unique_identifier": unique_identifier  # Using the combined identifier
    }
    log.insert_one(log_entry)

    # Get file path using bot.get_file
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path

    # Generate download link
    download_link = f"https://api.telegram.org/file/bot{os.getenv('bot')}/{file_path}"

    # Create response message with the combined identifier and download link
    response_text = f"File ID: {file_id}\nFile Size: {file_size} bytes\nFile Type: {file_type}\nFile Name: {file_name}\n"
    response_text += f"Use /file{unique_identifier} to retrieve this file later.\n"
    response_text += f"Download link: {download_link}"
    
    bot.reply_to(message, response_text)


@bot.message_handler(func=lambda message: message.text.startswith('/file'))
def handle_file_request(message):
    try:
        unique_identifier = message.text.split('/file')[1]
        file_entry = log.find_one({"unique_identifier": unique_identifier})

        if file_entry:
            file_id = file_entry["file_id"]
            bot.send_document(message.chat.id, file_id)
        else:
            bot.reply_to(message, "File not found.")
    except (ValueError, IndexError):
        bot.reply_to(message, "Invalid command format. Use /file<identifier> to retrieve a file.")


@bot.message_handler(commands=['all'])
def handle_all_files(message):
    try:
        all_files = log.find({}, {"unique_identifier": 1, "file_name": 1, "file_size": 1})

        if all_files:
            response_text = "All files:\n\n"
            for file_entry in all_files:
                unique_identifier = file_entry.get("unique_identifier", "N/A")
                file_name = file_entry.get("file_name", "N/A")
                file_size = file_entry.get("file_size", "N/A")

                response_text += f"/file{unique_identifier}: {file_name} - {file_size} bytes\n"

            bot.reply_to(message, response_text)
        else:
            bot.reply_to(message, "No files found.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

