from flask_restful import Resource, reqparse
import logging
from flask import request
import jwt
from data.config import jwtSecretKey
from data import db

class Tariffs(Resource):
    """
    GET /api/tariffs    -> Получить список всех тарифов
    POST /api/tariffs   -> Добавить тариф
    PUT /api/tariffs    -> Обновить тариф
    DELETE /api/tariffs -> Удалить тариф
    """

    def get(self):
        # Можно проверять авторизацию, если хотите. Пример:
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except:
            return {"message": "Invalid token"}, 401

        tariffs = db.TariffsDB.getAllTariffs()
        result = []
        for row in tariffs:
            if "createdAt" in row and row["createdAt"] is not None:
                row["createdAt"] = str(row["createdAt"])
            result.append(row)

        return result, 200

    def post(self):
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except:
            return {"message": "Invalid token"}, 401

        data = request.get_json()
        if not data:
            return {"message": "No input data"}, 400
        # Пример
        tariffName = data.get('tariffName','').strip()
        minPhones = data.get('minPhones',1)
        maxPhones = data.get('maxPhones',1)
        minSocials = data.get('minSocials',0)
        maxSocials = data.get('maxSocials',1)
        minPhotos = data.get('minPhotos',1)
        maxPhotos = data.get('maxPhotos',1)
        maxDesc = data.get('maxDescriptionLength',200)
        websiteAllowed = data.get('websiteAllowed',0)

        tariffId = db.TariffsDB.createTariff(tariffName, minPhones, maxPhones, minSocials, maxSocials,
                                             minPhotos, maxPhotos, maxDesc, websiteAllowed)
        if not tariffId:
            return {"message":"Failed to create tariff"}, 500
        logging.info(f"Создан тариф {tariffName} (tariffId={tariffId})")
        return {"message":"Tariff created","tariffId":tariffId}, 201

    def put(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except:
            return {"message": "Invalid token"}, 401

        data = request.get_json()
        if not data:
            return {"message":"No input data"}, 400
        tariffId = data.get('tariffId')
        if not tariffId:
            return {"message":"tariffId is required"}, 400

        # Пример обновления
        updateData = {}
        if 'tariffName' in data:
            updateData['tariffName'] = data['tariffName']
        if 'minPhones' in data:
            updateData['minPhones'] = data['minPhones']
        if 'maxPhones' in data:
            updateData['maxPhones'] = data['maxPhones']
        if 'minSocials' in data:
            updateData['minSocials'] = data['minSocials']
        if 'maxSocials' in data:
            updateData['maxSocials'] = data['maxSocials']
        if 'minPhotos' in data:
            updateData['minPhotos'] = data['minPhotos']
        if 'maxPhotos' in data:
            updateData['maxPhotos'] = data['maxPhotos']
        if 'maxDescriptionLength' in data:
            updateData['maxDescriptionLength'] = data['maxDescriptionLength']
        if 'websiteAllowed' in data:
            updateData['websiteAllowed'] = data['websiteAllowed']

        ok = db.TariffsDB.updateTariff(tariffId, **updateData)
        if not ok:
            return {"message":"Failed to update tariff"}, 500
        logging.info(f"Обновлён тариф (tariffId={tariffId})")
        return {"message":"Tariff updated"}, 200

    def delete(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except:
            return {"message":"Invalid token"}, 401

        data = request.get_json()
        if not data:
            return {"message":"No input data"}, 400
        tariffId = data.get('tariffId')
        if not tariffId:
            return {"message":"tariffId is required"}, 400

        ok = db.TariffsDB.deleteTariff(tariffId)
        if not ok:
            return {"message":"Failed to delete tariff"}, 500
        logging.info(f"Удалён тариф (tariffId={tariffId})")
        return {"message":"Tariff deleted"}, 200