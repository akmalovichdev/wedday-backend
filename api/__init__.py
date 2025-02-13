from flask import Flask
from flask_restful import Api
from flask_cors import CORS
import logging
from datetime import datetime
import os

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
