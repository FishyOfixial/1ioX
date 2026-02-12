# SIM Manager

Aplicación web para la gestión de tarjetas SIM conectadas a dispositivos IoT, con control de usuarios por rol (matriz, distribuidor e instalador), monitoreo de consumo de datos y funciones administrativas como activación, desactivación y eliminación de cuentas.

---

## Funcionalidades

- ✅ Autenticación con control de acceso por roles.
- 📊 Dashboard con métricas de consumo y estado de SIMs.
- 🔍 Consulta de estado, ICCID, consumo de datos/SMS y fecha de expiración.
- 🧑‍💼 Asignación de SIMs a distribuidores e instaladores.
- 🔒 Activación y desactivación de cuentas de usuario.
- 📁 Exportación a CSV con soporte para caracteres especiales y formato texto en números.
- 🔗 Integración con la API de 1NCE para consultar uso en tiempo real.
- 🕐 Cron Jobs para la actualización constante de los datos
  
---

## Tecnologías utilizadas

- 🐍 Django (Backend)
- 🌐 HTML, CSS, JavaScript (Frontend) / Migrando a Tailwind CSS
- 🧑‍💻 Railway (Deploy)
- 🧠 API de 1NCE (Integración externa)
- 🗄️ SQLite / PostgreSQL (Base de datos)
- 🕐 Cron-Job.org (Tareas programadas)
---

## Roles de usuario

- **Matriz**: Acceso total a todas las SIMs y usuarios. Puede administrar distribuidores e instaladores.
- **Distribuidor**: Puede consultar, asignar y gestionar sus propias SIMs.
- **Instalador**: Enlaza SIMs a dispositivos o vehículos, con acceso limitado a datos técnicos.

---

## Estado del proyecto

🟡 En progreso — El proyecto ha concluido su fase activa de desarrollo. Actualmente no se encuentra finalizado, ya que están previstas mejoras y ajustes futuros, incluyendo optimización del estilo visual, adopción de buenas prácticas de maquetación y automatización de procesos de comunicación con clientes.

---


## Autor

Desarrollado por **Iván Ramos de la Torre**  
Estudiante de Ingeniería en Software y Minería de Datos – Universidad Autónoma de Guadalajara (UAG)
