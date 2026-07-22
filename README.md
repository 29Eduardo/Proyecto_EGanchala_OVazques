# TaskHub — Aplicación Distribuida con Docker

Plataforma web de entrega de tareas académicas, desplegada como una infraestructura distribuida con **3 nodos de aplicación**, **balanceo de carga con NGINX** (por pesos) y **replicación de base de datos MySQL (master-slave)**, orquestada con **Docker Compose**.

Proyecto final — Aplicaciones Distribuidas, Escuela Politécnica Nacional, 2026-A.

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![NGINX](https://img.shields.io/badge/NGINX-Load%20Balancer-009639?logo=nginx&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Master--Slave-4479A1?logo=mysql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Funcionalidades](#funcionalidades)
- [Tecnologías](#tecnologías)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Requisitos previos](#requisitos-previos)
- [Instalación y ejecución local](#instalación-y-ejecución-local)
- [Variables de entorno](#variables-de-entorno)
- [Balanceo de carga (NGINX)](#balanceo-de-carga-nginx)
- [Replicación de base de datos](#replicación-de-base-de-datos)
- [Sesión de usuario y cookies](#sesión-de-usuario-y-cookies)
- [Pruebas de carga](#pruebas-de-carga)
- [Despliegue en producción](#despliegue-en-producción)
- [Equipo](#equipo)
- [Informe técnico](#informe-técnico)

---

## Arquitectura

```
                    ┌──────────────┐
                    │   Usuario    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    NGINX     │  balanceo por pesos
                    │ (load balancer) │
                    └──┬────┬────┬─┘
                ┌──────┘    │    └──────┐
           ┌────▼────┐┌─────▼─────┐┌─────▼─────┐
           │  App 1   ││  App 2   ││  App 3    │
           │ (peso 3) ││ (peso 2) ││ (peso 1)  │
           └─────┬────┘└───────┬───┘└──────┬───┘
                 └───────┬─────┴──────┬────┘
                         ▼            
                 ┌───────────────┐   ┌────────────────┐
                 │  MySQL Master │──▶│  MySQL Replica │
                 └───────┬───────┘   └────────────────┘
                         ▲
                 ┌───────┴───────┐
                 │    Adminer    │  interfaz web para la BD
                 └───────────────┘
```

Los tres nodos de aplicación ejecutan la **misma imagen Docker**. NGINX distribuye el tráfico entre ellos de forma proporcional a un peso asignado según su capacidad (ver [Balanceo de carga](#balanceo-de-carga-nginx)). Todas las escrituras van al nodo maestro de MySQL, que replica en tiempo real hacia un nodo esclavo (la replicación configurada en este proyecto es **bidireccional**: ambos nodos aceptan escrituras y se replican entre sí, ver [Replicación de base de datos](#replicación-de-base-de-datos)).

## Funcionalidades

- [x] Registro e inicio de sesión para estudiantes, profesores y administradores
- [x] Consulta de tareas disponibles en tiempo real (título, código, descripción, fecha/hora límite)
- [x] Entrega de tareas mediante respuesta de texto
- [x] Validación de fecha y hora límite de entrega
- [x] Restricción de una única entrega por tarea y estudiante
- [x] Visualización de la tarea enviada (título + respuesta)
- [x] Asignación de tareas a estudiantes específicos (profesores/administradores)
- [x] Panel de administración: gestión de profesores y estudiantes

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python — FastAPI |
| Base de datos | MySQL 8.0 (replicación master-slave bidireccional) |
| ORM | SQLAlchemy |
| Balanceador de carga | NGINX |
| Contenedores | Docker + Docker Compose |
| Interfaz web para BD | Adminer |
| Pruebas de carga | Locust |

## Estructura del repositorio

```
.
├── app/                      # Código fuente de la aplicación web (Python/FastAPI)
│   ├── main.py                # Rutas: login, registro, tareas, entrega, admin, health
│   ├── models.py               # Modelos SQLAlchemy (Student, Task, Submission, Assignment)
│   ├── database.py             # Conexión a MySQL vía variables de entorno
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── views/                  # Plantillas Jinja2
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── tasks.html
│   │   ├── task_detail.html
│   │   ├── new_task.html
│   │   └── admin.html
│   └── static/
│       └── style.css
├── nginx/
│   └── nginx.conf              # Configuración del balanceador (pesos)
├── mysql/
│   ├── master/
│   │   ├── Dockerfile
│   │   ├── my.cnf
│   │   └── init.sql
│   ├── slave/
│   │   ├── Dockerfile
│   │   ├── my.cnf
│   │   └── init.sql.template
│   └── replica-setup.sh        # Configura la replicación bidireccional al levantar el entorno
├── tests/
│   ├── check_balance.py        # Verifica el reparto de tráfico entre nodos
│   ├── load-test.py            # Pruebas de carga con Locust
│   └── test_roles_and_passwords.py
├── docker-compose.yml
├── .env                        # No se sube al repositorio (ver .gitignore)
├── .gitignore
└── README.md
```

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose v2
- Git

## Instalación y ejecución local

```bash
# 1. Clonar el repositorio
git clone https://github.com/29Eduardo/Proyecto_EGanchala_OVazques.git
cd Proyecto_EGanchala_OVazques

# 2. Crear el archivo .env en la raíz del proyecto (ver sección "Variables de entorno")

# 3. Levantar toda la infraestructura
docker compose up -d --build

# 4. Verificar que todos los contenedores estén corriendo
docker compose ps
```

La aplicación queda disponible en `http://localhost` (a través de NGINX). Adminer queda disponible en `http://localhost:8080` para inspeccionar la base de datos.

Para detener y limpiar el entorno:
```bash
docker compose down -v
```

## Variables de entorno

El proyecto se configura mediante un archivo **`.env`** en la raíz del repositorio. Este archivo **no se sube a git** (ver `.gitignore`), así que cada quien debe crear el suyo localmente.

Ejemplo de `.env` para desarrollo/pruebas:

```env
# Base de datos
DB_ROOT_PASSWORD="Contraseña del usuario"
DB_NAME="Nombre de la base de datos de la aplicación "
DB_USER="Credenciales del usuario de aplicación; se crean automáticamente en ambos nodos de MySQL"
DB_PASSWORD="Clave secreta"

# Aplicación
SECRET_KEY=8xO7vD......
```
## Balanceo de carga (NGINX)

NGINX distribuye las peticiones entre los 3 nodos usando pesos (`weight`) proporcionales a la capacidad asignada a cada contenedor:

```nginx
upstream app_backend {
    server app1:8000 weight=3;
    server app2:8000 weight=2;
    server app3:8000 weight=1;
}
```

Configuración completa en [`nginx/nginx.conf`](./nginx/nginx.conf). La evidencia de la distribución proporcional del tráfico (obtenida con `tests/check_balance.py` y Locust) está documentada en el informe técnico.

## Replicación de base de datos

- **Maestro (`mysql-master`)** y **esclavo (`mysql-slave`)** se replican mutuamente mediante binlog + GTID (replicación **bidireccional**: ambos aceptan escrituras).
- El contenedor `replica-setup` configura automáticamente la replicación en ambos sentidos al iniciar el entorno (ver [`mysql/replica-setup.sh`](./mysql/replica-setup.sh)).
- Para evitar colisiones de claves primarias entre nodos, cada uno usa un offset distinto de `auto_increment` (maestro: IDs impares, esclavo: IDs pares).

Verificación rápida (en cualquiera de los dos nodos):
```sql
SHOW REPLICA STATUS\G
-- Replica_IO_Running: Yes
-- Replica_SQL_Running: Yes
```

Detalle completo del proceso de configuración en el informe técnico.
## Pruebas de carga

Las pruebas se ejecutaron con [Locust](https://locust.io/):

```bash
pip install locust
locust -f tests/load-test.py --host=http://localhost
```

Resultados, gráficos y análisis de desempeño en el informe técnico.

## Equipo

| Integrante | GitHub |
|---|---|
| Eduardo Ganchala | [29Eduardo](https://github.com/29Eduardo) |
| Oscar Vasquez  | [xOscar](https://github.com/Oscar-byte-c) |

**Asignatura:** Aplicaciones Distribuidas — **Profesora:** Ing. Vanessa Guevara — **Período:** 2026-A

## Informe técnico

El informe técnico completo (arquitectura, configuración, resultados de pruebas, conclusiones) se encuentra en [`docs/informe_tecnico.pdf`](./docs/informe_tecnico.pdf).
