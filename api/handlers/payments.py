from flask_restful import Resource
from flask import request, jsonify
import logging
import time
import base64
import jwt

from data.config import jwtSecretKey, merchantId, paymeSecretKey, paymeCheckoutUrl
from data import db

class PaymentsGenerate(Resource):
    """
    GET /api/payments/generate?cardId=...&type=[tariff|promotion]&tariffId=.../promotionId=...
    Авторизация: JWT в заголовке Authorization

    1) Проверяем userId в токене;
    2) Если type=tariff -> ищем тариф в tariffs, берём price;
    3) Если type=promotion -> ищем promo в promotions, берём price;
    4) Создаём запись в payments: paymentType='tariff'/'promotion', orderId, amount.
    5) Формируем ссылку PayMe (base64).
    """
    def get(self):
        token = request.headers.get("Authorization")
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message":"Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
        except Exception as e:
            logging.warning("Недействительный токен")
            return {"message":"Invalid token"}, 401

        userId = payload.get("userId")
        if not userId:
            return {"message":"Invalid token payload"}, 401

        args = request.args
        cardIdStr = args.get("cardId")
        paymentType = args.get("type","").lower()  # tariff / promotion
        if not cardIdStr or not paymentType:
            return {"message":"cardId and type are required"}, 400
        try:
            cardId = int(cardIdStr)
        except ValueError:
            return {"message":"cardId must be integer"}, 400

        amount = None
        tariffId = None
        promotionId = None

        if paymentType == "tariff":
            tIdStr = args.get("tariffId")
            if not tIdStr:
                return {"message":"tariffId is required when type=tariff"}, 400
            try:
                tariffId = int(tIdStr)
            except ValueError:
                return {"message":"tariffId must be integer"}, 400

            tariffRow = db.TariffsDB.getTariffById(tariffId)
            if not tariffRow:
                return {"message":f"Tariff {tariffId} not found"}, 400
            amount = tariffRow["price"]  # Предполагается, что в таблице tariffs есть поле price.

        elif paymentType == "promotion":
            pIdStr = args.get("promotionId")
            if not pIdStr:
                return {"message":"promotionId is required when type=promotion"}, 400
            try:
                promotionId = int(pIdStr)
            except ValueError:
                return {"message":"promotionId must be integer"}, 400

            promoRow = db.PromotionsDB.getPromotionById(promotionId)
            if not promoRow:
                return {"message":f"Promotion {promotionId} not found"}, 400
            amount = promoRow["price"]

        else:
            return {"message":"type must be 'tariff' or 'promotion'"}, 400

        if amount is None:
            return {"message":"Unable to determine amount"}, 500

        # Генерируем orderId
        orderId = f"order_{int(time.time())}"

        # Создаём запись в payments
        paymentId = db.PaymentsDB.createPayment(
            userId=userId,
            cardId=cardId,
            paymentType=paymentType,
            tariffId=tariffId,
            promotionId=promotionId,
            orderId=orderId,
            amount=amount
        )
        if not paymentId:
            logging.error(f"Ошибка при создании платежа, paymentType={paymentType}")
            return {"message":"Failed to create payment"}, 500

        # Формируем base64
        raw_params = f"m={merchantId};ac.order_id={orderId};a={amount}"
        encoded_params = base64.b64encode(raw_params.encode()).decode()
        payment_url = f"{paymeCheckoutUrl}/{encoded_params}"

        logging.info(f"[PaymentsGenerate] userId={userId}, cardId={cardId}, type={paymentType}, orderId={orderId}, amount={amount}")
        return {
            "paymentId": paymentId,
            "orderId": orderId,
            "amount": amount,
            "payment_url": payment_url
        }, 200

class PaymeWebhook(Resource):
    """
    POST /api/payme_webhook
    Приём PayMe мерчант-запросов: (CheckPerformTransaction, CreateTransaction, PerformTransaction, CancelTransaction, ...).
    При успешном PerformTransaction, если paymentType='tariff' -> обновляем cards.tariffId.
                                если paymentType='promotion' -> добавляем запись в cardPromotions.
    """
    def post(self):
        auth = request.headers.get("Authorization","")
        if not auth.startswith("Basic "):
            return self.rpc_error(-32504, "Unauthorized", None)
        encoded = auth.split("Basic ")[-1]
        decoded = base64.b64decode(encoded).decode()
        login, password = decoded.split(":")
        if password != paymeSecretKey:
            return self.rpc_error(-32504, "Invalid credentials", None)

        data = request.get_json()
        method = data.get("method")
        params = data.get("params", {})
        req_id = data.get("id")
        account = params.get("account", {})
        order_id = account.get("order_id")
        amount = params.get("amount")

        if method == "CheckPerformTransaction":
            paymentRow = db.PaymentsDB.getPaymentByOrderId(order_id)
            if not paymentRow:
                return self.rpc_account_error(-31050, "order_id", "Заказ не найден", req_id)
            if paymentRow["amount"] != amount:
                return self.rpc_account_error(-31001, "amount", "Сумма не совпадает", req_id)
            return self.rpc_result({"allow": True}, req_id)

        elif method == "CreateTransaction":
            paymentRow = db.PaymentsDB.getPaymentByOrderId(order_id)
            if not paymentRow:
                return self.rpc_account_error(-31050, "order_id", "Заказ не найден", req_id)
            if paymentRow["amount"] != amount:
                return self.rpc_account_error(-31001, "amount", "Неверная сумма", req_id)

            transactionId = params.get("id")
            db.PaymentsDB.updatePaymentOnCreateTransaction(order_id, transactionId)
            return self.rpc_result({
                "create_time": self.now_ms(),
                "transaction": transactionId,
                "state": 1
            }, req_id)

        elif method == "PerformTransaction":
            paymentRow = db.PaymentsDB.getPaymentByOrderId(order_id)
            if not paymentRow:
                return self.rpc_account_error(-31050, "order_id", "Заказ не найден", req_id)
            db.PaymentsDB.updatePaymentOnPerform(order_id)

            paymentType = paymentRow["paymentType"]   # 'tariff' or 'promotion'
            cardId = paymentRow["cardId"]
            userId = paymentRow["userId"]
            if paymentType == "tariff":
                tId = paymentRow["tariffId"]
                # Ставим карточке tariffId = tId
                cardInfo = db.Cards.getCardById(cardId)
                if cardInfo:
                    db.Cards.updateCardMainFields(
                        userId=userId,
                        cardId=cardId,
                        tariffId=tId,
                        cardName=cardInfo["cardName"],
                        description=cardInfo["description"],
                        address=cardInfo["address"],
                        locationLat=cardInfo["locationLat"],
                        locationLng=cardInfo["locationLng"],
                        website=cardInfo["website"]
                    )
                    logging.info(f"[PaymeWebhook] Оплата тарифа (tariffId={tId}) → cardId={cardId}")
            elif paymentType == "promotion":
                pId = paymentRow["promotionId"]
                promoRow = db.PromotionsDB.getPromotionById(pId)
                if promoRow:
                    db.PromotionsDB.activatePromotion(
                        cardId=cardId,
                        promotionId=pId,
                        durationDays=promoRow["durationDays"]
                    )
                    logging.info(f"[PaymeWebhook] Оплата промо (promotionId={pId}) → cardId={cardId}")

            return self.rpc_result({
                "transaction": params.get("id"),
                "perform_time": self.now_ms(),
                "state": 2
            }, req_id)

        elif method == "CancelTransaction":
            paymentRow = db.PaymentsDB.getPaymentByOrderId(order_id)
            if not paymentRow:
                return self.rpc_account_error(-31050, "order_id", "Заказ не найден", req_id)
            reason = params.get("reason")
            db.PaymentsDB.updatePaymentOnCancel(order_id, reason)
            return self.rpc_result({
                "transaction": params.get("id"),
                "cancel_time": self.now_ms(),
                "state": -1,
                "reason": reason
            }, req_id)

        elif method == "CheckTransaction":
            paymentRow = db.PaymentsDB.getPaymentByOrderId(order_id)
            st = paymentRow["state"] if paymentRow else 0
            return self.rpc_result({
                "create_time": self.now_ms(),
                "perform_time": self.now_ms() if st==2 else 0,
                "cancel_time": self.now_ms() if st==-1 else 0,
                "transaction": params.get("id"),
                "state": st,
                "reason": paymentRow["reason"] if paymentRow else None
            }, req_id)

        elif method == "GetStatement":
            return self.rpc_result({"transactions": []}, req_id)

        else:
            return self.rpc_error(-32601, "Method not found", req_id)

    # ---- Утилиты ----
    def rpc_result(self, result, req_id):
        return jsonify({"result": result, "id": req_id})

    def rpc_error(self, code, message, req_id):
        return jsonify({
            "error": {
                "code": code,
                "message": {"ru": message, "uz": message, "en": message}
            },
            "id": req_id
        })

    def rpc_account_error(self, code, field, message, req_id):
        return jsonify({
            "error": {
                "code": code,
                "message": {"ru": message, "uz": message, "en": message},
                "data": field
            },
            "id": req_id
        })

    def now_ms(self):
        return int(time.time() * 1000)