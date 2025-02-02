from api import *
from data import db
import jwt
from data.config import jwtSecretKey

class Card(Resource):
    def post(self):
        logging.info('Получен запрос на создание карточки')
        token = request.headers.get('Authorization')
        if not token:
            logging.warning('Токен не предоставлен')
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
            logging.info(f'Payload из токена: {payload}')
            staffId = payload['staffId']
            permissions = db.get.permissions(staffId)
            logging.debug(f'Права пользователя: {permissions}')
            if "createCard" not in permissions and permissions != ["*"]:
                logging.warning('Недостаточно прав для доступа')
                return {"message": "Insufficient permissions"}, 403

            data = request.get_json(silent=True)
            logging.debug(f"Полученные данные: {data}")
            if not data:
                logging.warning('Недопустимые или отсутствующие данные JSON')
                return {"message": "Invalid or missing JSON data"}, 400

            category     = data.get('category')
            name         = data.get('name')
            comment      = data.get('comment')
            location     = data.get('location')
            location2    = data.get('location2')
            phoneNumbers = data.get('phoneNumbers')  # список до 3 номеров
            socials      = data.get('socials')       # список соцсетей

            # Проверка обязательных параметров
            if not all([category, name, comment, location, location2]) or phoneNumbers is None or socials is None:
                logging.warning('Отсутствуют обязательные параметры')
                return {"message": "Missing form data parameters"}, 400

            # Проверка phoneNumbers
            if not isinstance(phoneNumbers, list):
                logging.warning('phoneNumbers должно быть списком')
                return {"message": "phoneNumbers must be a list"}, 400
            if len(phoneNumbers) > 3:
                logging.warning('Можно добавить максимум 3 номера')
                return {"message": "Maximum 3 phone numbers allowed"}, 400

            # Проверка socials
            if not isinstance(socials, list):
                logging.warning('socials должно быть списком')
                return {"message": "socials must be a list"}, 400

            cardId = db.add.card(category, name, comment, location, location2, phoneNumbers, socials)
            logging.debug(f"cardId после добавления: {cardId}")
            if isinstance(cardId, tuple) and cardId[0] is False:
                error_message = cardId[1]
                logging.error(f"Ошибка при создании карточки: {error_message}")
                return {"message": f"Failed to create card: {error_message}"}, 500

            responseData = {
                "cardId": cardId,
                "category": category,
                "name": name,
                "comment": comment,
                "location": location,
                "location2": location2,
                "phoneNumbers": phoneNumbers,
                "socials": socials
            }
            logging.info(f"Успешное создание карточки: {responseData}")
            return responseData, 201

        except jwt.ExpiredSignatureError:
            logging.warning('Токен истек')
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning('Недействительный токен')
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f'Ошибка при обработке запроса: {str(e)}')
            return {"message": "An error occurred while processing the token"}, 500

    def get(self, cardId=None):
        logging.info('Получен запрос на получение данных карточек')
        token = request.headers.get('Authorization')
        if not token:
            logging.warning('Токен не предоставлен')
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
            logging.info(f'Payload из токена: {payload}')
            staffId = payload['staffId']
            permissions = db.get.permissions(staffId)
            logging.debug(f'Права пользователя: {permissions}')
            if "viewCard" not in permissions and permissions != ["*"]:
                logging.warning('Недостаточно прав для доступа')
                return {"message": "Insufficient permissions"}, 403

            if cardId:
                card = db.get.card(cardId)
                logging.debug(f"Полученные данные карточки: {card}")
                if isinstance(card, tuple) and card[0] is False:
                    error_message = card[1]
                    logging.error(f"Ошибка при получении карточки: {error_message}")
                    return {"message": f"Error receiving data: {error_message}"}, 400
                return card, 200
            else:
                cards = db.get.all_cards()
                logging.debug(f"Полученные данные карточек: {cards}")
                if isinstance(cards, tuple) and cards[0] is False:
                    error_message = cards[1]
                    logging.error(f"Ошибка при получении карточек: {error_message}")
                    return {"message": f"Error receiving data: {error_message}"}, 400
                return {"cards": cards}, 200

        except jwt.ExpiredSignatureError:
            logging.warning('Токен истек')
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning('Недействительный токен')
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f'Ошибка при обработке запроса: {str(e)}')
            return {"message": "An error occurred while processing the token"}, 500

    def put(self, cardId):
        logging.info('Получен запрос на обновление карточки')
        token = request.headers.get('Authorization')
        if not token:
            logging.warning('Токен не предоставлен')
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
            logging.info(f'Payload из токена: {payload}')
            staffId = payload['staffId']
            permissions = db.get.permissions(staffId)
            logging.debug(f'Права пользователя: {permissions}')
            if "putCard" not in permissions and permissions != ["*"]:
                logging.warning('Недостаточно прав для доступа')
                return {"message": "Insufficient permissions"}, 403

            data = request.get_json(silent=True)
            logging.debug(f"Полученные данные для обновления: {data}")
            if not data:
                logging.warning('Недопустимые или отсутствующие данные JSON')
                return {"message": "Invalid or missing JSON data"}, 400

            # Допустим, разрешаем обновлять все поля, но cardId не должен изменяться
            updateResult = db.update.card(cardId, data)
            if isinstance(updateResult, tuple) and updateResult[0] is False:
                error_message = updateResult[1]
                logging.error(f"Ошибка при обновлении карточки: {error_message}")
                return {"message": f"Failed to update card: {error_message}"}, 500

            card = db.get.card(cardId)
            if isinstance(card, tuple) and card[0] is False:
                error_message = card[1]
                logging.error(f"Ошибка при получении обновлённой карточки: {error_message}")
                return {"message": f"Error receiving data: {error_message}"}, 400

            logging.info(f"Успешное обновление карточки: {card}")
            return card, 200

        except jwt.ExpiredSignatureError:
            logging.warning('Токен истек')
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning('Недействительный токен')
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f'Ошибка при обработке запроса: {str(e)}')
            return {"message": "An error occurred while processing the token"}, 500

    def delete(self, cardId):
        logging.info('Получен запрос на удаление карточки')
        token = request.headers.get('Authorization')
        if not token:
            logging.warning('Токен не предоставлен')
            return {"message": "Token is missing"}, 401

        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
            logging.info(f'Payload из токена: {payload}')
            staffId = payload['staffId']
            permissions = db.get.permissions(staffId)
            logging.debug(f'Права пользователя: {permissions}')
            if "deleteCard" not in permissions and permissions != ["*"]:
                logging.warning('Недостаточно прав для доступа')
                return {"message": "Insufficient permissions"}, 403

            # Проверяем, существует ли карточка
            if not db.exist.card(cardId):
                logging.warning(f'Карточка {cardId} не существует')
                return {"message": f"Card with ID {cardId} does not exist"}, 400

            result = db.delete.card(cardId)
            if isinstance(result, tuple) and result[0] is False:
                error_message = result[1]
                logging.error(f"Ошибка при удалении карточки: {error_message}")
                return {"message": f"Failed to delete card: {error_message}"}, 500

            logging.info(f"Карточка {cardId} успешно удалена")
            return {"message": "Card successfully deleted"}, 200

        except jwt.ExpiredSignatureError:
            logging.warning('Токен истек')
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning('Недействительный токен')
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f'Ошибка при обработке запроса: {str(e)}')
            return {"message": "An error occurred while processing the token"}, 500

# Регистрируем ресурс. Можно задать два endpoint'а:
# 1. /api/v1/admin/cards – для работы с коллекцией (POST, GET всех карточек)
# 2. /api/v1/admin/cards/<int:cardId> – для работы с конкретной карточкой (GET, PUT, DELETE)
api.add_resource(Card,
    '/api/v1/admin/cards',
    '/api/v1/admin/cards/<int:cardId>'
)
