import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "my-backup-project-secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUP_DIR, exist_ok=True)


# Initialize Backup Activity Logs
def init_backup_logs():

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS backup_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            action TEXT,
            status TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# Save Backup Activity
def record_backup_log(filename, action, status, message):

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        INSERT INTO backup_logs
        (filename, action, status, message, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        filename,
        action,
        status,
        message,
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    ))

    conn.commit()
    conn.close()

# Verify Backup Database Integrity
def verify_backup_file(filename):

    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".db")
    ):
        return False, "Invalid backup filename"

    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        return False, "Backup file not found"

    try:
        conn = sqlite3.connect(backup_path)

        result = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        conn.close()

        if result and result[0] == "ok":
            return True, "Database integrity verified successfully"

        return False, str(result)

    except sqlite3.Error as error:
        return False, str(error)


# Admin authentication
ADMIN_USERNAME = "bhanu"

ADMIN_PASSWORD_HASH = generate_password_hash("bhanu@123")


# Login protection
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "admin" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# Database connection
def get_db():
    return sqlite3.connect(DB_PATH)


# Create database
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()



# Automatic Backup Function with Activity Logging
def create_backup():

    filename = "Not created"
    source = None
    destination = None

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"backup_{timestamp}.db"

        backup_path = os.path.join(BACKUP_DIR, filename)

        source = sqlite3.connect(DB_PATH)
        destination = sqlite3.connect(backup_path)

        # Create database backup
        source.backup(destination)

        source.close()
        source = None

        destination.close()
        destination = None

        print("Backup successful:", filename)

        # Record successful backup
        try:
            record_backup_log(
                filename,
                "Automatic Backup",
                "Success",
                "Backup created successfully"
            )
        except Exception as log_error:
            print("Backup log error:", log_error)

        return True

    except Exception as error:

        print("Backup failed:", error)

        # Record failed backup
        try:
            record_backup_log(
                filename,
                "Automatic Backup",
                "Failed",
                str(error)
            )
        except Exception as log_error:
            print("Failure log error:", log_error)

        return False

    finally:
        if source is not None:
            source.close()

        if destination is not None:
            destination.close()


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if (username == ADMIN_USERNAME and
                check_password_hash(ADMIN_PASSWORD_HASH, password)):

            session.clear()
            session["admin"] = username

            return redirect(url_for("index"))

        flash("Invalid username or password!", "error")

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# Main dashboard
@app.route("/")
@login_required
def index():

    conn = get_db()

    records = conn.execute(
        "SELECT * FROM records ORDER BY id DESC"
    ).fetchall()

    conn.close()

    backups = sorted(
        [
            {
                "name": f,
                "size": round(
                    os.path.getsize(os.path.join(BACKUP_DIR, f)) / 1024, 2
                ),
                "date": datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(BACKUP_DIR, f))
                ).strftime("%d-%m-%Y %H:%M:%S")
            }
            for f in os.listdir(BACKUP_DIR)
            if f.endswith(".db")
            and os.path.isfile(os.path.join(BACKUP_DIR, f))
        ],
        key=lambda x: x["date"],
        reverse=True
    )

    print("BACKUP DATA:", backups)

    return render_template(
        "index.html",
        records=records,
        total_records=len(records),
        backups=backups,
        last_backup=backups[0]["name"] if backups else "No backup yet",
        backup_interval=BACKUP_INTERVAL_MINUTES
    )



# Add data
@app.route("/add", methods=["POST"])
def add_record():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("Enter a title.", "error")
        return redirect(url_for("index"))

    conn = get_db()

    conn.execute(
        "INSERT INTO records (title, description, created_at) VALUES (?, ?, ?)",
        (title, description, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

    flash("Record added successfully!", "success")
    return redirect(url_for("index"))


# Manual backup
@app.route("/backup", methods=["POST"])
def manual_backup():
    if create_backup():
        flash("Backup created successfully!", "success")
    else:
        flash("Backup failed!", "error")

    return redirect(url_for("index"))


# Restore backup
@app.route("/restore/<filename>", methods=["POST"])
def restore_backup(filename):

    if os.path.basename(filename) != filename or not filename.endswith(".db"):
        flash("Invalid backup filename.", "error")
        return redirect(url_for("index"))

    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        flash("Backup not found.", "error")
        return redirect(url_for("index"))

    try:
        source = sqlite3.connect(backup_path)

        result = source.execute("PRAGMA integrity_check").fetchone()

        if not result or result[0] != "ok":
            source.close()
            raise ValueError("Backup is damaged.")

        # Save current data before restoration
        create_backup()

        destination = get_db()
        source.backup(destination)

        destination.close()
        source.close()

        flash("Data restored successfully!", "success")

    except Exception as error:
        flash(f"Restore failed: {error}", "error")

    return redirect(url_for("index"))

# Backup scheduling configuration
BACKUP_INTERVAL_MINUTES = 5

# Automatic backup scheduler
scheduler = BackgroundScheduler()

scheduler.add_job(
    create_backup,
    trigger="interval",
    minutes=BACKUP_INTERVAL_MINUTES,
    id="auto_backup",
    replace_existing=True
)



# Download Backup Route
@app.route("/download/<filename>")
@login_required
def download_backup(filename):

    # Security check
    if os.path.basename(filename) != filename or not filename.endswith(".db"):
        flash("Invalid backup file!", "error")
        return redirect(url_for("index"))

    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        flash("Backup file not found!", "error")
        return redirect(url_for("index"))

    return send_from_directory(
        BACKUP_DIR,
        filename,
        as_attachment=True
    )

print("REGISTERED ROUTES:")
print(app.url_map)


# Update automatic backup schedule
@app.route("/schedule", methods=["POST"])
@login_required
def update_schedule():

    global BACKUP_INTERVAL_MINUTES

    allowed_intervals = [1, 5, 10, 30, 60]

    try:
        minutes = int(request.form.get("interval"))

        if minutes not in allowed_intervals:
            flash("Invalid backup interval!", "error")
            return redirect(url_for("index"))

        # Update the existing scheduler job
        scheduler.reschedule_job(
            "auto_backup",
            trigger="interval",
            minutes=minutes
        )

        BACKUP_INTERVAL_MINUTES = minutes

        flash(
            f"Automatic backup updated to every {minutes} minutes!",
            "success"
        )

    except Exception as error:
        flash(f"Schedule update failed: {error}", "error")

    return redirect(url_for("index"))


# Backup Monitoring Dashboard
@app.route("/monitoring")
@login_required
def monitoring():

    backup_files = []

    for filename in os.listdir(BACKUP_DIR):

        file_path = os.path.join(BACKUP_DIR, filename)

        if filename.endswith(".db") and os.path.isfile(file_path):

            backup_files.append({
                "name": filename,
                "size": round(os.path.getsize(file_path) / 1024, 2),
                "date": datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).strftime("%d-%m-%Y %H:%M:%S")
            })

    backup_files.sort(
        key=lambda item: item["date"],
        reverse=True
    )

    total_backups = len(backup_files)

    total_storage = round(
        sum(item["size"] for item in backup_files) / 1024, 2
    )

    latest_backup = (
        backup_files[0]["date"]
        if backup_files else "No backup available"
    )

    scheduler_status = (
        "Running" if scheduler.running else "Stopped"
    )

    return render_template(
        "monitoring.html",
        backup_files=backup_files,
        total_backups=total_backups,
        total_storage=total_storage,
        latest_backup=latest_backup,
        scheduler_status=scheduler_status
    )


# Backup Verification Route
@app.route("/verify/<filename>", methods=["POST"])
@login_required
def verify_backup(filename):

    success, message = verify_backup_file(filename)

    status = "Success" if success else "Failed"

    record_backup_log(
        filename,
        "Integrity Verification",
        status,
        message
    )

    if success:
        flash("Backup verified successfully!", "success")
    else:
        flash("Backup verification failed: " + message, "error")

    return redirect(url_for("logs"))


# Backup Activity Logs and Statistics
@app.route("/logs")
@login_required
def logs():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    logs_data = conn.execute(
        "SELECT * FROM backup_logs ORDER BY id DESC"
    ).fetchall()

    total_automatic = conn.execute(
        """SELECT COUNT(*) FROM backup_logs
           WHERE action = 'Automatic Backup'"""
    ).fetchone()[0]

    successful = conn.execute(
        """SELECT COUNT(*) FROM backup_logs
           WHERE action = 'Automatic Backup'
           AND status = 'Success'"""
    ).fetchone()[0]

    failed = conn.execute(
        """SELECT COUNT(*) FROM backup_logs
           WHERE action = 'Automatic Backup'
           AND status = 'Failed'"""
    ).fetchone()[0]

    conn.close()

    return render_template(
        "logs.html",
        logs=logs_data,
        total_automatic=total_automatic,
        successful=successful,
        failed=failed
    )


if __name__ == "__main__":

    init_db()
    init_backup_logs()
    scheduler.start()

    print("Automatic backup system started!")

    try:
        app.run(debug=True, use_reloader=False)
    finally:
        scheduler.shutdown()