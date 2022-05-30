import datetime
import os
from PIL import Image
from flask import Flask, request, jsonify, make_response
from flaskext.mysql import MySQL
import settings
import jwt
from functools import wraps
import requests
import uuid

app = Flask(__name__)

app.config['MYSQL_DATABASE_HOST'] = settings.MYSQL_HOST
app.config['MYSQL_DATABASE_USER'] = settings.MYSQL_USER
app.config['MYSQL_DATABASE_PASSWORD'] = settings.MYSQL_PASSWORD
app.config['MYSQL_DATABASE_DB'] = settings.MYSQL_DB
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['DEBUG'] = True
app.config['TESTING'] = True

mysql = MySQL()
mysql.init_app(app)


def data_processing():
    data = request.args.to_dict() or request.data or request.form or {}
    return data

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')

        if not token:
            return jsonify({'message': 'Missing token'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
        except:
            return jsonify({'message': 'Invalid token'}), 403
        return f(*args, **kwargs)
    return decorated

# TODO: create or throw error if exists
@app.route('/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
@token_required
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


# TODO: complete this shit
@app.route('/images', methods=['GET', 'POST', 'PUT', 'DELETE'])
#@token_required
def images():
    data = data_processing()
    if request.method == 'GET':
        ...
    if request.method == 'POST':
        owner_id = data['owner_id']
        image_url = data['image_url']
        image_name = uuid.uuid4()
        image_path = os.path.join(os.path.dirname(__file__), f'images/{image_name}')
        os.makedirs(image_path)
        with open(f'{image_path}/{image_name}-orig.png', 'wb') as handle:
            image_data = requests.get(image_url, stream=True)
            if not image_data.ok:
                print(image_data)
            for block in image_data.iter_content(1024):
                if not block:
                    break
                handle.write(block)
        image_data_from_file = Image.open(f'{image_path}/{image_name}-orig.png')
        for ratio in reversed(range(20, 100, 20)):
            ratio = float(ratio / 100)
            image_data_from_file = image_data_from_file.resize([int(ratio * s) for s in image_data_from_file.size],
                                                                Image.ANTIALIAS)
            image_data_from_file.save(f'{image_path}/{image_name}-{int(ratio*100)}.png')

        cursor = mysql.get_db().cursor()
        cursor.execute(
            f'''INSERT INTO `school_x`.`images` (`owner_id`, `name`) VALUES("{owner_id}","{image_name}")''')
        cursor.connection.commit()
        cursor.execute(
            f'''SELECT `id` FROM `school_x`.`images` WHERE `name` = "{image_name}"'''
        )
        db_response = cursor.fetchone()
        cursor.execute(
            f'''INSERT INTO `school_x`.`files` (`image_id`, `folder_path`) VALUES("{db_response[0]}", "{image_path}")'''
        )
        cursor.connection.commit()
        cursor.close()
        return jsonify({'owner_id': owner_id, 'image_name': image_name}), 200





@app.route('/favorites', methods=['GET', 'POST', 'PUT', 'DELETE'])
@token_required
def favorites():
    ...


@app.route('/login')
def login():
    data = data_processing()
    auth = request.authorization
    if auth and auth.username == settings.MYSQL_USER and auth.password == "root":
        token = jwt.encode({'user': auth.username,
                            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.config['SECRET_KEY'],
                           algorithm='HS256')
        return jsonify({'token': token})
    if not auth and data['user'] == settings.MYSQL_USER and data['password'] == "root":
        token = jwt.encode({'user': data['user'],
                            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.config['SECRET_KEY'],
                           algorithm='HS256')
        return jsonify({'token': token})
    return make_response('get off', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


# no need for app.route files


if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
