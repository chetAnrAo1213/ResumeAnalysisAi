from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import google.generativeai as genai
import os
from datetime import datetime

app = Flask(__name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB configuration
client = MongoClient("mongodb://localhost:27017/")
db = client['Patients']
collection = db['Patient_Info']

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure the Google Gemini API
genai.configure(api_key="your Api Key")


def resume_format(file_path):
    """Prepares the resume file for Gemini API analysis."""
    mime_type = None

    # Set mime type for PDF or Word documents
    if file_path.endswith('.pdf'):
        mime_type = 'application/pdf'
    elif file_path.endswith('.doc') or file_path.endswith('.docx'):
        mime_type = 'application/msword'
    else:
        raise ValueError("Unsupported file format. Only PDF and DOC/DOCX are allowed.")

    # Upload the file to Gemini
    file = genai.upload_file(file_path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file


def get_resume_analysis(user_details, resume_path):
    """Generates resume analysis using Gemini AI."""
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-8b",
        generation_config=generation_config,
        system_instruction="You are a Resume Analyzer. Analyze the resume file and provide strengths, "
                           "weaknesses, suggestions, and an ATS score (0-100). If irrelevant data is found,"
                           " say 'Couldn't analyze data'."
    )

    # Upload the resume file
    resume_file = resume_format(resume_path)

    # Create a chat session and send the resume for analysis
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [resume_file],
            }
        ]
    )

    response = chat_session.send_message("Please analyze this resume and provide feedback.")
    return response.text


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Collect form data
        user_details = {
            'name': request.form['name'],
            'rollNo': request.form['rollNo'],
            'class': request.form['class'],
            'section': request.form['section'],
            'college': request.form['college'],
            'timestamp': datetime.now()
        }

        # Handle resume file upload
        file = request.files['resume']
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Analyze resume using Gemini API
            suggestions = get_resume_analysis(user_details, file_path)

            # Store the user data and analysis result in MongoDB
            user_details['analysis'] = suggestions
            collection.insert_one(user_details)

            # Render the results with analysis suggestions
            return render_template('Results.html', suggestions=suggestions)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
