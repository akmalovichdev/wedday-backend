import os
from dotenv import load_dotenv

load_dotenv()

mysqlHost = os.getenv("mysqlHost")
mysqlUser = os.getenv("mysqlUser")
mysqlPassword = os.getenv("mysqlPassword")
mysqlDatabase = os.getenv("mysqlDatabase")

ip = os.getenv("ip")
port = os.getenv("port")

jwtSecretKey = os.getenv('jwtSecretKey')

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")