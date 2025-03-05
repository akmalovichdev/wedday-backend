from flask_restful import Resource, reqparse
import logging
import bcrypt
import random
import string

from data.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
from data import db

def sendEmailConfirmation(email, code):
    import smtplib
    import logging
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Настраиваем тело письма (HTML-формат для красоты)
    message_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family:Arial, sans-serif; line-height:1.5;">
        <h2 style="color: #2a7ec5;">Wedday-ga xush kelibsiz!</h2>
        <p>Biz siz bilan hamkorlik qilishdan xursandmiz.</p>
        <p>Sizning tasdiqlash kodingiz:</p>
        <p style="font-size: 1.3em; font-weight:bold;">{code}</p>
        <p>
            Iltimos, ushbu kodni veb-saytimizga kiriting va ro‘yxatdan o‘tishni yakunlang.
            <br>Agar siz ushbu kodni so‘ramagan bo‘lsangiz yoki Wedday-da ro‘yxatdan o‘tmagan bo‘lsangiz, ushbu xabarni e'tiborsiz qoldiring.
        </p>
        <br>
        <p>
            Hurmat bilan,<br>
            Wedday jamoasi
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USERNAME
    msg["To"] = email
    msg["Subject"] = "Tasdiqlash kodingiz - Wedday"
    msg.attach(MIMEText(message_body, "html"))

    # Подключаемся к SMTP-серверу и отправляем письмо
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()
        print("Xat muvaffaqiyatli yuborildi!")
    except Exception as e:
        print(f"Xat yuborishda xatolik yuz berdi: {e}")

    logging.info(f"Tasdiqlash kodingiz '{code}' elektron pochtangizga yuborildi: {email}")

class Register(Resource):
    """
    1) POST /api/register
       JSON: { "email", "fullName", "password" }
       Создаёт пользователя (emailConfirmation=0), генерирует код и отправляет на почту.

    2) PUT /api/register
       JSON: { "email", "code" }
       Проверяет код, если верно - ставит emailConfirmation=1.
    """

    def post(self):
        """
        Шаг 1: создаём запись с emailConfirmation=0, генерируем confirmationCode.
        JSON:
        {
          "email": "user@example.com",
          "fullName": "Test User",
          "password": "Abc12345"
        }
        """
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, help='email is required')
        parser.add_argument('fullName', type=str, required=True, help='fullName is required')
        parser.add_argument('password', type=str, required=True, help='password is required')
        args = parser.parse_args()

        email = args['email'].strip().lower()
        fullName = args['fullName'].strip()
        password = args['password']

        # Простейшая проверка пароля
        if len(password) < 8:
            return {"message": "Пароль должен быть не менее 8 символов"}, 400
        if not any(ch.isupper() for ch in password):
            return {"message": "Должна быть хотя бы одна заглавная буква"}, 400
        if not any(ch.isdigit() for ch in password):
            return {"message": "Должна быть хотя бы одна цифра"}, 400

        hashedPassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Проверяем, нет ли уже такого email
        existingUser = db.Users.getUserByEmail(email)
        if existingUser:
            return {"message": "Такой email уже зарегистрирован"}, 400

        # Генерируем код подтверждения (например, 6 цифр)
        confirmationCode = ''.join(random.choices(string.digits, k=6))

        # Создаём запись
        userId = db.Users.createUserWithData(email, fullName, hashedPassword, confirmationCode)
        if not userId:
            return {"message": "Ошибка при создании пользователя"}, 500

        # Отправляем код на почту (заглушка)
        sendEmailConfirmation(email, confirmationCode)

        logging.info(f"Создан пользователь userId={userId}, email={email}, emailConfirmation=0")
        return {"message": "Регистрация успешна, код отправлен на почту", "userId": userId}, 201

    def put(self):
        """
        Шаг 2: пользователь вводит email и code, если совпадает – emailConfirmation=1
        JSON:
        {
          "email": "user@example.com",
          "code": "123456"
        }
        """
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, help='email is required')
        parser.add_argument('code', type=str, required=True, help='code is required')
        args = parser.parse_args()

        email = args['email'].strip().lower()
        code = args['code'].strip()

        userRow = db.Users.getUserByEmail(email)
        if not userRow:
            return {"message": "Пользователь с таким email не найден"}, 400

        # Проверяем, не подтвержден ли уже
        if userRow['emailConfirmation'] == 1:
            return {"message": "Пользователь уже подтвердил почту"}, 400

        # Сверяем код
        if userRow['confirmationCode'] != code:
            return {"message": "Неверный код подтверждения"}, 400

        # Всё ок – подтверждаем
        success = db.Users.confirmEmail(userRow['userId'])
        if not success:
            return {"message": "Ошибка при подтверждении почты"}, 500

        logging.info(f"Пользователь userId={userRow['userId']} подтвердил почту email={email}")
        return {"message": "Email успешно подтверждён"}, 200
