# Server Auto Backup System

A Python Flask-based web application designed to automatically create, manage, monitor, and restore server database backups.

## 🚀 Project Overview

The Server Auto Backup System helps protect important database records by creating automatic backups and providing an easy-to-use web interface to manage backup operations.

## ✨ Features

- **User Authentication:** Secure login and logout functionality.
- **Automatic Backup:** Automatically creates database backups.
- **Manual Backup:** Users can create backups whenever required.
- **Backup History:** Displays available backup files with date and size.
- **Download Backup:** Download backup files to a local system.
- **Restore Backup:** Restore database from previously created backups.
- **Backup Monitoring:** Monitor backup activities.
- **Activity Logs:** Track backup verification activities and alerts.
- **Database Verification:** Verify database backup integrity.

## 🛠️ Technologies Used

- Python
- Flask
- SQLite3
- HTML5
- CSS3
- JavaScript
- APScheduler

## 📁 Project Structure

```text
server-auto-backup/
│
├── app.py
├── app.db
├── requirements.txt
├── README.md
├── LICENSE
│
├── backups/
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── logs.html
│   └── monitoring.html
│
└── static/
    ├── style.css
    └── script.js
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bhanumaheshkoya18-art/server-auto-backup.git
```

### 2. Navigate to Project Folder

```bash
cd server-auto-backup
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the Application

```bash
python app.py
```

### 7. Open in Browser

```text
http://127.0.0.1:5000/
```

## 🔐 Security

- Login authentication is provided.
- Backup downloads require authentication.
- Backup filenames are validated.
- Database backups are stored separately.

**Important:** Configure a secure Flask secret key before deployment. Do not upload passwords, private credentials, or sensitive database files to GitHub.

## 🎯 Project Objective

The main objective of this project is to reduce data loss risks through automated database backup, backup monitoring, integrity verification, and database restoration.

## 👨‍💻 Author

Developed as a Python Flask-based Server Auto Backup System project.

## 📄 License

This project is licensed under the MIT License.
