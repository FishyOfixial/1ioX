# 1iox - Plataforma de Gestion de SIMs IoT

Software empresarial para administracion operativa, comercial y de servicio de SIMs IoT, diseñado para equipos internos y clientes finales bajo un esquema robusto de control por roles.

---

## Vision del Sistema

La plataforma integra en un solo entorno:

- Operacion diaria de inventario y estado de SIMs.
- Gestion de usuarios y jerarquia comercial.
- Control de planes, suscripciones y vigencias.
- Portal de cliente para consulta y autoservicio.
- Integracion con carrier y pasarela de pagos.
- Trazabilidad de eventos criticos para seguimiento operativo.

El objetivo principal es mantener continuidad de servicio, control comercial y visibilidad integral del ciclo de vida de cada SIM.

---

## Arquitectura de Alto Nivel

La solucion esta construida sobre Django con arquitectura modular por dominios.

### `SIM_Control` (Core Operativo)

Modulo principal del panel interno:

- Administracion de usuarios por rol.
- Gestion de SIMs, asignaciones y estado operativo.
- Vistas de supervision y administracion interna.
- Registro de actividad de usuarios y operacion.

### `billing` (Dominio de Servicio y Monetizacion)

Modulo de suscripciones y vigencias:

- Catalogo de planes de membresia.
- Motor de suscripciones por SIM.
- Reglas de activacion, renovacion, suspension, cancelacion y expiracion.
- Sincronizacion de estado de servicio con integraciones externas.
- Automatizacion de control de expiraciones y continuidad.

### `customer_portal` (Canal Cliente)

Modulo de experiencia para cliente final:

- Dashboard de SIMs asignadas.
- Consulta de estado de servicio y vigencia.
- Flujos de renovacion individual y multiple.
- Gestion de renovacion automatica (cuando aplica por plan).

### `auditlogs` (Auditoria Centralizada)

Nuevo modulo para centralizar trazabilidad tecnica y operativa:

- Modelo unificado `SystemLog`.
- Clasificacion por `log_type` y `severity`.
- Soporte para `reference_id`, `metadata` y usuario asociado.
- Helper reutilizable `create_log(...)` para eventos criticos.

---

## Componentes Funcionales Clave

- **Control por roles:** separacion de acceso para operacion interna y portal cliente.
- **Suscripciones como fuente de verdad:** la vigencia del plan gobierna el estado del servicio.
- **Planificacion por periodos calendario:** soporte para periodos diarios, mensuales y anuales.
- **Eventos y trazabilidad:** bitacora de acciones relevantes para auditoria operativa.
- **Procesamiento de pagos:** cobro puntual y capacidades para cobro recurrente segun configuracion de negocio.
- **Automatizacion operativa:** tareas programadas para mantener consistencia de estado.

---

## Actualizaciones Recientes

- Se migro la auditoria a `auditlogs.SystemLog` como fuente unica de logs.
- La vista de administracion en `SIM_Control` ahora muestra exclusivamente `SystemLog`.
- `UserActionLog` dejo de generar nuevos registros (deshabilitado para nuevos eventos).
- Se eliminaron `print()` en backend para evitar ruido en logs de Railway.
- Se estandarizo logging con `logging` y niveles de severidad.
- Se agrego control de llamadas externas para permitir simulacion local sin afectar produccion.
- Se agrego pricing por cliente+plan con ajustes porcentuales (`CustomerPlanPriceOverride`).
- La vista `/administration/` permite crear, editar y eliminar precios personalizados por cliente.
- El checkout individual, masivo y auto-renovacion ahora usan precio efectivo por cliente.
- La sincronizacion `enable/disable` con 1NCE ahora tiene reintentos automaticos en background.
- Los eventos de fallo y recuperacion de sincronizacion registran ICCID en mensaje y metadata.

---

## Simulacion Local Privada (No versionada)

La simulacion de APIs externas se maneja con un archivo local no versionado:

- Archivo local: `services/external_api_local.py`
- Este archivo esta incluido en `.gitignore` y no debe subirse a GitHub.
- Si el archivo no existe, el sistema usa comportamiento real de integracion.
- Produccion no depende de simulaciones locales.

---

## Configuracion Operativa Nueva

Variables utiles para sincronizacion 1NCE:

- `ONE_NCE_STATUS_SYNC_RETRY_IN_BACKGROUND` (default: `True`)
- `ONE_NCE_STATUS_SYNC_RETRY_DELAY_SECONDS` (default: `20`)
- `ONE_NCE_STATUS_SYNC_MAX_RETRIES` (default: `0`, infinito)

Regla de negocio de precio personalizado:

- `adjustment_percent = -20` aplica 20% de descuento sobre `MembershipPlan.price`.
- `adjustment_percent = 15` aplica 15% de recargo sobre `MembershipPlan.price`.

---

## Integraciones Empresariales

La plataforma contempla integraciones con:

- Proveedor de conectividad IoT (carrier).
- Pasarela de pagos para operaciones comerciales.
- Servicios de notificacion y comunicacion.

Por seguridad y gobierno de datos, este documento no publica endpoints internos, credenciales ni detalles sensibles de integracion.

---

## Seguridad y Gobierno de Plataforma

- Gestion de configuracion sensible por entorno.
- Validaciones de acceso por tipo de usuario y contexto funcional.
- Politica de eventos y logging orientada a observabilidad operativa.
- Separacion de responsabilidades entre panel interno y portal cliente.

---

## Entorno Tecnologico

- Django (backend)
- PostgreSQL (entorno productivo)
- WhiteNoise (manejo de estaticos)
- Gunicorn (capa WSGI)
- Infraestructura cloud administrada

---

## Estado del Producto

Producto activo en evolucion continua, con enfoque en estabilidad operativa, escalabilidad comercial y calidad de servicio para clientes IoT.

---

## Autor

**Ivan Ramos de la Torre**  
Ingenieria de Software y Mineria de Datos  
Universidad Autonoma de Guadalajara
