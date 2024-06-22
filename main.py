from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from datetime import datetime, timedelta
import threading
import traceback
from threading import Thread
import time
from sqlalchemy import desc, asc
from sqlalchemy.orm import aliased

Base = declarative_base()
active_threads = []

# VARIABLES A MODIFICAR POR EL USUARIO
postgres_url = "postgresql://user:pass@localhost:5432/europorra_tipstertrust"
telegram_admin = XXXXX  # Tu ID de Telegram
telegram_token = "XXXXZZZZYYYY"

# Configurar la base de datos para usar PostgreSQL
engine = create_engine(postgres_url)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Crear una sesión
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)
    points = Column(Integer, default=0)

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    match_time = Column(DateTime, nullable=False)
    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime, nullable=False)
    notified = Column(Boolean, default=False)
    pre_close_notified = Column(Boolean, default=False)
    close_notified = Column(Boolean, default=False)
    admin_notified = Column(Boolean, default=False)  # Nueva columna
    qualy = Column(Boolean, default=False)
    result = Column(String)
    qualifies = Column(String)

class NotificationsPending(Base):
    __tablename__ = 'notifications_pending'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    points_earned = Column(Integer, nullable=False)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    option1 = Column(String, nullable=False)
    option2 = Column(String)
    result = Column(String, nullable=False)
    qualifies = Column(String)
    notified = Column(Boolean, default=False)

    user = relationship('User')
    match = relationship('Match')

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    option = Column(String, nullable=False)
    option2 = Column(String)
    notified = Column(Boolean, default=False)

    user = relationship('User')
    match = relationship('Match')

# Decorador para manejar operaciones de base de datos
def handle_db_operations(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                result = func(*args, **kwargs)
                session.commit()
                return result
            except OperationalError:
                if session.is_active:
                    session.rollback()
                print("ERROR!!!! Operación fallida. Intentando reconectar...")
                reconnect()
                traceback.print_exc()  # Imprime la traza completa de la excepción
            except SQLAlchemyError as e:
                if session.is_active:
                    session.rollback()
                print(f"ERROR!!!! Error en la operación de base de datos: {e}")
                traceback.print_exc()  # Imprime la traza completa de la excepción
                break
    return wrapper

# Función de reconexión
def reconnect():
    global session
    session.close()
    time.sleep(5)  # Espera 5 segundos antes de intentar reconectar
    session = Session()

@handle_db_operations
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name if user.first_name else ""
    last_name = user.last_name if user.last_name else ""
    name = f"{first_name} {last_name}"

    existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    update.message.reply_text(
        '''👋 ¡<strong>Bienvenido</strong> a EuroPorra, la competición de predicciones de la Eurocopa organizada por @TipsterTrust!\n\nPara participar, simplemente espera a que te lleguen las notificaciones de cada partido.\n\nEl ganador de EuroPorra se llevará un premio de <strong>100€</strong>, que será transferido en un plazo máximo de <strong>3 días</strong> tras la finalización del torneo (En caso de empate en puntos se dividirá equitativamente entre los ganadores).\n\n24 horas antes de cada partido, recibirás un mensaje con un comando para votar. Utiliza "/votar [ID]" para indicar tu predicción, donde <strong>ID</strong> es el identificador único del partido proporcionado en el mensaje. Tienes hasta <strong>una hora antes del inicio del partido</strong> para votar o modificar tu predicción.\n\nEn los partidos de clasificación, puedes votar por el equipo que clasifica. En caso de acertar el resultado y la clasificación, recibirás <strong>3 puntos</strong> en vez de uno.\n\nPara consultar tus puntos, utiliza el comando "/consultar". Y para ver el ranking con los 10 mejores participantes, emplea el comando "/ranking". ¡Prepárate para disfrutar de la emoción de la Eurocopa y demuestra tus habilidades de predicción con EuroPorra! 🏆⚽️😊''', parse_mode=ParseMode.HTML)
    if not existing_user:
        new_user = User(telegram_id=telegram_id, username=username, name=name)
        session.add(new_user)
        session.commit()
        
        enviar_partidos_disponibles(update.message.bot, user)

@handle_db_operations
def enviar_partidos_disponibles(bot, user):
    now = datetime.now()
    matches = session.query(Match).filter(Match.open_time <= now, Match.close_time >= now).all()

    if matches:
        for match in matches:
            try:
                bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hola! Hay un partido disponible para votar:\n⚽️ {match.home_team} vs {match.away_team}\n"
                         f"⏰ Hora de inicio: {match.match_time}\n"
                         f"⏳ Hora límite para votar: {match.match_time - timedelta(hours=1)}\n\n"
                         f"🗳 Puedes votar en este partido escribiendo:\n /votar {match.id}\n\nRecuerda que el número después del comando es el identificador del partido, en  este caso {match.id}."
                )
            except Exception as e:
                print(f"Error al enviar mensaje del partido {match.id}: {e}")
        print("NOTIFICACION COMPLETA")

@handle_db_operations
def votar(update: Update, context: CallbackContext) -> None:
    try:
        match_id = int(context.args[0])
        match = session.query(Match).filter_by(id=match_id).first()
        if match.open_time > datetime.now():
            update.message.reply_text('Aún no puedes votar en este partido. Se abrirá la votación 24h antes de su comienzo..')
            return
        if not match:
            update.message.reply_text('ID de partido no válido.')
            return

        if datetime.now() > match.close_time:
            update.message.reply_text('Es demasiado tarde para votar en este partido.')
            return

        if match.qualy:
            keyboard = [
                [InlineKeyboardButton("Resultado: X y clasifica: 1", callback_data=f"{match_id}_X_1")],
                [InlineKeyboardButton("Resultado: X y clasifica: 2", callback_data=f"{match_id}_X_2")],
                [InlineKeyboardButton("Resultado: 1", callback_data=f"{match_id}_1")],
                [InlineKeyboardButton("Resultado: 2", callback_data=f"{match_id}_2")],

            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            keyboard = [
                [
                    InlineKeyboardButton("1", callback_data=f"{match_id}_1"),
                    InlineKeyboardButton("X", callback_data=f"{match_id}_X"),
                    InlineKeyboardButton("2", callback_data=f"{match_id}_2"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"Vota para el partido {match.home_team} vs {match.away_team}:", reply_markup=reply_markup)

    except (IndexError, ValueError):
        update.message.reply_text('Uso incorrecto. Debes usar /votar IDPARTIDO')


@handle_db_operations
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    try:
        query.answer()
    except Exception as e:
        print(f"Error al responder la consulta: {e}")
        query.message.reply_text("Ha ocurrido un error al procesar tu solicitud. Por favor, inténtalo de nuevo.")
        return

    try:
        data = query.data.split('_')
        match_id = int(data[0])
        option = data[1]
        option2 = data[2] if len(data) > 2 else None  # Para manejar la clasificación
    except (IndexError, ValueError) as e:
        print(f"Error procesando los datos del callback: {e}")
        query.message.reply_text("Datos del voto incorrectos. Por favor, inténtalo de nuevo.")
        return

    user = query.from_user
    telegram_id = user.id
    try:
        existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    except Exception as e:
        print(f"Error al acceder a la base de datos de usuarios: {e}")
        query.message.reply_text("Ha ocurrido un error al acceder a la base de datos. Por favor, inténtalo de nuevo.")
        return

    if not existing_user:
        query.edit_message_text('No estás registrado. Usa /start para registrarte.')
        return

    try:
        match = session.query(Match).filter_by(id=match_id).first()
    except Exception as e:
        print(f"Error al acceder a la base de datos de partidos: {e}")
        query.message.reply_text("Ha ocurrido un error al acceder a la base de datos. Por favor, inténtalo de nuevo.")
        return

    if not match:
        query.edit_message_text('Identificador de partido no válido.')
        return

    if datetime.now() > match.match_time - timedelta(hours=1):
        query.edit_message_text('Es demasiado tarde para votar en este partido.')
        return

    try:
        existing_vote = session.query(Vote).filter_by(user_id=existing_user.id, match_id=match_id).first()
    except Exception as e:
        print(f"Error al acceder a la base de datos de votos: {e}")
        query.message.reply_text("Ha ocurrido un error al acceder a la base de datos. Por favor, inténtalo de nuevo.")
        return

    try:
        if existing_vote:
            existing_vote.option = option
            existing_vote.option2 = option2
            query.edit_message_text('Tu voto ha sido actualizado.')
            session.commit()
        else:
            new_vote = Vote(user_id=existing_user.id, match_id=match_id, option=option, option2=option2)
            session.add(new_vote)
            session.commit()
            query.edit_message_text('Tu voto ha sido registrado. Si quieres modificarlo, vuelve a votar del mismo modo usando el mismo identificador de partido.')
        
    except Exception as e:
        print(f"Error al registrar el voto: {e}")
        query.message.reply_text("Ha ocurrido un error al registrar tu voto. Por favor, inténtalo de nuevo.")
        return


@handle_db_operations
def mod_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data.split('_')
    match_id = int(data[1])
    option = data[2]
    option2 = data[3] if len(data) > 3 else None  # Para manejar la clasificación

    user = query.from_user
    telegram_id = user.id
    existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()

    if not existing_user:
        query.edit_message_text('No estás registrado. Usa /start para registrarte.')
        return

    match = session.query(Match).filter_by(id=match_id).first()
    if not match:
        query.edit_message_text('ID de partido no válido.')
        return

    if datetime.now() > match.match_time - timedelta(hours=1):
        query.edit_message_text('Es demasiado tarde para modificar tu voto.')
        return

    existing_vote = session.query(Vote).filter_by(user_id=existing_user.id, match_id=match_id).first()
    if existing_vote:
        existing_vote.option = option
        existing_vote.option2 = option2
        session.commit()
        query.edit_message_text('Tu voto ha sido modificado.')
    else:
        query.edit_message_text('No has votado en este partido aún. Usa /votar para votar.')

@handle_db_operations
def notificar_usuarios(bot):
    def enviar_mensaje(usuario, mensaje):
        try:
            bot.send_message(chat_id=usuario.telegram_id, text=mensaje)
        except Exception as e:
            print(f"Error enviando mensaje a {usuario.telegram_id}: {e}")

    while True:
        print("Revisando partidos...")
        now = datetime.now()
        
        try:
            # Obtener partidos disponibles para notificar sobre su apertura
            matches_to_notify_open = session.query(Match).filter(Match.open_time <= now, Match.notified == False).all()
            
            for match in matches_to_notify_open:
                print("Nuevo partido!!")
                usuarios = session.query(User).all()
                match.notified = True
                session.commit()
                for usuario in usuarios:
                    mensaje = (f"👋 ¡Hola! Hay un nuevo partido disponible para votar:\n"
                               f"⚽️ {match.home_team} vs {match.away_team}\n"
                               f"⏰ Hora de inicio: {match.match_time}\n"
                               f"⏳ Hora límite para votar: {match.close_time}\n\n"
                               f"🗳 Puedes votar en este partido escribiendo /votar {match.id}")
                    threading.Thread(target=enviar_mensaje, args=(usuario, mensaje)).start()
                print("NOTIFICACION COMPLETA matches_to_notify_open")
        
        except Exception as e:
            print(f"Error al notificar partidos abiertos: {e}")

        try:
            # Obtener partidos disponibles para notificar que faltan 1 hora para cerrar
            matches_to_notify_one_hour = session.query(Match).filter(Match.close_time - timedelta(hours=1) <= now, Match.close_time > now, Match.pre_close_notified == False).all()
            
            for match in matches_to_notify_one_hour:
                usuarios = session.query(User).all()
                print("¡Una hora para el cierre!")
                match.pre_close_notified = True
                session.commit()
                for usuario in usuarios:
                    mensaje = (f"⌛️ ¡Atención! Queda una hora para cerrar la votación del partido:\n"
                               f"⚽️ {match.home_team} vs {match.away_team}\n"
                               f"⏰ Hora de inicio: {match.match_time}\n"
                               f"⏳ Hora límite para votar: {match.close_time}\n\n"
                               f"🗳 Puedes votar en este partido escribiendo /votar {match.id}")
                    threading.Thread(target=enviar_mensaje, args=(usuario, mensaje)).start()
                print("NOTIFICACION COMPLETA matches_to_notify_one_hour")
        
        except Exception as e:
            print(f"Error al notificar partidos a una hora del cierre: {e}")
    
        try:
            # Obtener partidos disponibles para notificar que se cerraron
            matches_to_notify_closed = session.query(Match).filter(Match.close_time <= now, Match.close_notified == False).all()
            
            for match in matches_to_notify_closed:
                print("CERRADOOOOOO!!!")
                usuarios = session.query(User).all()
                match.close_notified = True
                session.commit()
                for usuario in usuarios:
                    mensaje = (f"🔒 La votación para el partido:\n"
                               f"⚽️ {match.home_team} vs {match.away_team}\n"
                               f"⏰ Hora de inicio: {match.match_time}\n"
                               f"ha cerrado, ya no se permite votar ni modificar el voto.")
                    threading.Thread(target=enviar_mensaje, args=(usuario, mensaje)).start()
                print("NOTIFICACION COMPLETA matches_to_notify_closed")
        
        except Exception as e:
            print(f"Error al notificar partidos cerrados: {e}")

        time.sleep(60)

@handle_db_operations
def notificar_admin_resueltos(bot):
    user_id_especifico = telegram_admin
    while True:
        try:
            print("Revisando partidos admin...")
            now = datetime.now()

            # Obtener todos los partidos de la base de datos
            partidos = session.query(Match).all()
            
            for partido in partidos:
                if now > partido.match_time + timedelta(hours=2) and not partido.admin_notified:
                    # Obtener el usuario especifico
                    usuario = session.query(User).filter_by(telegram_id=user_id_especifico).first()
                    
                    if usuario:
                        # Enviar mensaje al usuario
                        bot.send_message(chat_id=usuario.telegram_id, text=f"🔔 El evento entre {partido.home_team} y {partido.away_team} con ID {partido.id} ha finalizado.")
                        
                        # Marcar el partido como notificado para el administrador
                        partido.admin_notified = True
                        session.commit()
                        
            time.sleep(60)
        
        except Exception as e:
            # Manejo de excepciones
            print(f"Ocurrió un error: {e}")
            # Si deseas hacer algo específico en caso de error, como enviar un mensaje al administrador o registrar el error en un log, puedes hacerlo aquí.


@handle_db_operations
def marcar_partidos(bot):
    try:
        print("Revisando resultados..")
        now = datetime.now()

        session.execute("SELECT * FROM update_user_points()")
        session.commit()

        # Iniciar el hilo para notificar a los usuarios
        pending_notis = session.query(NotificationsPending).all()
        if pending_notis:
            print("Procesando " + str(len(pending_notis)) + " votos (usuarios)")
            for index, notification in enumerate(pending_notis):
                try:
                    user = session.query(User).filter_by(id=notification.user_id).first()
                    match = session.query(Match).filter_by(id=notification.match_id).first()
                    if not user or not match:
                        continue

                    # Crear el mensaje para el usuario
                    message = ""
                    if notification.points_earned > 0:
                        message = f"✅ ¡Felicidades! Has ganado {notification.points_earned} puntos por acertar el resultado y/o la clasificación del partido {match.home_team} vs {match.away_team}.\n\n"
                    else:
                        if notification.qualifies:
                            message = f"❌ No has ganado puntos. El resultado del partido {match.home_team} vs {match.away_team} fue {notification.result} y {notification.qualifies}, pero tú votaste por {translate_option(notification.option1, match.home_team, match.away_team)} y {translate_option2(notification.option2, match.home_team, match.away_team)}.\n\n"
                        else:
                            message = f"❌ No has ganado puntos. El resultado del partido {match.home_team} vs {match.away_team} fue {notification.result}, pero tú votaste por {translate_option(notification.option1, match.home_team, match.away_team)}.\n\n"

                    # Calcular los votos y porcentajes
                    votes = session.query(Vote).filter_by(match_id=match.id).all()
                    vote_counts = {}
                    total_votes = 0

                    # Contar votos para option y option2
                    for v in votes:
                        if v.option not in vote_counts:
                            vote_counts[v.option] = 0
                        vote_counts[v.option] += 1
                        total_votes += 1
                        if match.qualy:
                            if v.option == 'X':
                                if v.option2 == '1':
                                    vote_counts['X1'] = vote_counts.get('X1', 0) + 1
                                elif v.option2 == '2':
                                    vote_counts['X2'] = vote_counts.get('X2', 0) + 1

                    # Añadir detalles de los votos al mensaje
                    message += "👥 <b>Votos del público:</b>\n"
                    options = ['1', 'X', '2']
                    if match.qualy:
                        options += ['X1', 'X2']

                    for option in options:
                        count = vote_counts.get(option, 0)
                        if count > 0:
                            percentage = (count / total_votes) * 100
                            message += f"{translate_option(option, match.home_team, match.away_team)} ({percentage:.2f}%) {count} votos\n"

                    try:
                        bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode=ParseMode.HTML
                        )
                        session.delete(notification)
                        session.commit()
                    except Exception as e:
                        print(f"Error al enviar mensaje a {user.telegram_id}: {e}")
                        if 'bot was blocked' in str(e):
                            session.delete(notification)
                            session.commit()

                    # Mostrar en consola cada 10 usuarios procesados
                    if (index + 1) % 10 == 0:
                        print(f"{index + 1} usuarios procesados...")

                except Exception as e:
                    print(f"Error inesperado al procesar usuario {notification.user_id}: {e}")

            print("Proceso de notificación completado.")

    except Exception as e:
        print(f"Error inesperado: {e}")
        time.sleep(60)


def translate_option(option, home_team, away_team):
    if option == '1':
        return home_team
    elif option == '2':
        return away_team
    elif option == 'X':
        return "Empate"
    elif option == 'X1':
        return f"Empate-{home_team}"
    elif option == 'X2':
        return f"Empate-{away_team}"

def translate_option2(option2, home_team, away_team):
    if option2 == '1':
        return home_team
    elif option2 == '2':
        return away_team
    else:
        return ""


@handle_db_operations
def consultar(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    telegram_id = user.id

    existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not existing_user:
        update.message.reply_text('No estás registrado. Usa /start para registrarte.')
        return

    puntos = existing_user.points

    # Obtener los votos del usuario
    votes = session.query(Vote).filter_by(user_id=existing_user.id).all()
    voted_match_ids = {vote.match_id for vote in votes}

    # Partidos resueltos y no resueltos
    resolved_matches = []
    unresolved_matches = []

    for vote in votes:
        match = session.query(Match).filter_by(id=vote.match_id).first()
        if match.result:
            resolved_matches.append((match, vote))
        else:
            unresolved_matches.append((match, vote))

    # Obtener partidos abiertos no votados por el usuario
    now = datetime.now()
    open_matches = session.query(Match).filter(
        Match.open_time <= now,
        Match.close_time > now
    ).all()

    unvoted_matches = [
        match for match in open_matches if match.id not in voted_match_ids
    ]

    # Calcular los puntos ganados
    total_ganados = 0

    # Construir el mensaje de respuesta
    response = f'📊 Hola {user.first_name}, estos son tus resultados.!\n\n'

    if resolved_matches:
        response += '<b>📜 Partidos resueltos:</b>\n'
        for match, vote in resolved_matches:
            puntos_ganados = 0
            opcion_traducida = translate_option(vote.option, match.home_team, match.away_team)
            opcion2_traducida = translate_option(vote.option2, match.home_team, match.away_team)
            if match.qualifies:
                if vote.option == match.result and vote.option2 == match.qualifies:
                    puntos_ganados = 3
                    response += f'✅ {match.home_team} vs {match.away_team} - Votaste: {opcion_traducida} y clasifica {opcion2_traducida} (Ganaste 3 puntos)\n'
                elif vote.option == match.result:
                    puntos_ganados = 1
                    response += f'✅ {match.home_team} vs {match.away_team} - Votaste: {opcion_traducida} (Ganaste 1 punto)\n'
                else:
                    response += f'❌ {match.home_team} vs {match.away_team} - Votaste: {opcion_traducida} y {opcion2_traducida} (No ganaste puntos)\n'
            else:
                if vote.option == match.result:
                    puntos_ganados = 1
                    response += f'✅ {match.home_team} vs {match.away_team} - Votaste: {opcion_traducida} (Ganaste 1 punto)\n'
                else:
                    response += f'❌ {match.home_team} vs {match.away_team} - Votaste: {opcion_traducida} (No ganaste puntos)\n'
            
            total_ganados += puntos_ganados

    if unresolved_matches:
        response += '\n⏳ <b>Partidos sin resolver:</b>\n'
        for match, vote in unresolved_matches:
            opcion_traducida = translate_option(vote.option, match.home_team, match.away_team)
            opcion2_traducida = translate_option(vote.option2, match.home_team, match.away_team)
            response += f'🔄 {match.home_team} vs {match.away_team} - Has votado: {opcion_traducida}'
            if match.qualifies:
                response += f' y clasifica {opcion2_traducida}'
            response += '\n'

    if unvoted_matches:
        response += '\n⚠️ <b>Partidos sin votar:</b>\n'
        for match in unvoted_matches:
            response += f'🔄 {match.home_team} vs {match.away_team} - Vota usando /votar {match.id}\n'

    response += f'\n➕ Total puntos ganados: {total_ganados}'

    update.message.reply_text(response, parse_mode=ParseMode.HTML)


@handle_db_operations
def ranking(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    telegram_id = user.id

    existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not existing_user:
        update.message.reply_text('No estás registrado. Usa /start para registrarte.')
        return

    # Consulta para obtener los usuarios ordenados por puntos y por número de votos
    subquery = session.query(Vote.user_id, func.count('*').label('vote_count')).group_by(Vote.user_id).subquery()
    all_users = session.query(User, func.coalesce(subquery.c.vote_count, 0).label('votes')).outerjoin(subquery, User.id == subquery.c.user_id).order_by(User.points.desc(), text('votes desc')).all()

    # Crear el mensaje del ranking
    message = "🏆 <b>Ranking EuroPorra</b> 🏆\n\n"

    top_users = all_users[:10]
    for i, (user, votes) in enumerate(top_users, start=1):
        message += f"{i}. {user.name} - {user.points} puntos ({votes} votos)\n"

    # Encontrar la posición del usuario que ejecuta el comando
    user_position = next((i for i, (u, _) in enumerate(all_users, start=1) if u.telegram_id == telegram_id), None)

    if user_position is not None:
        personal_points = next((u.points for u, _ in all_users if u.telegram_id == telegram_id), 0)
        personal_votes = next((votes for _, votes in all_users if _.telegram_id == telegram_id), 0)
        message += f"\n👤 <b>Tu posición</b>\n{user_position}. {existing_user.name} - {personal_points} puntos ({personal_votes} votos)"

    # Enviar el mensaje del ranking
    update.message.reply_text(message, parse_mode=ParseMode.HTML)

def announcement(update, context):
    # ID del usuario autorizado
    authorized_user_id = telegram_admin
    
    # ID del usuario que envía el comando
    user_id = update.message.from_user.id
    
    # Verificar si el usuario está autorizado
    if user_id == authorized_user_id:
        # Obtener el mensaje después del comando /announcement
        message_text = ' '.join(context.args)
        message_text = message_text.replace("\\n", "\n")
        
        # Obtener los IDs de telegram de los usuarios ordenados por puntos (de mayor a menor)
        usuarios = session.query(User.telegram_id).order_by(User.points.desc()).all()
        telegram_ids = [usuario.telegram_id for usuario in usuarios]
        
        # Cerrar la sesión de la base de datos
        session.close()

        def enviar_mensajes():
            # Enviar el mensaje a todos los usuarios en el array de IDs
            for telegram_id in telegram_ids:
                try:
                    context.bot.send_message(
                        chat_id=telegram_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"Error enviando mensaje a {telegram_id}: {e}")

        # Iniciar un hilo para enviar los mensajes
        thread = Thread(target=enviar_mensajes)
        thread.start()
    else:
        # Informar al usuario que no está autorizado
        update.message.reply_text("No tienes permiso para usar este comando.")


def announcement(update, context):
    # ID del usuario autorizado
    authorized_user_id = telegram_admin
    
    # ID del usuario que envía el comando
    user_id = update.message.from_user.id
    
    # Verificar si el usuario está autorizado
    if user_id == authorized_user_id:
        # Obtener el mensaje después del comando /announcement
        message_text = ' '.join(context.args)

        message_text = message_text.replace("\\n", "\n")
        
        # Obtener todos los usuarios
        usuarios = session.query(User).all()
        
        def enviar_mensajes():
            # Enviar el mensaje a todos los usuarios
            for usuario in usuarios:
                try:
                    context.bot.send_message(
                        chat_id=usuario.telegram_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"Error enviando mensaje a {usuario.telegram_id}: {e}")

        # Iniciar un hilo para enviar los mensajes
        thread = Thread(target=enviar_mensajes)
        thread.start()
    else:
        # Informar al usuario que no está autorizado
        update.message.reply_text("No tienes permiso para usar este comando.")

@handle_db_operations
def stats(update: Update, context: CallbackContext) -> None:
    # ID del usuario autorizado
    authorized_user_id = telegram_admin

    # ID del usuario que envía el comando
    user_id = update.message.from_user.id

    # Verificar si el usuario está autorizado
    if user_id != authorized_user_id:
        update.message.reply_text("No tienes permiso para usar este comando.")
        return

    try:
        # Obtener el número de usuarios
        num_users = session.query(User).count()

        # Obtener el número de votos
        num_votes = session.query(Vote).count()

        # Crear el mensaje de estadísticas
        stats_message = (
            "<b>📊 Estadísticas EuroPorra 📊</b>\n\n"
            f"<b>👥 Número de usuarios:</b> {num_users}\n"
            f"<b>🗳️ Número de votos:</b> {num_votes}\n"
        )

        # Enviar el mensaje de estadísticas
        update.message.reply_text(stats_message, parse_mode='HTML')

    except Exception as e:
        # En caso de error, enviar un mensaje básico al usuario y registrar el error en la consola
        update.message.reply_text("Ocurrió un error al obtener las estadísticas. Inténtalo de nuevo más tarde.")
        print(f"Error al obtener estadísticas: {e}")


@handle_db_operations
def marcar(update: Update, context: CallbackContext) -> None:
    # ID del usuario autorizado
    authorized_user_id = telegram_admin

    # ID del usuario que envía el comando
    user_id = update.message.from_user.id

    # Verificar si el usuario está autorizado
    if user_id != authorized_user_id:
        update.message.reply_text("No tienes permiso para usar este comando.")
        return

    try:
        match_id = int(context.args[0])
        result = context.args[1]
        qualifies = context.args[2] if len(context.args) > 2 else None

        # Validar el campo result
        if result not in ['1', 'X', '2']:
            update.message.reply_text("Valor de resultado inválido. Debe ser '1', 'X' o '2'.")
            return

        # Validar el campo qualifies si está presente
        if qualifies and qualifies not in ['1', '2']:
            update.message.reply_text("Valor de clasificación inválido. Debe ser '1' o '2'.")
            return

        match = session.query(Match).filter_by(id=match_id).first()
        if not match:
            update.message.reply_text('ID de partido no válido.')
            return
        resultado = "Empate" if result == 'X' else match.home_team if result == '1' else match.away_team
        clasificacion = None if not qualifies else match.home_team if qualifies == '1' else match.away_team

        # Mensaje de confirmación
        if qualifies is None:
            keyboard = [
                [
                    InlineKeyboardButton("Sí", callback_data=f"confirmar_{match_id}_{result}"),
                    InlineKeyboardButton("No", callback_data="cancelar")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                f"¿Estás seguro que deseas finalizar el evento entre los equipos {match.home_team} e {match.away_team} "
                f"con resultado {resultado}? De pulsar sí en el botón, se realizará el cambio. "
                "De pulsar no, se descartará.",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [
                    InlineKeyboardButton("Sí", callback_data=f"confirmar_{match_id}_{result}_{qualifies}"),
                    InlineKeyboardButton("No", callback_data="cancelar")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                f"¿Estás seguro que deseas finalizar el evento entre los equipos {match.home_team} e {match.away_team} "
                f"con resultado {resultado} y clasificación {clasificacion}? De pulsar sí en el botón, se realizará el cambio. "
                "De pulsar no, se descartará.",
                reply_markup=reply_markup
            )

    except (IndexError, ValueError):
        update.message.reply_text('Uso incorrecto. Debes usar /marcar IDPARTIDO RESULTADO [CLASIFICA]')

@handle_db_operations
def confirmar_marcar(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    data = query.data.split('_')
    if data[0] == "cancelar":
        query.edit_message_text("Operación cancelada.")
        return

    try:
        match_id = int(data[1])
        result = data[2]
        qualifies = data[3] if len(data) > 3 else None
        match_id = int(match_id)

        match = session.query(Match).filter_by(id=match_id).first()
        if not match:
            query.edit_message_text('ID de partido no válido.')
            return

        match.result = result
        if qualifies != 'None':
            match.qualifies = qualifies
        resultado = "Empate" if result == 'X' else match.home_team if result == '1' else match.away_team
        clasificacion = None if not qualifies else match.home_team if qualifies == '1' else match.away_team
        session.commit()
        if qualifies is None:
            query.edit_message_text(f"Partido {match_id} actualizado con resultado '{resultado}''.")
        else:
            query.edit_message_text(f"Partido {match_id} actualizado con resultado '{resultado}' y clasificación '{clasificacion}'.")
        marcar_partidos(context.bot)

    except (IndexError, ValueError):
        query.edit_message_text('Error procesando la solicitud.')


def supervisor():
    while True:
        for thread in active_threads:
            if not thread.is_alive():
                print(f"Thread {thread.name} se ha caído. Reiniciando...")
                thread.start()
        time.sleep(10)

def main() -> None:
    updater = Updater(telegram_token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("votar", votar))
    # Añadir el handler para el comando /ranking
    dispatcher.add_handler(CommandHandler("ranking", ranking))
    # Agregar el nuevo manejador de comando en la configuración del dispatcher
    dispatcher.add_handler(CommandHandler("consultar", consultar))
    # Crear y añadir el manejador del comando /announcement
    dispatcher.add_handler(CommandHandler("announcement", announcement))
    dispatcher.add_handler(CommandHandler("marcar", marcar))  # Añadir este manejador
    dispatcher.add_handler(CommandHandler("stats", stats))
    dispatcher.add_handler(CallbackQueryHandler(button, pattern='^\d+_[1X2]$'))
    dispatcher.add_handler(CallbackQueryHandler(mod_button, pattern='^mod_\d+_[1X2]$'))
    dispatcher.add_handler(CallbackQueryHandler(button, pattern='^\d+_[1X2]_[12]$'))
    dispatcher.add_handler(CallbackQueryHandler(mod_button, pattern='^mod_\d+_[1X2_[12]]$'))
    dispatcher.add_handler(CallbackQueryHandler(confirmar_marcar, pattern='^confirmar_\d+_[1X2]_[12]?$'))
    dispatcher.add_handler(CallbackQueryHandler(confirmar_marcar, pattern='^confirmar_\d+_[1X2]?$'))
    dispatcher.add_handler(CallbackQueryHandler(confirmar_marcar, pattern='^cancelar$'))

    # Iniciar el hilo del supervisor
    supervisor_thread = threading.Thread(target=supervisor, name="Supervisor")
    supervisor_thread.start()
    active_threads.append(supervisor_thread)

    # Iniciar el cron job en un hilo separado
    notification_thread = threading.Thread(target=notificar_usuarios, args=(updater.bot,))
    notification_thread.start()
    active_threads.append(notification_thread)

    # Iniciar el hilo para notificar administradores
    notification_admin_thread = threading.Thread(target=notificar_admin_resueltos, args=(updater.bot,))
    notification_admin_thread.start()
    active_threads.append(notification_admin_thread)

    # Iniciar el polling del bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
