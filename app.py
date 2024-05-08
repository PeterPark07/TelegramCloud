import os
from flask import Flask, request, render_template
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







UPLOAD_FOLDER = 'uploads'  # Directory to save uploaded file
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extract_file_info(document):
    file_id = document.file_id
    file_size = document.file_size
    file_type = document.mime_type
    file_name = document.file_name if document.file_name else "Not available"
    return file_id, file_size, file_type, file_name

# Function to send the file to the chat
def send_file_to_chat(chat_id, file_path):
    with open(file_path, 'rb') as file:
        sent = bot.send_document(chat_id, file)

        info = sent.document

        print(sent)
        
        return extract_file_info(info)




# Flask route to render the upload form
@app.route('/u')
def upload_page():
    return render_template('upload.html')

# Flask route to render the file manager page
@app.route('/files')
def file_manager():
    files = list(log.find({}, {"file_name": 1, "file_size": 1, "unique_identifier": 1}))
    return render_template('file_manager.html', files=files)

# Flask route to handle file deletion
@app.route('/delete/<unique_identifier>', methods=['POST'])
def delete_file(unique_identifier):
    try:
        # Delete the file from the log database
        delete_result = log.delete_one({"unique_identifier": unique_identifier})
        
        # Check if the deletion was successful
        if delete_result.deleted_count > 0:
            # Update file manager page after successful deletion
            return "File deleted successfully"
        else:
            return "File not found"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


# Flask route to handle file upload
@app.route('/upload', methods=['POST'])
def upload_files():
    # Check if request contains files
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)

    files = request.files.getlist('image')

    # Check if any file is selected
    if len(files) == 0:
        flash('No selected file')
        return redirect(request.url)

    s = 0
    errors = ''
    for file in files:
        try:
            # Create uploads directory if it doesn't exist
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
    
            # Save the file to the uploads directory
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
    
            # Specify the chat ID where you want to send the file
            chat_id = -4246785178
            
            # Send the file to the chat using the Telegram bot
            file_id, file_size, file_type, file_name = send_file_to_chat(chat_id, file_path)
        
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
        
            # Generate download link
            download_link = f"https://api.telegram.org/file/bot{os.getenv('bot')}/{file_info.file_path}"
    
            # Create response message with the combined identifier and download link
            response_text = f"File Name: {file_name}\nFile Size: {file_size} bytes\nFile Type: {file_type}\n"
            response_text += f"Use /file{unique_identifier} to retrieve this file later.\n"
            response_text += f"Download link: {download_link}"
    
            # Send the response message to the user
            bot.send_message(chat_id, response_text)
            
            s+=1
    
            # Delete the file after sending
            os.remove(file_path)
            
        except Exception as e:
            errors += f"An error occurred: {str(e)}\n\n"
    return f'{s} files uploaded successfully.' + '\n\n' + errors

  

    








# Handler for document messages
@bot.message_handler(content_types=['document'])
def handle_document(message):
    document = message.document

    # Extract information from the document
    file_id, file_size, file_type, file_name = extract_file_info(document)

    if (file_size//1024)//1024 > 20:
        bot.reply_to(message, "file too big")
        return

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
    response_text = f"File Name: {file_name}\nFile Size: {file_size} bytes\nFile Type: {file_type}\n"
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

# Handler for the '/delete' command
@bot.message_handler(func=lambda message: message.text.startswith('/delete'))
def delete_file(message):
    try:
        unique_identifier = message.text.split('/delete')[1].strip()
        delete_result = log.delete_one({"unique_identifier": unique_identifier})
        deleted_count = delete_result.deleted_count
        if deleted_count > 0:
            bot.reply_to(message, f"{deleted_count} file log(s) deleted successfully.")
        else:
            bot.reply_to(message, "File log not found.")
    except IndexError:
        bot.reply_to(message, "Invalid command format. Use /delete <identifier> to delete a file log.")

@bot.message_handler(commands=['all'])
def handle_all_files(message):
    try:
        all_files = log.find({}, {"unique_identifier": 1, "file_name": 1, "file_size": 1})
        file_list = list(all_files)
        total_files_count = len(file_list)
        bot.send_message(message.chat.id ,f"All files ({total_files_count}):\n\n" + str(message.chat.id))

        if file_list:
            i = 0
            response_text = "-\n"
            for file_entry in file_list :
                unique_identifier = file_entry.get("unique_identifier", "N/A")
                file_name = file_entry.get("file_name", "N/A")
                file_size_bytes = file_entry.get("file_size", "N/A")
                file_size = (file_size_bytes//1024) + 1

                # Create clickable delete link
                delete_link = f"/delete{unique_identifier}"


                response_text += f"/file{unique_identifier}: {file_name} - {file_size} kb\nDelete: {delete_link}\n\n"
                i += 1

                if i % 10 == 0 or i == total_files_count:
                    bot.reply_to(message, response_text)
                    time.sleep(0.5)
                    response_text = ""

            bot.reply_to(message, "File listing complete.")
        else:
            bot.reply_to(message, "No files found.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")


@bot.message_handler(commands=['reset_7363'])
def delete_all_files(message):
    try:
        delete_result = log.delete_many({"unique_identifier": {"$exists": True}, "file_name": {"$exists": True}, "file_size": {"$exists": True}})
        deleted_count = delete_result.deleted_count
        bot.reply_to(message, f"{deleted_count} file log(s) deleted successfully.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

@bot.message_handler(commands=['count'])
def count_all_files(message):
    try:
        all_files = log.find({}, {"unique_identifier": 1, "file_name": 1, "file_size": 1})
        file_list = list(all_files)
        total_files_count = len(file_list)
        bot.reply_to(message ,f"Total files - ({total_files_count})")
    except:
        bot.reply_to(message ,"Can't retrieve count")
