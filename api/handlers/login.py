from flask_restful import Resource, reqparse
import logging
import jwt
import bcrypt
from datetime import datetime, timedelta
from data.config import jwtSecretKey
from data import db

class Login(Resource):
    """
    POST /api/login
    JSON:
    {
      "email":"user@example.com",
      "password":"Abc12345"
    }
    Возвращает JWT-токен в поле token.
    """
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, help='Email is required')
        parser.add_argument('password', type=str, required=True, help='Password is required')
        args = parser.parse_args()

        email = args['email'].strip().lower()
        password = args['password']

        userRow = db.Users.getUserByEmail(email)
        if not userRow:
            return {"message": "Неверный логин или пароль"}, 400

        storedHash = userRow['password'].encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), storedHash):
            return {"message": "Неверный логин или пароль"}, 400

        # Генерируем JWT
        payload = {
            "userId": userRow['userId'],
            "email": userRow['email'],
            "exp": datetime.utcnow() + timedelta(days=1)  # токен живёт 1 день
        }
        token = jwt.encode(payload, jwtSecretKey, algorithm="HS256")

        logging.info(f"Пользователь userId={userRow['userId']} вошёл в систему.")
        return {"message": "Авторизация успешна", "token": token}, 200
