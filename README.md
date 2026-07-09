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
           ┌─────▼────┐┌─────▼────┐┌─────▼────┐
           │  App 1   ││  App 2   ││  App 3   │
           │ (peso 3) ││ (peso 2) ││ (peso 1) │
           └─────┬────┘└─────┬────┘└─────┬────┘
                 └──────┬─────┴──────┬────┘
                         ▼            
                 ┌───────────────┐   ┌────────────────┐
                 │  MySQL Master │──▶│  MySQL Replica  │
                 └───────┬───────┘   └────────────────┘
                         ▲
                 ┌───────┴───────┐
                 │    Adminer     │  interfaz web para la BD
                 └───────────────┘
```

Los tres nodos de aplicación ejecutan la **misma imagen Docker**. NGINX distribuye el tráfico entre ellos de forma proporcional a un peso asignado según su capacidad (ver [Balanceo de carga](#balanceo-de-carga-nginx)). Todas las escrituras van al nodo maestro de MySQL, que replica en tiempo real hacia un nodo esclavo de solo lectura.

## Funcionalidades

- [x] Inicio de sesión para estudiantes
- [x] Consulta de tareas disponibles en tiempo real (título, código, descripción, fecha/hora límite)
- [x] Entrega de tareas mediante respuesta de texto
- [x] Validación de fecha y hora límite de entrega
- [x] Restricción de una única entrega por tarea y estudiante
- [x] Visualización de la tarea enviada (título + respuesta)

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python — [FastAPI / Flask] |
| Base de datos | MySQL 8.0 (master-slave) |
| ORM | SQLAlchemy |
| Balanceador de carga | NGINX |
| Contenedores | Docker + Docker Compose |
| Interfaz web para BD | Adminer |
| Pruebas de carga | Locust |

## Estructura del repositorio

```
.
├── app/                    # Código fuente de la aplicación web
│   ├── main.py
│   ├── models.py
│   ├── templates/
│   └── requirements.txt
├── nginx/
│   └── nginx.conf          # Configuración del balanceador (pesos)
├── mysql/
│   ├── master/my.cnf
│   └── slave/my.cnf
├── locust/
│   └── locustfile.py       # Script de pruebas de carga
├── docs/
│   └── informe_tecnico.pdf # Informe técnico del proyecto
├── docker-compose.yml
├── .env.example
└── README.md
```

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose v2
- Git

## Instalación y ejecución local

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

# 2. Configurar variables de entorno
cp .env.example .env
# completar .env con las credenciales necesarias

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

| Variable | Descripción |
|---|---|
| `DB_ROOT_PASSWORD` | Contraseña root de MySQL |
| `DB_NAME` | Nombre de la base de datos |
| `DB_USER` / `DB_PASSWORD` | Credenciales de la aplicación |
| `REPL_USER` / `REPL_PASSWORD` | Credenciales del usuario de replicación |
| `SECRET_KEY` | Clave para firmar sesiones/JWT |

> El archivo `.env` **no** se sube al repositorio (ver `.gitignore`). Usen `.env.example` como plantilla.

## Balanceo de carga (NGINX)

NGINX distribuye las peticiones entre los 3 nodos usando pesos (`weight`) proporcionales a la capacidad asignada a cada contenedor:

```nginx
upstream app_backend {
    server app1:8000 weight=3;
    server app2:8000 weight=2;
    server app3:8000 weight=1;
}
```

Configuración completa en [`nginx/nginx.conf`](./nginx/nginx.conf). La evidencia de la distribución proporcional del tráfico (obtenida con Locust) está documentada en el informe técnico.

## Replicación de base de datos

- **Master:** recibe todas las escrituras, tiene `log-bin` habilitado.
- **Slave:** replica en tiempo real desde el master mediante binlog replication.

Verificación rápida:
```sql
-- En el slave
SHOW REPLICA STATUS\G
-- Replica_IO_Running: Yes
-- Replica_SQL_Running: Yes
```

Detalle completo del proceso de configuración en el informe técnico.

## Pruebas de carga

Las pruebas se ejecutaron con [Locust](https://locust.io/):

```bash
pip install locust
locust -f locust/locustfile.py --host=http://localhost
```

Resultados, gráficos y análisis de desempeño en el informe técnico.

## Despliegue en producción

La infraestructura completa está desplegada en un servidor con Docker Compose (no solo en local):

🔗 **URL de la aplicación:** `http://<IP-o-dominio-del-servidor>`

## Equipo

| Integrante | Rol | GitHub |
|---|---|---|
| [Nombre integrante 1] | Backend + Base de datos | [@usuario1](https://github.com/usuario1) |
| [Nombre integrante 2] | Infraestructura + Despliegue | [@usuario2](https://github.com/usuario2) |

**Asignatura:** Aplicaciones Distribuidas — **Profesora:** Ing. Vanessa Guevara — **Período:** 2026-A

## Informe técnico

El informe técnico completo (arquitectura, configuración, resultados de pruebas, conclusiones) se encuentra en [`docs/informe_tecnico.pdf`](./docs/informe_tecnico.pdf).
