import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
import os
from keep_alive import keep_alive


from pyrogram.types import Message

processing_queue = []
status_message = None
video_count = 0
doc_count = 0

import os
import time

MAX_RETRIES = 2  # Le nombre de tentatives pour retélécharger le fichier

# Créez une instance de client avec votre propre token de bot et votre nom d'utilisateur
app = Client("TEST_BÊTA", bot_token="6863934525:AAH5saeFht0RhxWxEsfBQOYyqgQ6XZGn4X8", api_id="21648908", api_hash="a6f834b1a8f86046078f05bfe34c0a5f")
Admin_id = 6217351762

# Créez un sémaphore avec une limite de 1
semaphore = asyncio.Semaphore(5)

# Liste de textes à remplacer
text_to_replace = ["Shar.Club", "SharClub"]

# Variable pour stocker le nom de l'image de la vignette
thumbnail_image = "img.jpg"

# Définition de la variable change_thumbnail
change_thumbnail = True

processing_enabled = True

# Ajoutez une commande /start
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    commands_list = [
        "`/start` - Affiche ce message d'accueil.",
        "`/activer` - Active la fonctionnalité de modification de la vignette.",
        "`/desactiver` - Désactive la fonctionnalité de modification de la vignette.",
        "`/add <texte>` - Ajoute un texte à la liste de remplacement.",
        "`/remove_text <texte|all>` - Retire un texte spécifique ou tous les textes de la liste de remplacement.",
        "`/list_text` - Affiche tous les textes dans la liste de remplacement.",
        "`/stop_processing` - Arrête le traitement des fichiers.",
        "`/start_processing` - Démarre le traitement des fichiers.",
        "`/traiter` - Traite les fichiers en attente.",
    ]

    await message.reply_text(f"Bonjour ! Je suis votre bot. Voici la liste des commandes disponibles :\n\n" + "\n".join(commands_list))

    global status_message, video_count, doc_count
    video_count = 0
    doc_count = 0
    processing_queue.clear()

    status_message = await message.reply_text(
        f"Veuillez m'envoyer des vidéos et documents :\nActuellement j'ai {video_count} vidéo(s) à traiter et {doc_count} document(s)."
    )


@app.on_message(filters.document)
async def queue_document(client: Client, message: Message):
    global video_count, doc_count, processing_queue, status_message

    # Ajout du document à la file d'attente
    processing_queue.append(message)
    doc_count += 1
    await update_status_message()

@app.on_message(filters.video)
async def queue_video(client: Client, message: Message):
    global video_count, doc_count, processing_queue, status_message

    # Ajout de la vidéo à la file d'attente
    processing_queue.append(message)
    video_count += 1
    await update_status_message()


async def update_status_message():
    global status_message, video_count, doc_count
    if status_message:
        try:
            await status_message.edit_text(
                f"Veuillez m'envoyer des vidéos et documents :\nActuellement j'ai {video_count} vidéo(s) à traiter et {doc_count} document(s)."
            )
        except Exception as e:
            print(f"Erreur de mise à jour du message : {e}")



# Fonction pour vérifier si le fichier a bien été téléchargé
async def verify_file_download(file_path, file_size):
    if os.path.exists(file_path) and os.path.getsize(file_path) == file_size:
        return True
    else:
        return False

# Fonction de traitement avec reprise après échec
async def process_with_retry(message, file_path, file_size, process_func):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        # Vérifier si le fichier est bien téléchargé
        if await verify_file_download(file_path, file_size):
            # Si le fichier est téléchargé correctement, traiter le fichier
            await process_func(message, file_path)
            return  # Si le traitement est réussi, on sort de la fonction

        else:
            # Si le fichier n'est pas bien téléchargé, on envoie un message d'erreur
            await message.reply_text(f"Le traitement du fichier a échoué (tentative {retry_count + 1}). Voulez-vous réessayer ?")
            retry_count += 1
            if retry_count < MAX_RETRIES:
                await message.reply_text("Nouvelle tentative en cours...")
                time.sleep(2)  # Attendre un peu avant de réessayer
                file_path = await message.download()  # Retélécharger le fichier
            else:
                await message.reply_text("Le traitement de ce fichier a échoué après 2 tentatives. Le processus passe au fichier suivant.")
                break  # Passer au fichier suivant

@app.on_message(filters.command("traiter") & filters.private)
async def start_processing(client, message):
    global processing_queue, video_count, doc_count

    if not processing_queue:
        await message.reply_text("Aucun fichier à traiter.")
        return

    await message.reply_text("Traitement en cours...")

    while processing_queue:
        item = processing_queue.pop(0)
        
        # Vérifie le type de fichier (vidéo ou document) et lance le traitement approprié
        if item.video:
            await rename_video(client, item)
            video_count -= 1
        elif item.document:
            await rename_media(client, item)
            doc_count -= 1

        # Mise à jour du message d'état après chaque traitement
        await update_status_message()

    await message.reply_text("Tous les fichiers ont été traités.")



# Fonction de traitement pour le document
async def rename_media(client: Client, message: Message):
    global processing_enabled, thumbnail_image, text_to_replace

    if not processing_enabled:
        await message.reply_text('Le traitement des fichiers est actuellement désactivé.')
        return

    if message.document.file_size <= 2 * 1024 * 1024 * 1024:  # Limite de 2 Go
        file_name = message.document.file_name
        file_path = await message.download()

        # Appeler la fonction pour traiter avec reprise après échec
        await process_with_retry(message, file_path, message.document.file_size, process_document)

    else:
        await message.reply_text("Le fichier est trop volumineux et ne peut pas être traité.")

# Fonction spécifique de traitement des documents
async def process_document(message, file_path):
    # Traitement spécifique du document ici
    file_name = message.document.file_name
    file_name = file_name.translate(str.maketrans("", "", "@[]"))
    
    for text in text_to_replace:
        file_name = file_name.replace(text, "")

    new_file_name = f"[@TurboSearch] {file_name.strip()}"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

    os.rename(file_path, new_file_path)

    # Préparer le caption
    filename_without_ext = os.path.splitext(file_name)[0]
    caption = f"`{filename_without_ext}` **| @TurboSearch**"

    # Application de la miniature
    thumb_path = os.path.join("tools", thumbnail_image) if change_thumbnail else None

    await message.reply_document(
        document=new_file_path,
        caption=caption,
        thumb=thumb_path if thumb_path and os.path.isfile(thumb_path) else None
    )

    # Nettoyage
    if os.path.exists(new_file_path):
        os.remove(new_file_path)

# Fonction de traitement pour la vidéo
async def rename_video(client: Client, message: Message):
    global processing_enabled, thumbnail_image, text_to_replace

    if not processing_enabled:
        await message.reply_text('Le traitement des fichiers est actuellement désactivé.')
        return

    if message.video.file_size <= 2 * 1024 * 1024 * 1024:  # Limite de 2 Go
        file_name = message.video.file_name or "video.mp4"
        file_path = await message.download(file_name=file_name)

        # Appeler la fonction pour traiter avec reprise après échec
        await process_with_retry(message, file_path, message.video.file_size, process_video)

    else:
        await message.reply_text("Le fichier est trop volumineux et ne peut pas être traité.")

# Fonction spécifique de traitement des vidéos
async def process_video(message, file_path):
    # Traitement spécifique de la vidéo ici
    file_name = message.video.file_name or "video.mp4"
    file_name = file_name.translate(str.maketrans("", "", "@[]"))
    
    for text in text_to_replace:
        file_name = file_name.replace(text, "")

    new_file_name = f"[@TurboSearch] {file_name.strip()}"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

    os.rename(file_path, new_file_path)

    # Préparer le caption
    filename_without_ext = os.path.splitext(file_name)[0]
    caption = f"`{filename_without_ext}` **| @TurboSearch**"

    # Application de la miniature
    thumb_path = os.path.join("tools", thumbnail_image) if change_thumbnail else None

    await message.reply_document(
        document=new_file_path,
        caption=caption,
        thumb=thumb_path if thumb_path and os.path.isfile(thumb_path) else None
    )

    # Nettoyage
    if os.path.exists(new_file_path):
        os.remove(new_file_path)


# Commande /add pour ajouter des textes à remplacer
@app.on_message(filters.command("add"))
async def add_text_to_replace(client: Client, message: Message):
    global text_to_replace

    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return


    if len(message.command) > 1:
        new_text = message.command[1]

        # Ajouter le nouveau texte uniquement s'il n'est pas déjà dans la liste
        if new_text not in text_to_replace:
            text_to_replace.append(new_text)
            all_texts = '\n'.join([f'- {text}' for text in text_to_replace])  # Formatage de la liste
            await message.reply_text(f'Texte "{new_text}" ajouté à la liste.\nListe actuelle :\n`{all_texts}`')
        else:
            await message.reply_text(f'Texte "{new_text}" est déjà dans la liste.')
    else:
        await message.reply_text('Veuillez spécifier un texte à ajouter à la liste.')

# Commande /list_text pour afficher tous les éléments de la liste
@app.on_message(filters.command("list_text"))
async def list_text(client: Client, message: Message):
    global text_to_replace

    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return

    if text_to_replace:
        all_texts = '\n'.join([f'- `{text}`' for text in text_to_replace])  # Formatage de la liste
        await message.reply_text(f'Liste actuelle :\n{all_texts}')
    else:
        await message.reply_text('La liste est actuellement vide.')

# Commande /remove_text pour retirer un élément spécifique ou tous les éléments de la liste
@app.on_message(filters.command("remove_text"))
async def remove_text(client: Client, message: Message):
    global text_to_replace

    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return

    if len(message.command) > 1:
        text_to_remove = message.command[1]

        if text_to_remove.lower() == "all":
            text_to_replace.clear()  # Retirer tous les éléments de la liste
            await message.reply_text('Tous les éléments ont été retirés de la liste.')
        elif text_to_remove in text_to_replace:
            text_to_replace.remove(text_to_remove)  # Retirer un élément spécifique
            await message.reply_text(f'Texte "{text_to_remove}" a été retiré de la liste.')
        else:
            await message.reply_text(f'Texte "{text_to_remove}" n\'est pas dans la liste.')
    else:
        await message.reply_text('Veuillez spécifier un texte à retirer de la liste.')

# Commande /start_processing pour démarrer le traitement des fichiers
@app.on_message(filters.command("start_processing"))
async def start_processing(client: Client, message: Message):
    global processing_enabled
    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return
    processing_enabled = True
    await message.reply_text('Le traitement des fichiers a été démarré.')

# Commande /stop_processing pour arrêter le traitement des fichiers
@app.on_message(filters.command("stop_processing"))
async def stop_processing(client: Client, message: Message):
    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return
    global processing_enabled
    processing_enabled = False
    await message.reply_text('Le traitement des fichiers a été arrêté.')

# Filtre pour les commandes
@app.on_message(filters.command(['activer', 'desactiver']))
async def handle_thumbnail_command(client: Client, message: Message):
    global change_thumbnail

    # Vérifie si l'utilisateur est l'admin autorisé
    if message.from_user.id != Admin_id:
        await message.reply_text("Vous n'êtes pas autorisé à exécuter cette commande.")
        return

    if message.command[0] == 'activer':
        change_thumbnail = True
        await message.reply_text('La fonctionnalité de modification de la vignette a été activée.')
    elif message.command[0] == 'desactiver':
        change_thumbnail = False
        await message.reply_text('La fonctionnalité de modification de la vignette a été désactivée.')

keep_alive()
app.run()

