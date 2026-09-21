import sqlite3

db = sqlite3.connect('users.db')
cursor = db.cursor()

cursor.execute('''CREATE TABLE passwords( login TEXT PRIMARY KEY, password TEXT NOT NULL);''')
db.commit()

cursor.close()
db.close()