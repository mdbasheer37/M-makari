# 📺 Makari Islamic TV

A complete, production-ready Islamic streaming platform dedicated to the lectures, tafsir, and teachings of **Malam Ibrahim Makari**.

---

## ✨ Features

| Feature | Status |
|---|---|
| Splash Screen + Onboarding | ✅ |
| Home Page (Featured, Trending, Live, Categories) | ✅ |
| Tafsir Section | ✅ |
| Audio Player (Stream, Download, Speed, Sleep Timer) | ✅ |
| Video Player (YouTube embed + Direct stream) | ✅ |
| Live Streaming | ✅ |
| 10 Content Categories | ✅ |
| Full-text Search | ✅ |
| Favorites System | ✅ |
| Downloads (offline) | ✅ |
| Push Notifications | ✅ |
| Islamic Library (Books/PDFs) | ✅ |
| Prayer Times (GPS-based) | ✅ |
| Qibla Direction Compass | ✅ |
| User Authentication (Register/Login) | ✅ |
| Admin Dashboard | ✅ |
| Dark Mode + Light Mode | ✅ |
| Hausa + English Language | ✅ |
| Mobile-first Responsive Design | ✅ |
| Skeleton Loaders + Shimmer Effects | ✅ |

---

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Mobile-first PWA)
- **Backend:** Python FastAPI
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Auth:** JWT (python-jose + bcrypt)
- **Media:** Static file serving + YouTube embed + Direct stream
- **Deployment:** Render / Railway

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Seed database with demo content
python seed.py

# Run the server
uvicorn main:app --reload --port 8000
```

API will be live at: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### 2. Frontend

Simply open `frontend/index.html` in a browser, or serve it:

```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

The frontend auto-detects the API at `localhost:8000` in development.

---

## 🔐 Default Admin Account

```
Email:    admin@makariilamictv.com
Password: admin123
```

> ⚠️ Change this immediately in production!

---

## 📁 Project Structure

```
makari-islamic-tv/
├── frontend/
│   └── index.html          # Complete single-page app
├── backend/
│   ├── main.py             # FastAPI entry point
│   ├── database.py         # DB connection + session
│   ├── models.py           # All SQLAlchemy models
│   ├── auth_utils.py       # JWT + password utilities
│   ├── seed.py             # Demo data seeder
│   ├── requirements.txt
│   ├── .env.example
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       ├── lectures.py
│       ├── videos.py
│       ├── audio.py
│       ├── categories.py
│       ├── search.py
│       ├── favorites.py
│       ├── downloads.py
│       ├── live.py
│       ├── library.py
│       ├── notifications.py
│       ├── admin.py
│       └── prayer.py
└── deployment/
    └── render.yaml
```

---

## 🌐 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |

### Lectures
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/lectures/` | All lectures (paginated) |
| GET | `/api/lectures/featured` | Featured lectures |
| GET | `/api/lectures/trending` | Trending |
| GET | `/api/lectures/latest` | Latest |
| GET | `/api/lectures/most-viewed` | Most viewed |
| GET | `/api/lectures/{id}` | Single lecture |
| POST | `/api/lectures/` | Create (admin) |
| PUT | `/api/lectures/{id}` | Update (admin) |
| DELETE | `/api/lectures/{id}` | Delete (admin) |

### Media
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/videos/` | Video list |
| POST | `/api/videos/upload` | Upload video (admin) |
| GET | `/api/audio/` | Audio list |
| POST | `/api/audio/upload` | Upload audio (admin) |

### Categories
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/categories/` | All categories |
| GET | `/api/categories/{slug}/lectures` | Lectures by category |
| POST | `/api/categories/` | Create (admin) |

### Live
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/live/` | All streams |
| GET | `/api/live/active` | Currently live |
| POST | `/api/live/` | Create stream (admin) |
| PATCH | `/api/live/{id}/toggle` | Go live/offline |

### Library
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/library/books` | All books |
| GET | `/api/library/books/{id}` | Single book |
| POST | `/api/library/books/upload` | Upload PDF |

### Prayer
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/prayer/times?lat=X&lng=Y` | Prayer times |
| GET | `/api/prayer/qibla?lat=X&lng=Y` | Qibla direction |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/stats` | Dashboard stats |
| GET | `/api/admin/users` | All users |
| PATCH | `/api/admin/users/{id}/toggle` | Enable/disable user |
| PATCH | `/api/admin/users/{id}/role` | Change user role |

### Notifications
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notifications/` | User notifications |
| POST | `/api/notifications/send` | Broadcast (admin) |
| PATCH | `/api/notifications/{id}/read` | Mark read |

### Search
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/search/?q=QUERY` | Full-text search |

---

## ☁️ Deploy to Render

1. Push code to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set root directory to `backend/`
4. Build command: `pip install -r requirements.txt && python seed.py`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `SECRET_KEY=your-secret-key`
7. For the frontend: create a **Static Site** pointing to `frontend/`

Or use the provided `render.yaml` for automatic setup.

---

## 🚂 Deploy to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy backend
cd backend
railway login
railway init
railway up

# Set env vars
railway variables set SECRET_KEY=your-secret-key
railway variables set DATABASE_URL=postgresql://...
```

---

## 🎨 Design System

| Token | Value |
|---|---|
| Primary Green | `#1e7e3c` |
| Gold Accent | `#c9a227` |
| Background | `#0b1410` |
| Card BG | `#141f19` |
| Font Display | Amiri (Arabic-style) |
| Font Body | Outfit |

---

## 📱 PWA Support

To enable PWA (installable app):

1. Add `manifest.json` to frontend/
2. Add a service worker for offline caching
3. Configure HTTPS on your deployment

---

## 📄 License

Built for **Makari Islamic TV** — All rights reserved.

---

*Alhamdulillah — May Allah bless this project and make it beneficial to the Ummah.*
