from flask import Flask, request
from flaskext.mysql import MySQL
import yaml
import os

app = Flask(__name__)

with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)
    app.config['MYSQL_HOST'] = settings['MYSQL']['MYSQL_HOST']
    app.config['MYSQL_USER'] = settings['MYSQL']['MYSQL_USER']
    app.config['MYSQL_PASSWORD'] = settings['MYSQL']['MYSQL_PASSWORD']
    app.config['MYSQL_DB'] = settings['MYSQL']['MYSQL_DB']
    app.config['DEBUG'] = True
    app.config['TESTING'] = True

mysql = MySQL()
mysql.init_app(app)


@app.route('/users', methods=['GET', 'POST'])
def users():  # put application's code here
    if request.method == 'GET':
        return "Login GET"
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        print(f'''INSERT INTO users VALUES({name},{email},{phone},{password})''')
        cursor = mysql.get_db().cursor()
        cursor.execute(f'''INSERT INTO users VALUES({name},{email},{phone},{password})''')
        mysql.connection.commit()
        cursor.close()
        return 200

    return 'Hello World!'


if __name__ == '__main__':
    app.run()
