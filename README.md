# DataNest Backend 

This project is a prototype backend system for **DataNest**, a fictional SaaS startup building analytics dashboards for small businesses. It is developed as part of the **XTechOn Backend Developer Intern Assignment**.

---

## 🚀 Project Overview

The backend is built with **FastAPI** and provides:

### ✅ User Authentication & Authorization
- JWT-based user login, registration, and profile access.
- Role-based access control (`admin` vs `user`).

### 📊 Sales Data Processing
- Admins can upload CSV files with sales data.
- Analytics endpoints for:
  - Total sales, average order value, and transaction count.
  - Top customers.
  - Date-range filtering.

### 🧬 String Compression Utility
- API to compress and decompress strings using `zlib` and `base64`.

---

## 🗂️ Folder Structure

```
FeatureRichPlatform/
├── __pycache__/                # Compiled Python bytecode files
│   ├── app.cpython-313.pyc
│   ├── auth.cpython-313.pyc
│   ├── database.cpython-313.pyc
│   ├── flask_app.cpython-313.pyc
│   ├── models.cpython-313.pyc
│   ├── routes.cpython-313.pyc
├── instance/
│   └── sales_analytics.db      # SQLite database (alternative location)
├── static/                     # Static files for frontend
│   ├── app.js                  # Frontend JavaScript
│   ├── style.css               # Frontend CSS
├── templates/                  # HTML templates
│   └── index.html              # Main frontend page
├── app.py                      # FastAPI application entry point
├── asgi.py                     # ASGI configuration
├── auth.py                     # Authentication logic (JWT, password hashing)
├── create_db.py                # Script to recreate database tables
├── create_users.py             # Script to seed default users
├── database.py                 # Database configuration (SQLite)
├── flask_app.py                # Unused Flask implementation
├── main.py                     # Alternative entry point (optional)
├── models.py                   # SQLAlchemy models (User, SalesRecord)
├── pyproject.toml              # Project metadata and dependencies
├── routes.py                   # API routes (auth, sales, utilities)
├── sales_analytics.db          # SQLite database (primary location)
├── seed_users.py               # Alternative user seeding script
├── start_server.py             # Alternative server startup script
├── utils.py                    # Utility functions
├── uv.lock                     # Dependency lock file
├── wsgi.py                     # WSGI configuration
```

## 📄 Project Output

The final output of the project is available in the PDF report below:

**➡ [Download DataNest Backend Output (PDF)](./DataNest%20Backend%20Output.pdf)**

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FeatureRichPlatform
```

### 2. Create & Activate Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

Ensure `requirements.txt` has:
```
fastapi
uvicorn
sqlalchemy
python-jose[cryptography]
passlib[bcrypt]
python-multipart
pandas
jinja2
bcrypt
```

Then install:
```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python create_db.py
```

### 5. Seed Default Users

```bash
python create_users.py
```

### 6. Run the Server

```bash
uvicorn app:app --reload
```

Visit: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 API Endpoints Overview

### 🔐 Authentication

- **POST** `/auth/register` – Register user
- **POST** `/auth/login` – Login and receive JWT
- **GET** `/auth/profile` – View user profile (auth required)

### 📤 Sales Upload (Admin only)

- **POST** `/sales/upload-sales` – Upload CSV of sales data

### 📈 Analytics

- **GET** `/sales/analytics/summary`
- **GET** `/sales/analytics/top-customers?limit=n`
- **GET** `/sales/analytics/by-date?from=YYYY-MM-DD&to=YYYY-MM-DD`

### 🔄 String Utilities

- **POST** `/api/compress-string`
- **POST** `/api/decompress-string`

---

## 🧪 Testing

### Manual
Use `curl` or Postman with endpoints above.

### Automated

Install pytest:
```bash
pip install pytest
```

Example test:
```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_auth():
    client.post("/auth/register", json={"username": "testadmin", "password": "testpass", "role": "admin"})
    response = client.post("/auth/login", data={"username": "testadmin", "password": "testpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

Run tests:
```bash
pytest tests/
```

---

## 🧰 Troubleshooting

- **404 errors**: Ensure correct endpoint path (`/auth`, `/sales`, `/api`)
- **JWT issues**: Ensure token is provided via `Authorization: Bearer <token>`
- **DB issues**: Re-run `create_db.py` and `create_users.py`

---

## 📬 Submission

- Upload code to GitHub or Zip folder (`zip -r datanest-backend.zip .`)
- Send to: `career@xtechon.com` with subject `Back-end Hiring Assignment - [Your Name]` by **May 30, 2025**

---

## 👨‍💻 Author

**Prashanth Bonkuru**  
📧 bonkuruprashanth05@gmail.com  
🌐 [GitHub: Prashanth2Github](https://github.com/Prashanth2Github)

