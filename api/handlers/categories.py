from flask_restful import Resource, reqparse
from flask import request
import logging
import jwt
import os
from werkzeug.utils import secure_filename
from data.config import jwtSecretKey
from data import db

UPLOAD_FOLDER_CATEGORIES = './uploads/categories/'

class Categories(Resource):
    """
    POST /api/categories - Добавить категорию с логотипом (form-data)
    GET /api/categories - Получить список категорий
    PUT /api/categories - Обновить категорию (включая логотип) (form-data)
    DELETE /api/categories - Удалить категорию
    """

    def get(self):
        categories = db.Categories.getAllCategories()
        return categories, 200

    def post(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        # Используем form-data для возможности загрузки логотипа
        form = request.form
        categoryName = form.get('categoryName', '').strip()
        if not categoryName:
            return {"message": "categoryName is required"}, 400

        # Получаем логотип (файл) из form-data
        logoFile = request.files.get('logo')
        logoUrl = None
        if logoFile:
            if not os.path.exists(UPLOAD_FOLDER_CATEGORIES):
                os.makedirs(UPLOAD_FOLDER_CATEGORIES, exist_ok=True)
            filename = secure_filename(logoFile.filename)
            # Можно уникализировать имя, например, добавив categoryName или timestamp
            uniqueName = f"{categoryName}_{filename}"
            logoFile.save(os.path.join(UPLOAD_FOLDER_CATEGORIES, uniqueName))
            logoUrl = f"/uploads/categories/{uniqueName}"

        categoryId = db.Categories.addCategory(categoryName, logoUrl)
        if not categoryId:
            return {"message": "Failed to add category"}, 500

        logging.info(f"Добавлена категория categoryId={categoryId}, categoryName={categoryName}")
        return {"message": "Category added successfully", "categoryId": categoryId}, 201

    def put(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        # Используем form-data для обновления категории
        form = request.form
        categoryId = form.get('categoryId')
        categoryName = form.get('categoryName', '').strip()
        if not categoryId or not categoryName:
            return {"message": "categoryId and categoryName are required"}, 400

        logoFile = request.files.get('logo')
        logoUrl = None
        if logoFile:
            if not os.path.exists(UPLOAD_FOLDER_CATEGORIES):
                os.makedirs(UPLOAD_FOLDER_CATEGORIES, exist_ok=True)
            filename = secure_filename(logoFile.filename)
            uniqueName = f"{categoryId}_{filename}"
            logoFile.save(os.path.join(UPLOAD_FOLDER_CATEGORIES, uniqueName))
            logoUrl = f"/uploads/categories/{uniqueName}"

        updated = db.Categories.updateCategory(categoryId, categoryName, logoUrl)
        if not updated:
            return {"message": "Failed to update category"}, 500

        logging.info(f"Обновлена категория categoryId={categoryId}, newName={categoryName}")
        return {"message": "Category updated successfully"}, 200

    def delete(self):
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
