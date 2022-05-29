from flask import Flask, request, jsonify
from flaskext.mysql import MySQL
import settings

app = Flask(__name__)

app.config['MYSQL_DATABASE_HOST'] = settings.MYSQL_HOST
app.config['MYSQL_DATABASE_USER'] = settings.MYSQL_USER
app.config['MYSQL_DATABASE_PASSWORD'] = settings.MYSQL_PASSWORD
app.config['MYSQL_DATABASE_DB'] = settings.MYSQL_DB
app.config['DEBUG'] = True
app.config['TESTING'] = True

mysql = MySQL()
mysql.init_app(app)


def data_processing():
    data = request.args.to_dict() or request.data or request.form or {}

    return data


# TODO: create or throw error if exists
# TODO: add PUT and DELETE
@app.route('/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
def users():
    data = data_processing()
    if request.method == 'GET':
        for k, v in data.items():
            if k == 'page':
                page = v
                offset, limit = (page * 10) - 10, 10
                cursor = mysql.get_db().cursor()
                cursor.execute(f'''SELECT `id`, `name` FROM `school_x`.`users` LIMIT {limit} OFFSET {offset}''')
                response = cursor.fetchall()
                cursor.close()
                return jsonify(response), 200
            if k == 'id':
                id = v
                cursor = mysql.get_db().cursor()
                cursor.execute(f'''SELECT `id`, `name` FROM `school_x`.`users` WHERE `id` = "{id}"''')
                response = cursor.fetchall()
                if str(response) == "()":
                    return "user not found", 404
                cursor.close()
                return jsonify(response), 200
        return "give me page or id", 400
    if request.method == 'POST':
        name = data['name']
        email = data['email']
        phone = data['phone']
        password = data['password']
        cursor = mysql.get_db().cursor()
        cursor.execute(
            f'''INSERT INTO `school_x`.`users` (`name`, `email`, `phone`, `password`) VALUES("{name}","{email}","{phone}","{password}")''')
        cursor.connection.commit()
        cursor.close()
        return 'all good, user created', 200
    if request.method == 'PUT':
        try:
            id = data['id']
            set_part = ''
            for k, v in data.items():
                print(data.items())
                if k in ["name", "email", "phone", "password"]:
                    set_part = set_part + f'`{k}` = "{v}",'
            cursor = mysql.get_db().cursor()
            # print(f'''UPDATE `school_x`.`users` SET {set_part.rstrip(',')}  WHERE `id` = {id}''')
            cursor.execute(f'''UPDATE `school_x`.`users` SET {set_part.rstrip(',')}  WHERE id = "{id}"''')
            cursor.connection.commit()
            cursor.close()
            return "user updated", 200
        except Exception as e:
            return str(e), 400
        else:
            return 'something went wrong', 400
    if request.method == 'DELETE':
        try:
            id = data['id']
            cursor = mysql.get_db().cursor()
            cursor.execute(f'''DELETE FROM `school_x`.`users` WHERE `id` = "{id}"''')
            cursor.connection.commit()
            cursor.close()
            return "user deleted", 200
        except Exception as e:
            return str(e), 400
        else:
            return "something went wrong", 400


if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
