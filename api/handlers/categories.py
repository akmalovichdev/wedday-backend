from flask_restful import Resource, reqparse
from flask import request
import logging
import jwt
from data.config import jwtSecretKey
from data import db

class Categories(Resource):
    """
    POST /api/categories - Добавить категорию
    GET /api/categories - Получить список категорий
    PUT /api/categories - Обновить категорию
    DELETE /api/categories - Удалить категорию
    """

    def get(self):
        """
        Получить список всех категорий.
        GET /api/categories
        """
        categories = db.Categories.getAllCategories()
        return categories, 200

    def post(self):
        """
        Создать новую категорию.
        JSON:
        {
            "token": "<JWT>",
            "categoryName": "Photography"
        }
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

        data = request.get_json()
        if not data:
            return {"message": "No input data provided"}, 400

        categoryName = data.get('categoryName', '').strip()
        if not categoryName:
            return {"message": "categoryName is required"}, 400

        categoryId = db.Categories.addCategory(categoryName)
        if not categoryId:
            return {"message": "Failed to add category"}, 500

        logging.info(f"Добавлена категория categoryId={categoryId}, categoryName={categoryName}")
        return {"message": "Category added successfully", "categoryId": categoryId}, 201

    def put(self):
        """
        Обновить категорию.
        JSON:
        {
            "token": "<JWT>",
            "categoryId": 1,
            "categoryName": "Updated Name"
        }
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

        data = request.get_json()
        if not data:
            return {"message": "No input data provided"}, 400

        categoryId = data.get('categoryId')
        categoryName = data.get('categoryName', '').strip()
        if not categoryId or not categoryName:
            return {"message": "categoryId and categoryName are required"}, 400

        updated = db.Categories.updateCategory(categoryId, categoryName)
        if not updated:
            return {"message": "Failed to update category"}, 500

        logging.info(f"Обновлена категория categoryId={categoryId}, newName={categoryName}")
        return {"message": "Category updated successfully"}, 200

    def delete(self):
        """
        Удалить категорию.
        JSON:
        {
            "token": "<JWT>",
            "categoryId": 1
        }
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

        data = request.get_json()
        if not data:
            return {"message": "No input data provided"}, 400

        categoryId = data.get('categoryId')
        if not categoryId:
            return {"message": "categoryId is required"}, 400

        deleted = db.Categories.deleteCategory(categoryId)
        if not deleted:
            return {"message": "Failed to delete category"}, 500

        logging.info(f"Удалена категория categoryId={categoryId}")
        return {"message": "Category deleted successfully"}, 200
