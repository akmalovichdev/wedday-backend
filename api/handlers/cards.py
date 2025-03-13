from flask_restful import Resource
from flask import request
import logging
import jwt
import os
import json
from werkzeug.utils import secure_filename
from data.config import jwtSecretKey
from data import db

UPLOAD_FOLDER = './uploads/cards/'  # Папка, куда сохраняем фото

class Cards(Resource):
    """
    POST /api/cards      -> Создание карточки
    GET /api/cards       -> Получение карточек с фильтрами:
                              - ?cardId=... (конкретная карточка)
                              - ?categoryId=... (по категории)
                              - ?userId=... (по пользователю)
                              - ?myCards=true (только мои карточки, определяется по токену)
    PUT /api/cards       -> Полное обновление карточки (form-data)
    DELETE /api/cards    -> Удаление карточки (JSON: { "cardId": ... })
    Authorization: <token>  (в заголовке, токен передается как есть)
    """

    def post(self):
        # 1) Проверка токена
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message": "Invalid or expired token"}, 401
        userId = payload.get('userId')
        if not userId:
            return {"message": "Invalid token payload"}, 401

        # 2) Считываем поля формы
        form = request.form
        tariff = form.get('tariff', 'basic').lower()
        categoryId = form.get('categoryId')
        cardName = form.get('cardName','').strip()
        description = form.get('description','')
        address = form.get('address','')
        locationLat = form.get('locationLat')
        locationLng = form.get('locationLng')
        website = form.get('website','')

        phoneNumbers = request.form.getlist('phoneNumbers')
        socialMedias_str_list = request.form.getlist('socialMedias')
        socialMedias = []
        for s in socialMedias_str_list:
            try:
                sm = json.loads(s)
                socialMedias.append(sm)
            except:
                pass
        photos = request.files.getlist('photos')

        # 3) Валидация тарифа
        if tariff not in ['basic','premium']:
            return {"message": "tariff must be 'basic' or 'premium'"}, 400
        if not categoryId:
            return {"message": "categoryId is required"}, 400
        if not cardName:
            return {"message": "cardName is required"}, 400
        if not description:
            return {"message": "description is required"}, 400
        if not address:
            return {"message": "address is required"}, 400

        maxDesc = 400 if tariff == 'premium' else 200
        if len(description) > maxDesc:
            return {"message": f"Описание превышает лимит {maxDesc} символов для тарифа {tariff}"}, 400
        if tariff == 'basic' and website:
            return {"message": "Website доступен только в тарифе premium"}, 400

        if tariff == 'basic':
            if len(phoneNumbers) != 1:
                return {"message": "Для тарифа basic нужен ровно 1 номер телефона"}, 400
        else:
            if not (1 <= len(phoneNumbers) <= 3):
                return {"message": "Для тарифа premium нужно от 1 до 3 номеров телефона"}, 400

        maxSocials = 1 if tariff == 'basic' else 4
        if len(socialMedias) > maxSocials:
            return {"message": f"Максимум {maxSocials} соцсетей для тарифа {tariff}"}, 400

        if tariff == 'basic':
            if len(photos) != 1:
                return {"message": "Для тарифа basic нужно ровно 1 фото"}, 400
        else:
            if not (1 <= len(photos) <= 5):
                return {"message": "Для тарифа premium нужно от 1 до 5 фото"}, 400

        latVal = float(locationLat) if locationLat else None
        lngVal = float(locationLng) if locationLng else None
        catId = int(categoryId)

        # 5) Создаём запись в БД
        cardId = db.Cards.addCard(
            userId=userId,
            categoryId=catId,
            cardName=cardName,
            description=description,
            address=address,
            locationLat=latVal,
            locationLng=lngVal,
            website=website,
            tariff=tariff
        )
        if not cardId:
            return {"message": "Ошибка при создании карточки"}, 500

        if not self._overwritePhones(cardId, phoneNumbers):
            return {"message": "Ошибка при добавлении телефонов"}, 500
        if not self._overwriteSocials(cardId, socialMedias):
            return {"message": "Ошибка при добавлении соцсетей"}, 500

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        photoUrls = []
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, uniqueName)
            file.save(filepath)
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)
        if not self._overwritePhotos(cardId, photoUrls):
            return {"message": "Ошибка при сохранении фото"}, 500

        logging.info(f"[userId={userId}] Создал карточку cardId={cardId}, тариф={tariff}")
        return {"message": "Карточка успешно создана", "cardId": cardId}, 201

    def get(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message": "Invalid or expired token"}, 401

        # Фильтры: можно передать cardId, categoryId, userId, myCards, а также параметры пагинации: page, perPage
        cardId = request.args.get('cardId')
        categoryId = request.args.get('categoryId')
        filterUserId = request.args.get('userId')
        myCards = request.args.get('myCards')

        # Если myCards=true, берем userId из токена
        if myCards and myCards.lower() == "true":
            filterUserId = payload.get('userId')

        # Параметры пагинации
        try:
            page = int(request.args.get('page', 1))
            perPage = int(request.args.get('perPage', 25))
        except ValueError:
            return {"message": "page and perPage must be integers"}, 400

        if cardId:
            cardData = db.Cards.getCardById(int(cardId))
            if not cardData:
                return {"message": "Карточка не найдена"}, 404
            return cardData, 200
        else:
            filters = {}
            if categoryId:
                filters['categoryId'] = int(categoryId)
            if filterUserId:
                filters['userId'] = int(filterUserId)
            result = db.Cards.getCards(filters, page=page, perPage=perPage)
            # result имеет формат: {"pages": pages, "cards": [...]}
            return result, 200

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

        form = request.form
        cardId = form.get('cardId')
        if not cardId:
            return {"message": "cardId is required"}, 400

        tariff = form.get('tariff','basic').lower()
        cardName = form.get('cardName','').strip()
        description = form.get('description','')
        address = form.get('address','')
        locationLat = form.get('locationLat')
        locationLng = form.get('locationLng')
        website = form.get('website','')

        phoneNumbers = request.form.getlist('phoneNumbers')
        socialMedias_str_list = request.form.getlist('socialMedias')
        socialMedias = []
        for s in socialMedias_str_list:
            try:
                sm = json.loads(s)
                socialMedias.append(sm)
            except:
                pass
        photos = request.files.getlist('photos')

        if tariff not in ['basic','premium']:
            return {"message": "tariff must be 'basic' or 'premium'"}, 400
        if not cardName:
            return {"message": "cardName is required"}, 400
        if not description:
            return {"message": "description is required"}, 400
        if not address:
            return {"message": "address is required"}, 400

        maxDesc = 400 if tariff == 'premium' else 200
        if len(description) > maxDesc:
            return {"message": f"Описание превышает лимит {maxDesc} символов для {tariff}"}, 400
        if tariff == 'basic' and website:
            return {"message": "Website доступен только в тарифе premium"}, 400

        if tariff == 'basic':
            if len(phoneNumbers) != 1:
                return {"message": "Для тарифа basic нужен ровно 1 номер телефона"}, 400
        else:
            if not (1 <= len(phoneNumbers) <= 3):
                return {"message": "Для тарифа premium нужно от 1 до 3 номеров телефона"}, 400

        maxSocials = 1 if tariff == 'basic' else 4
        if len(socialMedias) > maxSocials:
            return {"message": f"Максимум {maxSocials} соцсетей для {tariff}"}, 400

        if tariff == 'basic':
            if len(photos) != 1:
                return {"message": "Для тарифа basic нужно ровно 1 фото"}, 400
        else:
            if not (1 <= len(photos) <= 5):
                return {"message": "Для тарифа premium нужно от 1 до 5 фото"}, 400

        latVal = float(locationLat) if locationLat else None
        lngVal = float(locationLng) if locationLng else None

        okMain = db.Cards.updateCardMainFields(
            userId=userId,
            cardId=int(cardId),
            cardName=cardName,
            description=description,
            address=address,
            locationLat=latVal,
            locationLng=lngVal,
            website=website,
            tariff=tariff
        )
        if not okMain:
            return {"message": "Ошибка при обновлении (не ваша карточка или не найдена)"}, 400

        if not self._overwritePhones(cardId, phoneNumbers):
            return {"message": "Ошибка при обновлении телефонов"}, 500

        if not self._overwriteSocials(cardId, socialMedias):
            return {"message": "Ошибка при обновлении соцсетей"}, 500

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        photoUrls = []
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, uniqueName)
            file.save(filepath)
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)

        if not self._overwritePhotos(cardId, photoUrls):
            return {"message": "Ошибка при обновлении фото"}, 500

        logging.info(f"[userId={userId}] Обновил карточку cardId={cardId}, тариф={tariff}")
        return {"message": "Карточка обновлена"}, 200

    def delete(self):
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

        data = request.get_json(silent=True)
        if not data:
            return {"message": "No input data"}, 400
        cardId = data.get('cardId')
        if not cardId:
            return {"message": "cardId is required"}, 400

        deleted = db.Cards.deleteCard(userId, cardId)
        if not deleted:
            return {"message": "Ошибка при удалении (не ваша карточка или не найдена)"}, 400

        logging.info(f"[userId={userId}] Удалил карточку cardId={cardId}")
        return {"message": "Карточка удалена"}, 200

    # ----------------- Вспомогательные методы ----------------- #

    def _overwritePhones(self, cardId, phoneNumbers):
        db.Cards.deleteAllPhones(cardId)
        return db.Cards.addPhoneNumbers(cardId, phoneNumbers)

    def _overwriteSocials(self, cardId, socialMedias):
        db.Cards.deleteAllSocials(cardId)
        return db.Cards.addSocialMedia(cardId, socialMedias)

    def _overwritePhotos(self, cardId, photoUrls):
        db.Cards.deleteAllPhotos(cardId)
        return db.Cards.addPhotos(cardId, photoUrls)
