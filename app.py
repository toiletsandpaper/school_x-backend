from flask import Flask, request
from flaskext.mysql import MySQL
import yaml
import os

app = Flask(__name__)

with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)
    app.config['MYSQL_DATABASE_HOST'] = settings['MYSQL']['MYSQL_HOST']
    app.config['MYSQL_DATABASE_USER'] = settings['MYSQL']['MYSQL_USER']
    app.config['MYSQL_DATABASE_PASSWORD'] = settings['MYSQL']['MYSQL_PASSWORD']
    app.config['MYSQL_DATABASE_DB'] = settings['MYSQL']['MYSQL_DB']
    app.config['DEBUG'] = True
    app.config['TESTING'] = True

mysql = MySQL()
mysql.init_app(app)


def data_processing():
    data = request.args.to_dict() or request.data or request.form or {}

    return data


@app.route('/users', methods=['GET', 'POST'])
def users():
    data = data_processing()
    if request.method == 'GET':
        #cursor = mysql.get_db().cursor()
        return "Login GET"
    if request.method == 'POST':
        name = data['name']
        email = data['email']
        phone = data['phone']
        password = data['password']
        print(f'''INSERT INTO users VALUES({name},{email},{phone},{password})''')
        cursor = mysql.get_db().cursor()
        cursor.execute(f'''INSERT INTO `school_x`.`users` (`name`, `email`, `phone`, `password`) VALUES("{name}","{email}","{phone}","{password}")''')
        cursor.connection.commit()
        cursor.close()
        return 'all good, created'




if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
