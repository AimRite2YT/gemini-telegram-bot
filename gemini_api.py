# Файл: gemini_api.py

import google.generativeai as genai
from config import GEMINI_API_KEY, DEFAULT_SYSTEM_PROMPT

genai.configure(api_key=GEMINI_API_KEY)

# Доступные модели
AVAILABLE_MODELS = {
    'gemini-2.5-flash': 'gemini-2.5-flash-preview-05-20',
    'gemini-2.0-flash': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-1.5-pro-latest',
    'gemini-1.5-flash': 'gemini-1.5-flash-latest',
}

# Текущая модель (глобальная)
current_model_key = 'gemini-2.5-flash'
model = genai.GenerativeModel(AVAILABLE_MODELS[current_model_key])


def generate_gemini_response(prompt: str, system_prompt: str = None) -> str:
    """Генерирует текстовый ответ от Gemini."""
    try:
        sys_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        full_prompt = f"System: {sys_prompt}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"❌ Ошибка Gemini: {e}"


def generate_gemini_vision_response(prompt: str, image_data: bytes, mime_type: str = "image/jpeg", system_prompt: str = None) -> str:
    """Генерирует ответ от Gemini на основе изображения + текста."""
    try:
        import google.generativeai as genai_vision
        vision_model = genai_vision.GenerativeModel(AVAILABLE_MODELS[current_model_key])
        
        image_part = {
            "mime_type": mime_type,
            "data": image_data
        }
        sys_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        full_prompt = prompt if prompt else "Опиши это изображение подробно."
        content = [f"System: {sys_prompt}\n\nUser: {full_prompt}", image_part]
        
        response = vision_model.generate_content(content)
        return response.text
    except Exception as e:
        return f"❌ Ошибка обработки изображения: {e}"


def set_gemini_model(model_key: str) -> str:
    """Меняет активную модель Gemini."""
    global model, current_model_key
    
    # Поддерживаем и короткие ключи и полные названия
    if model_key in AVAILABLE_MODELS:
        current_model_key = model_key
        model = genai.GenerativeModel(AVAILABLE_MODELS[model_key])
        return f"✅ Модель изменена на: `{model_key}` ({AVAILABLE_MODELS[model_key]})"
    
    # Проверяем по полному названию
    for key, full_name in AVAILABLE_MODELS.items():
        if model_key == full_name:
            current_model_key = key
            model = genai.GenerativeModel(full_name)
            return f"✅ Модель изменена на: `{key}` ({full_name})"
    
    models_list = "\n".join([f"• `{k}` — {v}" for k, v in AVAILABLE_MODELS.items()])
    raise ValueError(f"❌ Модель `{model_key}` не найдена.\n\nДоступные модели:\n{models_list}")


def get_current_model() -> str:
    """Возвращает название текущей модели."""
    return current_model_key


def get_models_list() -> dict:
    """Возвращает словарь доступных моделей."""
    return AVAILABLE_MODELS
