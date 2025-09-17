<!-- ABOUT THE PROJECT -->
## About The Project


Этот проект был создан с помощью gemini, да , бот норм работает можно делать всё с ним давать пропмт и тд

Что там есть:
* Там есть система моделей на выбор /model [модель]
* Есть запись запросов которые участники задают боту
* Можно добавить или поменять API ключ и Telegram Bot Token

Конечно же бот почти сырой, там очень мало функций. Но я постараюсь добавить всё нужное туда.


<!-- Начало -->
## Начать

Чтобы бот работал корректно нужно скачать requirments-ы

### Модули

Нужно скачать эти требования:
* telebot
  ```python
  pip install telebot
  ```

  ```python
  pip install generativeai
  ```



### Установка

_Ниже предоставлены комманды для получения скрипта запуска gemini для телеграмма_

1. Получите API Key at [AI-Studio](https://aistudio.google.com/app/apikey)
2. Сколнируйте репозиторий
   ```sh
   git clone https://github.com/AimRite2YT/gemini-telegram-bot.git
   ```
3. Введи свой API ключ в `config.json`
   ```js
   GEMINI_API_KEY = 'ENTER YOUR API';
   ```
4. Создайте бота через специального бота @BotFather скопируйте токен и вставьте его сюда:
   ```telegram
   TELEGRAM_BOT_TOKEN = 'ENTER YOUR TOKEN'
   ```
5. Запустите скрипт
   ```bash
   python telegram_bot.py
   ```
