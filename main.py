from api import app
from data.config import ip, port
import os

if not os.path.exists("logs"):
    os.makedirs("logs")

if __name__ == '__main__':
    from api import handlers
    app.run(debug=True, port=port, host=ip)