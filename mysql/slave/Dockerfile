FROM mysql:8.0

COPY my.cnf /etc/mysql/conf.d/custom.cnf

# Las credenciales del usuario de la app se toman del .env (ver docker-compose.yml,
# sección build.args de mysql-slave) para no hardcodear contraseñas en el repo.
ARG DB_USER
ARG DB_PASSWORD
ARG DB_NAME

COPY init.sql.template /docker-entrypoint-initdb.d/init.sql.template

RUN sed \
      -e "s/__DB_USER__/${DB_USER}/g" \
      -e "s/__DB_PASSWORD__/${DB_PASSWORD}/g" \
      -e "s/__DB_NAME__/${DB_NAME}/g" \
      /docker-entrypoint-initdb.d/init.sql.template > /docker-entrypoint-initdb.d/init.sql \
    && rm /docker-entrypoint-initdb.d/init.sql.template

# Mismo motivo que en mysql/master/Dockerfile: copiamos el my.cnf dentro de la
# imagen para evitar el problema de permisos "world-writable" de los bind
# mounts en Windows, que hace que MySQL ignore el archivo silenciosamente.

RUN chmod 0444 /etc/mysql/conf.d/custom.cnf