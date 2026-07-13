#!/bin/sh
# Configura replicación bidireccional (master <-> slave) automáticamente.
# Se ejecuta una sola vez, en un contenedor aparte (ver servicio
# `replica-setup` en docker-compose.yml), que espera a que master y slave
# estén healthy y luego apunta cada uno hacia el otro usando GTID.
set -e

echo "[replica-setup] Esperando a que master y slave terminen de inicializar..."
sleep 10

echo "[replica-setup] Configurando slave -> master (el esclavo lee del maestro)..."
mysql -h mysql-slave -uroot -p"$DB_ROOT_PASSWORD" -e "
  STOP REPLICA;
  CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='mysql-master',
    SOURCE_USER='repl',
    SOURCE_PASSWORD='replpass',
    SOURCE_AUTO_POSITION=1;
  START REPLICA;
"

echo "[replica-setup] Configurando master -> slave (el maestro lee del esclavo)..."
mysql -h mysql-master -uroot -p"$DB_ROOT_PASSWORD" -e "
  STOP REPLICA;
  CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='mysql-slave',
    SOURCE_USER='repl',
    SOURCE_PASSWORD='replpass',
    SOURCE_AUTO_POSITION=1;
  START REPLICA;
"

echo "[replica-setup] Replicación bidireccional configurada. Verificando estado..."

echo "--- Estado en mysql-slave (replicando del maestro) ---"
mysql -h mysql-slave -uroot -p"$DB_ROOT_PASSWORD" -e "SHOW REPLICA STATUS\G" | grep -E "Replica_IO_Running|Replica_SQL_Running|Last_Error"

echo "--- Estado en mysql-master (replicando del esclavo) ---"
mysql -h mysql-master -uroot -p"$DB_ROOT_PASSWORD" -e "SHOW REPLICA STATUS\G" | grep -E "Replica_IO_Running|Replica_SQL_Running|Last_Error"

echo "[replica-setup] Listo."