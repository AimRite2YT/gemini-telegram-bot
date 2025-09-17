# Файл: gemini_api.py
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# Доступные модели (добавь сюда все модели, которые ты хочешь поддерживать)
available_models = {
    'gemini-2.5-flash-preview-05-20': 'gemini-2.5-flash-preview-05-20',
    'gemini-2.0-flash': 'gemini-2.0-flash', # Пример другой модели
    'gemini-1.5-pro-latest': 'gemini-1.5-pro-latest'
}

model_name = 'gemini-2.5-flash-preview-05-20' # Изначальная модель
model = genai.GenerativeModel(model_name)

def generate_gemini_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def set_gemini_model(new_model_name):
    global model, model_name # Используем global для изменения глобальной переменной
    if new_model_name in available_models:
        model_name = new_model_name
        model = genai.GenerativeModel(model_name)
        return f"Модель изменена на {model_name}."
    else:
        raise ValueError(f"Модель {new_model_name} не найдена. Доступные модели: {', '.join(available_models.keys())}")
