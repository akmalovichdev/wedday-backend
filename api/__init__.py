from flask import Flask, request, send_from_directory, abort
from flask_restful import Api, Resource, reqparse
import logging
from data.db import time
import jwt
import bcrypt
from data.config import jwtSecretKey
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, filename=f'logs/{time.getNowDate()}.log', filemode='a',
                    format='%(name)s - %(levelname)s - %(message)s', encoding='utf-8')

app = Flask(__name__)
CORS(app)
api = Api(app)