from flask_restful import Resource
from flask import request
import logging
import jwt
from data.config import jwtSecretKey
from data import db

class CategoriesWithCards(Resource):
    """
    GET /api/categories/with_cards
      Возвращает список всех категорий, у каждой до 10 карточек (cards).
      Пример результата:
      [
        {
          "categoryId": 1,
          "categoryName": "Category A",
          "cards": [
            {...}, {...}, ... (до 10)
          ]
        },
        {
          "categoryId": 2,
          "categoryName": "Category B",
          "cards": [...]
        },
        ...
      ]
    """
    def get(self):
        # Получаем все категории
        categories = db.Categories.getAllCategories()
        result = []

        for cat in categories:
            catId = cat["categoryId"]
            catName = cat["categoryName"]

            cards = db.Cards.getCards({"categoryId":catId}, perPage=10)

            for c in cards:
                if "createdAt" in c and c["createdAt"] is not None:
                    c["createdAt"] = str(c["createdAt"])
                if "updatedAt" in c and c["updatedAt"] is not None:
                    c["updatedAt"] = str(c["updatedAt"])

            result.append({
                "categoryId": catId,
                "categoryName": catName,
                "cards": cards
            })

        return result, 200