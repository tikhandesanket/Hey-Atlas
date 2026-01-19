# 🎙️ AI Voice Assistant – Atlas

Atlas is a real-time AI-powered voice assistant built with a web-based frontend and a Python backend using FastAPI and WebSockets.  
It supports low-latency, bidirectional voice communication directly in the browser.

---

## 🚀 Features

- 🎧 Real-time voice input & output
- 🔁 WebSocket-based communication
- ⚡ Low-latency AI responses
- 🌐 Browser-based frontend
- 🧠 LLM-powered intelligence
- 🔄 Hot reload for development

---

## 🛠 Tech Stack

### Frontend

- HTML / JavaScript
- Browser Audio APIs
- Static server (`http.server`)

### Backend

- Python
- FastAPI
- WebSockets
- Uvicorn

---

## 📦 Install Dependencies

- pip install -r requirements.txt

## 📦 Prerequisites

- Python **3.9+**
- pip
- `uvicorn`
- Modern browser (Chrome recommended)

Install backend dependencies:

```bash
pip install fastapi uvicorn
```

## 📦 Start Applications Dependencies

- Hey-Atlas/frontend$ python3 -m http.server 3000
- Hey-Atlas/backend$ uvicorn ws_server:app --reload
