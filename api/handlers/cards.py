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
    POST /api/cards
       form-data:
         - tariff: 'basic' | 'premium'
         - categoryId, cardName, description, address (обязательные)
         - locationLat, locationLng (необязательно)
         - website (только для premium)
         - phoneNumbers (list) => basic: ровно 1, premium: 1..3
         - socialMedias (list) => basic: макс 1, premium: макс 4
         - photos (файлы) => basic: ровно 1, premium: 1..5
       Authorization: <token>  (заголовок)

    GET /api/cards?cardId=...
       Authorization: <token>

    PUT /api/cards
       form-data: аналогично POST, но все поля в том же формате
       Полное перезаполнение номеров, соцсетей, фото.
       Authorization: <token>

    DELETE /api/cards
       JSON: { "cardId": ... }
       Authorization: <token>
    """

    def post(self):
        # 1) Проверка токена (без "Bearer ", только сам токен)
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

        # 3) Валидация тарифов
        if tariff not in ['basic','premium']:
            return {"message": "tariff must be 'basic' or 'premium'"}, 400

        # Обязательные поля
        if not categoryId:
            return {"message": "categoryId is required"}, 400
        if not cardName:
            return {"message": "cardName is required"}, 400
        if not description:
            return {"message": "description is required"}, 400
        if not address:
            return {"message": "address is required"}, 400

        # Лимиты описания
        maxDesc = 400 if tariff == 'premium' else 200
        if len(description) > maxDesc:
            return {"message": f"Описание превышает лимит {maxDesc} символов для {tariff}"}, 400

        # Website — только в premium
        if tariff == 'basic' and website:
            return {"message": "Website доступен только в тарифе premium"}, 400

        # phoneNumbers
        if tariff == 'basic':
            # ровно 1
            if len(phoneNumbers) != 1:
                return {"message": "Для тарифа basic нужен ровно 1 номер телефона"}, 400
        else:
            # premium => 1..3
            if not (1 <= len(phoneNumbers) <= 3):
                return {"message": "Для тарифа premium нужно от 1 до 3 номеров телефона"}, 400

        # socialMedias
        maxSocials = 1 if tariff == 'basic' else 4
        if len(socialMedias) > maxSocials:
            return {"message": f"Максимум {maxSocials} соцсетей для тарифа {tariff}"}, 400

        # photos
        if tariff == 'basic':
            # ровно 1
            if len(photos) != 1:
                return {"message": "Для тарифа basic нужно ровно 1 фото"}, 400
        else:
            # premium => 1..5
            if not (1 <= len(photos) <= 5):
                return {"message": "Для тарифа premium нужно от 1 до 5 фото"}, 400

        # 4) Преобразуем данные
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

        # 6) Сохраняем телефоны (перезапись)
        if not self._overwritePhones(cardId, phoneNumbers):
            return {"message": "Ошибка при добавлении телефонов"}, 500

        # 7) Сохраняем соцсети (перезапись)
        if not self._overwriteSocials(cardId, socialMedias):
            return {"message": "Ошибка при добавлении соцсетей"}, 500

        # 8) Сохраняем фото
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        photoUrls = []
        from werkzeug.utils import secure_filename
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, uniqueName)
            file.save(filepath)
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)

        if not self._overwritePhotos(cardId, photoUrls):
            return {"message":"Ошибка при сохранении фото"}, 500

        logging.info(f"[userId={userId}] Создал карточку cardId={cardId}, тариф={tariff}")
        return {"message": "Карточка успешно создана", "cardId": cardId}, 201


    def get(self):
        # Авторизация
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message":"Invalid or expired token"}, 401

        cardId = request.args.get('cardId')
        if not cardId:
            return {"message":"Parameter cardId is required"}, 400

        cardData = db.Cards.getCardById(int(cardId))
        if not cardData:
            return {"message":"Карточка не найдена"}, 404

        return cardData, 200


    def put(self):
        """
        Полное обновление карточки (form-data).
        - Должны выполняться те же правила тарифа, что и при POST.
        - Удаляем все старые записи (телефоны, соцсети, фото), вставляем заново.
        """
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message":"Invalid or expired token"}, 401

        userId = payload.get('userId')
        if not userId:
            return {"message":"Invalid token payload"}, 401

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

        # Проверки тарифов
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

        # phoneNumbers
        if tariff == 'basic':
            # ровно 1
            if len(phoneNumbers) != 1:
                return {"message":"Для тарифа basic нужен ровно 1 номер телефона"}, 400
        else:
            # premium => 1..3
            if not (1 <= len(phoneNumbers) <= 3):
                return {"message":"Для тарифа premium нужно 1..3 номеров телефона"}, 400

        # socialMedias
        maxSocials = 1 if tariff == 'basic' else 4
        if len(socialMedias) > maxSocials:
            return {"message": f"Максимум {maxSocials} соцсетей для тарифа {tariff}"}, 400

        # photos
        if tariff == 'basic':
            if len(photos) != 1:
                return {"message":"Для тарифа basic нужно ровно 1 фото"}, 400
        else:
            if not (1 <= len(photos) <= 5):
                return {"message":"Для тарифа premium нужно от 1 до 5 фото"}, 400

        # Обновляем основные поля
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
            return {"message":"Ошибка при обновлении (не ваша карточка или не найдена)"}, 400

        # Снова перезапишем телефоны, соцсети, фото
        if not self._overwritePhones(cardId, phoneNumbers):
            return {"message": "Ошибка при обновлении телефонов"}, 500

        if not self._overwriteSocials(cardId, socialMedias):
            return {"message": "Ошибка при обновлении соцсетей"}, 500

        # Фото
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        photoUrls = []
        from werkzeug.utils import secure_filename
        for file in photos:
            filename = secure_filename(file.filename)
            uniqueName = f"{cardId}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, uniqueName)
            file.save(filepath)
            photoUrl = f"/uploads/cards/{uniqueName}"
            photoUrls.append(photoUrl)

        if not self._overwritePhotos(cardId, photoUrls):
            return {"message":"Ошибка при обновлении фото"}, 500

        logging.info(f"[userId={userId}] Обновил карточку cardId={cardId}, тариф={tariff}")
        return {"message": "Карточка обновлена"}, 200


    def delete(self):
        token = request.headers.get('Authorization')
        if not token:
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return {"message":"Invalid or expired token"}, 401

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

        logging.info(f"[userId={userId}] Удалил карточку {cardId}")
        return {"message":"Карточка удалена"}, 200


    # ----------------- Вспомогательные методы ----------------- #

    def _overwritePhones(self, cardId, phoneNumbers):
        """
        Полная перезапись телефонов: удаляем все => добавляем все.
        """
        db.Cards.deleteAllPhones(cardId)
        return db.Cards.addPhoneNumbers(cardId, phoneNumbers)

    def _overwriteSocials(self, cardId, socialMedias):
        """
        Полная перезапись соцсетей: удаляем все => добавляем.
        """
        db.Cards.deleteAllSocials(cardId)
        return db.Cards.addSocialMedia(cardId, socialMedias)

    def _overwritePhotos(self, cardId, photoUrls):
        """
        Полная перезапись фото: удаляем все => добавляем.
        """
        db.Cards.deleteAllPhotos(cardId)
        return db.Cards.addPhotos(cardId, photoUrls)
