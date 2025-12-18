---

# 🎉 Event Management System (Flask Web App)

## 📌 Project Overview

The **Event Management System** is a Flask-based web application that helps users create, manage, and view events efficiently.
It allows event organizers to handle event details such as title, date, time, and description through a simple web interface.

This project is built using **Python Flask**, **HTML/CSS**, and **SQLite**.

---

## 🛠️ Technologies Used

* **Python 3**
* **Flask**
* **SQLite**
* **HTML / CSS**
* **Jinja2 Templates**

---

## 🚀 Features

* Create new events
* View upcoming events
* Update and delete events
* User-friendly web interface
* Lightweight and easy to deploy

---

## 📂 Project Structure

```
event_management/
│
├── app.py
├── requirements.txt
├── instance/
│   └── events.db
├── templates/
│   ├── home.html
│   ├── create_event.html
│   └── view_events.html
├── static/
│   └── style.css
└── README.md
```

---

## ⚙️ Setup Instructions (Important)

### ✅ Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/event-management-flask.git
cd event-management-flask
```

---

### ✅ Step 2: Create a Virtual Environment

> **Using a virtual environment is mandatory before running the app**

#### 🔹 On Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### 🔹 On macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### ✅ Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

### ✅ Step 4: Run the Flask Application

```bash
python app.py
```

---

### ✅ Step 5: Open in Browser

Go to:

```
http://127.0.0.1:5000/
```

---

## 🗄️ Database

* Uses **SQLite**
* Database file is stored inside the `instance/` folder
* Automatically created when the app runs for the first time

---

## 📌 Requirements File (`requirements.txt`)

```
Flask
Flask-SQLAlchemy
Werkzeug
```

---

## 🧪 Testing

* Manual testing via browser
* CRUD operations tested for events

---

## 🔐 Security

* Uses Flask session management
* Secret key configured for session handling

---

## 📈 Future Enhancements

* User authentication (Login/Register)
* Event registration for participants
* Email notifications
* Admin dashboard
* Deployment on cloud (AWS / Render / Railway)

---

## 👩‍💻 Author

**Vishnu Priya**
Flask Web Application Developer

---

## 📄 License

This project is for **educational purposes**.

---
