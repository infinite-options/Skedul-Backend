
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from data import connect
import json

class OwnerProperties(Resource):
    decorators = [jwt_required()]
    def get(self):
        response = {}
        user = get_jwt_identity()
        with connect() as db:
            where = {
                'owner_id': user['user_uid']
            }
            response = db.select('propertyInfo', where)
        return response
