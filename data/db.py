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

        # Таблица tariffs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            tariffId INT AUTO_INCREMENT PRIMARY KEY,
            tariffName VARCHAR(255) NOT NULL,
            minPhones INT NOT NULL DEFAULT 1,
            maxPhones INT NOT NULL DEFAULT 1,
            minSocials INT NOT NULL DEFAULT 0,
            maxSocials INT NOT NULL DEFAULT 1,
            minPhotos INT NOT NULL DEFAULT 1,
            maxPhotos INT NOT NULL DEFAULT 1,
            maxDescriptionLength INT NOT NULL DEFAULT 200,
            websiteAllowed TINYINT(1) NOT NULL DEFAULT 0,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # Таблица promotions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            promotionId INT AUTO_INCREMENT PRIMARY KEY,
            promotionName VARCHAR(255) NOT NULL,
            description VARCHAR(255) DEFAULT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # Таблица cardPromotions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardPromotions (
            cardPromotionId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            promotionId INT NOT NULL,
            startDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            endDate DATETIME
        ) ENGINE=InnoDB;
        """)

        # Таблица cards
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            cardId INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            categoryId INT NOT NULL,
            tariffId INT NOT NULL,
            cardName VARCHAR(255) NOT NULL,
            description TEXT,
            address VARCHAR(255),
            locationLat DECIMAL(10, 6) DEFAULT NULL,
            locationLng DECIMAL(10, 6) DEFAULT NULL,
            website VARCHAR(255) DEFAULT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # Таблица cardPhoneNumbers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardPhoneNumbers (
            phoneId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            phoneNumber VARCHAR(20) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId)
        ) ENGINE=InnoDB;
        """)

        # Таблица cardSocialMedia
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardSocialMedia (
            socialId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            socialType VARCHAR(100) NOT NULL,
            socialLink VARCHAR(255) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId)
        ) ENGINE=InnoDB;
        """)

        # Таблица cardPhotos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardPhotos (
            photoId INT AUTO_INCREMENT PRIMARY KEY,
            cardId INT NOT NULL,
            photoUrl VARCHAR(255) NOT NULL,
            FOREIGN KEY (cardId) REFERENCES cards(cardId)
        ) ENGINE=InnoDB;
        """)

        # Таблица favorites
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            favoriteId INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            cardId INT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES users(userId),
            FOREIGN KEY (cardId) REFERENCES cards(cardId),
            UNIQUE KEY uniqueFavorite (userId, cardId)
        ) ENGINE=InnoDB;
        """)

        # Таблица payments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            paymentId INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            cardId INT NOT NULL,           -- к какой карточке относится оплата
            paymentType VARCHAR(50) NOT NULL,   -- 'tariff' или 'promotion'
            tariffId INT DEFAULT NULL,     -- если paymentType='tariff', указываем tariffId
            promotionId INT DEFAULT NULL,  -- если paymentType='promotion', указываем promotionId
            orderId VARCHAR(255) NOT NULL UNIQUE,
            amount INT NOT NULL,           -- сумма в тийинах
            transactionId VARCHAR(255) DEFAULT NULL,
            state INT NOT NULL DEFAULT 0,  -- 0=pending, 1=created, 2=performed, -1=canceled
            reason INT DEFAULT NULL,       -- причина отмены, если state=-1
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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

    @staticmethod
    def updateProfile(userId, fullName, avatarUrl=None):
        """
        Обновляет профиль пользователя: fullName и avatar.
        Возвращает True при успешном обновлении, иначе False.
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            if avatarUrl:
                cursor.execute("""
                    UPDATE users
                    SET fullName = %s, avatar = %s
                    WHERE userId = %s
                """, (fullName, avatarUrl, userId))
            else:
                cursor.execute("""
                    UPDATE users
                    SET fullName = %s
                    WHERE userId = %s
                """, (fullName, userId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updateProfile: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

# -------------------- Класс Cards -------------------- #
class Cards:
    @staticmethod
    def addCard(userId, categoryId, tariffId, cardName, description,
                address, locationLat, locationLng, website):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        cardId = None
        try:
            cursor.execute("""
                INSERT INTO cards
                (userId, categoryId, tariffId, cardName, description, address,
                locationLat, locationLng, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                userId, categoryId, tariffId, cardName, description, address,
                locationLat, locationLng, website
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
    def getCards(filters, page=1, perPage=25):
        """
        Получить список карточек с учетом фильтров и пагинации.
        filters – словарь с ключами: categoryId, userId (необязательно).
        Возвращает словарь вида:
        { "pages": <общее число страниц>, "cards": [ список карточек ] }
        """
        conn = connect()
        if not conn:
            return {"pages": 0, "cards": []}
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM cards"
        conditions = []
        params = []

        if 'categoryId' in filters:
            conditions.append("categoryId = %s")
            params.append(filters['categoryId'])
        if 'userId' in filters:
            conditions.append("userId = %s")
            params.append(filters['userId'])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY createdAt DESC"

        # Получаем общее число карточек
        countQuery = "SELECT COUNT(*) as total FROM cards"
        if conditions:
            countQuery += " WHERE " + " AND ".join(conditions)
        cursor.execute(countQuery, tuple(params))
        countRow = cursor.fetchone()
        total = countRow['total'] if countRow and 'total' in countRow else 0
        pages = (total + perPage - 1) // perPage

        # Добавляем пагинацию
        offset = (page - 1) * perPage
        query += " LIMIT %s OFFSET %s"
        params.extend([perPage, offset])
        cursor.execute(query, tuple(params))
        cardRows = cursor.fetchall()
        cards = []
        for cardRow in cardRows:
            cardId = cardRow["cardId"]
            # Получаем телефоны
            cursor.execute("SELECT phoneNumber FROM cardPhoneNumbers WHERE cardId=%s", (cardId,))
            phoneRows = cursor.fetchall()
            # Получаем соцсети
            cursor.execute("SELECT socialType, socialLink FROM cardSocialMedia WHERE cardId=%s", (cardId,))
            socialRows = cursor.fetchall()
            # Получаем фото
            cursor.execute("SELECT photoUrl FROM cardPhotos WHERE cardId=%s", (cardId,))
            photosRows = cursor.fetchall()

            card = {
                "cardId": cardRow["cardId"],
                "userId": cardRow["userId"],
                "categoryId": cardRow["categoryId"],
                "cardName": cardRow["cardName"],
                "description": cardRow["description"],
                "address": cardRow["address"],
                "locationLat": float(cardRow["locationLat"]) if cardRow["locationLat"] is not None else None,
                "locationLng": float(cardRow["locationLng"]) if cardRow["locationLng"] is not None else None,
                "website": cardRow["website"],
                "tariffId": cardRow["tariffId"],
                "createdAt": str(cardRow["createdAt"]),
                "updatedAt": str(cardRow["updatedAt"]),
                "phoneNumbers": [p["phoneNumber"] for p in phoneRows],
                "socialMedias": socialRows,
                "photos": [ph["photoUrl"] for ph in photosRows]
            }
            cards.append(card)
        cursor.close()
        conn.close()
        return {"pages": pages, "cards": cards}

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
            "tariffId": cardRow["tariffId"],
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
    def addCategory(categoryName, logo=None):
        """
        Добавить новую категорию с логотипом.
        Возвращает categoryId или None.
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        categoryId = None
        try:
            cursor.execute("INSERT INTO categories (categoryName, logo) VALUES (%s, %s)",
                           (categoryName, logo))
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
    def updateCategory(categoryId, categoryName, logo=None):
        """
        Обновить категорию: изменяются имя и логотип (если предоставлен).
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            if logo:
                cursor.execute("""
                    UPDATE categories
                    SET categoryName=%s, logo=%s
                    WHERE categoryId=%s
                """, (categoryName, logo, categoryId))
            else:
                cursor.execute("""
                    UPDATE categories
                    SET categoryName=%s
                    WHERE categoryId=%s
                """, (categoryName, categoryId))
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
        favoritesRows = cursor.fetchall()

        for favoritesRow in favoritesRows:
            favoritesRow['createdAt'] = favoritesRow['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
            favoritesRow['locationLat'] = str(favoritesRow['locationLat'])
            favoritesRow['locationLng'] = str(favoritesRow['locationLng'])
        favorites = [favoritesRow for favoritesRow in favoritesRows]
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

# -------------------- Класс TariffsDB -------------------- #
class TariffsDB:
    @staticmethod
    def createTariff(tariffName, minPhones, maxPhones, minSocials, maxSocials,
                     minPhotos, maxPhotos, maxDescLength, websiteAllowed):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        tariffId = None
        try:
            cursor.execute("""
                INSERT INTO tariffs
                (tariffName, minPhones, maxPhones, minSocials, maxSocials,
                 minPhotos, maxPhotos, maxDescriptionLength, websiteAllowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (tariffName, minPhones, maxPhones, minSocials, maxSocials,
                  minPhotos, maxPhotos, maxDescLength, websiteAllowed))
            conn.commit()
            tariffId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка createTariff: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return tariffId

    @staticmethod
    def getTariffById(tariffId):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tariffs WHERE tariffId=%s", (tariffId,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def updateTariff(tariffId, **kwargs):
        """
        Обновляет тариф по указанному tariffId.
        Принимаем поля в kwargs (tariffName, minPhones, maxPhones, и т.д.)
        """
        # Собираем динамически SET
        sets = []
        params = []
        for key, val in kwargs.items():
            sets.append(f"{key}=%s")
            params.append(val)
        if not sets:
            return False

        query = f"UPDATE tariffs SET {', '.join(sets)} WHERE tariffId=%s"
        params.append(tariffId)

        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(query, tuple(params))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updateTariff: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def deleteTariff(tariffId):
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM tariffs WHERE tariffId=%s", (tariffId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка deleteTariff: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def getAllTariffs():
        conn = connect()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tariffs ORDER BY tariffId")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

# -------------------- Класс PromotionsDB -------------------- #
class PromotionsDB:
    @staticmethod
    def getPromotionById(promotionId):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM promotions WHERE promotionId=%s", (promotionId,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def activatePromotion(cardId, promotionId, durationDays):
        """
        Создаёт запись в cardPromotions, где endDate = startDate + durationDays.
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        cpId = None
        try:
            cursor.execute("""
                INSERT INTO cardPromotions (cardId, promotionId, startDate, endDate)
                VALUES (%s, %s, NOW(), DATE_ADD(NOW(), INTERVAL %s DAY))
            """, (cardId, promotionId, durationDays))
            conn.commit()
            cpId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка activatePromotion: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return cpId

# -------------------- Класс PaymentsDB -------------------- #
class PaymentsDB:
    @staticmethod
    def createPayment(userId, cardId, paymentType, tariffId, promotionId, orderId, amount):
        """
        Создаёт запись в payments (state=0).
        paymentType='tariff' => tariffId != None
        paymentType='promotion' => promotionId != None
        """
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor()
        paymentId = None
        try:
            cursor.execute("""
                INSERT INTO payments
                (userId, cardId, paymentType, tariffId, promotionId, orderId, amount, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            """, (userId, cardId, paymentType, tariffId, promotionId, orderId, amount))
            conn.commit()
            paymentId = cursor.lastrowid
        except Exception as e:
            logging.error(f"Ошибка createPayment: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return paymentId

    @staticmethod
    def getPaymentByOrderId(orderId):
        conn = connect()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM payments WHERE orderId=%s", (orderId,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def updatePaymentOnCreateTransaction(orderId, transactionId):
        """
        Ставим state=1, прописываем transactionId.
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE payments
                SET state=1, transactionId=%s
                WHERE orderId=%s
            """, (transactionId, orderId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updatePaymentOnCreateTransaction: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def updatePaymentOnPerform(orderId):
        """
        Ставим state=2 (performed).
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE payments
                SET state=2
                WHERE orderId=%s
            """, (orderId,))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updatePaymentOnPerform: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def updatePaymentOnCancel(orderId, reason):
        """
        Ставим state=-1 (canceled), reason=<причина>.
        """
        conn = connect()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE payments
                SET state=-1, reason=%s
                WHERE orderId=%s
            """, (reason, orderId))
            conn.commit()
        except Exception as e:
            logging.error(f"Ошибка updatePaymentOnCancel: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
        cursor.close()
        conn.close()
        return True
