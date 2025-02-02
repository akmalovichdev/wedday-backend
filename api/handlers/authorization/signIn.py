from api import *
from data import db
import datetime

class SignIn(Resource):
    def post(self):
        logging.info('Получен запрос на вход пользователя')

        try:
            # Попытка получить данные из запроса
            data = request.get_json(silent=True)
            logging.debug(f"Полученные данные: {data}")

            if not data:
                logging.warning('Недопустимые или отсутствующие данные JSON')
                return {"message": "Invalid or missing JSON data"}, 400

            # Получение данных из JSON
            email = data.get('email')
            password = data.get('password')

            # Проверка обязательных параметров
            if not all([email, password]):
                logging.warning('Отсутствуют обязательные параметры: '
                                f'email/username={email}, password={password}')
                return {"message": "Missing form data parameters"}, 400

            # Попытка аутентификации пользователя
            userData = db.authenticate(email, password)

            # Проверка результата аутентификации
            if isinstance(userData, tuple) and userData[0] is False:
                errorMessage = userData[1]
                logging.error(f"Ошибка при входе: {errorMessage}")
                return {"message": f"Authentication failed: {errorMessage}"}, 401

            # Успешный ответ
            email: str = userData['email']
            fullName: str = userData['fullName']
            userId = userData['userId']
            token = self.generateToken(userId, fullName)

            responseData = {
                "email": email,
                "fullName": fullName,
                "token": token,
                "userId": userId
            }
            logging.info(f"Успешный вход: {responseData}")
            return responseData, 200

        except Exception as e:
            # Обработка всех других исключений
            logging.error(f"Ошибка при обработке запроса: {str(e)}")
            return {"message": f"An error occurred: {str(e)}"}, 500

    def generateToken(self, userId, userName):
        try:
            payload = {
                'userId': userId,
                'userName': userName,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            }
            secret_key = jwtSecretKey
            token = jwt.encode(payload, secret_key, algorithm='HS256')
            return token
        except Exception as e:
            logging.error(f"Ошибка при генерации токена: {str(e)}")
            return None

api.add_resource(SignIn, '/api/v1/admin/sign-in')
