import sqlite3


class db_helper:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS ShardT (
                            stud_id_low INTEGER NOT NULL,
                            shard_id TEXT NOT NULL,
                            shard_size INTEGER NOT NULL,
                            valid_idx INTEGER NOT NULL
                        )''')
        self.conn.commit()

        cursor.execute('''CREATE TABLE IF NOT EXISTS MapT (
                            shard_id TEXT NOT NULL,
                            server_id TEXT NOT NULL,
                            FOREIGN KEY (Shard_id) REFERENCES ShardT(shard_id)
                        )''')
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def get_connection(self):
        return self.conn

    def add_shard(self, shard):
        print(shard)
        self.conn.execute('INSERT INTO shardT (stud_id_low, shard_id, shard_size, valid_idx) VALUES (?,?,?,?)', (shard['Stud_id_low'], shard['Shard_id'], shard['Shard_size'], shard['Stud_id_low']))
        self.conn.commit()

    def add_server(self,shard,server):
        self.conn.execute('INSERT INTO mapT (shard_id , server_id) VALUES (?,?)', (shard, server))
        self.conn.commit()
