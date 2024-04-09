import sqlite3

class MusicDataStorage:
    def __init__(self, db_name='music_data.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS music_data (
                                id INTEGER PRIMARY KEY,
                                album TEXT,
                                album_id TEXT,
                                artists TEXT,
                                title TEXT,
                                elapsed TEXT,
                                track TEXT,
                                tracks TEXT,
                                npclient TEXT,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )''')
        self.conn.commit()

    def insert_data(self, album, album_id, artists, title, elapsed, track, tracks, npclient):
        self.cursor.execute('''INSERT INTO music_data (album, album_id, artists, title, elapsed, track, tracks, npclient) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (album, album_id, artists, title, elapsed, track, tracks, npclient))
        self.conn.commit()

    def retrieve_data(self):
        self.cursor.execute('''SELECT * FROM music_data''')
        return self.cursor.fetchall()

    def close_connection(self):
        self.conn.close()

    def retrieve_tracks(self):
        self.cursor.execute('''SELECT * FROM music_data''')
        tracks = self.cursor.fetchall()
        track_data = []
        for track in tracks:
            track_data.append({
                'album_id': track[1],
                'album': track[2],
                'artists': track[3],
                'title': track[4],
                'elapsed': track[5],
                'track': track[6],
                'tracks': track[7],
                'npclient': track[8],
                'timestamp': track[9]  # Changed index to 9
            })
        return track_data
    
    def retrieve_albums(self):
        self.cursor.execute('''SELECT DISTINCT album_id, album, timestamp FROM music_data''')
        albums = self.cursor.fetchall()
        album_data = []
        for album in albums:
            album_data.append({
                'album_id': album[0],
                'album': album[1],
                'timestamp': album[2]
            })
        return album_data