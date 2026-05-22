# Codex Email Sender

Proyecto de envio masivo por SMTP con SQLite, hecho para que sea facil de correr hoy y tambien facil de entender cuando vuelvas a tocarlo dentro de unos meses.

## Que tiene de bueno este enfoque

- Reserva contactos con estado `processing` antes de enviar para evitar duplicados entre ejecuciones simultaneas.
- Valida la configuracion antes de arrancar y falla con mensajes claros si algo esta mal.
- Cuenta correctamente `sent`, `failed` e `invalid`, incluso cuando hay reintentos.
- Usa backoff exponencial real en los reintentos.
- Cierra mejor las conexiones SQLite y SMTP.
- Permite crear la base de datos desde la linea de comandos.
