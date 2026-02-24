# 1iox - SIM Management Platform

Plataforma profesional para administracion operativa de SIMs IoT, orientada a equipos internos y clientes empresariales bajo un esquema de acceso por roles.

Este repositorio corresponde al sistema productivo de gestion de servicio, suscripciones y operacion comercial para conectividad IoT.

---

## Resumen Ejecutivo

El sistema centraliza:

- Gestion de inventario y estado de SIMs.
- Operacion multi-rol para canal comercial.
- Control de planes y suscripciones.
- Automatizacion de vencimientos y continuidad del servicio.
- Portal cliente para consulta y renovacion de servicio.
- Integraciones de carrier y cobro.

La solucion se mantiene con arquitectura monolitica en Django, priorizando mantenibilidad, trazabilidad y tiempos de respuesta operativos.

---

## Arquitectura General

### `SIM_Control`
Nucleo operativo interno del negocio:

- Gestion de usuarios por rol y permisos.
- Dashboard interno y vistas de operacion diaria.
- Control de SIMs, asignaciones y configuracion.
- Integracion operativa con servicios externos del carrier.
- Registro de actividad y logs administrativos.

### `billing`
Dominio de monetizacion y vigencia de servicio:

- Catalogo de planes (`MembershipPlan`).
- Ciclo de vida de suscripciones (`Subscription`).
- Reglas de negocio de renovacion, cambio, suspension, cancelacion y expiracion.
- Sincronizacion de estado de servicio con integraciones externas.
- Comandos de mantenimiento y automatizacion por cron.

### `customer_portal`
Experiencia de cliente final (canal autoservicio):

- Portal independiente del panel interno.
- Visualizacion de SIMs y estado de suscripcion.
- Renovacion individual y masiva.
- Flujo de pago con confirmacion previa y desglose.

---

## Capacidades Principales

- Modelo de acceso por perfiles empresariales.
- Gestion de suscripciones como fuente de verdad de servicio.
- Soporte de periodos calendario para vigencias (dia, mes, ano).
- Fechas normalizadas por zona horaria de negocio.
- Flujo de pagos integrado para renovaciones.
- Automatizacion programada para control de expiraciones.
- Trazabilidad de eventos relevantes de integracion.

---

## Integraciones Externas

- Carrier IoT (operacion de estado y consulta).
- Pasarela de pagos (checkout y webhook).
- Correo transaccional para comunicaciones del sistema.

Nota: por politicas de seguridad, este documento omite detalles de endpoints, credenciales, payloads y mecanismos internos de control.

---

## Operacion Programada

El sistema contempla ejecuciones recurrentes via scheduler para tareas operativas y de billing, incluyendo control de expiraciones de suscripcion.

La programacion exacta y frecuencia se definen por ambiente (staging/produccion) segun ventana operativa del negocio.

---

## Seguridad y Gobierno

- Variables sensibles gestionadas por entorno (`.env` / secretos de plataforma).
- Controles de acceso por tipo de usuario.
- Endpoints de automatizacion protegidos por token.
- Politica de logs orientada a eventos de negocio e incidencias.

---

## Despliegue y Entorno

Stack principal:

- Django
- PostgreSQL (produccion)
- WhiteNoise para estaticos
- Gunicorn para ejecucion WSGI

El proyecto soporta despliegue en infraestructura cloud administrada y separacion por ambientes.

---

## Estado del Producto

Plataforma activa en evolucion continua, con foco en estabilidad operativa, experiencia de cliente y escalabilidad comercial.
