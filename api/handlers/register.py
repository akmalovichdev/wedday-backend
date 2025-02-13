from flask_restful import Resource, reqparse
import logging
import bcrypt
from data import db

class Register(Resource):
    """
    POST /api/register
    JSON:
    {
      "email": "user@example.com",
      "fullName": "Test User",
      "password": "Abc12345"
    }
    """
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, help='email is required')
        parser.add_argument('fullName', type=str, required=True, help='fullName is required')
        parser.add_argument('password', type=str, required=True, help='password is required')
        args = parser.parse_args()

        email = args['email'].strip().lower()
        fullName = args['fullName'].strip()
        password = args['password']

        # Минимальная проверка пароля
        if len(password) < 8:
            return {"message": "Пароль должен быть не менее 8 символов"}, 400
        if not any(ch.isupper() for ch in password):
            return {"message": "Должна быть хотя бы одна заглавная буква"}, 400
        if not any(ch.isdigit() for ch in password):
            return {"message": "Должна быть хотя бы одна цифра"}, 400

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Проверяем, нет ли уже такого email
        existingUser = db.Users.getUserByEmail(email)
        if existingUser:
            return {"message": "Такой email уже зарегистрирован"}, 400

        userId = db.Users.createUserWithData(email, fullName, hashed)
        if not userId:
            return {"message": "Ошибка при создании пользователя"}, 500

        logging.info(f"Создан пользователь userId={userId}, email={email}")
        return {"message": "Регистрация успешна", "userId": userId}, 201
