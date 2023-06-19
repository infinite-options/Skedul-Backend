# To run program:  python3 skedul_api.py
# https://pi4chbdo50.execute-api.us-west-1.amazonaws.com/dev/api/v2
# README:  if conn error make sure password is set properly in RDS PASSWORD section

# README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)

# README:  if there are errors, make sure you have all requirements are loaded
# pip3 install flask
# pip3 install flask_restful
# pip3 install flask_cors
# pip3 install Werkzeug
# pip3 install pymysql
# pip3 install python-dateutil

import os
import uuid
import boto3
import json
import math
import httplib2

from datetime import time, date, datetime, timedelta
import calendar

from pytz import timezone
import random
import string
import stripe


from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message

from collections import OrderedDict, Counter

# used for serializer email and error handling
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
# from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.security import generate_password_hash, check_password_hash

import googleapiclient.discovery as discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

#  NEED TO SOLVE THIS
# from NotificationHub import Notification
# from NotificationHub import NotificationHub

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from twilio.rest import Client

from dateutil.relativedelta import *
from dateutil import tz
from decimal import Decimal
# from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
import string
import random
import hashlib

# BING API KEY
# Import Bing API key into bing_api_key.py

#  NEED TO SOLVE THIS
# from env_keys import BING_API_KEY, RDS_PW

import decimal
import sys
import json
import pytz
import pymysql
import requests


RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
RDS_PORT = 3306
RDS_USER = "admin"
RDS_DB = "skedul"

# SCOPES = "https://www.googleapis.com/auth/calendar"
SCOPES = "https://www.googleapis.com/auth/calendar.events"
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "skedul"
# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")


# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead


# STRIPE AND PAYPAL KEYS
paypal_secret_test_key = os.environ.get("paypal_secret_key_test")
paypal_secret_live_key = os.environ.get("paypal_secret_key_live")

paypal_client_test_key = os.environ.get("paypal_client_test_key")
paypal_client_live_key = os.environ.get("paypal_client_live_key")

stripe_public_test_key = os.environ.get("stripe_public_test_key")
stripe_secret_test_key = os.environ.get("stripe_secret_test_key")

stripe_public_live_key = os.environ.get("stripe_public_live_key")
stripe_secret_live_key = os.environ.get("stripe_secret_live_key")

stripe.api_key = stripe_secret_test_key

# use below for local testing
# stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3""


CORS(app)

# --------------- Mail Variables ------------------
# Setting for mydomain.com
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465

# Mail username and password loaded in zappa_settings.json file
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
# pp.config["MAIL_USERNAME"] = os.environ.get("SUPPORT_EMAIL")
app.config["MAIL_USERNAME"] = "support@skedul.online"
# app.config["MAIL_PASSWORD"] = os.environ.get("SUPPORT_PASSWORD")
app.config["MAIL_PASSWORD"] = "SupportSkedul1"
# app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("SUPPORT_EMAIL")
app.config["MAIL_DEFAULT_SENDER"] = "support@skedul.online"
app.config["MAIL_SUPPRESS_SEND"] = False

# Set this to false when deploying to live application
app.config["DEBUG"] = True
app.testing = False
# app.config["DEBUG"] = False

app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc

# # These statment return Day and Time in GMT
def getTodayUTC(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
def getNowUTC(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")

# These statment return Day and Time in Local Time - Not sure about PST vs PDT
def getToday():
    return datetime.strftime(datetime.now(), "%Y-%m-%d")

def getNow():
    return datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")


# Not sure what these statments do
# getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
# print(getToday)
# getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
# print(getNow)


# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""


# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = "prashant"
# RDS_PW = RdsPw()


s3 = boto3.client("s3")

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('skedul-images')
BUCKET_NAME = "skedul-images"
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])


# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.environ.get("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.environ.get("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# Connect to MySQL database (API v2)


def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            port=RDS_PORT,
            passwd=RDS_PW,
            db=RDS_DB,
            cursorclass=pymysql.cursors.DictCursor,
        )
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")


# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")


# Serialize JSON
def serializeResponse(response):
    try:
        # print("In Serialize JSON")
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        # print("In Serialize JSON response", response)
        return response
    except:
        raise Exception("Bad query JSON")


# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization=False):

    # print("In SQL Execute Function")
    # print(cmd)
    # print(sql)
    response = {}
    try:
        with conn.cursor() as cur:
            # print("Before Execute")
            cur.execute(sql)
            # print("After Execute")
            if cmd == "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd == "post":
                conn.commit()
                response["message"] = "Successfully committed SQL command."
                # Return status code of 281 for successful POST request
                response["code"] = 281
            else:
                response[
                    "message"
                ] = "Request failed. Unknown or ambiguous instruction given for MySQL command."
                # Return status code of 480 for unknown HTTP method
                response["code"] = 480
    except:
        response["message"] = "Request failed, could not execute MySQL command."
        # Return status code of 490 for unsuccessful HTTP request
        response["code"] = 490
    finally:
        response["sql"] = sql
        return response


# Close RDS connection
def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")


# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples
def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")


# -- Stored Procedures start here -------------------------------------------------------------------------------


# RUN STORED PROCEDURES
def get_new_paymentID(conn):
    newPaymentQuery = execute("CALL new_payment_uid", "get", conn)
    if newPaymentQuery["code"] == 280:
        return newPaymentQuery["result"][0]["new_id"]
    return "Could not generate new payment ID", 500


def get_new_contactUID(conn):
    newPurchaseQuery = execute("CALL skedul.new_contact_uid()", "get", conn)
    if newPurchaseQuery["code"] == 280:
        return newPurchaseQuery["result"][0]["new_id"]
    return "Could not generate new contact UID", 500


# -- Queries start here -------------------------------------------------------------------------------


class GoogleCalenderEvents(Resource):
    def post(self, user_unique_id, start, end):
        print("In Google Calender Events")
        try:
            conn = connect()
            # data = request.get_json(force=True)
            print(user_unique_id, start, end)
            timestamp = getNow()
            # user_unique_id = data["id"]
            # start = data["start"]
            # end = data["end"]

            items = execute(
                """SELECT user_email_id, google_refresh_token, google_auth_token, social_timestamp, access_expires_in FROM customers WHERE user_unique_id = \'"""
                + user_unique_id
                + """\'""",
                "get",
                conn,
            )

            if len(items["result"]) == 0:
                return "No such user exists"
            print("items", items)
            if (
                items["result"][0]["access_expires_in"] == None
                or items["result"][0]["social_timestamp"] == None
            ):
                f = open(
                    "credentials.json",
                )
                print("in if")
                data = json.load(f)
                client_id = data["web"]["client_id"]
                client_secret = data["web"]["client_secret"]
                refresh_token = items["result"][0]["google_refresh_token"]
                print("in if", data)
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items["result"][0]["google_refresh_token"],
                }
                print("in if", params)
                authorization_url = "https://accounts.google.com/o/oauth2/token"
                r = requests.post(authorization_url, data=params)
                auth_token = ""
                if r.ok:
                    auth_token = r.json()["access_token"]
                expires_in = r.json()["expires_in"]
                print("in if", expires_in)
                execute(
                    """UPDATE customers SET
                                google_auth_token = \'"""
                    + str(auth_token)
                    + """\'
                                , social_timestamp = \'"""
                    + str(timestamp)
                    + """\'
                                , access_expires_in = \'"""
                    + str(expires_in)
                    + """\'
                                WHERE user_unique_id = \'"""
                    + user_unique_id
                    + """\';""",
                    "post",
                    conn,
                )
                items = execute(
                    """SELECT user_email_id, google_refresh_token, google_auth_token, social_timestamp, access_expires_in FROM customers WHERE user_unique_id = \'"""
                    + user_unique_id
                    + """\'""",
                    "get",
                    conn,
                )
                print(items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&"
                timeMaxMin = "timeMax=" + end + "&timeMin=" + start
                url = baseUri + timeMaxMin
                bearerString = "Bearer " + \
                    items["result"][0]["google_auth_token"]
                headers = {"Authorization": bearerString,
                           "Accept": "application/json"}
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                calendars = response.json().get("items")
                return calendars

            else:
                print("in else")
                access_issue_min = int(
                    items["result"][0]["access_expires_in"]) / 60
                print("in else", access_issue_min)
                print("in else", items["result"][0]["social_timestamp"])
                social_timestamp = datetime.strptime(
                    items["result"][0]["social_timestamp"], "%Y-%m-%d %H:%M:%S"
                )
                print("in else", social_timestamp)

                timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                print("in else", timestamp)
                diff = (timestamp - social_timestamp).total_seconds() / 60
                print("in else", diff)
                if int(diff) > int(access_issue_min):
                    print("in else", diff)
                    f = open(
                        "credentials.json",
                    )
                    data = json.load(f)
                    client_id = data["web"]["client_id"]
                    client_secret = data["web"]["client_secret"]
                    refresh_token = items["result"][0]["google_refresh_token"]
                    print("in else data", data)
                    params = {
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": items["result"][0]["google_refresh_token"],
                    }
                    print("in else", params)
                    authorization_url = "https://accounts.google.com/o/oauth2/token"
                    r = requests.post(authorization_url, data=params)
                    print("in else", r)
                    auth_token = ""
                    if r.ok:
                        auth_token = r.json()["access_token"]
                    expires_in = r.json()["expires_in"]
                    print("in else", expires_in)
                    execute(
                        """UPDATE customers SET
                                    google_auth_token = \'"""
                        + str(auth_token)
                        + """\'
                                    , social_timestamp = \'"""
                        + str(timestamp)
                        + """\'
                                    , access_expires_in = \'"""
                        + str(expires_in)
                        + """\'
                                    WHERE user_unique_id = \'"""
                        + user_unique_id
                        + """\';""",
                        "post",
                        conn,
                    )

                items = execute(
                    """SELECT user_email_id, google_refresh_token, google_auth_token, social_timestamp, access_expires_in FROM customers WHERE user_unique_id = \'"""
                    + user_unique_id
                    + """\'""",
                    "get",
                    conn,
                )
                print("items2", items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&singleEvents=true&"
                print("items2", baseUri)
                timeMaxMin = "timeMax=" + end + "&timeMin=" + start
                print(timeMaxMin)
                url = baseUri + timeMaxMin
                print(url)
                bearerString = "Bearer " + \
                    items["result"][0]["google_auth_token"]
                print(bearerString)
                headers = {"Authorization": bearerString,
                           "Accept": "application/json"}
                print(headers)
                response = requests.get(url, headers=headers)

                print(response)

                response.raise_for_status()
                calendars = response.json().get("items")
                return calendars

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- SKEDUL ENDPOINTS -----------------------------------------------------------------
# -- ACCOUNT ENDPOINTS ----------------

# Creating new user
class UserSignUp(Resource):
    def post(self):
        print("In UserSignUp")
        response = {}
        items = {}
        timestamp = getNow()
        try:
            conn = connect()
            data = request.get_json(force=True)
            email_id = data["email_id"]
            password = data["password"]
            first_name = data["first_name"]
            last_name = data["last_name"]
            time_zone = data["time_zone"]

            user_id_response = execute(
                """SELECT user_unique_id FROM users
                                            WHERE user_email_id = \'"""
                + email_id
                + """\';""",
                "get",
                conn,
            )

            if len(user_id_response["result"]) > 0:
                response["message"] = "User already exists"

            else:

                salt = os.urandom(32)

                dk = hashlib.pbkdf2_hmac(
                    "sha256", password.encode("utf-8"), salt, 100000, dklen=128
                )
                key = (salt + dk).hex()

                user_id_response = execute("CAll get_user_id;", "get", conn)
                new_user_id = user_id_response["result"][0]["new_id"]

                execute(
                    """INSERT INTO users
                           SET user_unique_id = \'"""
                    + new_user_id
                    + """\',
                               user_timestamp = \'"""
                    + timestamp
                    + """\',
                               user_email_id  = \'"""
                    + email_id
                    + """\',
                               user_first_name = \'"""
                    + first_name
                    + """\',
                               user_last_name = \'"""
                    + last_name
                    + """\',
                               password_hashed = \'"""
                    + key
                    + """\',
                               time_zone = \'"""
                    + time_zone
                    + """\';""",
                    "post",
                    conn,
                )

                response["message"] = "successful"
                response["result"] = new_user_id

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# creating new user social
class UserSocialSignUp(Resource):
    def post(self):
        print("In create new user")
        response = {}
        items = {}
        timestamp = getNow()
        try:
            conn = connect()
            data = request.get_json(force=True)
            print("In try", data)
            email_id = data["email_id"]
            print(email_id)
            first_name = data["first_name"]
            print(first_name)
            last_name = data["last_name"]
            print(last_name)
            time_zone = data["time_zone"]
            print(time_zone)
            google_auth_token = data["google_auth_token"]
            print(google_auth_token)
            social_id = data["social_id"]
            print(social_id)
            google_refresh_token = data["google_refresh_token"]
            print(google_refresh_token)
            access_expires_in = data["access_expires_in"]
            print(access_expires_in)

            user_id_response = execute(
                """SELECT user_unique_id FROM users
                                            WHERE user_email_id = \'"""
                + email_id
                + """\';""",
                "get",
                conn,
            )

            if len(user_id_response["result"]) > 0:
                response["message"] = "User already exists"

            else:
                user_id_response = execute("CAll get_user_id;", "get", conn)
                new_user_id = user_id_response["result"][0]["new_id"]

                execute(
                    """INSERT INTO users
                           SET user_unique_id = \'"""
                    + new_user_id
                    + """\',
                               user_timestamp = \'"""
                    + timestamp
                    + """\',
                               user_email_id = \'"""
                    + email_id
                    + """\',
                               user_first_name = \'"""
                    + first_name
                    + """\',
                               user_last_name = \'"""
                    + last_name
                    + """\',
                               social_id = \'"""
                    + social_id
                    + """\',
                               google_auth_token = \'"""
                    + google_auth_token
                    + """\',
                               google_refresh_token = \'"""
                    + google_refresh_token
                    + """\',
                               access_expires_in = \'"""
                    + access_expires_in
                    + """\',
                               time_zone = \'"""
                    + time_zone
                    + """\',
                               user_have_pic = \'"""
                    + "False"
                    + """\',
                               user_picture = \'"""
                    + ""
                    + """\',
                               user_social_media = \'"""
                    + "null"
                    + """\',
                               new_account = \'"""
                    + "True"
                    + """\',
                               user_guid_device_id_notification = \'"""
                    + "null"
                    + """\';""",
                    "post",
                    conn,
                )

                response["message"] = "successful"
                response["result"] = new_user_id

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# get user tokens
class UserToken(Resource):
    def get(self, user_email_id):
        print("In usertoken")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None

            query = (
                """SELECT user_unique_id
                                , user_email_id
                                , google_auth_token
                                , google_refresh_token
                        FROM
                        users WHERE user_email_id = \'"""
                + user_email_id
                + """\';"""
            )

            items = execute(query, "get", conn)
            print(items)
            response["message"] = "successful"
            response["user_unique_id"] = items["result"][0]["user_unique_id"]
            response["user_email_id"] = items["result"][0]["user_email_id"]
            response["google_auth_token"] = items["result"][0]["google_auth_token"]
            response["google_refresh_token"] = items["result"][0][
                "google_refresh_token"
            ]

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# get user tokens
class UserDetails(Resource):
    def get(self, user_id):
        print("In userDetails")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None

            query = (
                """SELECT user_unique_id
                                , user_email_id
                                , user_first_name
                                , user_last_name
                                , google_auth_token
                                , google_refresh_token
                                , time_zone
                        FROM
                        users WHERE user_unique_id = \'"""
                + user_id
                + """\';"""
            )

            items = execute(query, "get", conn)
            print(items)
            response["message"] = "successful"
            response["user_unique_id"] = items["result"][0]["user_unique_id"]
            response["user_first_name"] = items["result"][0]["user_first_name"]
            response["user_last_name"] = items["result"][0]["user_last_name"]
            response["user_email_id"] = items["result"][0]["user_email_id"]
            response["google_auth_token"] = items["result"][0]["google_auth_token"]
            response["google_refresh_token"] = items["result"][0][
                "google_refresh_token"
            ]
            response["user_time_zone"] = items["result"][0]["time_zone"]

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# updating access token if expired
class UpdateAccessToken(Resource):
    def post(self, user_unique_id):
        print("In UpdateAccessToken")
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            google_auth_token = data["google_auth_token"]

            execute(
                """UPDATE users
                       SET google_auth_token = \'"""
                + google_auth_token
                + """\'
                       WHERE user_unique_id = \'"""
                + user_unique_id
                + """\';
                        """,
                "post",
                conn,
            )

            response["message"] = "successful"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# CHECK THAT THIS IS ONLY USED FOR MOBILE LOGIN
class Login(Resource):
    def post(self):
        print("In Login")
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            timestamp = getNow()

            email = data["email"]
            user_first_name = data["user_first_name"]
            user_last_name = data["user_last_name"]
            social_id = data["social_id"]
            # password = data.get('password')
            refresh_token = data.get("mobile_refresh_token")
            access_token = data.get("mobile_access_token")
            signup_platform = data.get("signup_platform")
            time_zone = data["time_zone"]
            print("time_zone: ", time_zone, type(time_zone))

            if email == "":

                query = (
                    """
                        SELECT user_unique_id,
                            user_last_name,
                            user_first_name,
                            user_email_id,
                            user_social_media,
                            google_auth_token,
                            google_refresh_token
                        FROM users
                        WHERE social_id = \'"""
                    + social_id
                    + """\';
                        """
                )

                items = execute(query, "get", conn)

            else:
                query = (
                    """
                        SELECT user_unique_id,
                            user_last_name,
                            user_first_name,
                            user_email_id,
                            user_social_media,
                            google_auth_token,
                            google_refresh_token
                        FROM users
                        WHERE user_email_id = \'"""
                    + email
                    + """\';
                        """
                )

                items = execute(query, "get", conn)

            # print('Password', password)
            print(items)

            if items["code"] != 280:
                response["message"] = "Internal Server Error."
                response["code"] = 500
                return response
            elif not items["result"]:

                # CREATE NEW ACCOUNT HERE
                print("Account not found. Creating new account")
                user_id_response = execute("CAll get_user_id;", "get", conn)
                new_user_id = user_id_response["result"][0]["new_id"]

                execute(
                    """INSERT INTO users
                           SET user_unique_id = \'"""
                    + new_user_id
                    + """\',
                               user_timestamp = \'"""
                    + timestamp
                    + """\',
                               user_email_id = \'"""
                    + email
                    + """\',
                               user_first_name = \'"""
                    + user_first_name
                    + """\',
                               user_last_name = \'"""
                    + user_last_name
                    + """\',
                               social_id = \'"""
                    + social_id
                    + """\',
                               mobile_auth_token = \'"""
                    + access_token
                    + """\',
                               mobile_refresh_token = \'"""
                    + refresh_token
                    + """\',
                               time_zone = \'"""
                    + time_zone
                    + """\',
                               user_have_pic = \'"""
                    + "False"
                    + """\',
                               user_picture = \'"""
                    + ""
                    + """\',
                               user_social_media = \'"""
                    + signup_platform
                    + """\',
                               new_account = \'"""
                    + "True"
                    + """\',
                               cust_guid_device_id_notification = \'"""
                    + "null"
                    + """\';""",
                    "post",
                    conn,
                )

                response["message"] = "successful"
                response["result"] = new_user_id

                # QUERY DB TO GET USER INFO
                query = "SELECT * from users WHERE user_email_id = '" + email + "';"
                items = execute(query, "get", conn)

                items["message"] = "User Not Found. New User Created."
                items["code"] = 200
                return items

            else:
                print(items["result"])
                print("sc: ", items["result"][0]["user_social_media"])

                if email == "":
                    execute(
                        """
                        UPDATE users
                        SET mobile_refresh_token = \'"""
                        + refresh_token
                        + """\'
                          , mobile_auth_token =  \'"""
                        + access_token
                        + """\'
                          , time_zone = \'"""
                        + time_zone
                        + """\'
                        WHERE social_id =  \'"""
                        + social_id
                        + """\';
                        """,
                        "post",
                        conn,
                    )

                    query = "SELECT * from users WHERE social_id = '" + social_id + "';"
                    items = execute(query, "get", conn)
                else:
                    print(email)
                    execute(
                        """
                        UPDATE users
                        SET mobile_refresh_token = \'"""
                        + refresh_token
                        + """\'
                          , mobile_auth_token =  \'"""
                        + access_token
                        + """\'
                          , social_id =  \'"""
                        + social_id
                        + """\'
                          , user_social_media =  \'"""
                        + signup_platform
                        + """\'
                          , time_zone = \'"""
                        + time_zone
                        + """\'
                        WHERE user_email_id =  \'"""
                        + email
                        + """\';""",
                        "post",
                        conn,
                    )

                    query = "SELECT * from users WHERE user_email_id = '" + email + "';"
                    items = execute(query, "get", conn)
                items["message"] = "Authenticated successfully."
                items["code"] = 200
                return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class AccessRefresh(Resource):
    def post(self, user_unique_id):
        print("In AccessRefresh")
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            refresh_token = data.get("mobile_refresh_token")
            access_token = data.get("mobile_access_token")

            execute(
                """UPDATE users SET mobile_refresh_token = \'"""
                + refresh_token
                + """\'
                                    , mobile_auth_token =  \'"""
                + access_token
                + """\'
                    WHERE user_unique_id =  \'"""
                + user_unique_id
                + """\';""",
                "post",
                conn,
            )

            items["message"] = "Updated successfully."
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# Existing User login
class UserLogin(Resource):
    def get(self, email_id, password):
        print("In UserLogin")
        response = {}
        items = {}

        try:
            conn = connect()
            # data = request.get_json(force=True)
            # email_id = data['email_id']
            # password = data['password']
            temp = False
            emails = execute(
                """SELECT user_email_id from users;""", "get", conn)
            for i in range(len(emails["result"])):
                email = emails["result"][i]["user_email_id"]
                if email == email_id:
                    temp = True
            if temp == True:
                emailIDResponse = execute(
                    """SELECT user_unique_id, password_hashed from users where user_email_id = \'"""
                    + email_id
                    + """\'""",
                    "get",
                    conn,
                )
                password_storage = emailIDResponse["result"][0]["password_hashed"]

                original = bytes.fromhex(password_storage)
                salt_from_storage = original[:32]
                key_from_storage = original[32:]

                new_dk = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt_from_storage,
                    100000,
                    dklen=128,
                )

                if key_from_storage == new_dk:
                    response["result"] = emailIDResponse["result"][0]["user_unique_id"]
                    response["message"] = "Correct Email and Password"
                else:
                    response["result"] = False
                    response["message"] = "Wrong Password"

            if temp == False:
                response["result"] = False
                response["message"] = "Email ID doesnt exist"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# user social login
class UserSocialLogin(Resource):
    def get(self, email_id):
        print("In UserSocialLogin")
        response = {}
        items = {}

        try:
            conn = connect()
            temp = False
            emails = execute(
                """SELECT user_unique_id, user_email_id, google_auth_token from users;""",
                "get",
                conn,
            )
            for i in range(len(emails["result"])):
                email = emails["result"][i]["user_email_id"]
                if email == email_id:
                    temp = True
                    user_unique_id = emails["result"][i]["user_unique_id"]
                    google_auth_token = emails["result"][i]["google_auth_token"]
            if temp == True:

                response["result"] = user_unique_id, google_auth_token
                response["message"] = "Correct Email"

            if temp == False:
                response["result"] = False
                response["message"] = "Email ID doesnt exist"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetEmailId(Resource):
    def get(self, email_id):
        print("In GetEmailID")
        response = {}
        items = {}

        try:
            conn = connect()
            emails = execute(
                """SELECT user_email_id, user_unique_id from users where user_email_id = \'"""
                + email_id
                + """\';""",
                "get",
                conn,
            )
            if len(emails["result"]) > 0:
                response["message"] = "User EmailID exists"
                response["result"] = emails["result"][0]["user_unique_id"]
            else:
                response["message"] = "User EmailID doesnt exist"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- EVENT PAGE ----------------
class AddEvent(Resource):
    def post(self):
        print("In AddEvent")
        response = {}
        items = {}
        try:
            conn = connect()
            print("Before Data")
            data = request.get_json(force=True)
            view_id = data["view_id"]
            print("View ID")
            print(view_id)
            user_id = data["user_id"]
            print(user_id)
            event_name = data["event_name"]
            print(event_name)
            location = data["location"]
            print(location)
            duration = data["duration"]
            print(duration)
            buffer_time = data["buffer_time"]
            print(buffer_time)
            # buffer_time = json.loads(buffer_time)
            print(buffer_time)
            before_is_enable = buffer_time["before"]["is_enabled"]
            before_time = buffer_time["before"]["time"]
            after_is_enable = buffer_time["after"]["is_enabled"]
            after_time = buffer_time["after"]["time"]

            buffer = {
                "before": {"is_enabled": before_is_enable, "time": before_time},
                "after": {"is_enabled": after_is_enable, "time": after_time},
            }
            print(buffer)

            if duration != "":
                print("1")
                if duration[3:5] == "30":
                    duration = duration[0:2] + ":29" + ":59"
                    print("2")
                elif duration[0:2] == "00":
                    x = int(duration[3:5])
                    print(x)
                    x -= 1
                    print(x)
                    duration = duration[0:2] + ":" + str(x) + ":59"
                    print(duration)
                elif duration[3:5] == "00" and duration[6:8] == "00":
                    x = int(duration[0:2])
                    print(x)
                    x -= 1
                    duration = "0" + str(x) + ":59" + ":59"
                else:
                    x = int(duration[3:5])
                    print(x)
                    x -= 1
                    print(x)
                    duration = duration[0:2] + ":" + str(x) + ":59"

                    print(duration)
                    # x = int(duration[0])
                    # x -= 1
                    # position = 0
                    # duration = duration[:position] + str(x) + duration[position + 1 :]
                    # print(duration)

            query = ["CALL skedul.get_event_id;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO skedul.event_types
                    SET event_unique_id  = \'"""
                + str(NewID)
                + """\',
                        user_id = \'"""
                + str(user_id)
                + """\',
                        view_id = \'"""
                + str(view_id)
                + """\',
                        event_name = \'"""
                + str(event_name).replace("'", "''")
                + """\',
                        location = \'"""
                + str(location).replace("'", "''")
                + """\',
                        duration= \'"""
                + str(duration)
                + """\',
                        buffer_time = \'"""
                + str(json.dumps(buffer, sort_keys=False))
                + """\';
                    """
            )
            print(query)
            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "New Event Added"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UpdateEvent(Resource):
    def post(self, event_id):
        print("In UpdateEvent")
        response = {}
        items = {}
        try:
            conn = connect()
            print("Before Data")
            data = request.get_json(force=True)
            event_name = data["event_name"]
            location = data["location"]
            duration = data["duration"]
            buffer_time = data["buffer_time"]
            print(buffer_time)
            before_is_enable = buffer_time["before"]["is_enabled"]
            before_time = buffer_time["before"]["time"]
            after_is_enable = buffer_time["after"]["is_enabled"]
            after_time = buffer_time["after"]["time"]
            print("Date Received")
            buffer = {
                "before": {"is_enabled": before_is_enable, "time": before_time},
                "after": {"is_enabled": after_is_enable, "time": after_time},
            }

            print("Data Received")

            if duration != "":
                if duration[3:5] == "30":
                    duration = duration[0:2] + ":29" + ":59"
                elif duration[0:2] == "00":
                    x = int(duration[3:5])
                    print(x)
                    x -= 1
                    print(x)
                    duration = duration[0:2] + ":" + str(x) + ":59"
                    print(duration)
                elif duration[3:5] == "00" and duration[6:8] == "00":
                    x = int(duration[0:2])
                    print(x)
                    x -= 1
                    duration = "0" + str(x) + ":59" + ":59"
                else:
                    x = int(duration[3:5])
                    print(x)
                    x -= 1
                    print(x)
                    duration = duration[0:2] + ":" + str(x) + ":59"

                    print(duration)

            query = (
                """
                    UPDATE skedul.event_types
                    SET event_name = \'"""
                + str(event_name).replace("'", "''")
                + """\',
                        location = \'"""
                + str(location).replace("'", "''")
                + """\',
                        duration= \'"""
                + str(duration)
                + """\',
                        buffer_time = \'"""
                + str(json.dumps(buffer, sort_keys=False))
                + """\'
                        WHERE event_unique_id = \'"""
                + event_id
                + """\';
                    """
            )
            print(query)
            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Event Updated"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class DeleteEvent(Resource):
    def post(self):
        print("In DeleteEvent")
        response = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            event_id = data['event_id']

            query = """DELETE FROM event_types WHERE event_unique_id = \'""" + event_id + """\';"""
            execute(query, 'post', conn)
            query = """DELETE FROM meetings WHERE event_id = \'""" + event_id + """\';"""
            execute(query, 'post', conn)

            response['message'] = 'successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class GetAllEvents(Resource):
    def get(self, view_id):
        print("In GetAllEvents")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT view_id
                            , user_id
                            , event_unique_id
                            , event_name
                            , location
                            , duration
                            , buffer_time
                        FROM skedul.event_types
                        WHERE view_id = \'"""
                + view_id
                + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetAllEventsUser(Resource):
    def get(self, user_id):
        print("In GetAllEventsUser")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT view_id
                            , user_id
                            , event_unique_id
                            , event_name
                            , location
                            , duration
                            , buffer_time
                        FROM skedul.event_types
                        WHERE user_id = \'"""
                + user_id
                + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetEvent(Resource):
    def get(self, event_id):
        print("In GetEvent")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT view_id
                            , user_id
                            , event_unique_id
                            , event_name
                            , location
                            , duration
                            , buffer_time
                        FROM skedul.event_types
                        WHERE event_unique_id = \'""" + event_id + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class SendEmail(Resource):
    def post(self, email):
        try:
            conn = connect()
            data = request.get_json(force=True)
            url = data["url"]
            print(url)
            msg = Message(
                subject="Schedule a meeting",
                sender="support@skedul.online",
                recipients=[email],
            )

            msg.body = (
                "Hello!\n\n"
                "Please click on the link below to schedule a meeting with.\n\n"
                "{}".format(url)
                + "\n\n"
                + "Email support@skedul.online if you run into any problems or have any questions.\n"
                "Thanks - The Skedul Team"
            )

            print(msg.body)
            mail.send(msg)
            return "Email Sent"
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- VIEW PAGE ----------------


class AddView(Resource):
    def post(self):
        print("In AddView")
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            user_id = data["user_id"]
            view_name = data["view_name"]
            color = data["color"]
            schedule = data["schedule"]
            # print(schedule)
            print(str(json.dumps(schedule)))
            query = ["CALL skedul.get_view_id;"]
            # print(query)
            NewIDresponse = execute(query[0], "get", conn)
            # print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            # print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO skedul.views
                    SET view_unique_id  = \'"""
                + str(NewID)
                + """\',
                        user_id = \'"""
                + str(user_id)
                + """\',
                        view_name = \'"""
                + str(view_name).replace("'", "''")
                + """\',
                        color = \'"""
                + str(color)
                + """\',
                        schedule= \'"""
                + json.dumps(schedule, sort_keys=False)
                + """\';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "New View Added"
                response["data"] = items
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UpdateView(Resource):
    def post(self, view_id):
        print("In UpdateView")
        response = {}
        items = {}
        try:
            conn = connect()
            print("Before Data")
            data = request.get_json(force=True)
            type = data["updateType"]
            query = ()
            if type == "view":
                name = data["name"]
                color = data["color"]
                print("Data Received")

                query = (
                    """
                        UPDATE skedul.views
                        SET view_name= \'"""
                    + str(name).replace("'", "''")
                    + """\',
                        color = \'"""
                    + str(color)
                    + """\'
                            WHERE view_unique_id = \'"""
                    + view_id
                    + """\';
                        """
                )
            else:
                schedule = data["schedule"]
                print("Data Received")
                query = (
                    """
                        UPDATE skedul.views
                        SET schedule= \'"""
                    + json.dumps(schedule, sort_keys=False)
                    + """\'
                            WHERE view_unique_id = \'"""
                    + view_id
                    + """\';
                        """
                )
            print(query)
            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "View Updated"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class DeleteView(Resource):
    def post(self):
        print("In DeleteView")
        response = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            view_id = data['view_id']

            query = """DELETE FROM views WHERE view_unique_id = \'""" + view_id + """\';"""
            execute(query, 'post', conn)
            query = """DELETE FROM event_types WHERE view_id = \'""" + view_id + """\';"""
            execute(query, 'post', conn)
            query = """DELETE FROM meetings WHERE view_id = \'""" + view_id + """\';"""
            execute(query, 'post', conn)

            response['message'] = 'successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class GetAllViews(Resource):
    def get(self, user_id):
        print("In GetAllViews")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT user_id
                            , view_unique_id
                            , view_name
                            , schedule
                            , color
                        FROM skedul.views
                        WHERE user_id = \'"""
                + user_id
                + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)
            # print(items)
            query = (
                """SELECT time_zone
                FROM skedul.users
                        WHERE user_unique_id = \'"""
                + user_id
                + """\';"""
             )
            timeZoneResult = execute(query, "get", conn)
            user_timezone = timeZoneResult['result'][0]['time_zone']
            if user_timezone == '' :
                user_timezone = 'America/Los_Angeles'
            # print("user_timezone",user_timezone)
            weekDatesResult = weekDates()
            # print("weekDates",weekDatesResult)

            for i in items["result"]:
                utc_schedule = json.loads(i["schedule"])
                scheduleArray = {}
                # print("utc schedule ", utc_schedule)
                for day in utc_schedule:
                    # print(day)
                    if day not in scheduleArray:
                        scheduleArray[day] = []
                    if len(utc_schedule[day]) != 0 and utc_schedule[day][0]['start_time'] != '' and utc_schedule[day][0]['end_time'] != '':
                        corresponding_date = weekDatesResult[day]
                        dateTimeStringStart = corresponding_date + " " + utc_schedule[day][0]['start_time'] + ":00 " + day
                        local_startDateTime = convertToLocalTZ(user_timezone, dateTimeStringStart)
                        local_startTime = local_startDateTime.strftime("%H:%M")
                        local_startDay = local_startDateTime.strftime("%A")
                        print("local_startDateTime ", local_startDateTime)
                        print("local_startTime ", local_startTime)
                        print("local_startDay ", local_startDay)

                        dateTimeStringEnd = corresponding_date + " " + utc_schedule[day][0]['end_time'] + ":00 " + day
                        local_endDateTime = convertToLocalTZ(user_timezone,dateTimeStringEnd)
                        local_endTime = local_endDateTime.strftime("%H:%M")
                        local_endDay = local_endDateTime.strftime("%A")
                        print("local_endDateTime ", local_endDateTime)
                        print("local_endTime ", local_endTime)
                        print("local_endDay ", local_endDay)
                        checkSameDate = local_startDateTime.date() == local_endDateTime.date()
                        # print(" check ", local_startDateTime.date() == local_endDateTime.date())

                        if checkSameDate == False:
                            localSchedule = {'start_time' : local_startTime, 'end_time' : "23:59"}
                            scheduleArray[local_startDay] = [localSchedule]
                            localSchedule = {'start_time' : "00:00", 'end_time' : local_endTime}
                            if local_endDay not in scheduleArray:
                                scheduleArray[local_endDay]=[localSchedule]
                            else:
                                scheduleArray[local_endDay].append(localSchedule)
                        else:
                            # print("checkSameDate ",checkSameDate)
                            localSchedule = {'start_time' : local_startTime, 'end_time' : local_endTime}
                            # print("localSchedule ",localSchedule, " 88 ",local_startDay)
                            # print("scheduleArray ===== ",scheduleArray)
                            if local_startDay not in scheduleArray:
                                scheduleArray[local_startDay]=[localSchedule]
                            else:
                                scheduleArray[local_startDay].append(localSchedule)
                        #     print("scheduleArray ",scheduleArray[local_startDay])
                        # print("**** scheduleArray", scheduleArray)
                # print("scheduleArray", scheduleArray)
                # print("sched ", i)
                scheduleStr = json.dumps(scheduleArray)
                i.update({'schedule':scheduleStr})
                print("sched2 ", i)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetView(Resource):
    def get(self, view_id):
        print("In GetView")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT user_id
                            , view_unique_id
                            , view_name
                            , schedule
                            , color
                        FROM skedul.views
                        WHERE view_unique_id = \'""" + view_id + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- SCHEDULE PAGE -----------

def weekDates() :
    try :
        today = datetime.utcnow()
        # print("today utc",today)
        result = {}
        for x in range(7):
            d = today + timedelta(days=x)
            date = d.strftime("%Y-%m-%d")
            dayOfWeek = d.strftime('%A')
            result[dayOfWeek] = date
            # print(date, dayOfWeek)
        # print(result)
        return result
    except Exception as e: 
        print(e)

def convertToLocalTZ(user_timezone, dateTimeString) :
    try :
        print("dateTimeString ", dateTimeString)
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(user_timezone)
        # print("from_zone ", from_zone, " to_zone ", to_zone)
        utc_date = datetime.strptime(dateTimeString, '%Y-%m-%d %H:%M:%S %A')
        utc_date = utc_date.replace(tzinfo=from_zone)
        local_date = utc_date.astimezone(to_zone)
        print("utc_date",utc_date, " ** local_date ", local_date)
        return local_date
    except Exception as e: 
        print(e)

class GetSchedule(Resource):
    def get(self, user_id):
        print("In GetSchedule")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT view_unique_id
                            , view_name
                            , (schedule)
                            , color
                        FROM skedul.views
                        WHERE user_id = \'"""
                + user_id
                + """\';"""
            )
            items = execute(query, "get", conn)

            query = (
                """SELECT time_zone
                FROM skedul.users
                        WHERE user_unique_id = \'"""
                + user_id
                + """\';"""
             )
            timeZoneResult = execute(query, "get", conn)
            user_timezone = timeZoneResult['result'][0]['time_zone']
            if user_timezone == '' :
                user_timezone = 'America/Los_Angeles'
            # print("user_timezone",user_timezone)
            weekDatesResult = weekDates()
            # print("weekDates",weekDatesResult)

            for i in items["result"]:
                utc_schedule = json.loads(i["schedule"])
                scheduleArray = {}
                # print("utc schedule ", utc_schedule)
                for day in utc_schedule:
                    print(day)
                    if day not in scheduleArray:
                        scheduleArray[day] = []
                    if len(utc_schedule[day]) != 0:
                        corresponding_date = weekDatesResult[day]
                        dateTimeStringStart = corresponding_date + " " + utc_schedule[day][0]['start_time'] + ":00 " + day
                        local_startDateTime = convertToLocalTZ(user_timezone, dateTimeStringStart)
                        local_startTime = local_startDateTime.strftime("%H:%M")
                        local_startDay = local_startDateTime.strftime("%A")
                        print("local_startDateTime ", local_startDateTime)
                        print("local_startTime ", local_startTime)
                        print("local_startDay ", local_startDay)

                        dateTimeStringEnd = corresponding_date + " " + utc_schedule[day][0]['end_time'] + ":00 " + day
                        local_endDateTime = convertToLocalTZ(user_timezone,dateTimeStringEnd)
                        local_endTime = local_endDateTime.strftime("%H:%M")
                        local_endDay = local_endDateTime.strftime("%A")
                        print("local_endDateTime ", local_endDateTime)
                        print("local_endTime ", local_endTime)
                        print("local_endDay ", local_endDay)
                        print(" check ", local_startDateTime.date() == local_endDateTime.date())

                        if local_startDateTime.date() != local_endDateTime.date():
                            localSchedule = {'start_time' : local_startTime, 'end_time' : "23:59"}
                            scheduleArray[local_startDay].append(localSchedule)
                            localSchedule = {'start_time' : "00:00", 'end_time' : local_endTime}
                            scheduleArray[local_endDay].append(localSchedule)
                        else:
                            localSchedule = {'start_time' : local_startTime, 'end_time' : local_endTime}
                            scheduleArray[local_startDay].append(localSchedule)
                print("scheduleArray", scheduleArray)
                print("sched ", i)
                scheduleStr = json.dumps(scheduleArray)
                i.update({'schedule':scheduleStr})
                print("sched2 scheduleAPI ", i)

            sunday = []
            monday = []
            tuesday = []
            wednesday = []
            thursday = []
            friday = []
            saturday = []

            for i in items["result"]:
                schedule = json.loads(i["schedule"])
                print("user_schedule ", schedule)
                for s in schedule["Sunday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        sun = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        sunday.append(sun)
                        print("sunday", sunday)
                for s in schedule["Monday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        mon = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        monday.append(mon)
                        print("monday", monday)
                for s in schedule["Tuesday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        tues = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        tuesday.append(tues)
                        print("tuesday", tuesday)
                for s in schedule["Wednesday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        wed = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        wednesday.append(wed)
                        print("wednesday", wednesday)
                for s in schedule["Thursday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        thurs = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        thursday.append(thurs)
                        print("thursday", thursday)
                for s in schedule["Friday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        fri = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        friday.append(fri)
                        print("friday", friday)
                for s in schedule["Saturday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        sat = {
                            "id": i["view_unique_id"],
                            "name": i["view_name"],
                            "schedule": s,
                            "color": i["color"],
                        }
                        saturday.append(sat)
                        print("saturday", saturday)

                item = {
                    "sunday": sunday,
                    "monday": monday,
                    "tuesday": tuesday,
                    "wednesday": wednesday,
                    "thursday": thursday,
                    "friday": friday,
                    "saturday": saturday,
                }
                print(item)

            response["message"] = "successful"
            response["result"] = item

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)
# class GetSchedule(Resource):
#     def get(self, user_id):
#         print("In GetSchedule")
#         response = {}
#         items = {}

#         try:
#             conn = connect()

#             query = (
#                 """SELECT view_unique_id
#                             , view_name
#                             , (schedule)
#                             , color
#                         FROM skedul.views
#                         WHERE user_id = \'"""
#                 + user_id
#                 + """\';"""
#             )
#             items = execute(query, "get", conn)
#             sunday = []
#             monday = []
#             tuesday = []
#             wednesday = []
#             thursday = []
#             friday = []
#             saturday = []

#             for i in items["result"]:
#                 schedule = json.loads(i["schedule"])
#                 print("user_schedule ", schedule)
#                 for s in schedule["Sunday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         sun = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         sunday.append(sun)
#                         print("sunday", sunday)
#                 for s in schedule["Monday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         mon = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         monday.append(mon)
#                         print("monday", monday)
#                 for s in schedule["Tuesday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         tues = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         tuesday.append(tues)
#                         print("tuesday", tuesday)
#                 for s in schedule["Wednesday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         wed = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         wednesday.append(wed)
#                         print("wednesday", wednesday)
#                 for s in schedule["Thursday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         thurs = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         thursday.append(thurs)
#                         print("thursday", thursday)
#                 for s in schedule["Friday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         fri = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         friday.append(fri)
#                         print("friday", friday)
#                 for s in schedule["Saturday"]:
#                     print("s", s)
#                     if s["start_time"] != "":
#                         sat = {
#                             "id": i["view_unique_id"],
#                             "name": i["view_name"],
#                             "schedule": s,
#                             "color": i["color"],
#                         }
#                         saturday.append(sat)
#                         print("saturday", saturday)

#                 item = {
#                     "sunday": sunday,
#                     "monday": monday,
#                     "tuesday": tuesday,
#                     "wednesday": wednesday,
#                     "thursday": thursday,
#                     "friday": friday,
#                     "saturday": saturday,
#                 }
#                 print(item)

#             response["message"] = "successful"
#             response["result"] = item

#             return response, 200
#         except:
#             raise BadRequest("Request failed, please try again later.")
#         finally:
#             disconnect(conn)


class AvailableAppointments(Resource):
    def get(self, date_value, duration, start_time, end_time):
        print("\nInside Available Appointments")
        try:
            conn = connect()
            print("Inside try block", date_value, duration)
            h, m, s = duration.split(':')
            interval = math.ceil(
                ((int(h) * 3600 + int(m) * 60 + int(s))/60)/30)
            print("Inverval: ", interval, type(interval))
            # print(range(start_time,end_time))
            # CALCULATE AVAILABLE TIME SLOTS
            # query = (
            #     """
            #         -- AVAILABLE TIME SLOTS QUERY - WORKS
            #         WITH ats AS (
            #         -- CALCULATE AVAILABLE TIME SLOTS
            #         SELECT
            #             row_num,
            #             cast(begin_datetime as time) AS begin_time,
            #             cast(end_datetime as time) AS end_time
            #         FROM(
            #             -- GET TIME SLOTS
            #             SELECT ts.*,
            #                 ROW_NUMBER() OVER() AS row_num,
            #                 TIME(ts.begin_datetime) AS ts_begin,
            #                 TIME(ts.end_datetime) AS ts_end,
            #                 meet_dur.*
            #             FROM skedul.time_slots ts
            #             -- GET CURRENT APPOINTMENTS
            #             LEFT JOIN (
            #                 SELECT -- *,
            #                     meeting_unique_id,
            #                     meetDate,
            #                     meetTime AS start_time,
            #                     duration,
            #                     ADDTIME(meetTime, duration) AS end_time,
            #                     cast(concat(meetDate, ' ', meetTime) as datetime) as start,
            #                     cast(concat(meetDate, ' ', ADDTIME(meetTime, duration)) as datetime) as end
            #                 FROM skedul.meetings
            #                 LEFT JOIN skedul.event_types
            #                 ON event_id = event_unique_id
            #                 WHERE meetDate = '"""
            #     + date_value
            #     + """') AS meet_dur
            #             ON TIME(ts.begin_datetime) = meet_dur.start_time
            #                 OR (TIME(ts.begin_datetime) > meet_dur.start_time AND TIME(end_datetime) <= ADDTIME(meet_dur.end_time,"0:29"))
            #             )AS taadpa
            #          WHERE ISNULL(taadpa.meeting_unique_id) AND (taadpa.ts_begin BETWEEN '"""
            #     + start_time
            #     + """' AND '"""
            #     + end_time
            #     + """')
            #         )

            #         SELECT *
            #         FROM (
            #             SELECT -- *,
            #                 row_num,
            #                 DATE_FORMAT(begin_time, '%T') AS "begin_time",
            #                 '""" + duration + """' AS available_duration
            #             FROM (
            #                 SELECT *
            #                 FROM ats
            #                 LEFT JOIN (
            #                     SELECT
            #                         row_num as row_num_hr,
            #                         begin_time AS begin_time_hr,
            #                         end_time AS end_time_hr
            #                     FROM ats) AS ats1
            #                 ON ats.row_num + '""" + interval + """' = ats1.row_num_hr) AS atss) AS atsss
            #         WHERE '"""
            #     + duration
            #     + """' <= available_duration;
            #         """
            # )
            atimes = {'message': 'Successfully executed SQL query.',
                      'code': 280, 'result': []}
            print("atime", atimes)
            for k in range(0, interval):
                print(k)
                query = ("""
                    -- AVAILABLE TIME SLOTS QUERY - WORKS
                    WITH ats AS (
                    -- CALCULATE AVAILABLE TIME SLOTS
                    SELECT
                        row_num,
                        cast(begin_datetime as time) AS begin_time,
                        cast(end_datetime as time) AS end_time
                    FROM(
                        -- GET TIME SLOTS
                        SELECT ts.*,
                            ROW_NUMBER() OVER() AS row_num,
                            TIME(ts.begin_datetime) AS ts_begin,
                            TIME(ts.end_datetime) AS ts_end,
                            meet_dur.*
                        FROM skedul.time_slots ts
                        -- GET CURRENT APPOINTMENTS
                        LEFT JOIN (
                            SELECT -- *,
                                meeting_unique_id,
                                meetDate,
                                meetTime AS start_time,
                                duration,
                                ADDTIME(meetTime, duration) AS end_time,
                                cast(concat(meetDate, ' ', meetTime) as datetime) as start,
                                cast(concat(meetDate, ' ', ADDTIME(meetTime, duration)) as datetime) as end
                            FROM skedul.meetings
                            LEFT JOIN skedul.event_types
                            ON event_id = event_unique_id
                            WHERE meetDate = '"""
                         + date_value
                         + """') AS meet_dur
                        ON TIME(ts.begin_datetime) = meet_dur.start_time
                            OR (TIME(ts.begin_datetime) > meet_dur.start_time AND TIME(end_datetime) <= ADDTIME(meet_dur.end_time,"0:29"))
                        )AS taadpa
                     WHERE ISNULL(taadpa.meeting_unique_id) AND (taadpa.ts_begin BETWEEN '"""
                         + start_time
                         + """' AND '"""
                         + end_time
                         + """')
                    )

                    SELECT *
                    FROM (
                        SELECT  -- *,
                              row_num,
                              -- row_num_hr,
                              DATE_FORMAT(begin_time, '%T') AS "begin_time",
                              CASE
                                WHEN ISNULL(row_num_hr) THEN "0:29:59"
                                ELSE '""" + duration + """'
                              END AS available_duration
                        FROM (
                            SELECT *
                            FROM ats
                            LEFT JOIN (
                                SELECT
                                    row_num as row_num_hr,
                                    begin_time AS begin_time_hr,
                                    end_time AS end_time_hr
                                FROM ats) AS ats1
                            ON ats.row_num + """ + str(k) + """ = ats1.row_num_hr
                          ) AS atss) AS atsss
                    WHERE '""" + duration + """' <= available_duration; """)
                print('Query ', k, ": ", query)
                available_times = execute(query, "get", conn)
                atimes['result'] = atimes['result'] + \
                    (available_times['result'])

            blocked = ["row_num_hr", "begin_time", "available_duration"]

            total = []
            for i in atimes['result']:
                for key, value in i.items():
                    if key not in blocked:
                        total.append(value)

            counts = {}
            for i in total:
                if i in counts.keys():
                    counts[i] += 1
                else:
                    counts[i] = 1
            finalResult = {'message': 'Successfully executed SQL query.',
                           'code': 280, 'result': []}

            for key, value in counts.items():
                if int(value) == interval:
                    selectKey = key
                    # print(selectKey)
                    for i in atimes['result']:
                        # print(i)
                        for key, value in i.items():
                            # print(key, value)
                            if value == selectKey and key not in blocked:
                                # print('here')
                                finalResult['result'].append(i)
                                # print('finalResult', finalResult)

            # print("Available Times: ", (available_times))
            # print("Number of time slots: ", len(available_times["result"]))
            # print("Available Times: ", str(available_times['result'][0]["appt_start"]))
            seen = set()
            result = {'message': 'Successfully executed SQL query.',
                      'code': 280, 'result': []}

            for dic in finalResult['result']:
                key = (dic['row_num'], dic['begin_time'])
                if key in seen:
                    continue

                result['result'].append(dic)
                seen.add(key)

            print(result['result'])
            return result

        except:
            raise BadRequest(
                "Available Time Request failed, please try again later.")
        finally:
            disconnect(conn)


class AddMeeting(Resource):
    def post(self):
        print("In AddMeeting")
        response = {}
        items = {}
        try:
            conn = connect()
            print("Before Data")
            data = request.get_json(force=True)
            print(data)
            view_id = data["view_id"]
            user_id = data["user_id"]
            event_id = data["event_id"]
            meeting_name = data["meeting_name"]
            print(meeting_name)
            location = data["location"]
            print(location)
            attendees = data["attendees"]
            print(attendees)
            meeting_date = data["meeting_date"]
            meeting_time = data["meeting_time"]
            print(meeting_time)
            query = ["CALL skedul.get_meeting_id;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO skedul.meetings
                    SET meeting_unique_id  = \'"""
                + str(NewID)
                + """\',
                        user_id = \'"""
                + str(user_id)
                + """\',
                        view_id = \'"""
                + str(view_id)
                + """\',
                event_id = \'"""
                + str(event_id)
                + """\',
                        meeting_name = \'"""
                + str(meeting_name).replace("'", "''")
                + """\',
                        location = \'"""
                + str(location).replace("'", "''")
                + """\',
                guest_email= \'"""
                + json.dumps(attendees)
                + """\',
                        meetDate= \'"""
                + str(meeting_date)
                + """\',
                        meetTime = \'"""
                + str(meeting_time)
                + """\';
                    """
            )
            print(query)
            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "New meeting Added"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetMeeting(Resource):
    def get(self, user_id):
        print("In GetMeeting")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT -- *,

                    meeting_unique_id,
                    skedul.meetings.view_id,
                    event_id,
                    skedul.meetings.user_id,
                    meeting_name,
                    skedul.meetings.location,
                    guest_email,
                    duration,
                    meetTime AS start_time,
                    ADDTIME(meetTime, duration) AS end_time,
                    cast(concat(meetDate, ' ', meetTime) as datetime) as start,
                    cast(concat(meetDate, ' ', ADDTIME(meetTime, duration)) as datetime) as end
                    FROM skedul.meetings
                    LEFT JOIN skedul.event_types
                    ON event_id = event_unique_id
                    WHERE skedul.meetings.user_id = \'"""
                + user_id
                + """\';"""
            )
            print(query)
            items = execute(query, "get", conn)

            response["message"] = "successful"
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- SCHEDULE AN EVENT ----------------

class GetEventViewDetails(Resource):
    def get(self, view_id):
        print("In GetEventViewDetails")
        response = {}
        items = {}

        try:
            conn = connect()

            # WHERE event_unique_id = \'""" + view_id + """\'
            query = (
                """ SELECT e.*,
                        view_name, schedule, color,
                        JSON_EXTRACT(schedule, '$.Sunday') AS Sunday,
                        JSON_EXTRACT(schedule, '$.Monday') AS Monday,
                        JSON_EXTRACT(schedule, '$.Tuesday') AS Tuesday,
                        JSON_EXTRACT(schedule, '$.Wednesday') AS Wednesday,
                        JSON_EXTRACT(schedule, '$.Thursday') AS Thursday,
                        JSON_EXTRACT(schedule, '$.Friday') AS Friday,
                        JSON_EXTRACT(schedule, '$.Saturday') AS Saturday
                    FROM (
                        SELECT *, 
                            JSON_UNQUOTE(JSON_EXTRACT(buffer_time, '$.before.time')) AS before_time,
                            JSON_EXTRACT(buffer_time, '$.before.is_enabled') AS before_enabled, 
                            JSON_UNQUOTE(JSON_EXTRACT(buffer_time, '$.after.time')) AS after_time, 
                            JSON_EXTRACT(buffer_time, '$.after.is_enabled') AS after_enabled
                    FROM skedul.event_types
                    WHERE event_unique_id = \'""" + view_id + """\'
                    ) AS e
                    LEFT JOIN skedul.views AS v
                    ON e.view_id = v.view_unique_id;"""
            )
            # print(query)
            items = execute(query, "get", conn)
            # print(items)

            response["message"] = "successful"
            response["result"] = items["result"]

            return response, 200
        except:
            raise BadRequest(
                "GetEventViewDetails Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetAvailableAppointments(Resource):
    def get(self, view_id, day_selected):
        print("In GetEventViewDetails")
        print(view_id, day_selected)
        response = {}
        items = {}

        try:
            conn = connect()

            # WHERE event_unique_id = \'""" + view_id + """\'
            # meetDate = \'""" + day_selected + """\'
            query = (
                """ SELECT ats.*, meetings.Actual_Start, meetings.Actual_end, available.start_time, available.end_time
                    FROM (SELECT 
                            ROW_NUMBER() OVER() AS row_num,
                            SUBSTRING_INDEX(begin_datetime,' ',-1) AS begin_time,
                            SUBSTRING_INDEX(end_datetime,' ',-1) AS end_time
                        FROM skedul.time_slots 
                    ) AS ats
                    LEFT JOIN (SELECT *,
                                    IF (before_enabled = true,SUBTIME(str_to_date(meetTime,"%T"), before_time ),meetTime) Actual_Start, 
                                    IF (after_enabled = true,ADDTIME(str_to_date(endTime,"%T"), after_time),endTime) Actual_End
                                FROM (
                                SELECT m.*,
                                    duration, 
                                    ADDTIME(str_to_date(meetTime,"%T"), duration) AS endTime,
                                    event_name,
                                    JSON_EXTRACT(buffer_time, '$.before.time') AS before_time,
                                    JSON_EXTRACT(buffer_time, '$.before.is_enabled') AS before_enabled, 
                                    JSON_EXTRACT(buffer_time, '$.after.time') AS after_time, 
                                    JSON_EXTRACT(buffer_time, '$.after.is_enabled') AS after_enabled
                                    
                                FROM (
                                    SELECT * 
                                    FROM skedul.meetings
                                    WHERE user_id =  (SELECT DISTINCT user_id 
                                                    FROM skedul.meetings
                                                    WHERE event_id = \'""" + view_id + """\') 
                                    AND meetDate = \'""" + day_selected + """\'
                                    ) AS m
                                LEFT JOIN skedul.event_types
                                        ON event_id = event_unique_id) AS meeting_info 
                    ) AS meetings
                    ON (ats.begin_time >= meetings.Actual_Start AND ats.end_time <=meetings.Actual_End) 
                    OR (ats.begin_time <= meetings.Actual_Start AND ats.end_time > meetings.Actual_Start)
                    OR (ats.begin_time <= meetings.Actual_End AND ats.end_time > meetings.Actual_End)
                    LEFT JOIN (SELECT view_unique_id, user_id, view_name, color, day, r.*
                    FROM (SELECT *,
                            WEEKDAY(\'""" + day_selected + """\') AS day,
                                CASE WEEKDAY(\'""" + day_selected + """\')
                                    WHEN '0' THEN  JSON_EXTRACT(schedule, '$.Monday')
                                    WHEN '1' THEN  JSON_EXTRACT(schedule, '$.Tuesday')
                                    WHEN '2' THEN  JSON_EXTRACT(schedule, '$.Wednesday')
                                    WHEN '3' THEN  JSON_EXTRACT(schedule, '$.Thursday')
                                    WHEN '4' THEN  JSON_EXTRACT(schedule, '$.Friday')
                                    WHEN '5' THEN  JSON_EXTRACT(schedule, '$.Saturday')
                                    WHEN '6' THEN JSON_EXTRACT(schedule, '$.Sunday')
                                END AS dday
                        FROM skedul.views
                        WHERE view_unique_id =  (SELECT DISTINCT view_id 
                                            FROM skedul.meetings
                                            WHERE event_id = \'""" + view_id + """\')
                        GROUP BY user_id) AS t,
                        JSON_TABLE(t.dday, '$[*]'
                        COLUMNS (
                                    a FOR ORDINALITY,
                                    start_time VARCHAR(40)  PATH '$.start_time',
                                    end_time VARCHAR(40)  PATH '$.end_time')
                        ) AS r 
                    ) AS available
                    ON (ats.begin_time >= available.start_time AND ats.end_time <=available.end_time) 
                    OR (ats.begin_time <= available.start_time AND ats.end_time > available.start_time)
                    OR (ats.begin_time <= available.end_time AND ats.end_time > available.end_time)
                    WHERE ISNULL(meetings.Actual_Start) AND available.start_time IS NOT NULL;"""
            )
            # print(query)
            items = execute(query, "get", conn)
            # print(items)

            response["message"] = "successful"
            response["result"] = items["result"]

            return response, 200
        except:
            raise BadRequest(
                "GetAvailableAppointments Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetWeekAvailableAppointments(Resource):
    def get(self, view_id):
        print("In GetWeekAvailableAppointments", view_id)
        response = {}
        items = {}

        try:
            conn = connect()

            # WHERE event_unique_id = \'""" + view_id + """\'
            query = ("""
                    SELECT event_unique_id, view_id, user_id, event_name, location, duration, before_time, before_enabled, after_time, after_enabled, view_name, color,
                        JSON_OBJECTAGG(CONCAT(meeting_day, " ", next_date), availtime) AS schedule
                    FROM (

                    SELECT event_unique_id, view_id, user_id, event_name, location, duration, before_time, before_enabled, after_time, after_enabled, view_name, color, -- rn, Weekday, available_times, a, start_hhmm, finish_hhmm, start_time, finish_time, row_num, meeting_day, day_index, begin_time, end_time, Actual_Start, Actual_End, availability
                            meeting_day, next_date, if(avail2.start_time = 'Not Available','[]',JSON_ARRAYAGG(availability)) AS availtime
                    FROM (
                    SELECT available.*, ats.*, -- available.start_time, available.finish_time,
                        meetings.Actual_Start, meetings.Actual_end,
                            json_object(
                            'start_time',begin_time
                            ,'end_time',end_time) AS availability
                    FROM (
                        SELECT 
                            ROW_NUMBER() OVER() AS row_num, meeting_day, day_index,
                            DATE_FORMAT(CURDATE() + IF(day_index > WEEKDAY(CURDATE()), day_index - WEEKDAY(CURDATE()) , day_index + 7 - WEEKDAY(CURDATE())), '%Y-%m-%d') AS next_date,
                            SUBSTRING_INDEX(begin_datetime,' ',-1) AS begin_time,
                            SUBSTRING_INDEX(end_datetime,' ',-1) AS end_time
                        FROM skedul.wk_time_slots
                        ) as ats
                    -- LEFT JOIN WITH AVAILABLE TIMES
                    LEFT JOIN (
                        SELECT *, IF(ISNULL(start_hhmm),"Not Available",CONCAT(start_hhmm,":00")) AS start_time, IF(ISNULL(finish_hhmm),"Not Available",CONCAT(finish_hhmm,":00")) AS finish_time
                        FROM skedul.new_view3,
                        JSON_TABLE(new_view3.available_times, 
                            '$'  -- THIS RETURNS THE BLANK ROWS
                            COLUMNS (
                                a FOR ORDINALITY,
                                NESTED PATH '$[*]'
                                COLUMNS (
                                start_hhmm VARCHAR(40)  PATH '$.start_time',
                                finish_hhmm VARCHAR(40)  PATH '$.end_time')
                                )
                            ) AS r
                        WHERE event_unique_id = \'""" + view_id + """\'
                    ) AS available
                    ON IF(available.start_time = 'Not Available', ats.meeting_day = available.Weekday, ats.meeting_day = available.Weekday AND (
                        (CAST(ats.begin_time AS TIME) >= CAST(available.start_time AS TIME) AND CAST(ats.end_time AS TIME) <= CAST(available.finish_time AS TIME)) OR
                        (CAST(ats.begin_time AS TIME) <= CAST(available.start_time AS TIME) AND CAST(ats.end_time AS TIME) > CAST(available.start_time AS TIME)) OR
                        (CAST(ats.begin_time AS TIME) < CAST(available.finish_time AS TIME) AND CAST(ats.end_time AS TIME) >= CAST(available.finish_time AS TIME))))
                    -- LEFT JOIN WITH EXISTING MEETINGS
                    LEFT JOIN (SELECT *,
                        IF (before_enabled = true,SUBTIME(meetTime, before_time),meetTime) Actual_Start,
                        IF (after_enabled = true,ADDTIME(endTime, after_time),endTime) Actual_End
                    FROM (
                        SELECT m.*,
                            duration, 
                            ADDTIME(meetTime, duration) AS endTime,
                            event_name,
                            JSON_EXTRACT(buffer_time, '$.before.time') AS before_time,
                            JSON_EXTRACT(buffer_time, '$.before.is_enabled') AS before_enabled, 
                            JSON_EXTRACT(buffer_time, '$.after.time') AS after_time, 
                            JSON_EXTRACT(buffer_time, '$.after.is_enabled') AS after_enabled
                        FROM (
                            SELECT * 
                            FROM skedul.meetings
                            WHERE user_id =  (SELECT DISTINCT user_id 
                                            FROM skedul.meetings
                                            WHERE event_id = \'""" + view_id + """\') 
                            AND meetDate >= CURDATE() AND meetDate < ADDDATE(CURDATE(),7)
                            ) AS m
                        LEFT JOIN skedul.event_types
                                ON event_id = event_unique_id
                        ) AS meeting_info
                    ) AS meetings
                    ON ats.day_index = WEEKDAY(meetings.meetDate) AND ( 
                        (ats.begin_time >= meetings.Actual_Start AND ats.end_time <=meetings.Actual_End) OR
                        (ats.begin_time <= meetings.Actual_Start AND ats.end_time > meetings.Actual_Start) OR
                        (ats.begin_time <= meetings.Actual_End AND ats.end_time > meetings.Actual_End) )

                    WHERE ISNULL(meetings.Actual_Start) AND available.start_time IS NOT NULL) as avail2
                    GROUP BY meeting_day) AS avail3;
                    """)

            # print(query)
            items = execute(query, "get", conn)
            # print(items)

            response["message"] = "successful"
            response["result"] = items["result"]

            return response, 200
        except:
            raise BadRequest("GetAvailableAppointments Request failed.")
        finally:
            disconnect(conn)


# -- DEFINE APIS -------------------------------------------------------------------------------
api.add_resource(
    GoogleCalenderEvents,
    "/api/v2/calenderEvents/<string:user_unique_id>,<string:start>,<string:end>",
)
# Define API routes
# account endpoints
api.add_resource(UserSignUp, "/api/v2/UserSignUp")
api.add_resource(UserSocialSignUp, "/api/v2/UserSocialSignUp")
api.add_resource(UpdateAccessToken,
                 "/api/v2/UpdateAccessToken/<string:user_unique_id>")
api.add_resource(UserToken, "/api/v2/UserToken/<string:user_email_id>")
api.add_resource(UserDetails, "/api/v2/UserDetails/<string:user_id>")

api.add_resource(Login, "/api/v2/Login")
api.add_resource(
    AccessRefresh, "/api/v2/AccessRefresh/<string:user_unique_id>")
api.add_resource(
    UserLogin, "/api/v2/UserLogin/<string:email_id>,<string:password>")
api.add_resource(UserSocialLogin, "/api/v2/UserSocialLogin/<string:email_id>")
api.add_resource(GetEmailId, "/api/v2/GetEmailId/<string:email_id>")

# view endpoints
api.add_resource(AddView, "/api/v2/AddView")
api.add_resource(UpdateView, "/api/v2/UpdateView/<string:view_id>")
api.add_resource(DeleteView, "/api/v2/DeleteView")
api.add_resource(GetAllViews, "/api/v2/GetAllViews/<string:user_id>")
api.add_resource(GetView, "/api/v2/GetView/<string:view_id>")

# events endpoints
api.add_resource(AddEvent, "/api/v2/AddEvent")
api.add_resource(UpdateEvent, "/api/v2/UpdateEvent/<string:event_id>")
api.add_resource(DeleteEvent, "/api/v2/DeleteEvent")

api.add_resource(GetAllEvents, "/api/v2/GetAllEvents/<string:view_id>")
api.add_resource(GetAllEventsUser, "/api/v2/GetAllEventsUser/<string:user_id>")
api.add_resource(GetEvent, "/api/v2/GetEvent/<string:event_id>")
api.add_resource(SendEmail, "/api/v2/sendEmail/<string:email>")
# schedule endpoints
api.add_resource(GetSchedule, "/api/v2/GetSchedule/<string:user_id>")
api.add_resource(AvailableAppointments,
                 "/api/v2/AvailableAppointments/<string:date_value>/<string:duration>/<string:start_time>,<string:end_time>")
api.add_resource(AddMeeting, "/api/v2/AddMeeting")
api.add_resource(GetMeeting, "/api/v2/GetMeeting/<string:user_id>")
# schedule meeting endpoints
api.add_resource(GetEventViewDetails,
                 "/api/v2/GetEventViewDetails/<string:view_id>")
api.add_resource(GetAvailableAppointments,
                 "/api/v2/GetAvailableAppointments/<string:view_id>/<string:day_selected>")
api.add_resource(GetWeekAvailableAppointments,
                 "/api/v2/GetWeekAvailableAppointments/<string:view_id>")
# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
