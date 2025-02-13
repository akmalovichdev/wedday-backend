from flask_restful import Resource
from flask import request
import logging
import jwt
from data.config import jwtSecretKey
from data import db

class Cards(Resource):
    """
    POST /api/cards   -> создать карточку
    GET /api/cards?cardId=... -> получить карточку
    PUT /api/cards    -> обновить
    DELETE /api/cards -> удалить
    Все действия требуют JWT-токен в заголовке Authorization
    """

    def post(self):
        """
        Создание карточки.
        JSON:
        {
          "categoryId": 1,
          "cardName": "My Card",
          "description": "Some desc",
          "address": "Tashkent",
          "locationLat": 41.123,
          "locationLng": 69.123,
          "website": "https://example.com",
          "phoneNumbers": ["+998900001111","+998900002222"],
          "socialMedias": [
            {"socialType":"instagram","socialLink":"https://instagram.com/..."}
          ]
        }
        Заголовок: Authorization: <JWT>
        """
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

        data = request.get_json(silent=True)
        if not data:
            return {"message": "No input data"}, 400

        categoryId = data.get('categoryId')
        cardName = data.get('cardName','').strip()
        description = data.get('description','')
        address = data.get('address','')
        locationLat = data.get('locationLat')
        locationLng = data.get('locationLng')
        website = data.get('website','')

        phoneNumbers = data.get('phoneNumbers', [])
        socialMedias = data.get('socialMedias', [])

        # Лимиты
        if len(phoneNumbers) > 3:
            return {"message": "Максимум 3 номера телефона"}, 400
        if len(socialMedias) > 4:
            return {"message": "Максимум 4 соцсети"}, 400

        cardId = db.Cards.addCard(
            userId, categoryId, cardName, description, address,
            locationLat, locationLng, website
        )
        if not cardId:
            return {"message": "Ошибка при создании карточки"}, 500

        # Добавляем номера
        if not db.Cards.addPhoneNumbers(cardId, phoneNumbers):
            return {"message": "Ошибка при добавлении номеров"}, 500

        # Добавляем соцсети
        if not db.Cards.addSocialMedia(cardId, socialMedias):
            return {"message": "Ошибка при добавлении соцсетей"}, 500

        logging.info(f"Пользователь {userId} создал карточку {cardId}")
        return {"message":"Карточка успешно создана","cardId":cardId}, 201

    def get(self):
        """
        GET /api/cards?cardId=...
        Заголовок: Authorization: <JWT>
        """
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        cardId = request.args.get('cardId')
        if not cardId:
            return {"message":"Parameter cardId is required"}, 400

        cardData = db.Cards.getCardById(int(cardId))
        if not cardData:
            return {"message":"Карточка не найдена"}, 404

        return cardData, 200

    def put(self):
        """
        Обновление карточки (может изменить только владелец).
        JSON:
        {
          "cardId":123,
          "cardName":"Updated",
          "description":"New desc",
          "address":"New address",
          "locationLat":40.1,
          "locationLng":70.1,
          "website":"https://updated.com"
        }
        Заголовок: Authorization: <JWT>
        """
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        userId = payload.get('userId')

        data = request.get_json(silent=True)
        if not data:
            return {"message":"No input data"}, 400

        cardId = data.get('cardId')
        if not cardId:
            return {"message":"cardId is required"}, 400

        cardName = data.get('cardName','')
        description = data.get('description','')
        address = data.get('address','')
        locationLat = data.get('locationLat')
        locationLng = data.get('locationLng')
        website = data.get('website','')

        updated = db.Cards.updateCard(userId, cardId, cardName, description, address, locationLat, locationLng, website)
        if not updated:
            # либо карточка не найдена, либо не принадлежит этому userId
            return {"message":"Ошибка при обновлении (не ваша карточка или не найдена)."}, 400

        logging.info(f"Пользователь {userId} обновил карточку {cardId}")
        return {"message":"Карточка обновлена"}, 200

    def delete(self):
        """
        Удаление карточки (только владелец).
        JSON:
        {
          "cardId":123
        }
        Заголовок: Authorization: <JWT>
        """
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message":"Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message":"Invalid token"}, 401

        userId = payload.get('userId')

        data = request.get_json(silent=True)
        if not data:
            return {"message":"No input data"}, 400

        cardId = data.get('cardId')
        if not cardId:
            return {"message":"cardId is required"}, 400

        deleted = db.Cards.deleteCard(userId, cardId)
        if not deleted:
            return {"message":"Ошибка при удалении (не ваша карточка или не найдена)."}, 400

        logging.info(f"Пользователь {userId} удалил карточку {cardId}")
        return {"message":"Карточка удалена"}, 200
