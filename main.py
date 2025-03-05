from api import app, api
from data.db import initDB
from data.config import ip, port

# Импортируем наши ресурсы
from api.handlers.register import Register
from api.handlers.login import Login
from api.handlers.profile import Profile
from api.handlers.cards import Cards
from api.handlers.categories import Categories

if __name__ == '__main__':
    initDB()  # Проверка/создание таблиц

    api.add_resource(Register, '/api/register')  # POST, PUT
    api.add_resource(Login, '/api/login')        # POST
    api.add_resource(Profile, '/api/profile')    # GET
    api.add_resource(Cards, '/api/cards')        # POST,GET,PUT,DELETE
    api.add_resource(Categories, '/api/categories')  # POST,GET,PUT,DELETE

    app.run(debug=True, host=ip, port=port)
