from flask_restful import Resource
from flask import request
import logging
import jwt
import os
import json
import time
from werkzeug.utils import secure_filename
from data.config import jwtSecretKey
from data import db

UPLOAD_FOLDER = './static/uploads/cards/'  # Папка, куда сохраняем фото

class Cards(Resource):
    """
    POST /api/cards -> Создание карточки (form-data)
      - tariffId (int) - обязательный
      - categoryId, cardName, description, address - обязательные
      - website, locationLat, locationLng - опциональные
      - phoneNumbers[] (list), socialMedias[] (list of JSON), photos (files)
      - Валидация происходит на основе таблицы tariffs (minPhones/maxPhones, и т.д.)

    GET /api/cards -> получение карточек с фильтрами:
      - ?cardId=... (конкретная карточка)
      - ?categoryId=... (по категории)
      - ?userId=... (по пользователю)
      - ?myCards=true (если нужно только карточки текущего пользователя)
      - page, perPage для пагинации (по умолчанию 1 и 25)

    PUT /api/cards -> обновление (form-data), аналогично POST
      - Нужно указать cardId
      - Если хотим изменить тариф, передаём новый tariffId
      - phoneNumbers, socialMedias, photos перезаписываются (удаляем, вставляем заново)

    DELETE /api/cards -> удаление (JSON: {"cardId": N})

    Авторизация: токен в заголовке Authorization (без префикса Bearer)
    """

    def post(self):
        # Авторизация
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Токен не предоставлен"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            logging.warning("Недействительный или просроченный токен")
            return {"message": "Недействительный или просроченный токен"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message": "Некорректный токен (отсутствует userId)"}, 401

        # Считываем поля
        form = request.form
        tariffIdStr = form.get('tariffId')
        if not tariffIdStr:
            return {"message": "tariffId is required"}, 400
        try:
            tariffId = int(tariffIdStr)
        except ValueError:
            return {"message": "tariffId must be integer"}, 400

        # Получаем тариф из БД
        tariffRow = db.TariffsDB.getTariffById(tariffId)
        if not tariffRow:
            return {"message": f"Тариф с ID={tariffId} не найден"}, 400

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

        # Валидация полей
        if not categoryId:
            return {"message": "categoryId is required"}, 400
        if not cardName:
            return {"message": "cardName is required"}, 400
        if not description:
            return {"message": "description is required"}, 400
        if not address:
            return {"message": "address is required"}, 400

        # Проверка описания
        maxDesc = tariffRow['maxDescriptionLength']
        if len(description) > maxDesc:
            return {"message": f"Описание превышает лимит {maxDesc} символов для данного тарифа"}, 400

        # Проверка website
        if not tariffRow['websiteAllowed'] and website:
            return {"message": "В данном тарифе нельзя указывать website"}, 400

        # Телефоны
        minPhones = tariffRow['minPhones']
        maxPhones = tariffRow['maxPhones']
        if not (minPhones <= len(phoneNumbers) <= maxPhones):
            return {"message": f"Нужно от {minPhones} до {maxPhones} номеров телефона для данного тарифа"}, 400

        # Соцсети
        minSocials = tariffRow['minSocials']
        maxSocials = tariffRow['maxSocials']
        if not (minSocials <= len(socialMedias) <= maxSocials):
            return {"message": f"Нужно от {minSocials} до {maxSocials} соцсетей для данного тарифа"}, 400

        # Фото
        minPhotos = tariffRow['minPhotos']
        maxPhotos = tariffRow['maxPhotos']
        if not (minPhotos <= len(photos) <= maxPhotos):
            return {"message": f"Нужно от {minPhotos} до {maxPhotos} фото для данного тарифа"}, 400

        # Преобразуем
        latVal = float(locationLat) if locationLat else None
        lngVal = float(locationLng) if locationLng else None
        catId = int(categoryId)

        # Создаём карточку
        cardId = db.Cards.addCard(
            userId=userId,
            categoryId=catId,
            tariffId=tariffId,  # <-- теперь передаём tariffId
            cardName=cardName,
            description=description,
            address=address,
            locationLat=latVal,
            locationLng=lngVal,
            website=website
        )
        if not cardId:
            logging.error("Ошибка при создании карточки (addCard вернул None)")
            return {"message": "Ошибка при создании карточки"}, 500

        # Телефоны
        if not db.Cards.addPhoneNumbers(cardId, phoneNumbers):
            return {"message": "Ошибка при добавлении телефонов"}, 500

        # Соцсети
        if not db.Cards.addSocialMedia(cardId, socialMedias):
            return {"message": "Ошибка при добавлении соцсетей"}, 500

        # Фотографии
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        photoUrls = []
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{int(time.time())}_{filename}"
            file.save(os.path.join(UPLOAD_FOLDER, uniqueName))
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)

        if not db.Cards.addPhotos(cardId, photoUrls):
            return {"message": "Ошибка при сохранении фото"}, 500

        logging.info(f"[userId={userId}] Создал карточку cardId={cardId}, тарифId={tariffId}")
        return {"message": "Карточка успешно создана", "cardId": cardId}, 201


    def get(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message": "Invalid or expired token"}, 401

        cardId = request.args.get('cardId')
        categoryId = request.args.get('categoryId')
        filterUserId = request.args.get('userId')
        myCards = request.args.get('myCards')
        try:
            page = int(request.args.get('page', 1))
            perPage = int(request.args.get('perPage', 25))
        except ValueError:
            return {"message": "page и perPage должны быть целыми числами"}, 400

        if myCards and myCards.lower() == "true":
            filterUserId = payload.get('userId')

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
            # Возвращаем {"pages": ..., "cards": [...]}
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
        cardIdStr = form.get('cardId')
        if not cardIdStr:
            return {"message": "cardId is required"}, 400
        try:
            cardId = int(cardIdStr)
        except:
            return {"message": "cardId must be integer"}, 400

        # Считываем tariffId
        tariffIdStr = form.get('tariffId')
        if not tariffIdStr:
            return {"message": "tariffId is required"}, 400
        try:
            tariffId = int(tariffIdStr)
        except:
            return {"message": "tariffId must be integer"}, 400

        tariffRow = db.TariffsDB.getTariffById(tariffId)
        if not tariffRow:
            return {"message": f"Тариф с ID={tariffId} не найден"}, 400

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

        if not cardName:
            return {"message": "cardName is required"}, 400
        if not description:
            return {"message": "description is required"}, 400
        if not address:
            return {"message": "address is required"}, 400

        maxDesc = tariffRow['maxDescriptionLength']
        if len(description) > maxDesc:
            return {"message": f"Описание превышает лимит {maxDesc} символов для тарифа ID={tariffId}"}, 400

        if not tariffRow['websiteAllowed'] and website:
            return {"message": "В данном тарифе нельзя указывать website"}, 400

        minPhones = tariffRow['minPhones']
        maxPhones = tariffRow['maxPhones']
        if not (minPhones <= len(phoneNumbers) <= maxPhones):
            return {"message": f"Нужно от {minPhones} до {maxPhones} телефонов для данного тарифа"}, 400

        minSocials = tariffRow['minSocials']
        maxSocials = tariffRow['maxSocials']
        if not (minSocials <= len(socialMedias) <= maxSocials):
            return {"message": f"Нужно от {minSocials} до {maxSocials} соцсетей для данного тарифа"}, 400

        minPhotos = tariffRow['minPhotos']
        maxPhotos = tariffRow['maxPhotos']
        if not (minPhotos <= len(photos) <= maxPhotos):
            return {"message": f"Нужно от {minPhotos} до {maxPhotos} фото для данного тарифа"}, 400

        latVal = float(locationLat) if locationLat else None
        lngVal = float(locationLng) if locationLng else None

        okMain = db.Cards.updateCardMainFields(
            userId=userId,
            cardId=cardId,
            tariffId=tariffId,
            cardName=cardName,
            description=description,
            address=address,
            locationLat=latVal,
            locationLng=lngVal,
            website=website
        )
        if not okMain:
            return {"message": "Ошибка при обновлении (не ваша карточка или не найдена)"}, 400

        # Перезаписываем телефоны / соцсети / фото
        if not self._overwritePhones(cardId, phoneNumbers):
            return {"message": "Ошибка при обновлении телефонов"}, 500

        if not self._overwriteSocials(cardId, socialMedias):
            return {"message": "Ошибка при обновлении соцсетей"}, 500

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        photoUrls = []
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{int(time.time())}_{filename}"
            file.save(os.path.join(UPLOAD_FOLDER, uniqueName))
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)

        if not self._overwritePhotos(cardId, photoUrls):
            return {"message":"Ошибка при обновлении фото"}, 500

        logging.info(f"[userId={userId}] Обновил карточку cardId={cardId}, тарифId={tariffId}")
        return {"message":"Карточка обновлена"}, 200

    def delete(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message": "Invalid or expired token"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message":"Invalid token payload"}, 401

        data = request.get_json(silent=True)
        if not data:
            return {"message":"No input data"}, 400
        cardId = data.get('cardId')
        if not cardId:
            return {"message":"cardId is required"}, 400

        deleted = db.Cards.deleteCard(userId, cardId)
        if not deleted:
            return {"message":"Ошибка при удалении (не ваша карточка или не найдена)"}, 400

        logging.info(f"[userId={userId}] Удалил карточку cardId={cardId}")
        return {"message":"Карточка удалена"}, 200

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