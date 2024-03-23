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