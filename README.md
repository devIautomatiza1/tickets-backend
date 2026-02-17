# Soporte Oportunidades - Backend API

FastAPI backend para gestión de tickets y grabaciones de audio con Supabase.

## 🚀 Deploy en Railway

1. Conecta tu repositorio GitHub en [railway.app](https://railway.app)
2. Railway detecta automáticamente `Procfile`
3. Configura variables de entorno en Railway dashboard

## 🔧 Configuración de Entorno

```bash
# Crear archivo .env (no incluir en Git)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-clave-publica
FRONTEND_URL=https://tu-app.vercel.app
ENVIRONMENT=production
LOG_LEVEL=info
```

## 💻 Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn main:app --reload --port 8000

# Ver documentación interactiva
# http://localhost:8000/docs
```

## 📚 Endpoints Principales

- `GET /health` - Health check
- `GET /api/tickets` - Obtener tickets
- `PUT /api/tickets/{id}` - Actualizar ticket
- `POST /api/recordings/upload` - Subir grabación
- `GET /api/recordings` - Obtener grabaciones
- `GET /api/recordings/{id}/download` - Descargar grabación

## 📖 Documentación Interactiva

Después de ejecutar el servidor:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🗄️ Base de Datos

Usa Supabase PostgreSQL. Asegúrate que existan estas tablas:
- `opportunities` - Tickets
- `recordings` - Grabaciones
- Bucket Storage: `tickets`
