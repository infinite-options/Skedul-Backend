
from flask import request
from flask_restful import Resource

from data import connect
from security import createSalt, createHash, createTokens


def getUserByEmail(email):
    with connect() as db:
        result = db.select('users', {'email': email})
        if len(result['result']) > 0:
            return result['result'][0]


def createUser(firstName, lastName, phoneNumber, email, password, role,
               google_auth_token=None, google_refresh_token=None, social_id=None, access_expires_in=None):
    with connect() as db:
        newUserID = db.call('new_user_id')['result'][0]['new_id']
        passwordSalt = createSalt()
        passwordHash = createHash(password, passwordSalt)
        newUser = {
            'user_uid': newUserID,
            'first_name': firstName,
            'last_name': lastName,
            'phone_number': phoneNumber,
            'email': email,
            'password_salt': passwordSalt,
            'password_hash': passwordHash,
            'role': role,
            'google_auth_token': google_auth_token,
            'google_refresh_token': google_refresh_token,
            'social_id': social_id,
            'access_expires_in': access_expires_in
        }
        response = db.insert('users', newUser)
        return newUser


class Login(Resource):
    def post(self):
        response = {}
        print('IN LOGIN')
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = getUserByEmail(email)
        if user:
            print('IN IF LOGIN')
            passwordSalt = user['password_salt']
            passwordHash = createHash(password, passwordSalt)
            print('IN IF LOGIN', passwordHash, passwordSalt)
            if passwordHash == user['password_hash']:
                response['message'] = 'Login successful'
                response['code'] = 200
                response['result'] = createTokens(user)
                print('IN IF IF LOGIN', response)
            else:
                response['message'] = 'Incorrect password'
                response['code'] = 401
                print('IN IF ELSE LOGIN', response)
        else:
            print('IN ELSE LOGIN')
            response['message'] = 'Email not found'
            response['code'] = 404
            print('IN ELSE LOGIN', response)
        return response


class Users(Resource):
    def get(self):
        response = {}
        filters = ['user_uid', 'email', 'role']
        where = {}
        for filter in filters:
            filterValue = request.args.get(filter)
            if filterValue is not None:
                where[filter] = filterValue
        with connect() as db:
            response = db.select('users', where)
        return response

    def post(self):
        response = {}
        data = request.get_json()
        firstName = data.get('first_name')
        lastName = data.get('last_name')
        phoneNumber = data.get('phone_number')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        user = getUserByEmail(email)
        # if user:
        #     response['message'] = 'Email taken'
        #     response['code'] = 409
        # else:
        #     user = createUser(firstName, lastName, phoneNumber, email, password, role)
        #     response['message'] = 'Signup success'
        #     response['code'] = 200
        #     response['result'] = createTokens(user)
        user = createUser(firstName, lastName, phoneNumber,
                          email, password, role)
        response['message'] = 'Signup success'
        response['code'] = 200
        response['result'] = createTokens(user)
        return response

    def put(self):
        response = {}
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')
        user = getUserByEmail(email)
        if user:
            print(user)
            uid = {'user_uid': user['user_uid']}
            updateRole = {'role': user['role'] + ',' + role}
            with connect() as db:
                res = db.update('users', uid, updateRole)
                u = getUserByEmail(email)
                response['message'] = 'Signup success'
                response['code'] = 200
                response['result'] = createTokens(u)

        else:

            response['message'] = 'Account does not exist! Please Signup'
            response['code'] = 200

        return response
