from flask_restful import Resource
from flask import request
import logging
import jwt
from data.config import jwtSecretKey
from data import db

class Profile(Resource):
    """
    GET /api/profile
    Заголовок:
    Authorization: <JWT>
    """
    def get(self):
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
            logging.info(f"Payload из токена: {payload}")
        except jwt.ExpiredSignatureError:
            logging.warning('Срок действия токена истёк')
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning('Недействительный токен')
            return {"message": "Invalid token"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message": "Invalid payload (no userId)"}, 401

        userRow = db.Users.getUserById(userId)
        if not userRow:
            return {"message": "Пользователь не найден"}, 404

        # Пример ответа
        return {
            "userId": userRow['userId'],
            "email": userRow['email'],
            "fullName": userRow['fullName'],
            "avatar": userRow['avatar'],
            "emailConfirmation": userRow['emailConfirmation'],
            "createdAt": str(userRow['createdAt'])
        }, 200
