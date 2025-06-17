from flask import Flask, render_template, request, jsonify
import json
import requests
import pickle
import numpy as np
from tensorflow import keras
import re
import warnings
import os

warnings.filterwarnings("ignore")

app = Flask(__name__)

# Use your Gemini API key here (or use an environment variable)
api_key = 'AIzaSyCA-PNvXQpLMy4Y5cLA8dHO5xcj3pUDQ2M'  # 🔒 Replace with your actual key or load from env

# Load intents
with open('intents.json') as file:
    data = json.load(file)

# Load trained model
model = keras.models.load_model('chat-model.keras')

# Load tokenizer and label encoder
with open('tokenizer.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)

with open('label_encoder.pickle', 'rb') as enc:
    lbl_encoder = pickle.load(enc)

# Text processing parameters
max_len = 20

def clean_response(text):
    """Clean the chatbot response."""
    if not text:
        return text
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'^[#\-*].*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('**', '').replace('__', '')
    if text and text[-1] not in {'.', '!', '?'}:
        text += '.'
    text = text[0].upper() + text[1:] if text else text
    return text

def get_gemini_response(user_input):
    """Call Gemini API with summarizing instruction."""
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
    headers = {'Content-Type': 'application/json'}

    # 🔽 Modified prompt to instruct for concise answer
    prompt = f"Answer in 1–2 short sentences: {user_input}"

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response_data = response.json()
        if 'candidates' in response_data:
            raw_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return clean_response(raw_response)
        return None
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    user_input = request.form['user_input'].strip()

    if not user_input:
        return jsonify({'response': "Please type something so I can help you."})

    if user_input.lower() == "who made you":
        return jsonify({'response': "I was developed by Gatik to help with emotional support."})

    # Predict tag using model
    result = model.predict(keras.preprocessing.sequence.pad_sequences(
        tokenizer.texts_to_sequences([user_input]), truncating='post', maxlen=max_len))
    tag = lbl_encoder.inverse_transform([np.argmax(result)])

    # Get concise Gemini reply
    response = get_gemini_response(user_input)

    # Fallback if no Gemini response
    if not response:
        if tag[0] == 'greeting':
            response = "Hello! How can I support you today?"
        elif tag[0] == 'goodbye':
            response = "Take care. I'm here if you need to talk."
        else:
            response = "I'm here to listen. Tell me more."

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
