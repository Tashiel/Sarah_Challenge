import sqlite3

conn = sqlite3.connect("data/social_insights.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM cleaned_posts LIMIT 10;")
for row in cursor.fetchall():
    print(row)

conn.close()
