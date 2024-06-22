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

#### Creación de un Procedimiento en la Base de Datos

Es necesario crear un procedimiento en la base de datos para actualizar los puntos de los usuarios. Puedes hacerlo ejecutando el siguiente script en pgAdmin o en cualquier herramienta de administración de PostgreSQL:

```sql
CREATE OR REPLACE FUNCTION public.update_user_points()
RETURNS void
LANGUAGE 'plpgsql'
COST 100
VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    vote RECORD;
    user_points INTEGER;
BEGIN
    FOR vote IN
        SELECT v.id, v.user_id, v.match_id, v.option AS option1, v.option2, m.result, m.qualifies
        FROM public.votes v
        JOIN public.matches m ON v.match_id = m.id
        WHERE v.notified = false AND m.result IS NOT NULL
    LOOP
        -- Inicializamos los puntos a sumar
        user_points := 0;

        -- Caso 1: result no es nulo y option1 = result
        IF vote.option1 = vote.result THEN
            user_points := 1;
        END IF;

        -- Caso 2: result y qualifies no son nulos, option1 = result y option2 = qualifies
        IF vote.result IS NOT NULL AND vote.qualifies IS NOT NULL AND vote.option1 = vote.result AND vote.option2 = vote.qualifies THEN
            user_points := 3;
        END IF;

        -- Actualizamos los puntos del usuario
        UPDATE public.users
        SET points = COALESCE(points, 0) + user_points
        WHERE id = vote.user_id;

        -- Insertamos en la tabla de notificaciones pendientes
        INSERT INTO public.notifications_pending (user_id, points_earned, match_id, option1, option2, result, qualifies)
        VALUES (vote.user_id, user_points, vote.match_id, vote.option1, vote.option2, vote.result, vote.qualifies);

        -- Marcamos el voto como notificado
        UPDATE public.votes
        SET notified = true
        WHERE id = vote.id;
    END LOOP;
END 
$BODY$;

ALTER FUNCTION public.update_user_points()
OWNER TO postgres;
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
