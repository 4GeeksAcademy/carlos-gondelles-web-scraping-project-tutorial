import requests
import pandas as pd
from io import StringIO
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

url = "https://en.wikipedia.org/wiki/List_of_most-streamed_songs_on_Spotify"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html = response.text
except Exception as e:
    print(f"Error al obtener la página: {e}")
    exit()

tables = pd.read_html(StringIO(html))
df = tables[0].copy()

df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^a-z0-9_]', '', regex=True)

rename_dict = {}
for col in df.columns:
    if 'song' in col or 'title' in col:
        rename_dict[col] = 'title'
    elif 'artist' in col:
        rename_dict[col] = 'artist'
    elif 'stream' in col:
        rename_dict[col] = 'streams_billions'
    elif 'publish' in col or 'release' in col:
        rename_dict[col] = 'release_date'
df = df.rename(columns=rename_dict)

df = df.dropna(subset=['title', 'artist', 'streams_billions'])  # Eliminar filas sin columnas clave
df = df[~df['title'].str.contains('As of', case=False, na=False)]  # Eliminar filas basura
df['streams_billions'] = pd.to_numeric(df['streams_billions'].str.replace(',', ''), errors='coerce')  # Convertir a numérico
df = df.drop_duplicates().reset_index(drop=True)  # Eliminar duplicados
df['scraping_date'] = datetime.utcnow().date()  # Agregar fecha de scraping

db_path = 'spotify_streams.db'
try:
    conn = sqlite3.connect(db_path)
    df.to_sql('most_streamed_spotify', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Datos guardados en {db_path}. Filas: {len(df)}")
except Exception as e:
    print(f"Error al guardar en DB: {e}")

try:
    conn = sqlite3.connect(db_path)
    print(pd.read_sql("SELECT * FROM most_streamed_spotify LIMIT 5", conn))
    conn.close()
except Exception as e:
    print(f"Error al verificar DB: {e}")

total_streams = df['streams_billions'].sum()
avg_streams = df['streams_billions'].mean()
top_song = df.loc[df['streams_billions'].idxmax(), 'title']
top_artist = df.loc[df['streams_billions'].idxmax(), 'artist']
print(f"Total streams (billones): {total_streams:.2f}")
print(f"Promedio streams: {avg_streams:.2f}")
print(f"Top: '{top_song}' por {top_artist}")

plt.figure(figsize=(10,6))
sns.barplot(data=df.nlargest(10, 'streams_billions'), x='streams_billions', y='title', color='lightgreen')
plt.title('Top 10 Canciones Más Reproducidas en Spotify')
plt.xlabel('Streams (Billones)')
plt.ylabel('')
plt.tight_layout()
plt.savefig('top_10_songs.png')
plt.show()

artist_counts = df['artist'].value_counts().head(10)
plt.figure(figsize=(10,6))
sns.barplot(x=artist_counts.values, y=artist_counts.index, hue=artist_counts.index, palette='viridis', legend=False)
plt.title('Artistas con Más Canciones en el Top de Spotify')
plt.xlabel('Número de Canciones')
plt.ylabel('')
plt.tight_layout()
plt.savefig('top_artists.png')
plt.show()

df['rank'] = df['streams_billions'].rank(ascending=False)
plt.figure(figsize=(10,6))
sns.scatterplot(data=df, x='rank', y='streams_billions', color='steelblue', alpha=0.7)
plt.gca().invert_xaxis() 
plt.title('Streams vs. Rank')
plt.xlabel('Rank (1 = Mayores Streams)')
plt.ylabel('Streams (Billones)')
plt.tight_layout()
plt.savefig('streams_vs_rank.png')
plt.show()