from flask import Flask
from flask_restful import Api
from flask_cors import CORS
import logging
from datetime import datetime
import os
import traceback
from flask import jsonify

# Создаём папку logs, если не существует
if not os.path.exists("logs"):
    os.makedirs("logs")

# logging.basicConfig(
#     level=logging.INFO,
#     filename=f'logs/{datetime.now().strftime("%Y-%m-%d")}.log',
#     filemode='a',
#     format='%(name)s - %(levelname)s - %(message)s',
#     encoding='utf-8'
# )

app = Flask(__name__)
CORS(app)
api = Api(app)

@app.errorhandler(Exception)
def handle_exception(e):
    """
    Глобальный обработчик всех неперехваченных исключений.
    Возвращает единый JSON-ответ вместо HTML-трейсбека.
    """
    logging.error(f"Global exception caught: {e}")
    # Для безопасности можно не возвращать e.__str__()
    # Но если нужно отладить, можно добавить e.__str__() или traceback.format_exc().
    return jsonify({
        "message": "На сервере произошла ошибка, пожалуйста обратитесь к разработчику",
        "error": str(e),  # или уберите для продакшна
        "status": False
    }), 500