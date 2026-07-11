FROM mysql:8.0

# Copiamos el my.cnf y el init.sql DENTRO de la imagen en vez de montarlos como
# volumen. En Windows, los archivos montados vía bind mount llegan con permisos
# demasiado abiertos ("world-writable") y MySQL los ignora por seguridad.
# Al copiarlos durante el build, controlamos los permisos nosotros mismos.
COPY my.cnf /etc/mysql/conf.d/custom.cnf
COPY init.sql /docker-entrypoint-initdb.d/init.sql

RUN chmod 0444 /etc/mysql/conf.d/custom.cnf