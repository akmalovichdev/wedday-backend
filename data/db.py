import mysql.connector
from mysql.connector import Error, IntegrityError, DataError, DatabaseError, OperationalError
from data.config import mysqlHost, mysqlUser, mysqlPassword, mysqlDatabase
import logging

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
        logging.error(f"Ошибка подключения к базе данных: {error}")
        return None

def initDB():
    conn = connect()
    if not conn:
        logging.error("Не удалось подключиться к базе для инициализации.")
        return
    cursor = conn.cursor()
    try:
        # Таблица users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            userId INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            fullName VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            avatar VARCHAR(255) DEFAULT NULL,
            -- Поля для подтверждения почты (если нужно)
            emailConfirmation TINYINT(1) DEFAULT 0,
            confirmationCode VARCHAR(50) DEFAULT NULL,

            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # Таблица categories
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            categoryId INT AUTO_INCREMENT PRIMARY KEY,
            categoryName VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB;
        """)

        # Таблица cards (добавляем поле tariff VARCHAR(20))
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            cardId INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            categoryId INT NOT NULL,
            cardName VARCHAR(255) NOT NULL,
            description TEXT,
            address VARCHAR(255),
            locationLat DECIMAL(10, 6) DEFAULT NULL,
            locationLng DECIMAL(10, 6) DEFAULT NULL,
            website VARCHAR(255) DEFAULT NULL,
            tariff VARCHAR(20) NOT NULL DEFAULT 'basic',

            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            FOREIGN KEY (userId) REFERENCES users(userId) ON DELETE CASCADE,
            FOREIGN KEY (categoryId) REFERENCES categories(categoryId) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Таблица cardPhoneNumbers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardPhoneNumbers (
            phoneId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            phoneNumber VARCHAR(20) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Таблица cardSocialMedia
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardSocialMedia (
            socialId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            socialType VARCHAR(100) NOT NULL,
            socialLink VARCHAR(255) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Таблица cardPhotos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardPhotos (
            photoId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            photoUrl VARCHAR(255) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Таблица favorites
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            favoriteId INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            cardId INT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES users(userId) ON DELETE CASCADE,
            FOREIGN KEY (cardId) REFERENCES cards(cardId) ON DELETE CASCADE,
            UNIQUE KEY uniqueFavorite (userId, cardId)
        ) ENGINE=InnoDB;
        """)

        conn.commit()
        logging.info("Инициализация БД завершена.")
    except Exception as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# -------------------- Класс Users -------------------- #
class Users:
    @staticmethod
    def createUserWithData(email, fullName, hashedPassword, confirmationCode):
        """
        Создаёт пользователя (emailConfirmation=0, хранит confirmationCode).
        Возвращает userId или None
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        userId = None
        try:
            cursor.execute("""
                INSERT INTO users (email, fullName, password, emailConfirmation, confirmationCode)
                VALUES (%s, %s, %s, 0, %s)
            """, (email, fullName, hashedPassword, confirmationCode))
            conn.commit()
            userId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка createUserWithData: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return userId

    @staticmethod
    def updateConfirmationCode(userId, code):
        """
        Обновить код верификации email
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET confirmationCode=%s
                WHERE userId=%s
            """, (code, userId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updateConfirmationCode: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def confirmEmail(userId):
        """
        emailConfirmation=1, confirmationCode=NULL
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET emailConfirmation=1, confirmationCode=NULL
                WHERE userId=%s
            """, (userId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка confirmEmail: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def getUserByEmail(email):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def getUserById(userId):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE userId=%s", (userId,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

# -------------------- Класс Cards -------------------- #
class Cards:
    @staticmethod
    def addCard(userId, categoryId, cardName, description,
                address, locationLat, locationLng,
                website, tariff):
        """
        Создаёт новую карточку, поле 'tariff' (basic/premium) записывается в БД.
        Возвращает cardId или None.
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        cardId = None
        try:
            cursor.execute("""
                INSERT INTO cards
                (userId, categoryId, cardName, description, address,
                 locationLat, locationLng, website, tariff)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                userId, categoryId, cardName, description, address,
                locationLat, locationLng, website, tariff
            ))
            conn.commit()
            cardId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка addCard: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return cardId

    @staticmethod
    def updateCardMainFields(userId, cardId, cardName, description,
                             address, locationLat, locationLng,
                             website, tariff):
        """
        Обновляем основные поля карточки, включая tariff.
        Не трогаем телефоны, соцсети, фото (они перезаписываются отдельно).
        Проверяем, что карточка принадлежит userId.
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            # Проверяем владельца
            cursor.execute("SELECT userId FROM cards WHERE cardId=%s", (cardId,))
            row = cursor.fetchone()
            if not row or row[0] != userId:
                cursor.close()
                conn.close()
                return False

            cursor.execute("""
                UPDATE cards
                SET cardName=%s, description=%s, address=%s,
                    locationLat=%s, locationLng=%s,
                    website=%s, tariff=%s
                WHERE cardId=%s
            """, (
                cardName, description, address,
                locationLat, locationLng,
                website, tariff,
                cardId
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updateCardMainFields: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def getCardById(cardId: int):
        """
        Возвращает полную информацию о карточке, включая телефоны, соцсети, фото.
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cards WHERE cardId=%s", (cardId,))
        cardRow = cursor.fetchone()
        if not cardRow:
            cursor.close()
            conn.close()
            return None

        # Телефоны
        cursor.execute("SELECT phoneNumber FROM cardPhoneNumbers WHERE cardId=%s", (cardId,))
        phoneRows = cursor.fetchall()

        # Соцсети
        cursor.execute("SELECT socialType, socialLink FROM cardSocialMedia WHERE cardId=%s", (cardId,))
        socialRows = cursor.fetchall()

        # Фото
        cursor.execute("SELECT photoUrl FROM cardPhotos WHERE cardId=%s", (cardId,))
        photosRows = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "cardId": cardRow["cardId"],
            "userId": cardRow["userId"],
            "categoryId": cardRow["categoryId"],
            "cardName": cardRow["cardName"],
            "description": cardRow["description"],
            "address": cardRow["address"],
            "locationLat": float(cardRow["locationLat"]) if cardRow["locationLat"] else None,
            "locationLng": float(cardRow["locationLng"]) if cardRow["locationLng"] else None,
            "website": cardRow["website"],
            "tariff": cardRow["tariff"],
            "createdAt": str(cardRow["createdAt"]),
            "updatedAt": str(cardRow["updatedAt"]),
            "phoneNumbers": [p["phoneNumber"] for p in phoneRows],
            "socialMedias": socialRows,
            "photos": [ph["photoUrl"] for ph in photosRows]
        }

    @staticmethod
    def deleteCard(userId: int, cardId: int):
        """
        Удаляем карточку, если она принадлежит userId.
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            # Проверяем владельца
            cursor.execute("SELECT userId FROM cards WHERE cardId=%s", (cardId,))
            row = cursor.fetchone()
            if not row or row[0] != userId:
                cursor.close()
                conn.close()
                return False

            cursor.execute("DELETE FROM cards WHERE cardId=%s", (cardId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteCard: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    # ----------------------------------------------------------------
    # Методы для телефонов
    # ----------------------------------------------------------------
    @staticmethod
    def deleteAllPhones(cardId: int):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cardPhoneNumbers WHERE cardId=%s", (cardId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteAllPhones: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def addPhoneNumbers(cardId: int, phoneNumbers: list):
        """
        Добавляет список phoneNumbers. Если phoneNumbers пуст, пропускаем.
        """
        if not phoneNumbers:
            return True
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            for phone in phoneNumbers:
                cursor.execute("""
                    INSERT INTO cardPhoneNumbers (cardId, phoneNumber)
                    VALUES (%s, %s)
                """, (cardId, phone))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка addPhoneNumbers: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    # ----------------------------------------------------------------
    # Методы для соцсетей
    # ----------------------------------------------------------------
    @staticmethod
    def deleteAllSocials(cardId: int):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cardSocialMedia WHERE cardId=%s", (cardId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteAllSocials: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def addSocialMedia(cardId: int, socialMedias: list):
        """
        Добавляет список соцсетей:
        [
          {"socialType":"instagram","socialLink":"..."},
          ...
        ]
        """
        if not socialMedias:
            return True
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            for sm in socialMedias:
                sType = sm.get('socialType','').strip()
                sLink = sm.get('socialLink','').strip()
                if sType and sLink:
                    cursor.execute("""
                        INSERT INTO cardSocialMedia (cardId, socialType, socialLink)
                        VALUES (%s, %s, %s)
                    """, (cardId, sType, sLink))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка addSocialMedia: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    # ----------------------------------------------------------------
    # Методы для фото
    # ----------------------------------------------------------------
    @staticmethod
    def deleteAllPhotos(cardId: int):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cardPhotos WHERE cardId=%s", (cardId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteAllPhotos: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def addPhotos(cardId: int, photoUrls: list):
        """
        Добавляем записи в cardPhotos (photoUrl).
        photoUrls – список строк (ссылок).
        """
        if not photoUrls:
            return True
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            for url in photoUrls:
                cursor.execute("""
                    INSERT INTO cardPhotos (cardId, photoUrl)
                    VALUES (%s, %s)
                """, (cardId, url))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка addPhotos: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

# -------------------- Класс Categories -------------------- #
class Categories:
    @staticmethod
    def getAllCategories():
        conn = connect()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return categories

    @staticmethod
    def addCategory(categoryName):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        categoryId = None
        try:
            cursor.execute("INSERT INTO categories (categoryName) VALUES (%s)", (categoryName,))
            conn.commit()
            categoryId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка addCategory: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return categoryId

    @staticmethod
    def updateCategory(categoryId, categoryName):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE categories SET categoryName=%s WHERE categoryId=%s", (categoryName, categoryId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updateCategory: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def deleteCategory(categoryId):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM categories WHERE categoryId=%s", (categoryId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteCategory: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

# -------------------- Класс FavoritesDB -------------------- #
class FavoritesDB:
    @staticmethod
    def addFavorite(userId: int, cardId: int):
        """
        Добавить запись в favorites (userId, cardId), с UNIQUE(userId, cardId)
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO favorites (userId, cardId)
                VALUES (%s, %s)
            """, (userId, cardId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка addFavorite: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def getFavorites(userId: int):
        """
        Вернуть список избранных карточек данного userId
        """
        conn = connect()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.favoriteId, f.cardId, c.cardName, c.description,
                   c.address, c.locationLat, c.locationLng, c.website, c.createdAt
            FROM favorites f
            JOIN cards c ON f.cardId = c.cardId
            WHERE f.userId = %s
            ORDER BY f.createdAt DESC
        """, (userId,))
        favorites = cursor.fetchall()
        cursor.close()
        conn.close()
        return favorites

    @staticmethod
    def removeFavorite(userId: int, cardId: int):
        """
        Удалить запись из favorites
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM favorites WHERE userId=%s AND cardId=%s", (userId, cardId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка removeFavorite: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True
