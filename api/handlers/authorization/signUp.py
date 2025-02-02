from api import *
from data import db
import json
import logging

class SignUp(Resource):
    def post(self):

        logging.info(f'Получен запрос на создание пользователя')

        data = request.get_json()
        if not data:
            logging.warning('Входные данные не предоставлены')
            return {"message": "Входные данные не предоставлены"}, 400

        try:
            email = data['email']
            fullName = data['fullName']
            password = data['password']
            logging.debug(f'Полученные данные: email={email}, fullName={fullName}')
        except KeyError as e:
            logging.error(f"Отсутствует параметр: {e.args[0]}")
            return {"message": f"Parameter '{e.args[0]}' is missing"}, 400

        try:
            addedUser = db.Add.user(email, fullName, password)
        except Exception as e:
            logging.error(f"Ошибка добавления пользователя в базу данных: {e}")
            return {"message": "Ошибка добавления пользователя в базу данных"}, 500

        try:
            userInfo = json.loads(addedUser)
            logging.debug(f'Информация о пользователе после добавления: {userInfo}')

            response = {
                "email": userInfo.get("email", ""),
                "fullName": userInfo.get("username", "")
            }
            logging.info('Ответ успешно сформирован')
            return response, 200
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка декодирования JSON: {e}")
            return {"message": "Ошибка обработки данных пользователя"}, 500

api.add_resource(SignUp, '/api/v1/authorization/sign-up')
