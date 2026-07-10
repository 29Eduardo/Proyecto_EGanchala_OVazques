-- Crea el usuario que el esclavo usará para conectarse y replicar.
-- En un entorno real, cambia 'replpass' por el valor de una variable de entorno.

CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED WITH mysql_native_password BY 'replpass';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
