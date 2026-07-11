FROM mysql:8.0

# Mismo motivo que en mysql/master/Dockerfile: copiamos el my.cnf dentro de la
# imagen para evitar el problema de permisos "world-writable" de los bind
# mounts en Windows, que hace que MySQL ignore el archivo silenciosamente.
COPY my.cnf /etc/mysql/conf.d/custom.cnf

RUN chmod 0444 /etc/mysql/conf.d/custom.cnf