FROM python:3.12-slim

# Fija la zona horaria a Ecuador para que datetime.now() en el servidor
# coincida con la hora que el navegador usa en el formulario de fecha límite
# (sin esto, el contenedor usa UTC por defecto y las tareas aparecen "vencidas"
# antes de tiempo).
ENV TZ=America/Guayaquil
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Instala dependencias primero para aprovechar el cache de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]