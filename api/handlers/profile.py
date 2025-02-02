from api import *
from data import db
import jwt
from data.config import jwtSecretKey

class Profile(Resource):
    def get(self):
        """
        Получение профиля пользователя.
        Требуется передать в заголовке запроса валидный JWT токен.
        Из токена извлекается userId, затем запрашивается профиль из БД.
        """
        logging.info("Получен запрос на получение профиля пользователя")
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
            logging.debug(f"Payload из токена: {payload}")
            userId = payload.get("userId")
            if not userId:
                logging.warning("userId отсутствует в токене")
                return {"message": "Invalid token payload"}, 401

            # Получаем профиль пользователя из БД
            user = db.get.user(userId)
            if isinstance(user, tuple) and user[0] is False:
                error_message = user[1]
                logging.error(f"Ошибка получения профиля: {error_message}")
                return {"message": f"Error retrieving profile: {error_message}"}, 400

            logging.info("Профиль успешно получен")
            return user, 200

        except jwt.ExpiredSignatureError:
            logging.warning("Токен истек")
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning("Недействительный токен")
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f"Ошибка при обработке запроса профиля: {str(e)}")
            return {"message": "An error occurred while processing the request"}, 500

    def put(self):
        """
        Обновление профиля пользователя.
        Требуется передать в заголовке запроса валидный JWT токен, из которого извлекается userId.
        В теле запроса передаются изменяемые поля профиля.
        """
        logging.info("Получен запрос на обновление профиля пользователя")
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Токен не предоставлен")
            return {"message": "Token is missing"}, 401
        try:
            payload = jwt.decode(token, jwtSecretKey, algorithms=["HS256"])
            logging.debug(f"Payload из токена: {payload}")
            userId = payload.get("userId")
            if not userId:
                logging.warning("userId отсутствует в токене")
                return {"message": "Invalid token payload"}, 401

            data = request.get_json(silent=True)
            if not data:
                logging.warning("Нет данных для обновления профиля")
                return {"message": "Invalid or missing JSON data"}, 400

            # Обновляем профиль пользователя
            update_result = db.update.user(userId, data)
            if isinstance(update_result, tuple) and update_result[0] is False:
                error_message = update_result[1]
                logging.error(f"Ошибка обновления профиля: {error_message}")
                return {"message": f"Failed to update profile: {error_message}"}, 500

            # После обновления получаем обновлённый профиль
            user = db.get.user(userId)
            if isinstance(user, tuple) and user[0] is False:
                error_message = user[1]
                logging.error(f"Ошибка получения обновленного профиля: {error_message}")
                return {"message": f"Error retrieving profile: {error_message}"}, 400

            logging.info("Профиль успешно обновлён")
            return user, 200

        except jwt.ExpiredSignatureError:
            logging.warning("Токен истек")
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            logging.warning("Недействительный токен")
            return {"message": "Invalid token"}, 401
        except Exception as e:
            logging.error(f"Ошибка при обработке запроса: {str(e)}")
            return {"message": "An error occurred while processing the request"}, 500

# Регистрируем ресурс profile на endpoint'е /api/v1/admin/profile
api.add_resource(Profile, '/api/v1/admin/profile')
