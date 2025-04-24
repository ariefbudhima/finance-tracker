project-root/
│
├── app/
│   ├── main.py               # Entry point FastAPI
│   ├── config/               # Konfigurasi global
│   │   └── settings.py
│   ├── core/                 # Core logic umum (auth, middleware, exceptions)
│   │   └── logger.py
│   │
│   ├── domains/
│   │   ├── ocr/
│   │   │   ├── routes.py     # Endpoint khusus OCR
│   │   │   ├── services.py   # Logic OCR (pakai PaddleOCR)
│   │   │   ├── schemas.py    # Request/Response schema (Pydantic)
│   │   │   ├── models.py     # Kalau ada ORM atau entitas OCR
│   │   │   └── __init__.py
│   │   │
│   │   └── whatsapp/
│   │       ├── routes.py     # Endpoint LLM (OpenAI GPT)
│   │       ├── services.py   # Logic komunikasi ke LLM API
│   │       ├── schemas.py    # Schema request/response
│   │       ├── models.py     # Kalau nanti pakai history chat misalnya
│   │       └── __init__.py
│   │
│   └── shared/               # Helper/utils umum
│       ├── http_client.py    # Contoh helper untuk HTTP (ke OpenAI)
│       ├── file_utils.py
│       └── __init__.py
│
├── tests/
│   ├── ocr/
│   └── llm/
│
├── .env
├── requirements.txt
├── README.md
└── run.py                   # Untuk run langsung
