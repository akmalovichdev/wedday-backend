from flask_restful import Resource, reqparse
from flask import request
import logging
import jwt
from data.config import jwtSecretKey
from data import db

class Favorites(Resource):
    """
    API для работы с избранными карточками:
      POST /api/favorites   -> добавить карточку в избранное
      GET /api/favorites    -> получить список избранного пользователя
      DELETE /api/favorites -> удалить карточку из избранного

    Для всех методов требуется JWT-токен в заголовке Authorization.
    """

    def post(self):
        """
        Добавляет карточку в избранное.
        JSON:
        {
          "cardId": 123
        }
        Заголовок:
          Authorization: Bearer <token>
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

        userId = payload.get('userId')
        parser = reqparse.RequestParser()
        parser.add_argument('cardId', type=int, required=True, help='cardId is required')
        args = parser.parse_args()
        cardId = args['cardId']

        success = db.FavoritesDB.addFavorite(userId, cardId)
        if not success:
            return {"message": "Failed to add favorite. It might already exist."}, 500

        logging.info(f"Пользователь {userId} добавил карточку {cardId} в избранное")
        return {"message": "Card added to favorites"}, 201

    def get(self):
        """
        Получает список избранных карточек для текущего пользователя.
        Заголовок:
          Authorization: Bearer <token>
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

        userId = payload.get('userId')
        favorites = db.FavoritesDB.getFavorites(userId)
        return favorites, 200

    def delete(self):
        """
        Удаляет карточку из избранного.
        JSON:
        {
          "cardId": 123
        }
        Заголовок:
          Authorization: Bearer <token>
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

        userId = payload.get('userId')
        parser = reqparse.RequestParser()
        parser.add_argument('cardId', type=int, required=True, help='cardId is required')
        args = parser.parse_args()
        cardId = args['cardId']

        success = db.FavoritesDB.removeFavorite(userId, cardId)
        if not success:
            return {"message": "Failed to remove favorite"}, 500

        logging.info(f"Пользователь {userId} удалил карточку {cardId} из избранного")
        return {"message": "Favorite removed"}, 200
