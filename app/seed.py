"""
Script para insertar datos de prueba (un estudiante y dos tareas).
Ejecutar una vez dentro de cualquier nodo:
    docker compose exec app1 python seed.py
"""
from datetime import datetime, timedelta

import bcrypt

from database import Base, engine, SessionLocal
from models import Student, Task

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(Student).filter(Student.email == "demo@epn.edu.ec").first():
    password_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    db.add(Student(
        full_name="Estudiante Demo",
        email="demo@epn.edu.ec",
        password_hash=password_hash,
    ))
    print("Estudiante demo creado -> demo@epn.edu.ec / 123456")

if not db.query(Task).filter(Task.code == "TSK-001").first():
    db.add(Task(
        code="TSK-001",
        title="Introducción a Docker",
        description="Investigar y resumir las ventajas de usar contenedores frente a máquinas virtuales.",
        due_datetime=datetime.now() + timedelta(days=7),
    ))

if not db.query(Task).filter(Task.code == "TSK-002").first():
    db.add(Task(
        code="TSK-002",
        title="Configurar balanceo de carga",
        description="Configurar NGINX como balanceador de carga por pesos entre 3 nodos.",
        due_datetime=datetime.now() + timedelta(hours=36),
    ))

db.commit()
db.close()
print("Datos de prueba listos.")
