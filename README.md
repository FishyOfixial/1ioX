# 1iox - SIM Manager

Aplicación web para la gestión de tarjetas SIM conectadas a dispositivos IoT, con control de usuarios por rol (matriz, distribuidor, revendedor y cliente), monitoreo de consumo de datos y funciones administrativas para operación diaria.

---

## Funcionalidades

- Autenticación con control de acceso por roles.
- Dashboard interno con métricas de consumo y estado de SIMs.
- Consulta de estado, ICCID, consumo de datos/SMS y fecha de expiración.
- Asignación de SIMs a distribuidores, revendedores y clientes.
- Activación y desactivación de cuentas de usuario.
- Exportación a CSV con soporte para caracteres especiales y formato texto en números.
- Integración con API de 1NCE para consulta operativa.
- Cron jobs para actualización continua de datos.

### Nuevas funcionalidades (Billing / Suscripciones)
- Modelo `MembershipPlan` para planes de membresía.
- Modelo `Subscription` ligado a cada `SimCard`.
- Reglas de negocio de suscripción:
  - `active` enciende la SIM.
  - `suspended`, `cancelled`, `expired` deshabilitan la SIM.
- Acciones de suscripción desde `sim_detail` (sin admin):
  - asignar plan, renovar, cambiar plan, suspender y cancelar.
- Confirmaciones frontend para acciones críticas de suscripción.
- Comando `check_subscriptions` para expiración automática de planes.
- Comando `initialize_existing_sims` para inicialización masiva de SIMs sin suscripción.

### Fechas de suscripción (refactor)
- Soporte de periodos calendario (`day`, `month`, `year`) en planes.
- Cálculo centralizado en `billing/services/subscription_dates.py`.
- Vencimientos normalizados a las `12:00:00` (mediodía).
- Zona horaria de negocio:
  - `TIME_ZONE = 'America/Mexico_City'`
  - `USE_TZ = True`

### Portal de Cliente
- Nueva app `customer_portal` independiente del panel interno.
- Acceso exclusivo para `user_type == 'CLIENTE'`.
- Vista `/portal/` con:
  - listado de SIMs del cliente,
  - buscador por ICCID,
  - filtro por estado de suscripción.
- Vista `/portal/sim/<id>/` solo lectura con:
  - datos de SIM,
  - estado y fechas de suscripción,
  - cuotas disponibles de DATA/SMS (sin gráficas).
- Soporte multiidioma (`es`, `en`, `pt`) usando `preferred_lang`.

---

## Tecnologías utilizadas

- Django (Backend)
- HTML, CSS, JavaScript (Frontend)
- Railway (Deploy)
- API de 1NCE (Integración externa)
- SQLite / PostgreSQL (Base de datos)
- Cron jobs para tareas programadas

---

## Roles de usuario

- **Matriz**: Acceso total a todas las SIMs y usuarios.
- **Distribuidor**: Puede consultar, asignar y gestionar sus propias SIMs.
- **Revendedor**: Gestión operativa según su alcance de asignación.
- **Cliente**: Acceso al portal de cliente para consulta de sus SIMs y suscripciones.

---

## Estado del proyecto

En progreso. El sistema se encuentra operativo y en mejora continua con nuevas capacidades de suscripción y experiencia de cliente final.

---

## Autor

Desarrollado por **Iván Ramos de la Torre**  
Estudiante de Ingeniería en Software y Minería de Datos - Universidad Autónoma de Guadalajara (UAG)

