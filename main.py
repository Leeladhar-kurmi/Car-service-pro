from app import app
from scheduler import start_scheduler

if __name__ == '__main__':
    start_scheduler(app)
    app.run(debug=True, host='127.0.0.1', port=5000)
