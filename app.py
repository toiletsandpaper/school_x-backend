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
            return jsonify({'message': 'Missing token'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
        except:
            return jsonify({'message': 'Invalid token'}), 403
        return f(*args, **kwargs)

    return decorated


def image_processing(image_path, image_name, image_url) -> [bool, str]:
    try:
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
            image_data_from_file.save(f'{image_path}/{image_name}-{int(ratio * 100)}.png')
        return True, f'Images created at {image_path}'
    except Exception as e:
        return False, f'Error while creating image: {e}'


# TODO: Uncomment @token_required
@app.route('/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
# @token_required
def users():
    data = data_processing()
    if request.method == 'GET':
        for k, v in data.items():
            if k == 'page':
                page = v
                offset, limit = (page * 10) - 10, 10
                cursor = mysql.get_db().cursor()
                cursor.execute(f'''SELECT `id`, `name` FROM `school_x`.`users` LIMIT {limit} OFFSET {offset};''')
                response = cursor.fetchall()
                cursor.close()
                return jsonify(response), 200
            if k == 'id':
                id = v
                cursor = mysql.get_db().cursor()
                cursor.execute(f'''SELECT `id`, `name` FROM `school_x`.`users` WHERE `id` = "{id}";''')
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
            f'''SELECT `email` FROM `school_x`.`users` WHERE `email` = "{email}";'''
        )
        email_exists = cursor.fetchone()
        if email_exists:
            return "user with this email already exists", 400
        cursor.execute(
            f'''INSERT INTO `school_x`.`users` (`name`, `email`, `phone`, `password`) VALUES("{name}","{email}","{phone}","{password}");''')
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
            cursor.execute(f'''UPDATE `school_x`.`users` SET {set_part.rstrip(',')}  WHERE id = "{id}";''')
            cursor.connection.commit()
            cursor.close()
            return "user updated", 200
        except Exception as e:
            return str(e), 400
    if request.method == 'DELETE':
        try:
            id = data['id']
            cursor = mysql.get_db().cursor()
            cursor.execute(f'''DELETE FROM `school_x`.`users` WHERE `id` = "{id}";''')
            cursor.connection.commit()
            cursor.close()
            return "user deleted", 200
        except Exception as e:
            return str(e), 400


# TODO: Uncomment @token_required
@app.route('/images', methods=['GET', 'POST', 'PUT', 'DELETE'])
# @token_required
def images():
    data = data_processing()
    if request.method == 'GET':
        image_id = None
        owner_id = None
        ratio = None
        for k, v in data.items():
            if k == 'image_id': image_id = v
            if k == 'owner_id': owner_id = v
            if k == 'ratio': ratio = v

        if not image_id and not owner_id:
            return jsonify({'message': "No image_id OR owner_id provided"}), 403
        cursor = mysql.get_db().cursor()
        if image_id and not owner_id:
            cursor.execute(
                f'''SELECT `owner_id`, `name` FROM `school_x`.`images` WHERE `id` = "{image_id}";'''
            )
            fetcher = cursor.fetchone()
            if not fetcher:
                return jsonify({'message': 'File not found'}), 404
            owner_id = fetcher[0]
            image_name = fetcher[1]
            cursor.execute(
                f'''SELECT `name` FROM `school_x`.`users` WHERE `id` = "{owner_id}";'''
            )
            owner_name = cursor.fetchone()[0]

            cursor.execute(
                f'''SELECT `folder_path` FROM `school_x`.`files` WHERE `image_id` = "{image_id}";'''
            )
            folder_path = cursor.fetchone()[0]
            cursor.close()
            return jsonify({'image_id': image_id,
                            'owner_id': owner_id,
                            'owner_name': owner_name,
                            'image_name': image_name,
                            'folder_path': folder_path})

        if owner_id and not image_id:
            cursor.execute(
                f'''SELECT `name` FROM `school_x`.`users` WHERE `id` = "{owner_id}";'''
            )
            owner_name = cursor.fetchone()[0]

            cursor.execute(
                f'''SELECT `name` FROM `school_x`.`images` WHERE `owner_id` = "{owner_id}";'''
            )
            images_names = cursor.fetchall()
            images_ids = {}
            folders_paths = {}
            for image_name in images_names:
                image_name = image_name[0]
                cursor.execute(
                    f'''SELECT `id` FROM `school_x`.`images` WHERE `name` = "{image_name}";'''
                )
                image_id_ = cursor.fetchone()
                # return jsonify(image_name)
                images_ids[image_id_[0]] = image_name

                cursor.execute(
                    f'''SELECT `folder_path` FROM `school_x`.`files` WHERE `image_id` = "{image_id_[0]}";'''
                )
                folders_paths[image_id_[0]] = cursor.fetchone()[0]
            cursor.cloe()
            return jsonify({'owner_name': owner_name,
                            'images_ids': images_ids,
                            'folder_paths': folders_paths,
                            'owner_id': owner_id,
                            'ratio': ratio}
                           ), 200
    if request.method == 'POST':
        owner_id = data['owner_id']
        image_url = data['image_url']
        image_name = uuid.uuid4()
        image_path = os.path.join(os.path.dirname(__file__), f'images/{image_name}')
        os.makedirs(image_path)
        image_created, is_image_created_msg = image_processing(image_url=image_url,
                                                               image_name=image_name,
                                                               image_path=image_path)
        if image_created:
            cursor = mysql.get_db().cursor()
            cursor.execute(
                f'''INSERT INTO `school_x`.`images` (`owner_id`, `name`) VALUES("{owner_id}","{image_name}");''')
            cursor.connection.commit()
            cursor.execute(
                f'''SELECT `id` FROM `school_x`.`images` WHERE `name` = "{image_name}";'''
            )
            db_response = cursor.fetchone()
            cursor.execute(
                f'''INSERT INTO `school_x`.`files` (`image_id`, `folder_path`) VALUES("{db_response[0]}", "{image_path}");'''
            )
            cursor.connection.commit()
            cursor.close()
            return jsonify({'owner_id': owner_id, 'image_name': image_name}), 200
        if not image_created:
            return jsonify({'message': 'Image not created'}), 500
    if request.method == 'PUT':
        image_url = data['image_url']
        old_image_name = data['old_image_name']
        image_name = uuid.uuid4()
        old_image_path = os.path.join(os.path.dirname(__file__), f'images/{old_image_name}')
        image_path = os.path.join(os.path.dirname(__file__), f'images/{image_name}')
        os.makedirs(image_path)
        image_created, is_image_created_msg = image_processing(image_url=image_url,
                                                               image_name=image_name,
                                                               image_path=image_path)
        if image_created:
            cursor = mysql.get_db().cursor()
            cursor.execute(
                f'''UPDATE `school_x`.`images` SET `name` = "{image_name}" WHERE `name` = "{old_image_name}";'''
            )
            #return jsonify(f'''UPDATE `school_x`.`images` SET `name` = "{image_name}" WHERE `name` = "{old_image_path}";''')
            cursor.connection.commit()
            #return jsonify({1: old_image_path, 2: image_path})
            cursor.execute(
                f'''UPDATE `school_x`.`files` SET `folder_path` = "{image_path}" WHERE `folder_path` = "{old_image_path}";'''
            )
            cursor.connection.commit()
            cursor.close()
            return jsonify({"message": "Image successfully updated", "image_name": image_name}), 200
        if not image_created:
            return jsonify({'message': "Image not updated"}), 500
    if request.method == 'DELETE':
        image_name = data['image_name']
        try:
            cursor = mysql.get_db().cursor()
            cursor.execute(
                f'''SELECT `id` FROM `school_x`.`images` WHERE `name` = "{image_name}";'''
            )
            image_id = cursor.fetchone()[0]
            cursor.execute(
                f'''DELETE FROM `school_x`.`files` WHERE `image_id` = "{image_id}";'''
            )
            cursor.connection.commit()
            cursor.execute(
                f'''DELETE FROM `school_x`.`images` WHERE `name` = "{image_name}";'''
            )
            cursor.connection.commit()
            cursor.close()
            return jsonify({'message': "Image successfully deleted"}), 200
        except Exception as e:
            return jsonify({"message": "Image not deleted", 'exception': str(e)}), 500


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

# TODO: function that will clear not used photos each week

if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
