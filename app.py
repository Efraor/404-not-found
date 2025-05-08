from flask import Flask, render_template, request, redirect, session
import openai
import os
import requests
import urllib.parse
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/callback"
SCOPE = "playlist-modify-public"

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Generar canciones con GPT
def generar_canciones_con_gpt(estado_animo):
    prompt = (
        f"Comportate como un experto musical segun el estado de animo e interpreta el estado {estado_animo} y como se quiere sentir. "
        "Recomiéndame 6 canciones con su artista que representen ese estado de ánimo. Devuélvelo como una lista simple, formato: Canción - Artista"
    )

    respuesta = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Actuá como un curador musical experto. Según el siguiente estado de ánimo o actividad, generá una playlist variada de 5 canciones. Incluí diferentes géneros musicales, artistas y canciones tanto en español como en inglés (al menos 2 canciones deben estar en español). No repitas artistas ni estilos similares. Buscá una selección original que capture bien la emoción o energía de la situación.Devolvé únicamente una lista numerada con el nombre de la canción y el artista, sin explicaciones ni contexto adicional. Estado de ánimo o actividad del usuario: {{input_usuario}}"},
            {"role": "user", "content": prompt}
        ]
    )

    texto = respuesta.choices[0].message['content']
    lineas = texto.strip().split("\n")

    canciones = []
    for linea in lineas:
        if "-" in linea:
            partes = linea.split("-", 1)
            cancion = partes[0].strip()
            artista = partes[1].strip()
            canciones.append(f"{cancion} - {artista}")

    return canciones

#  Formulario principal
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

#  POST: recibe el estado de ánimo, genera canciones y redirige a login Spotify
@app.route("/generar_playlist", methods=["POST"])
def generar_playlist():
    estado_animo = request.form.get("estado_animo")
    plataforma = request.form.get("plataforma")

    canciones = generar_canciones_con_gpt(estado_animo)
    session["canciones"] = canciones
    session["estado_animo"] = estado_animo
    session["plataforma"] = plataforma

    return redirect("/login")

# Login con Spotify
@app.route("/login")
def login():
    auth_url = (
        "https://accounts.spotify.com/authorize?"
        + urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE
        })
    )
    return redirect(auth_url)

# Callback de Spotify
@app.route("/callback")
def callback():
    code = request.args.get("code")

    response = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    data = response.json()
    session["access_token"] = data["access_token"]

    return redirect("/crear_playlist_spotify")

# Crear la playlist en Spotify automáticamente
@app.route("/crear_playlist_spotify")
def crear_playlist_spotify():
    token = session.get("access_token")
    canciones = session.get("canciones", [])
    estado_animo = session.get("estado_animo", "Moodify Playlist")

    if not token or not canciones:
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}

    # Obtener usuario
    user = requests.get("https://api.spotify.com/v1/me", headers=headers).json()
    user_id = user["id"]

    # Crear playlist
    playlist = requests.post(
        f"https://api.spotify.com/v1/users/{user_id}/playlists",
        headers=headers,
        json={"name": f"MOODify 🎵 - {estado_animo}", "public": True}
    ).json()
    playlist_id = playlist["id"]

    # Buscar URIs de canciones
    uris = []
    for entrada in canciones:
        q = urllib.parse.quote(entrada)
        res = requests.get(
            f"https://api.spotify.com/v1/search?q={q}&type=track&limit=1",
            headers=headers
        ).json()
        items = res.get("tracks", {}).get("items")
        if items:
            uris.append(items[0]["uri"])

    # Agregar canciones
    if uris:
        requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": uris}
        )

    # Redirigir a la playlist
    return redirect(f"https://open.spotify.com/playlist/{playlist_id}")

# Ejecutar app
if __name__ == "__main__":
    app.run(debug=True, port=8000)