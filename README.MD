# Fisioterapia RH – API (Flask)

API base desarrollada en **Flask** para el sistema de gestión de una clínica de fisioterapia.  
Este proyecto establece la estructura inicial del backend, separando responsabilidades por capas y dejando listo el crecimiento hacia autenticación real, base de datos y despliegue.

---

## Tecnologías utilizadas

- Python 3.10+
- Flask
- Python-dotenv
- Pytest
- Gunicorn

---

## Estructura del proyecto

```text
ProyectoIngeniería/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   └── auth_routes.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py
│   │
│   └── models/
│       └── __init__.py
│
├── tests/
│   └── test_auth.py
│
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Clonar el repositorio

```bash
git clone https://github.com/nahum0804/fisioterapia-RH.git
```

## Instalación y ejecución

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Puerto por defecto: **http://127.0.0.1:5000** (/api/...)
