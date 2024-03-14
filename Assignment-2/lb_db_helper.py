import sqlite3


class db_helper:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.conn.isolation_level = None
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS ShardT (
                            stud_id_low INTEGER NOT NULL,
                            shard_id TEXT NOT NULL,
                            shard_size INTEGER NOT NULL,
                            valid_idx INTEGER NOT NULL
                        )''')
        self.conn.commit()

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS MapT (
                            shard_id TEXT NOT NULL,
                            server_id TEXT NOT NULL,
                            FOREIGN KEY (Shard_id) REFERENCES ShardT(shard_id)
                        )''')
        self.conn.commit()
        # self.cursor.close()

    def __del__(self):
        self.conn.close()

    def get_connection(self):
        return self.conn

    def add_shard(self, shard):
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO shardT (stud_id_low, shard_id, shard_size, valid_idx) VALUES (?,?,?,?)',
                       (shard['Stud_id_low'], shard['Shard_id'], shard['Shard_size'], shard['curr_idx']))
        self.conn.commit()
        cursor.close()
        # self.conn.close()

    def add_server(self, shard, server):
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO mapT (shard_id , server_id) VALUES (?,?)', (shard, server))
        self.conn.commit()
        cursor.close()
        # self.conn.close()

    def get_shard_data(self):
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM shardT')
        data = cursor.fetchall()
        cursor.close()
        # self.conn.close()
        return data

    def get_server_data(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM mapT')
        data = cursor.fetchall()
        cursor.close()
        # self.conn.close()
        return data

    def get_shard_id(self, stud_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT shard_id FROM shardT WHERE stud_id_low <= ? AND ? < stud_id_low + shard_size ORDER BY stud_id_low DESC LIMIT 1',
            (stud_id, stud_id))
        data = cursor.fetchone()
        cursor.close()
        # self.conn.close()
        return data

    def update_curr_idx(self, shard_id, curr_idx):
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        cursor.execute('UPDATE ? SET curr_idx = ? WHERE shard_id = ?', ("shardT", curr_idx, shard_id))
        cursor.close()
        self.conn.commit()
       #  self.conn.close()
