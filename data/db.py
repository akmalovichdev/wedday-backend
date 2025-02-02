import mysql.connector
from mysql.connector import Error, IntegrityError, DataError, DatabaseError, OperationalError
from data.config import mysqlHost, mysqlUser, mysqlPassword, mysqlDatabase
import datetime
import json
import logging
import bcrypt

# Функция подключения к БД
def connect():
    try:
        conn = mysql.connector.connect(
            host=mysqlHost,
            user=mysqlUser,
            password=mysqlPassword,
            database=mysqlDatabase
        )
        return conn
    except Exception as error:
        logging.error("Ошибка подключения к базе данных: {}".format(error))
        return None

# Функция обработки ошибок MySQL
def handleError(error):
    if isinstance(error, IntegrityError):
        return False, f"IntegrityError: {error}"
    elif isinstance(error, DataError):
        return False, f"DataError: {error}"
    elif isinstance(error, OperationalError):
        return False, f"OperationalError: {error}"
    elif isinstance(error, DatabaseError):
        return False, f"DatabaseError: {error}"
    elif isinstance(error, Error):
        return False, f"MySQL Error: {error}"
    else:
        return False, f"Unexpected error: {error}"

# Функция инициализации БД (создание таблиц, если они отсутствуют)
def init_db():
    conn = connect()
    if conn is None:
        logging.error("Не удалось установить подключение для инициализации базы данных")
        return
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        userId INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        fullName VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        profilePhoto VARCHAR(255) DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """)
    # Таблица карточек
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        cardId INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        comment TEXT NOT NULL,
        location VARCHAR(255) NOT NULL,
        location2 VARCHAR(255) NOT NULL,
        phone1 VARCHAR(50),
        phone2 VARCHAR(50),
        phone3 VARCHAR(50),
        socials TEXT,
        created_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """)
    # Таблица квартир (примерная структура, можно расширять)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apartments (
        apartmentId INT AUTO_INCREMENT PRIMARY KEY,
        sectionId INT NOT NULL,
        apartmentNumber VARCHAR(255) NOT NULL,
        floor INT NOT NULL,
        roomType VARCHAR(255) NOT NULL,
        squareMeters FLOAT NOT NULL,
        status VARCHAR(50) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """)
    conn.commit()
    cursor.close()
    conn.close()
    logging.info("Инициализация базы данных завершена")

# При импорте модуля выполняем инициализацию БД
init_db()

#########################################################################
# Функция аутентификации пользователя

def authenticate(email, password):
    try:
        conn = connect()
        if conn is None:
            return False, "Ошибка подключения к базе данных"
        cursor = conn.cursor(dictionary=True)
        query = "SELECT userId, email, fullName, password, profilePhoto FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            storedPassword = user['password']
            if bcrypt.checkpw(password.encode('utf-8'), storedPassword.encode('utf-8')):
                return user
            else:
                return False, "Incorrect password"
        else:
            return False, "User not found"
    except Exception as err:
        return handleError(err)

#########################################################################
# Класс Add – методы добавления записей

class Add:
    @staticmethod
    def user(email, fullName, password):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            # Хэшируем пароль с использованием bcrypt
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            query = "INSERT INTO users (email, fullName, password) VALUES (%s, %s, %s)"
            cursor.execute(query, (email, fullName, hashed))
            userId = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return userId
        except Exception as err:
            return handleError(err)

    @staticmethod
    def card(category, name, comment, location, location2, phoneNumbers, socials):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            # Если передано меньше 3 номеров – заполняем оставшиеся значениями NULL
            phones = phoneNumbers + [None] * (3 - len(phoneNumbers))
            phone1, phone2, phone3 = phones[:3]
            socials_json = json.dumps(socials)
            created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = """
                INSERT INTO cards
                (category, name, comment, location, location2, phone1, phone2, phone3, socials, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (category, name, comment, location, location2,
                                     phone1, phone2, phone3, socials_json, created_at))
            cardId = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return cardId
        except Exception as err:
            return handleError(err)

    @staticmethod
    def apartment(sectionId, apartmentNumber, floor, roomType, squareMeters, status):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            query = """
                INSERT INTO apartments (sectionId, apartmentNumber, floor, roomType, squareMeters, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (sectionId, apartmentNumber, floor, roomType, squareMeters, status))
            apartmentId = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return apartmentId
        except Exception as err:
            return handleError(err)

#########################################################################
# Класс Get – методы получения данных

class Get:
    @staticmethod
    def user(userId):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor(dictionary=True)
            query = "SELECT userId, email, fullName, profilePhoto FROM users WHERE userId = %s"
            cursor.execute(query, (userId,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            if user:
                return user
            else:
                return False, "User not found"
        except Exception as err:
            return handleError(err)

    @staticmethod
    def card(cardId):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM cards WHERE cardId = %s"
            cursor.execute(query, (cardId,))
            card = cursor.fetchone()
            cursor.close()
            conn.close()
            if card:
                # Преобразуем socials из JSON в список
                card['socials'] = json.loads(card['socials']) if card.get('socials') else []
                # Формируем список phoneNumbers
                phoneNumbers = []
                for key in ['phone1', 'phone2', 'phone3']:
                    if card.get(key):
                        phoneNumbers.append(card.get(key))
                card['phoneNumbers'] = phoneNumbers
                # Убираем отдельные поля телефонов
                card.pop('phone1', None)
                card.pop('phone2', None)
                card.pop('phone3', None)
                return card
            else:
                return False, "Card not found"
        except Exception as err:
            return handleError(err)

    @staticmethod
    def all_cards():
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM cards"
            cursor.execute(query)
            cards = cursor.fetchall()
            cursor.close()
            conn.close()
            result = []
            for card in cards:
                card['socials'] = json.loads(card['socials']) if card.get('socials') else []
                phoneNumbers = []
                for key in ['phone1', 'phone2', 'phone3']:
                    if card.get(key):
                        phoneNumbers.append(card.get(key))
                card['phoneNumbers'] = phoneNumbers
                card.pop('phone1', None)
                card.pop('phone2', None)
                card.pop('phone3', None)
                result.append(card)
            return result
        except Exception as err:
            return handleError(err)

    @staticmethod
    def apartment(apartmentId):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM apartments WHERE apartmentId = %s"
            cursor.execute(query, (apartmentId,))
            apartment = cursor.fetchone()
            cursor.close()
            conn.close()
            if apartment:
                return apartment
            else:
                return False, "Apartment not found"
        except Exception as err:
            return handleError(err)

#########################################################################
# Класс Update – методы обновления данных

class Update:
    @staticmethod
    def user(userId, data):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            fields = []
            values = []
            if "email" in data:
                fields.append("email = %s")
                values.append(data["email"])
            if "fullName" in data:
                fields.append("fullName = %s")
                values.append(data["fullName"])
            if "profilePhoto" in data:
                fields.append("profilePhoto = %s")
                values.append(data["profilePhoto"])
            if not fields:
                return True  # Нет изменений
            query = "UPDATE users SET " + ", ".join(fields) + " WHERE userId = %s"
            values.append(userId)
            cursor.execute(query, tuple(values))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            return handleError(err)

    @staticmethod
    def card(cardId, data):
        try:
            # Получаем текущую карточку для подстановки отсутствующих полей
            current_card = Get.card(cardId)
            if isinstance(current_card, tuple) and current_card[0] is False:
                return False, "Card not found"
            category  = data.get("category", current_card.get("category"))
            name      = data.get("name", current_card.get("name"))
            comment   = data.get("comment", current_card.get("comment"))
            location  = data.get("location", current_card.get("location"))
            location2 = data.get("location2", current_card.get("location2"))
            phoneNumbers = data.get("phoneNumbers")
            if phoneNumbers is not None:
                if not isinstance(phoneNumbers, list):
                    return False, "phoneNumbers must be a list"
                if len(phoneNumbers) > 3:
                    return False, "Maximum 3 phone numbers allowed"
                phones = phoneNumbers + [None] * (3 - len(phoneNumbers))
                phone1, phone2, phone3 = phones[:3]
            else:
                phoneNumbers_current = current_card.get("phoneNumbers", [])
                phone1 = phoneNumbers_current[0] if len(phoneNumbers_current) > 0 else None
                phone2 = phoneNumbers_current[1] if len(phoneNumbers_current) > 1 else None
                phone3 = phoneNumbers_current[2] if len(phoneNumbers_current) > 2 else None
            socials = data.get("socials")
            if socials is not None:
                if not isinstance(socials, list):
                    return False, "socials must be a list"
                socials_json = json.dumps(socials)
            else:
                socials_json = json.dumps(current_card.get("socials"))
            query = """
                UPDATE cards SET
                    category = %s,
                    name = %s,
                    comment = %s,
                    location = %s,
                    location2 = %s,
                    phone1 = %s,
                    phone2 = %s,
                    phone3 = %s,
                    socials = %s
                WHERE cardId = %s
            """
            values = (category, name, comment, location, location2, phone1, phone2, phone3, socials_json, cardId)
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            return handleError(err)

    @staticmethod
    def apartment(apartmentId, data):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            fields = []
            values = []
            for field in ["sectionId", "apartmentNumber", "floor", "roomType", "squareMeters", "status"]:
                if field in data:
                    fields.append(f"{field} = %s")
                    values.append(data[field])
            if not fields:
                return True
            query = "UPDATE apartments SET " + ", ".join(fields) + " WHERE apartmentId = %s"
            values.append(apartmentId)
            cursor.execute(query, tuple(values))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            return handleError(err)

#########################################################################
# Класс Delete – методы удаления данных

class Delete:
    @staticmethod
    def card(cardId):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            query = "DELETE FROM cards WHERE cardId = %s"
            cursor.execute(query, (cardId,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            return handleError(err)

    @staticmethod
    def apartment(apartmentId):
        try:
            conn = connect()
            if conn is None:
                return False, "Ошибка подключения к базе данных"
            cursor = conn.cursor()
            query = "DELETE FROM apartments WHERE apartmentId = %s"
            cursor.execute(query, (apartmentId,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            return handleError(err)

#########################################################################
# Класс Exist – проверка существования записей

class Exist:
    @staticmethod
    def card(cardId):
        try:
            conn = connect()
            if conn is None:
                return False
            cursor = conn.cursor()
            query = "SELECT cardId FROM cards WHERE cardId = %s"
            cursor.execute(query, (cardId,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return bool(result)
        except Exception as err:
            logging.error(f"Ошибка при проверке существования карточки: {err}")
            return False

    @staticmethod
    def apartment(apartmentId):
        try:
            conn = connect()
            if conn is None:
                return False
            cursor = conn.cursor()
            query = "SELECT apartmentId FROM apartments WHERE apartmentId = %s"
            cursor.execute(query, (apartmentId,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return bool(result)
        except Exception as err:
            logging.error(f"Ошибка при проверке существования квартиры: {err}")
            return False

#########################################################################
# Для удобства создаём объект db с нужными разделами

get = Get
add = Add
update = Update
delete = Delete
exist = Exist
authenticate = authenticate
