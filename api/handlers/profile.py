from flask_restful import Resource, reqparse
from flask import request
import logging
import jwt
import os
from werkzeug.utils import secure_filename
from data.config import jwtSecretKey
from data import db

UPLOAD_FOLDER_PROFILE = './uploads/profile/'  # Папка для сохранения аватарок

class Profile(Resource):
    """
    GET /api/profile
      Возвращает профиль пользователя и его карточки.

    PUT /api/profile
      Обновление профиля (partial update):
         - fullName (опционально)
         - avatar (файл, опционально)
      Если поле не передано, оно сохраняется без изменений.
      Заголовок: Authorization: <token>
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
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message": "Invalid payload (no userId)"}, 401

        userRow = db.Users.getUserById(userId)
        if not userRow:
            return {"message": "Пользователь не найден"}, 404

        userCards = db.Cards.getCards(filters={"userId": userId})
        return {
            "userId": userRow['userId'],
            "email": userRow['email'],
            "fullName": userRow['fullName'],
            "avatar": userRow['avatar'],
            "emailConfirmation": userRow.get("emailConfirmation", 0),
            "createdAt": str(userRow['createdAt']),
            "cards": userCards
        }, 200

    def put(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message": "Invalid or expired token"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message": "Invalid token payload"}, 401

        # Получаем текущие данные пользователя, чтобы сохранить не обновляемые поля
        userRow = db.Users.getUserById(userId)
        if not userRow:
            return {"message": "Пользователь не найден"}, 404

        # Получаем данные из form-data
        # Если fullName не передано, используем текущее значение
        fullName = request.form.get('fullName', '').strip() or userRow['fullName']

        # Проверяем, передан ли файл аватара
        avatarFile = request.files.get('avatar')
        avatarUrl = None
        if avatarFile:
            if not os.path.exists(UPLOAD_FOLDER_PROFILE):
                os.makedirs(UPLOAD_FOLDER_PROFILE, exist_ok=True)
            filename = secure_filename(avatarFile.filename)
            # Уникальное имя можно сформировать, например, по userId и timestamp
            import time
            uniqueName = f"{userId}_{int(time.time())}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER_PROFILE, uniqueName)
            avatarFile.save(filepath)
            avatarUrl = f"/uploads/profile/{uniqueName}"
        else:
            # Если файл не передан, сохраняем текущее значение
            avatarUrl = userRow['avatar']

        # Обновляем профиль в базе
        updated = db.Users.updateProfile(userId, fullName, avatarUrl)
        if not updated:
            return {"message": "Ошибка при обновлении профиля"}, 500

        logging.info(f"Пользователь {userId} обновил профиль: fullName='{fullName}', avatar='{avatarUrl}'")
        return {"message": "Профиль успешно обновлён"}, 200
