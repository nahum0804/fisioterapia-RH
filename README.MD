<h1 align="center">Flask REST API</h1>

<p align="center">
Backend desarrollado en <strong>Flask</strong> con arquitectura modular basada en Blueprints,
orientado a la gestión clínica, planificación, autenticación y automatización de procesos.
</p>

<hr>

## Descripción General

Esta API está diseñada bajo un enfoque estructurado por capas (Routes → Services → Models) y utiliza **SQLAlchemy** como ORM para la gestión de base de datos PostgreSQL.

Incluye:

- Autenticación basada en JWT  
- Gestión de pacientes  
- Gestión de citas y propuestas  
- Planificador (planner) con sincronización  
- Registros clínicos  
- Gestión de usuarios  
- Chatbot con motor de intents  
- Envío de correos automatizados  
- CORS configurado para entornos frontend específicos  

---

## Arquitectura del Proyecto

app/
│
├── models/ # Modelos SQLAlchemy
├── routes/ # Blueprints (controladores HTTP)
├── services/ # Lógica de negocio
├── utils/ # Decoradores y utilidades
├── extensions.py # Inicialización de extensiones
├── db.py # Configuración de base de datos
└── init.py # Factory pattern (create_app)


### Patrón utilizado

- Application Factory (`create_app`)
- Separación clara de responsabilidades
- Blueprints por dominio funcional
- Capa de servicios desacoplada de las rutas

---

## Stack Tecnológico

- Python 3.x  
- Flask  
- Flask-CORS  
- SQLAlchemy  
- PostgreSQL  
- psycopg2  
- python-dotenv  

---

## Configuración de Entorno

La aplicación utiliza variables de entorno definidas en un archivo `.env`.

### Variables requeridas

DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
DB_NAME=
DATABASE_URL= (opcional)


La conexión se construye dinámicamente como:

postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DB_NAME


---

## Instalación y Ejecución

### 1. Clonar el repositorio

git clone <repo-url>
cd <project>


### 2. Crear entorno virtual

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate


### 3. Instalar dependencias

pip install -r requirements.txt


### 4. Ejecutar servidor

python run.py


Servidor por defecto:
http://localhost:5000


---

## Endpoints Principales

| Módulo        | Prefijo Base |
|--------------|-------------|
| Pacientes     | `/api/patients` |
| Citas         | `/api/appointments` |
| Planificador  | `/api/planner` |
| Usuarios      | `/api/users` |
| Registros     | `/api/records` |
| Chatbot       | `/chatbot` |
| Autenticación | Rutas directas |
| Sitio         | Rutas directas |

---

## Seguridad

- Autenticación basada en JWT
- Decoradores personalizados para protección de rutas
- Control de CORS configurado explícitamente
- Separación de lógica de autenticación en `auth_service` y `jwt_service`

---

## Características Técnicas Relevantes

- Manejo estructurado de propuestas de citas
- Sincronización de planificación (`planner_sync`)
- Motor de chatbot basado en intents JSON
- Servicio de envío de correos desacoplado
- Manejo de preflight OPTIONS para evitar redirecciones 308

---

## Buenas Prácticas Implementadas

- Arquitectura limpia y modular
- Bajo acoplamiento entre capas
- Separación clara entre lógica HTTP y lógica de negocio
- Uso del patrón Factory para escalabilidad
- Configuración por entorno mediante variables seguras

---

<p align="center">
Proyecto backend orientado a producción, escalable y mantenible.
</p>
