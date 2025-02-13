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
