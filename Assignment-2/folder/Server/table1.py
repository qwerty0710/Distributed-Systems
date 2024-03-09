import sqlite3
import random
import string

class StudentDatabase:
    def __init__(self, db_name='studTable.db'):
        self.db_name = db_name
        
    def create_connection(self):
        conn = sqlite3.connect(self.db_name)
        return conn
    
    def create_table(self, conn, payload):
        payload = payload
        schema = payload.get('schema')
        shards = payload.get('shards')
        cursor = conn.cursor()
        for sh in shards:
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS {sh}(
                                {schema["columns"][0]} INTEGER PRIMARY KEY NOT NULL,
                                {schema["columns"][1]} TEXT NOT NULL,
                                {schema["columns"][2]} TEXT NOT NULL,
                                CONSTRAINT id_range CHECK ({schema["columns"][0]} BETWEEN 000000 AND 1000000)
                            )''')
            conn.commit()
        cursor.close()
        result = shards
        return result
    
    def check_table(self, conn, table):
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' and name={table} ")
        check = cursor.fetchone()
        cursor.close()
        return check
    
    def create_meta_table(self, conn): #this is not needed 
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS ShardT (
                Stud_id_low INTEGER PRIMARY KEY,
                Shard_id TEXT NOT NULL,
                Shard_size INTEGER NOT NULL,
                valid_idx INTEGER  ,
                CONSTRAINT  v_idx CHECK (valid_idx BETWEEN 000000 AND 1000000 )
            )''')
        conn.commit()
    
        cursor.execute('''CREATE TABLE IF NOT EXISTS MapT (
                Shard_id TEXT NOT NULL,
                Server_id TEXT NOT NULL,
                FOREIGN KEY (Shard_id) REFERENCES ShardT(Shard_id)       
            )''')
        conn.commit()
        cursor.close()

    def generate_random_name(self):
        return ''.join(random.choices(string.ascii_uppercase, k=5))

    def generate_random_marks(self):
        return random.randint(0, 100)

    def write(self, conn, payload):
        table = payload.get('shard')
        curr_idx = int(payload.get('curr_idx'))
        datas = payload.get('data')
        cursor = conn.cursor()
        for data in datas:
            cursor.execute("INSERT INTO {} (Stud_id, Stud_name, Stud_marks) VALUES (?,?,?)".format(table),(int(data['Stud_id']), data['Stud_name'], str(data['Stud_marks'])))
            conn.commit()
            curr_idx += 1
        cursor.close()
        message = 'Data entries added'
        current_idx = curr_idx
        return message, current_idx
    
    def insert_shards(self, conn, payload):   # this is not needed
        table = payload.get('shard')
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO ? (Stud_id_low, Shard_id, Shard_size) VALUES (?, ?, ?)", (table,0, "sh1", 50))
        conn.commit()
        cursor.close()

    def insert_shard_mapping(self, conn): #this is not needed
        cursor = conn.cursor()
        cursor.execute("INSERT INTO MapT (Shard_id, Server_id) VALUES (?, ?)", ("sh1", "Server0"))
        conn.commit()
        cursor.close()
    
    def select_all_rows(self, conn, shard):
        table = shard
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        listofstu = cursor.fetchall()  # Fetch all rows
        message = []
        data = {}
        for i in listofstu:
            data['Stud_id'] = i[0]
            data['Stud_name'] = i[1]
            data['Stud_marks'] = i[2]
            message.append(str(data))
        cursor.close()
        return message
    
    def copy(self, conn, shards):
        #table = payload.get('shard')
        message = []
        for i in shards:
            message.append(self.select_all_rows(conn,i))
        return message
    
    def read(self, conn, payload):
        table = payload.get('shard')
        low = payload['Stud_id']['low']
        high = payload['Stud_id']['high']
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table} WHERE Stud_id BETWEEN {low} AND {high}")
        listofstu = cursor.fetchall()  # Fetch all rows
        message = []
        data = {}
        for i in listofstu:
            data['Stud_id'] = i[0]
            data['Stud_name'] = i[1]
            data['Stud_marks'] = i[2]
            message.append(str(data))
        cursor.close()
        return message
    
    def update(self, conn, payload):
        table = payload.get('shard')
        data = payload.get('data')
        s_id = payload.get('Stud_id')
        stud_id = int(data['Stud_id'])
        stud_marks = data['Stud_marks']
        stud_name = data['Stud_name']
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table} SET Stud_id=?, Stud_name=?, Stud_marks=? WHERE Stud_id=?", (stud_id, stud_name, stud_marks, s_id))
        conn.commit()
        message = f'data entry for stud_id {s_id} updated'
        return message
           
    def delete(self, conn, payload):
        table = payload.get('shard')
        stud_id = payload.get('Stud_id')
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE Stud_id=?", (stud_id,))
        conn.commit()
        message = f'data entry for stud_id {stud_id} deleted '
        return message

def main():
    student_db = StudentDatabase()
    conn = student_db.create_connection()
    conn.close()

if __name__ == "__main__":
    main()

