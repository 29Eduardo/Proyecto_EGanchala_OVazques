"""
TaskHub — Aplicación distribuida de entrega de tareas.
Cada nodo (app1, app2, app3) ejecuta esta misma aplicación; NODE_NAME
identifica al nodo que atendió la petición (útil para verificar el balanceo de NGINX).
"""
import os
from datetime import datetime

import bcrypt
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine, get_db, SessionLocal
from models import Student, Task, Submission

NODE_NAME = os.getenv("NODE_NAME", "app-desconocido")
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")

# Crea las tablas si no existen (idempotente; en producción usar Alembic).
#
# Como los 3 nodos (app1/app2/app3) arrancan casi al mismo tiempo, es normal
# que más de uno intente crear las mismas tablas simultáneamente. MySQL solo
# deja que uno lo logre y a los demás les responde "ya existe" (error 1050);
# eso NO es un fallo real, así que lo ignoramos en vez de dejar que tumbe el
# contenedor.
try:
    Base.metadata.create_all(bind=engine)
except OperationalError as e:
    if "1050" not in str(e) and "already exists" not in str(e):
        raise

# Sembrado automático de datos por defecto (estudiante, profesor, administrador y tareas demo)
def seed_default_data():
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        # 1. Estudiante Demo
        if not db.query(Student).filter(Student.email == "demo@epn.edu.ec").first():
            password_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
            db.add(Student(
                full_name="Estudiante Demo",
                email="demo@epn.edu.ec",
                password_hash=password_hash,
                role="student",
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        # 2. Profesor Demo
        if not db.query(Student).filter(Student.email == "profesor@epn.edu.ec").first():
            password_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
            db.add(Student(
                full_name="Profesor Demo",
                email="profesor@epn.edu.ec",
                password_hash=password_hash,
                role="teacher",
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        # 3. Administrador Demo
        if not db.query(Student).filter(Student.email == "admin@epn.edu.ec").first():
            password_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
            db.add(Student(
                full_name="Administrador Demo",
                email="admin@epn.edu.ec",
                password_hash=password_hash,
                role="teacher",  # Rol 'teacher' para que tenga permisos de gestión (crear tareas, ver entregas)
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        # 4. Tarea TSK-001
        if not db.query(Task).filter(Task.code == "TSK-001").first():
            db.add(Task(
                code="TSK-001",
                title="Introducción a Docker",
                description="Investigar y resumir las ventajas de usar contenedores frente a máquinas virtuales.",
                due_datetime=datetime.now() + timedelta(days=7),
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        # 5. Tarea TSK-002
        if not db.query(Task).filter(Task.code == "TSK-002").first():
            db.add(Task(
                code="TSK-002",
                title="Configurar balanceo de carga",
                description="Configurar NGINX como balanceador de carga por pesos entre 3 nodos.",
                due_datetime=datetime.now() + timedelta(hours=36),
            ))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
    except Exception as e:
        print(f"Error al sembrar datos por defecto: {e}")
        db.rollback()
    finally:
        db.close()

# Ejecutar el sembrado
try:
    seed_default_data()
except Exception as e:
    print(f"Error en la llamada de sembrado: {e}")

app = FastAPI(title="TaskHub")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="views")


# ---------- Helpers ----------

def current_student(request: Request, db: Session):
    student_id = request.session.get("student_id")
    if not student_id:
        return None
    return db.query(Student).filter(Student.id == student_id).first()


def build_task_view(task: Task, submitted_ids: set, now: datetime) -> dict:
    """Calcula el estado visual de una tarea: enviada / vigente / vencida."""
    is_submitted = task.id in submitted_ids
    is_overdue = now > task.due_datetime
    remaining = task.due_datetime - now

    if is_submitted:
        urgency = "done"
    elif is_overdue:
        urgency = "overdue"
    elif remaining.total_seconds() < 60 * 60 * 48:
        urgency = "soon"
    else:
        urgency = "ok"

    return {
        "task": task,
        "is_submitted": is_submitted,
        "is_overdue": is_overdue,
        "urgency": urgency,
    }


# ---------- Rutas ----------

@app.get("/health")
def health():
    """Endpoint simple para comprobar qué nodo respondió (útil al probar el balanceo de NGINX)."""
    return {"status": "ok", "node": NODE_NAME}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if request.session.get("student_id"):
        return RedirectResponse("/tasks")
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": None, "node": NODE_NAME}
    )


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    if request.session.get("student_id"):
        return RedirectResponse("/tasks")
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None, "node": NODE_NAME}
    )


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    full_name = full_name.strip()
    email = email.strip().lower()

    error = None
    if len(full_name) < 2:
        error = "Ingresa tu nombre completo."
    elif "@" not in email:
        error = "Ingresa un correo válido."
    elif len(password) < 6:
        error = "La contraseña debe tener al menos 6 caracteres."
    elif db.query(Student).filter(Student.email == email).first():
        error = "Ya existe una cuenta registrada con ese correo."

    if error:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": error, "node": NODE_NAME,
             "full_name": full_name, "email": email},
        )

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    student = Student(full_name=full_name, email=email, password_hash=password_hash)
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        # Protección extra por si dos registros con el mismo correo llegan casi al mismo tiempo
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Ya existe una cuenta registrada con ese correo.",
             "node": NODE_NAME, "full_name": full_name, "email": email},
        )

    request.session["student_id"] = student.id
    return RedirectResponse("/tasks", status_code=303)


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.email == email).first()
    valid = student and bcrypt.checkpw(password.encode(), student.password_hash.encode())
    if not valid:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Correo o contraseña incorrectos.", "node": NODE_NAME},
        )
    request.session["student_id"] = student.id
    return RedirectResponse("/tasks", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": None, "node": NODE_NAME, "full_name": "", "email": ""},
    )


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    full_name = full_name.strip()
    email = email.strip().lower()

    error = None
    if len(full_name) < 3:
        error = "Ingresa tu nombre completo."
    elif len(password) < 6:
        error = "La contraseña debe tener al menos 6 caracteres."
    elif password != confirm_password:
        error = "Las contraseñas no coinciden."
    elif db.query(Student).filter(Student.email == email).first():
        error = "Ya existe una cuenta registrada con ese correo."

    if error:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request, "error": error, "node": NODE_NAME,
                "full_name": full_name, "email": email,
            },
        )

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    student = Student(full_name=full_name, email=email, password_hash=password_hash)
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        # Protección extra por si dos registros llegan casi al mismo tiempo con el mismo correo
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request, "node": NODE_NAME,
                "full_name": full_name, "email": email,
                "error": "Ya existe una cuenta registrada con ese correo.",
            },
        )

    db.refresh(student)
    request.session["student_id"] = student.id
    return RedirectResponse("/tasks", status_code=303)


@app.get("/tasks/new", response_class=HTMLResponse)
def new_task_form(request: Request, db: Session = Depends(get_db)):
    student = current_student(request, db)
    if not student:
        return RedirectResponse("/login")
    if student.role != "teacher":
        return RedirectResponse("/tasks")
    return templates.TemplateResponse(
        "new_task.html", {"request": request, "student": student, "node": NODE_NAME, "error": None}
    )


@app.post("/tasks/new", response_class=HTMLResponse)
def create_task(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    due_datetime: str = Form(...),
    db: Session = Depends(get_db),
):
    student = current_student(request, db)
    if not student:
        return RedirectResponse("/login")
    if student.role != "teacher":
        return RedirectResponse("/tasks")

    code = code.strip().upper()
    title = title.strip()
    description = description.strip()

    error = None
    try:
        due_dt = datetime.strptime(due_datetime, "%Y-%m-%dT%H:%M")
    except ValueError:
        due_dt = None
        error = "Fecha y hora límite inválida."

    if not error and db.query(Task).filter(Task.code == code).first():
        error = "Ya existe una tarea con ese código."

    if error:
        return templates.TemplateResponse(
            "new_task.html",
            {"request": request, "student": student, "node": NODE_NAME, "error": error,
             "code": code, "title": title, "description": description, "due_datetime": due_datetime},
        )

    task = Task(code=code, title=title, description=description, due_datetime=due_dt)
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "new_task.html",
            {"request": request, "student": student, "node": NODE_NAME,
             "error": "Ya existe una tarea con ese código.",
             "code": code, "title": title, "description": description, "due_datetime": due_datetime},
        )

    return RedirectResponse("/tasks", status_code=303)


@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request, db: Session = Depends(get_db)):
    student = current_student(request, db)
    if not student:
        return RedirectResponse("/login")

    now = datetime.now()
    submitted_ids = {s.task_id for s in student.submissions}
    tasks = db.query(Task).order_by(Task.due_datetime).all()
    task_views = [build_task_view(t, submitted_ids, now) for t in tasks]

    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "student": student, "task_views": task_views, "node": NODE_NAME},
    )


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail(task_id: int, request: Request, db: Session = Depends(get_db)):
    student = current_student(request, db)
    if not student:
        return RedirectResponse("/login")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse("/tasks")

    submission = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .first()
    )

    all_submissions = None
    if student.role == "teacher":
        all_submissions = (
            db.query(Submission)
            .filter(Submission.task_id == task_id)
            .order_by(Submission.submitted_at)
            .all()
        )

    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "student": student,
            "task": task,
            "submission": submission,
            "all_submissions": all_submissions,
            "now": datetime.now(),
            "node": NODE_NAME,
            "error": None,
        },
    )


@app.post("/tasks/{task_id}/submit", response_class=HTMLResponse)
def submit_task(
    task_id: int,
    request: Request,
    response_text: str = Form(...),
    db: Session = Depends(get_db),
):
    student = current_student(request, db)
    if not student:
        return RedirectResponse("/login")
    if student.role == "teacher":
        return RedirectResponse(f"/tasks/{task_id}")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return RedirectResponse("/tasks")

    existing = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .first()
    )

    error = None
    if existing:
        error = "Ya realizaste una entrega para esta tarea."
    elif datetime.now() > task.due_datetime:
        error = "El plazo de entrega para esta tarea ya venció."

    if error:
        return templates.TemplateResponse(
            "task_detail.html",
            {
                "request": request, "student": student, "task": task,
                "submission": existing, "now": datetime.now(),
                "node": NODE_NAME, "error": error,
            },
        )

    submission = Submission(
        student_id=student.id,
        task_id=task_id,
        response_text=response_text.strip(),
        submitted_at=datetime.now(),
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        # Protección extra por condiciones de carrera (dos pestañas enviando a la vez)
        db.rollback()
        return templates.TemplateResponse(
            "task_detail.html",
            {
                "request": request, "student": student, "task": task,
                "submission": existing, "now": datetime.now(),
                "node": NODE_NAME, "error": "Ya realizaste una entrega para esta tarea.",
            },
        )

    return RedirectResponse(f"/tasks/{task_id}", status_code=303)