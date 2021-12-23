# To run program:  python3 skedul_api.py
# https://pi4chbdo50.execute-api.us-west-1.amazonaws.com/dev
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

from collections import OrderedDict

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
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
import string
import random

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

SCOPES = "https://www.googleapis.com/auth/calendar"
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "skedul"
# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")


# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead
import stripe


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
# Mail username and password loaded in zappa_settings.json file
app.config["MAIL_USERNAME"] = os.environ.get("SUPPORT_EMAIL")
app.config["MAIL_PASSWORD"] = os.environ.get("SUPPORT_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("SUPPORT_EMAIL")

# Use locally defined Username and Password to test via localhost and Postman
# app.config['MAIL_USERNAME'] = 'support@skedulayurveda.com'
# app.config['MAIL_PASSWORD'] = '<enter password here>'
# app.config['MAIL_DEFAULT_SENDER'] = 'support@skedulayurveda.com'

# Setting for mydomain.com
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465

# Setting for gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465


app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True


# Set this to false when deploying to live application
app.config["DEBUG"] = True
# app.config["DEBUG"] = False

app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc

# # These statment return Day and Time in GMT
# def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
# def getNow(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")

# # These statment return Day and Time in Local Time - Not sure about PST vs PDT
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
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd in "post":
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


class UserToken(Resource):
    def get(self, user_unique_id=None):
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
                        customers WHERE user_unique_id = \'"""
                + user_unique_id
                + """\';"""
            )

            items = execute(query, "get", conn)
            print(items)
            response["message"] = "successful"
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


class UpdateAccessToken(Resource):
    def post(self, user_unique_id=None):
        print("In usertoken")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
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
                bearerString = "Bearer " + items["result"][0]["google_auth_token"]
                headers = {"Authorization": bearerString, "Accept": "application/json"}
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                calendars = response.json().get("items")
                return calendars

            else:
                print("in else")
                access_issue_min = int(items["result"][0]["access_expires_in"]) / 60
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
                bearerString = "Bearer " + items["result"][0]["google_auth_token"]
                print(bearerString)
                headers = {"Authorization": bearerString, "Accept": "application/json"}
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
            user_id = data["user_id"]
            event_name = data["event_name"]
            location = data["location"]
            duration = data["duration"]
            buffer_time = data["buffer_time"]
            print(buffer_time)
            # buffer_time = json.loads(buffer_time)
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
                        WHERE event_unique_id = \'"""
                + event_id
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
                        WHERE view_unique_id = \'"""
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


class GetSchedule(Resource):
    def get(self, user_id):
        print("In GetSchedule")
        response = {}
        items = {}

        try:
            conn = connect()

            query = (
                """SELECT view_unique_id
                            , (schedule)
                            , color
                        FROM skedul.views
                        WHERE user_id = \'"""
                + user_id
                + """\';"""
            )
            items = execute(query, "get", conn)
            sunday = []
            monday = []
            tuesday = []
            wednesday = []
            thursday = []
            friday = []
            saturday = []

            for i in items["result"]:
                schedule = json.loads(i["schedule"])
                for s in schedule["Sunday"]:
                    print("s", s)
                    if s["start_time"] != "":
                        sun = {
                            "id": i["view_unique_id"],
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


# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes

api.add_resource(
    GoogleCalenderEvents,
    "/api/v2/calenderEvents/<string:user_unique_id>,<string:start>,<string:end>",
)
api.add_resource(UpdateAccessToken, "/api/v2/UpdateAccessToken/<string:user_unique_id>")
api.add_resource(UserToken, "/api/v2/customerToken/<string:user_unique_id>")


api.add_resource(AddView, "/api/v2/AddView")
api.add_resource(AddEvent, "/api/v2/AddEvent")

api.add_resource(UpdateEvent, "/api/v2/UpdateEvent/<string:event_id>")
api.add_resource(UpdateView, "/api/v2/UpdateView/<string:view_id>")

api.add_resource(GetAllEvents, "/api/v2/GetAllEvents/<string:view_id>")
api.add_resource(GetAllEventsUser, "/api/v2/GetAllEventsUser/<string:user_id>")
api.add_resource(GetEvent, "/api/v2/GetEvent/<string:event_id>")

api.add_resource(GetAllViews, "/api/v2/GetAllViews/<string:user_id>")
api.add_resource(GetView, "/api/v2/GetView/<string:view_id>")
api.add_resource(GetSchedule, "/api/v2/GetSchedule/<string:user_id>")
# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
