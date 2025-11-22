import sqlite3
conn = sqlite3.connect('autostack.db')
conn.execute("UPDATE projects SET auto_deploy_enabled=1, auto_deploy_branch='master' WHERE repository='sveltejs/template'")
conn.commit()
conn.close()
