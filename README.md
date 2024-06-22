```markdown
# europorra_tipstertrust

Este es el repositorio del proyecto `europorra_tipstertrust`, una aplicación en Python que utiliza PostgreSQL para la base de datos y Telegram para la interfaz de usuario. 

## Requisitos

Para poder ejecutar este proyecto, necesitas instalar todas las dependencias utilizando el siguiente comando:

```bash
pip install -r requirements.txt
```

## Configuración

Antes de ejecutar el proyecto, es necesario configurar algunas variables en el código. Estas variables se encuentran en el archivo `config.py` (o directamente en `main.py` si no se utiliza un archivo de configuración separado).

### Variables a modificar por el usuario

```python
postgres_url = "postgresql://user:pass@localhost:5432/europorra_tipstertrust"
telegram_admin = XXXXX  # Tu ID de Telegram
telegram_token = "XXXXZZZZYYYY"
```

#### Configuración de PostgreSQL

Para configurar PostgreSQL, sigue estos pasos:

1. Abre pgAdmin y crea una nueva base de datos.
2. Asigna el nombre `europorra_tipstertrust` a la base de datos.

La URL de conexión (`postgres_url`) debe tener el siguiente formato:

```
postgresql://<usuario>:<contraseña>@<host>:<puerto>/<nombre_base_datos>
```

Por ejemplo:

```python
postgres_url = "postgresql://miusuario:micontraseña@localhost:5432/europorra_tipstertrust"
```

#### Configuración de Telegram

1. **telegram_admin**: Es el ID de la cuenta de Telegram del propietario. Para obtener tu ID, puedes utilizar el bot de Telegram [@myidbot](https://t.me/myidbot). Simplemente envía `/getid` al bot y te responderá con tu ID de Telegram.
   
2. **telegram_token**: Es el token del bot que se crea con [@BotFather](https://t.me/botfather). Sigue estos pasos para obtener el token:
   - Abre un chat con [@BotFather](https://t.me/botfather).
   - Envía `/start` y luego `/newbot`.
   - Sigue las instrucciones para crear un nuevo bot.
   - Una vez creado, recibirás un token de acceso. Utiliza este token para la variable `telegram_token`.

## Ejecución

Para ejecutar el proyecto, utiliza uno de los siguientes comandos en tu terminal:

```bash
python3 main.py
```

o

```bash
python main.py
```

## Contribuciones

Las contribuciones son bienvenidas. Por favor, realiza un fork del repositorio, crea una nueva rama para tus cambios y envía un pull request.

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
```

### Archivo `requirements.txt`

Asegúrate de incluir las siguientes líneas en tu archivo `requirements.txt`:

```
python-telegram-bot==13.7
SQLAlchemy==1.4.20
```

Esto instalará las versiones específicas necesarias para el correcto funcionamiento del proyecto.
