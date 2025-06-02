from app import app
import routes  # noqa: F401
from scheduler import start_scheduler

if __name__ == "__main__":
    # Start the scheduler for service reminders
    start_scheduler(app)
    app.run(host="0.0.0.0", port=5000, debug=True)
