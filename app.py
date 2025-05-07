from flask import Flask, request, redirect, render_template
import openai
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar_playlist', methods=['POST'])
def generar_playlist():
    estado_animo = request.form.get('estado_animo', '')
    plataforma = request.form.get('plataforma', '').lower()

    prompt = f"Recomiéndame 5 canciones que combinen con este estado de ánimo: {estado_animo}."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        canciones = response.choices[0].message['content']

        # Simular redirección a la plataforma
        if plataforma == 'spotify':
            return redirect(f'https://open.spotify.com/search/{estado_animo}')
        elif plataforma == 'apple':
            return redirect(f'https://music.apple.com/search?term={estado_animo}')
        elif plataforma == 'deezer':
            return redirect(f'https://www.deezer.com/search/{estado_animo}')
        else:
            return f"<h2>Playlist sugerida:</h2><pre>{canciones}</pre>"

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)