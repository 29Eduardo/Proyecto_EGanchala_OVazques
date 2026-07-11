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

from database import Base, engine, get_db
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
    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "student": student,
            "task": task,
            "submission": submission,
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