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

# QUERY 1:  FINDS ALL CUSTOMERS APPOINTMENTS
class appointments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """  
                SELECT * FROM skedul.customers, skedul.treatments, skedul.appointments
                WHERE user_unique_id = appt_user_unique_id
	                AND treatment_uid = appt_treatment_uid;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT THAT WORKS
        # http://localhost:4000/api/v2/appointments


class OneCustomerAppointments(Resource):
    def get(self, user_unique_id):
        response = {}
        items = {}
        print("appointment_uid", user_unique_id)
        try:
            conn = connect()
            # QUERY 1B:  FINDS SPECIFIC CUSTOMERS APPOINTMENTS
            query = (
                """
                SELECT * FROM skedul.customers, skedul.treatments, skedul.appointments
		        WHERE user_unique_id = appt_user_unique_id
			        AND treatment_uid = appt_treatment_uid
                    AND user_unique_id = \'"""
                + user_unique_id
                + """\';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Appointment successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest(
                "Customer Appointments Request failed, please try again later."
            )
        finally:
            disconnect(conn)


# QUERY 2:  GETS ALL TREATMENTS
class treatments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 2
            query = """  
                SELECT * FROM  skedul.treatments
                WHERE availability = "Available"
                ORDER BY category, display_order; 
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)

        # http://localhost:4000/api/v2/treatments


class AddBlog(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            blogCategory = data["blogCategory"]
            # print(blogCategory)
            blogTitle = data["blogTitle"]
            # print(blogTitle)
            slug = data["slug"]
            # print(slug)
            postedOn = data["postedOn"]
            # print(postedOn)
            author = data["author"]
            # print(author)
            blogImage = data["blogImage"]
            print(blogImage)
            blogSummary = data["blogSummary"]
            # print(blogSummary)
            blogText = data["blogText"]
            # print(blogText)
            print("Data Received")

            query = ["CALL skedul.new_blog_uid;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO skedul.blog
                    SET blog_uid  = \'"""
                + NewID
                + """\',
                        blogCategory = \'"""
                + blogCategory
                + """\',
                        blogTitle = \'"""
                + blogTitle
                + """\',
                        blogStatus = 'ACTIVE',
                        slug = \'"""
                + slug
                + """\',
                        postedOn = \'"""
                + postedOn
                + """\',
                        author = \'"""
                + author
                + """\',
                        blogImage = \'"""
                + blogImage
                + """\',
                        blogSummary = \'"""
                + blogSummary
                + """\',
                        blogText = \'"""
                + blogText
                + """\';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Blog Post successful"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UploadImage(Resource):
    def post(self):
        try:
            print("in Upload Image")
            item_photo = request.files.get("item_photo")
            print(item_photo)
            uid = request.form.get("filename")
            print(uid)
            bucket = "skedul-images"
            TimeStamp_test = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            print(TimeStamp_test)
            key = "blogs/" + str(uid) + "_" + TimeStamp_test
            print(key)

            filename = (
                "https://s3-us-west-1.amazonaws.com/" + str(bucket) + "/" + str(key)
            )

            upload_file = s3.put_object(
                Bucket=bucket,
                Body=item_photo,
                Key=key,
                ACL="public-read",
                ContentType="image/jpeg",
            )
            return filename

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            print("image uploaded!")


class FullBlog(Resource):
    def get(self, blog_id):
        response = {}
        items = {}
        try:
            conn = connect()
            # QUERY 4
            query = (
                """
                    SELECT * FROM skedul.blog
                    WHERE blog_uid = \'"""
                + blog_id
                + """\'
                    AND blogStatus != 'DELETED';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Full Blog Request failed, please try again later.")
        finally:
            disconnect(conn)


class TruncatedBlog(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            # QUERY 5
            query = """
                    SELECT blog_uid, blogCategory, blogTitle, slug, postedOn, author, blogImage, blogSummary, LEFT(blogText, 1200) AS blogText 
                    FROM skedul.blog
                    WHERE blogStatus != 'DELETED'
                    ORDER BY postedOn DESC;
                    """
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Specific Blog Request failed, please try again later.")
        finally:
            disconnect(conn)


class DeleteBlog(Resource):
    def post(self, blog_id):
        print("\nInside Delete")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block")
            print("Received:", blog_id)

            query = (
                """
                    UPDATE skedul.blog
                    SET blogStatus = 'DELETED'
                    WHERE blog_uid = \'"""
                + blog_id
                + """\';
                    """
            )

            products = execute(query, "post", conn)
            print("Back in class")
            print(products)
            return products["code"]

        except:
            raise BadRequest("Delete Request failed, please try again later.")
        finally:
            disconnect(conn)


class CreateAppointment(Resource):
    def post(self):
        response = {}
        items = {}
        cus_id = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print("Received:", data)

            #  GET CUSTOMER APPOINTMENT INFO
            first_name = data["first_name"]
            last_name = data["last_name"]
            email = data["email"]
            phone_no = data["phone_no"]
            treatment_uid = data["appt_treatment_uid"]
            notes = data["notes"]
            datevalue = data["appt_date"]
            timevalue = data["appt_time"]
            purchase_price = data["purchase_price"]
            purchase_date = data["purchase_date"]

            #  PRINT CUSTOMER APPOINTMENT INFO
            print("first_name", first_name)
            print("last_name", last_name)
            print("email", email)
            print("phone_no", phone_no)
            print("treatment_uid", treatment_uid)
            print("notes", notes)
            print("date", datevalue)
            print("time", timevalue)
            print("purchase_price", purchase_price)
            print("purchase_date", purchase_date)

            #  CREATE CUSTOMER APPOINTMENT UID
            # Query [0]  Get New UID
            # query = ["CALL new_refund_uid;"]
            query = ["CALL skedul.new_appointment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)
            # NewID is an Array and new_id is the first element in that array

            #  FIND EXISTING CUSTOMER UID
            query1 = (
                """ 
                    SELECT user_unique_id FROM skedul.customers 
                    WHERE user_email_id = \'"""
                + email
                + """\' 
                    AND   customer_phone_num = \'"""
                + phone_no
                + """\';
                """
            )
            cus_id = execute(query1, "get", conn)
            print(cus_id["result"])
            for obj in cus_id["result"]:
                NewcustomerID = obj["user_unique_id"]
                print(NewcustomerID)

            print(len(cus_id["result"]))

            #  FOR NEW CUSTOMERS - CREATE NEW CUSTOMER UID AND INSERT INTO CUSTOMER TABLE
            if len(cus_id["result"]) == 0:
                query = ["CALL skedul.new_user_unique_id;"]
                NewIDresponse = execute(query[0], "get", conn)
                NewcustomerID = NewIDresponse["result"][0]["new_id"]

                customer_insert_query = (
                    """
                    INSERT INTO skedul.customers
                    SET user_unique_id = \'"""
                    + NewcustomerID
                    + """\',
                        customer_first_name = \'"""
                    + first_name
                    + """\',
                        customer_last_name = \'"""
                    + last_name
                    + """\',
                        customer_phone_num = \'"""
                    + phone_no
                    + """\',
                        user_email_id = \'"""
                    + email
                    + """\'
                    """
                )

                customer_items = execute(customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)

            #  FOR EXISTING CUSTOMERS - USE EXISTING CUSTOMER UID
            else:
                for obj in cus_id["result"]:
                    NewcustomerID = obj["user_unique_id"]
                    print("customerID = ", NewcustomerID)

            #  convert to new format:  payment_time_stamp = \'''' + getNow() + '''\',

            #  INSERT INTO APPOINTMENTS TABLE
            query2 = (
                """
                    INSERT INTO skedul.appointments
                    SET appointment_uid = \'"""
                + NewID
                + """\',
                        appt_user_unique_id = \'"""
                + NewcustomerID
                + """\',
                        appt_treatment_uid = \'"""
                + treatment_uid
                + """\',
                        notes = \'"""
                + str(notes)
                + """\',
                        appt_date = \'"""
                + datevalue
                + """\',
                        appt_time = \'"""
                + timevalue
                + """\',
                        purchase_price = \'"""
                + purchase_price
                + """\',
                        purchase_date = \'"""
                + purchase_date
                + """\'
                    """
            )
            items = execute(query2, "post", conn)

            # Send receipt emails
            name = first_name + " " + last_name
            message = treatment_uid + " " + purchase_price + " " + purchase_date
            print(name)
            SendEmail.get(self, name, email, phone_no, message)

            response["message"] = "Appointments Post successful"
            response["result"] = items
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointment


class AddTreatment(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            availability = data["availability"]
            duration = data["duration"]
            image_url = data["image_url"]

            query = ["CALL skedul.new_treatment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO skedul.treatments
                    SET treatment_uid = \'"""
                + NewID
                + """\',
                        title = \'"""
                + title
                + """\',
                        category = \'"""
                + category
                + """\',
                        description = \'"""
                + description
                + """\',
                        cost = \'"""
                + cost
                + """\',
                        availability = \'"""
                + availability
                + """\',
                        duration = \'"""
                + duration
                + """\',
                        image_url = \'"""
                + image_url
                + """\';
                    """
            )

            items = execute(query, "post", conn)

            response["message"] = "Treatments Post successful"
            response["result"] = items
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class AddContact(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            name = data["name"]
            email = data["email"]
            subject = data["subject"]
            message = data["message"]
            print(data)
            print(message)

            new_contact_uid = get_new_contactUID(conn)
            print(new_contact_uid)
            print(getNow())

            query = (
                """
                INSERT INTO skedul.contact
                SET contact_uid = \'"""
                + new_contact_uid
                + """\',
                    contact_created_at = \'"""
                + getNow()
                + """\',
                    name = \'"""
                + name
                + """\',
                    email = \'"""
                + email
                + """\',
                    subject = \'"""
                + subject
                + """\',
                    message = \'"""
                + message
                + """\'
                """
            )

            items = execute(query, "post", conn)
            print("items: ", items)

            # Send receipt emails
            phone = message
            SendEmail.get(self, name, email, phone, subject)

            if items["code"] == 281:
                response["message"] = "Contact Post successful"
                return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class AvailableAppointments(Resource):
    def get(self, date_value, duration):
        print("\nInside Available Appointments")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", date_value, duration)

            # CALCULATE AVAILABLE TIME SLOTS
            query = (
                """
                    -- AVAILABLE TIME SLOTS QUERY - WORKS
                    WITH ats AS (
                    -- CALCULATE AVAILABLE TIME SLOTS
                    SELECT -- *,
                        -- ROW_NUMBER() OVER() AS row_num,
                        row_num,
                        cast(begin_datetime as time) AS begin_time,
                        cast(end_datetime as time) AS end_time
                        -- *,
                        -- TIMEDIFF(stop_time,begin_time),
                        -- IF (ISNULL(taadpa.appointment_uid) AND ISNULL(taadpa.prac_avail_uid) AND !ISNULL(days_uid), "Available", "Not Available") AS AVAILABLE
                    FROM(
                        -- GET TIME SLOTS
                        SELECT ts.*,
                            ROW_NUMBER() OVER() AS row_num,
                            TIME(ts.begin_datetime) AS ts_begin,
                            TIME(ts.end_datetime) AS ts_end,
                            appt_dur.*,
                            pa.*,
                            openhrs.*
                        FROM skedul.time_slots ts
                        -- GET CURRENT APPOINTMENTS
                        LEFT JOIN (
                            SELECT -- *,
                                appointment_uid,
                                appt_date,
                                appt_time AS start_time,
                                duration,
                                ADDTIME(appt_time, duration) AS end_time,
                                cast(concat(appt_date, ' ', appt_time) as datetime) as start,
                                cast(concat(appt_date, ' ', ADDTIME(appt_time, duration)) as datetime) as end
                            FROM skedul.appointments
                            LEFT JOIN skedul.treatments
                            ON appt_treatment_uid = treatment_uid    
                            WHERE appt_date = '"""
                + date_value
                + """') AS appt_dur
                        ON TIME(ts.begin_datetime) = appt_dur.start_time
                            OR (TIME(ts.begin_datetime) > appt_dur.start_time AND TIME(end_datetime) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM skedul.practioner_availability
                            WHERE date = '"""
                + date_value
                + """') AS pa
                        ON TIME(ts.begin_datetime) = pa.start_time_notavailable
                            OR (TIME(ts.begin_datetime) > pa.start_time_notavailable AND TIME(ts.end_datetime) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                            FROM skedul.days
                            WHERE dayofweek = DAYOFWEEK('"""
                + date_value
                + """')) AS openhrs
                        ON TIME(ts.begin_datetime) = openhrs.morning_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.morning_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_datetime) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.afternoon_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.afternoon_end_time,"0:29")) 
                        )AS taadpa
                    WHERE ISNULL(taadpa.appointment_uid) 
                        AND ISNULL(taadpa.prac_avail_uid)
                        AND !ISNULL(days_uid)
                    )

                    SELECT *
                    FROM (
                        SELECT -- *,
                            row_num,
                            DATE_FORMAT(begin_time, '%T') AS "begin_time",
                            CASE
                                WHEN ISNULL(row_num_hr) THEN "0:29:59"
                                WHEN ISNULL(row_num_hrhalf) THEN "0:59:59"
                                WHEN ISNULL(row_num_twohr) THEN "1:29:59"
                                ELSE "1:59:59"
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
                            ON ats.row_num + 1 = ats1.row_num_hr
                            LEFT JOIN (
                                SELECT 	
                                    row_num as row_num_hrhalf,
                                    begin_time AS begin_time_hrhalf,
                                    end_time AS end_time_hrhalf
                                FROM ats) AS ats2
                            ON ats.row_num + 2 = ats2.row_num_hrhalf
                            LEFT JOIN (
                                SELECT 	
                                    row_num as row_num_twohr,
                                    begin_time AS begin_time_twohr,
                                    end_time AS end_time_twohr
                                FROM ats) AS ats3
                            ON ats.row_num + 3 = ats3.row_num_twohr) AS atss) AS atsss
                    WHERE '"""
                + duration
                + """' <= available_duration;
                    """
            )

            available_times = execute(query, "get", conn)
            print("Available Times: ", str(available_times["result"]))
            print("Number of time slots: ", len(available_times["result"]))
            # print("Available Times: ", str(available_times['result'][0]["appt_start"]))

            return available_times

        except:
            raise BadRequest("Available Time Request failed, please try again later.")
        finally:
            disconnect(conn)


class Calendar(Resource):
    def get(self, date_value):
        print("\nInside Calendar Availability")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", id)

            # CALCULATE AVAILABLE TIME SLOTS
            query = (
                """
                    SELECT 
                        TIME_FORMAT(ts_begin, '%T') AS appt_start,
                        TIME_FORMAT(ts_end, '%T') AS appt_end
                        -- *,
                        -- TIMEDIFF(stop_time,begin_time),
                        -- IF (ISNULL(taadpa.appointment_uid) AND ISNULL(taadpa.prac_avail_uid) AND !ISNULL(days_uid), "Available", "Not Available") AS AVAILABLE
                    FROM(
                        -- GET TIME SLOTS
                        SELECT ts.*,
                            TIME(ts.begin_time) AS ts_begin,
                            TIME(ts.stop_time) AS ts_end,
                            appt_dur.*,
                            pa.*,
                            openhrs.*
                        FROM skedul.time_slots ts
                        -- GET CURRENT APPOINTMENTS
                        LEFT JOIN (
                            SELECT -- *,
                                appointment_uid,
                                appt_date,
                                appt_time AS start_time,
                                duration,
                                ADDTIME(appt_time, duration) AS end_time,
                                cast(concat(appt_date, ' ', appt_time) as datetime) as start,
                                cast(concat(appt_date, ' ', ADDTIME(appt_time, duration)) as datetime) as end
                            FROM skedul.appointments
                            LEFT JOIN skedul.treatments
                            ON appt_treatment_uid = treatment_uid    
                            WHERE appt_date = '"""
                + date_value
                + """') AS appt_dur
                        ON TIME(ts.begin_time) = appt_dur.start_time
                            OR (TIME(ts.begin_time) > appt_dur.start_time AND TIME(ts.stop_time) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM skedul.practioner_availability
                            WHERE date = '"""
                + date_value
                + """') AS pa
                        ON TIME(ts.begin_time) = pa.start_time_notavailable
                            OR (TIME(ts.begin_time) > pa.start_time_notavailable AND TIME(ts.stop_time) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                                -- ADDTIME(morning_start_time, "0:29"),
                                -- if(morning_start_time = "9:00:00","Y","N")
                            FROM skedul.days
                            WHERE dayofweek = DAYOFWEEK('"""
                + date_value
                + """')) AS openhrs
                        ON TIME(ts.begin_time) = openhrs.morning_start_time
                            OR (TIME(ts.begin_time) > openhrs.morning_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_time) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_time) > openhrs.afternoon_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.afternoon_end_time,"0:29")) 
                        )AS taadpa
                    WHERE ISNULL(taadpa.appointment_uid) 
                        AND ISNULL(taadpa.prac_avail_uid)
                        AND !ISNULL(days_uid)
                    """
            )

            available_times = execute(query, "get", conn)
            print("Available Times: ", str(available_times["result"]))
            print("Number of time slots: ", len(available_times["result"]))
            print("Available Times: ", str(available_times["result"][0]["appt_start"]))

            return available_times["result"]

        except:
            raise BadRequest("Available Time Request failed, please try again later.")
        finally:
            disconnect(conn)


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


# SEND EMAIL
class SendEmail(Resource):
    def __call__(self):
        print("In SendEmail")

    def get(self, name, email, phone, subject):
        print("In Send EMail get")
        try:
            conn = connect()

            # Send email to Client
            msg = Message(
                "Thanks for your Email!",
                sender="support@skedulayurveda.com",
                recipients=[email],
            )
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            msg.body = (
                "Hi !\n\n"
                "We are looking forward to meeting with you! \n"
                "Email Leena@skedulayurveda.com if you need to get in touch with us directly.\n"
                "Thx - skedul Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            mail.send(msg)

            # print("first email sent")
            # Send email to Host
            msg = Message(
                "New Email from Website!",
                sender="support@skedulayurveda.com",
                recipients=["Lmarathay@yahoo.com"],
            )
            msg.body = (
                "Hi !\n\n"
                "You just got an email from your website! \n"
                "Here are the particulars:\n"
                "Name:      " + name + "\n"
                "Email:     " + email + "\n"
                "Phone:     " + phone + "\n"
                "Subject:   " + subject + "\n"
            )
            "Thx - skedul Ayurveda\n\n"
            # print('msg-bd----', msg.body)
            mail.send(msg)

            return "Email Sent", 200

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

    def post(self):

        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]

            # msg = Message("Thanks for your Email!", sender='pmarathay@manifestmy.space', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='info@infiniteoptions.com', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='leena@skedulayurveda.com', recipients=[email])
            # msg = Message("Thanks for your Email!", sender='pmarathay@buildsuccess.org', recipients=[email])
            msg = Message(
                "Thanks for your Email!",
                sender="support@skedulayurveda.com",
                recipients=[email],
            )
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            msg.body = (
                "Hi !\n\n"
                "We are looking forward to meeting with you! \n"
                "Email support@skedulayurveda.com if you need to get in touch with us directly.\n"
                "Thx - skedul Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            # print('msg-')
            mail.send(msg)

            # Send email to Host
            # msg = Message("Email Verification", sender='support@mealsfor.me', recipients=[email])

            # print('MESSAGE----', msg)
            # print('message complete')
            # # print("1")
            # link = url_for('confirm', token=token, hashed=password, _external=True)
            # # print("2")
            # print('link---', link)
            # msg.body = "Click on the link {} to verify your email address.".format(link)
            # print('msg-bd----', msg.body)
            # mail.send(msg)
            return "Email Sent", 200

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# ACCOUNT QUERIES
class findCustomerUID(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            phone = data["phone_num"]
            email = data["email"]
            query = (
                """
                    # QUERY 5
                    # GET CUSTOMER UID FROM PHONE NUMBER OR EMAIL
                    SELECT user_unique_id,
                        customer_phone_num,
                        user_email_id
                    FROM skedul.customers 
                    WHERE customer_phone_num = \'"""
                + phone
                + """\'
                        OR user_email_id = \'"""
                + email
                + """\';
                """
            )
            items = execute(query, "get", conn)
            print(items)
            if not items["result"]:
                items["message"] = "Email and Phone Number do not exist"
                items["code"] = 404
                return items
            items["message"] = "Customer Found"
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class createAccount(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            firstName = data["first_name"]
            lastName = data["last_name"]
            phone = data["phone_number"]
            address = data["address"]
            unit = data["unit"] if data.get("unit") is not None else "NULL"
            social_id = (
                data["social_id"] if data.get("social_id") is not None else "NULL"
            )
            city = data["city"]
            state = data["state"]
            zip_code = data["zip_code"]
            latitude = data["latitude"]
            longitude = data["longitude"]
            referral = data["referral_source"]
            role = data["role"]
            cust_id = data["cust_id"] if data.get("cust_id") is not None else "NULL"

            if (
                data.get("social") is None
                or data.get("social") == "FALSE"
                or data.get("social") == False
                or data.get("social") == "NULL"
            ):
                social_signup = False
            else:
                social_signup = True

            print(social_signup)
            get_user_id_query = "CALL new_user_unique_id();"
            NewUserIDresponse = execute(get_user_id_query, "get", conn)

            print("New User Code: ", NewUserIDresponse["code"])

            if NewUserIDresponse["code"] == 490:
                string = " Cannot get new User id. "
                print("*" * (len(string) + 10))
                print(string.center(len(string) + 10, "*"))
                print("*" * (len(string) + 10))
                response["message"] = "Internal Server Error."
                return response, 500
            NewUserID = NewUserIDresponse["result"][0]["new_id"]
            print("New User ID: ", NewUserID)

            if social_signup == False:

                salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

                password = sha512((data["password"] + salt).encode()).hexdigest()
                print("password------", password)
                algorithm = "SHA512"
                mobile_access_token = "NULL"
                mobile_refresh_token = "NULL"
                google_auth_token = "NULL"
                google_refresh_token = "NULL"
                user_social_signup = "NULL"
            else:

                mobile_access_token = data["mobile_access_token"]
                mobile_refresh_token = data["mobile_refresh_token"]
                google_auth_token = data["google_auth_token"]
                google_refresh_token = data["google_refresh_token"]
                salt = "NULL"
                password = "NULL"
                algorithm = "NULL"
                user_social_signup = data["social"]

                print("ELSE- OUT")

            if cust_id != "NULL" and cust_id:

                NewUserID = cust_id

                query = (
                    """
                        SELECT google_auth_token, google_refresh_token, mobile_access_token, mobile_refresh_token 
                        FROM skedul.customers
                        WHERE user_unique_id = \'"""
                    + cust_id
                    + """\';
                    """
                )
                it = execute(query, "get", conn)
                print("it-------", it)

                if it["result"][0]["google_auth_token"] != "FALSE":
                    google_auth_token = it["result"][0]["google_auth_token"]

                if it["result"][0]["google_refresh_token"] != "FALSE":
                    google_refresh_token = it["result"][0]["google_refresh_token"]

                if it["result"][0]["mobile_access_token"] != "FALSE":
                    mobile_access_token = it["result"][0]["mobile_access_token"]

                if it["result"][0]["mobile_refresh_token"] != "FALSE":
                    mobile_refresh_token = it["result"][0]["mobile_refresh_token"]

                customer_insert_query = [
                    """
                        UPDATE skedul.customers 
                        SET 
                        customer_created_at = \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                        customer_first_name = \'"""
                    + firstName
                    + """\',
                        customer_last_name = \'"""
                    + lastName
                    + """\',
                        customer_phone_num = \'"""
                    + phone
                    + """\',
                        customer_address = \'"""
                    + address
                    + """\',
                        customer_unit = \'"""
                    + unit
                    + """\',
                        customer_city = \'"""
                    + city
                    + """\',
                        customer_state = \'"""
                    + state
                    + """\',
                        customer_zip = \'"""
                    + zip_code
                    + """\',
                        customer_lat = \'"""
                    + latitude
                    + """\',
                        customer_long = \'"""
                    + longitude
                    + """\',
                        password_salt = \'"""
                    + salt
                    + """\',
                        password_hashed = \'"""
                    + password
                    + """\',
                        password_algorithm = \'"""
                    + algorithm
                    + """\',
                        referral_source = \'"""
                    + referral
                    + """\',
                        role = \'"""
                    + role
                    + """\',
                        user_social_media = \'"""
                    + user_social_signup
                    + """\',
                        social_timestamp  =  DATE_ADD(now() , INTERVAL 14 DAY)
                        WHERE user_unique_id = \'"""
                    + cust_id
                    + """\';
                    """
                ]

            else:

                # check if there is a same user_unique_id existing
                query = (
                    """
                        SELECT user_email_id FROM skedul.customers
                        WHERE user_email_id = \'"""
                    + email
                    + "';"
                )
                print("email---------")
                items = execute(query, "get", conn)
                if items["result"]:

                    items["result"] = ""
                    items["code"] = 409
                    items["message"] = "Email address has already been taken."

                    return items

                if items["code"] == 480:

                    items["result"] = ""
                    items["code"] = 480
                    items["message"] = "Internal Server Error."
                    return items

                print("Before write")
                # write everything to database
                customer_insert_query = [
                    """
                        INSERT INTO skedul.customers 
                        (
                            user_unique_id,
                            customer_created_at,
                            customer_first_name,
                            customer_last_name,
                            customer_phone_num,
                            user_email_id,
                            customer_address,
                            customer_unit,
                            customer_city,
                            customer_state,
                            customer_zip,
                            customer_lat,
                            customer_long,
                            password_salt,
                            password_hashed,
                            password_algorithm,
                            referral_source,
                            role,
                            user_social_media,
                            google_auth_token,
                            social_timestamp,
                            google_refresh_token,
                            mobile_access_token,
                            mobile_refresh_token,
                            social_id
                        )
                        VALUES
                        (
                        
                            \'"""
                    + NewUserID
                    + """\',
                            \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                            \'"""
                    + firstName
                    + """\',
                            \'"""
                    + lastName
                    + """\',
                            \'"""
                    + phone
                    + """\',
                            \'"""
                    + email
                    + """\',
                            \'"""
                    + address
                    + """\',
                            \'"""
                    + unit
                    + """\',
                            \'"""
                    + city
                    + """\',
                            \'"""
                    + state
                    + """\',
                            \'"""
                    + zip_code
                    + """\',
                            \'"""
                    + latitude
                    + """\',
                            \'"""
                    + longitude
                    + """\',
                            \'"""
                    + salt
                    + """\',
                            \'"""
                    + password
                    + """\',
                            \'"""
                    + algorithm
                    + """\',
                            \'"""
                    + referral
                    + """\',
                            \'"""
                    + role
                    + """\',
                            \'"""
                    + user_social_signup
                    + """\',
                            \'"""
                    + google_auth_token
                    + """\',
                            DATE_ADD(now() , INTERVAL 14 DAY),
                            \'"""
                    + google_refresh_token
                    + """\',
                            \'"""
                    + mobile_access_token
                    + """\',
                            \'"""
                    + mobile_refresh_token
                    + """\',
                            \'"""
                    + social_id
                    + """\');"""
                ]
            print(customer_insert_query[0])
            items = execute(customer_insert_query[0], "post", conn)

            if items["code"] != 281:
                items["result"] = ""
                items["code"] = 480
                items["message"] = "Error while inserting values in database"

                return items

            items["result"] = {
                "first_name": firstName,
                "last_name": lastName,
                "user_unique_id": NewUserID,
                "access_token": google_auth_token,
                "refresh_token": google_refresh_token,
                "access_token": mobile_access_token,
                "refresh_token": mobile_refresh_token,
                "social_id": social_id,
            }
            items["message"] = "Signup successful"
            items["code"] = 200

            print("sss-----", social_signup)

        except:
            print("Error happened while Sign Up")
            if "NewUserID" in locals():
                execute(
                    """DELETE FROM customers WHERE user_unique_id = '"""
                    + NewUserID
                    + """';""",
                    "post",
                    conn,
                )
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class AccountSalt(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            query = (
                """
                    SELECT password_algorithm, 
                            password_salt,
                            user_social_media 
                    FROM skedul.customers cus
                    WHERE user_email_id = \'"""
                + email
                + """\';
                """
            )
            items = execute(query, "get", conn)
            print(items)
            if not items["result"]:
                items["message"] = "Email doesn't exists"
                items["code"] = 404
                return items
            if items["result"][0]["user_social_media"] != "NULL":
                items["message"] = (
                    """Social Signup exists. Use \'"""
                    + items["result"][0]["user_social_media"]
                    + """\' """
                )
                items["code"] = 401
                return items
            items["message"] = "SALT sent successfully"
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class Login(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            password = data.get("password")
            social_id = data.get("social_id")
            signup_platform = data.get("signup_platform")
            query = (
                """
                    # CUSTOMER QUERY 1: LOGIN
                    SELECT user_unique_id,
                        customer_last_name,
                        customer_first_name,
                        user_email_id,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        google_auth_token,
                        google_refresh_token,
                        google_auth_token,
                        google_refresh_token,
                        social_id
                    FROM skedul.customers c
                    WHERE user_email_id = \'"""
                + email
                + """\';
                """
            )
            items = execute(query, "get", conn)
            print("Password", password)
            print(items)

            if items["code"] != 280:
                response["message"] = "Internal Server Error."
                response["code"] = 500
                return response
            elif not items["result"]:
                items["message"] = "Email Not Found. Please signup"
                items["result"] = ""
                items["code"] = 404
                return items
            else:
                print(items["result"])
                print("sc: ", items["result"][0]["user_social_media"])

                # checks if login was by social media
                if (
                    password
                    and items["result"][0]["user_social_media"] != "NULL"
                    and items["result"][0]["user_social_media"] != None
                ):
                    response["message"] = "Need to login by Social Media"
                    response["code"] = 401
                    return response

                # nothing to check
                elif (password is None and social_id is None) or (
                    password is None
                    and items["result"][0]["user_social_media"] == "NULL"
                ):
                    response["message"] = "Enter password else login from social media"
                    response["code"] = 405
                    return response

                # compare passwords if user_social_media is false
                elif (
                    items["result"][0]["user_social_media"] == "NULL"
                    or items["result"][0]["user_social_media"] == None
                ) and password is not None:

                    if items["result"][0]["password_hashed"] != password:
                        items["message"] = "Wrong password"
                        items["result"] = ""
                        items["code"] = 406
                        return items

                    if ((items["result"][0]["email_verified"]) == "0") or (
                        items["result"][0]["email_verified"] == "FALSE"
                    ):
                        response["message"] = "Account need to be verified by email."
                        response["code"] = 407
                        return response

                # compare the social_id because it never expire.
                elif (items["result"][0]["user_social_media"]) != "NULL":

                    if signup_platform != items["result"][0]["user_social_media"]:
                        items["message"] = (
                            "Wrong social media used for signup. Use '"
                            + items["result"][0]["user_social_media"]
                            + "'."
                        )
                        items["result"] = ""
                        items["code"] = 411
                        return items

                    if items["result"][0]["social_id"] != social_id:
                        print(items["result"][0]["social_id"])

                        items["message"] = "Cannot Authenticated. Social_id is invalid"
                        items["result"] = ""
                        items["code"] = 408
                        return items

                else:
                    string = " Cannot compare the password or social_id while log in. "
                    print("*" * (len(string) + 10))
                    print(string.center(len(string) + 10, "*"))
                    print("*" * (len(string) + 10))
                    response["message"] = string
                    response["code"] = 500
                    return response
                del items["result"][0]["password_hashed"]
                del items["result"][0]["email_verified"]

                query = (
                    "SELECT * from skedul.customers WHERE user_email_id = '"
                    + email
                    + "';"
                )
                items = execute(query, "get", conn)
                items["message"] = "Authenticated successfully."
                items["code"] = 200
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class stripe_key(Resource):
    def get(self, desc):
        print(desc)
        if desc == "skedulTEST":
            return {"publicKey": stripe_public_test_key}
        else:
            return {"publicKey": stripe_public_live_key}


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
            response["result"] = items

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes

api.add_resource(appointments, "/api/v2/appointments")
api.add_resource(treatments, "/api/v2/treatments")
api.add_resource(FullBlog, "/api/v2/fullBlog/<string:blog_id>")
api.add_resource(TruncatedBlog, "/api/v2/truncatedBlog")
api.add_resource(AddBlog, "/api/v2/addBlog")
api.add_resource(UploadImage, "/api/v2/uploadImage")
api.add_resource(DeleteBlog, "/api/v2/deleteBlog/<string:blog_id>")


api.add_resource(
    OneCustomerAppointments, "/api/v2/oneCustomerAppointments/<string:user_unique_id>"
)
api.add_resource(CreateAppointment, "/api/v2/createAppointment")
api.add_resource(AddTreatment, "/api/v2/addTreatment")

api.add_resource(
    GoogleCalenderEvents,
    "/api/v2/calenderEvents/<string:user_unique_id>,<string:start>,<string:end>",
)
api.add_resource(UpdateAccessToken, "/api/v2/UpdateAccessToken/<string:user_unique_id>")
api.add_resource(UserToken, "/api/v2/customerToken/<string:user_unique_id>")
api.add_resource(
    AvailableAppointments,
    "/api/v2/availableAppointments/<string:date_value>/<string:duration>",
)
api.add_resource(AddContact, "/api/v2/addContact")

api.add_resource(SendEmail, "/api/v2/sendEmail")


api.add_resource(findCustomerUID, "/api/v2/findCustomer")
api.add_resource(createAccount, "/api/v2/createAccount")
api.add_resource(AccountSalt, "/api/v2/AccountSalt")
api.add_resource(Login, "/api/v2/Login/")
api.add_resource(stripe_key, "/api/v2/stripe_key/<string:desc>")

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
