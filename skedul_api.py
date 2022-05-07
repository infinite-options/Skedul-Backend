
from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail, Message

from properties import Properties, Property
from users import Users, Login
from ownerProfileInfo import OwnerProfileInfo
from managerProfileInfo import ManagerProfileInfo
from tenantProfileInfo import TenantProfileInfo
from businessProfileInfo import BusinessProfileInfo
from rentals import Rentals
from purchases import Purchases
from payments import Payments, UserPayments
from ownerProperties import OwnerProperties
from managerProperties import ManagerProperties
from tenantProperties import TenantProperties
from refresh import Refresh
from businesses import Businesses
from employees import Employees
from maintenanceRequests import MaintenanceRequests
from maintenanceRequests import MaintenanceRequestsandQuotes
from maintenanceQuotes import MaintenanceQuotes
from contracts import Contracts
from propertyInfo import PropertiesOwnerDetail, PropertyInfo, AvailableProperties, PropertiesOwner
from applications import Applications
from socialLogin import UserSocialLogin, UserSocialSignup
from leaseTenants import LeaseTenants

# app = Flask(__name__)
APPLICATION_NAME = "skedul"
# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")
# cors = CORS(app, resources={r'/api/v2/api/*': {'origins': '*'}})
# # cors = CORS(app)
CORS(app)
api = Api(app)
app.config['JWT_SECRET_KEY'] = 'secret'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
app.config['PROPAGATE_EXCEPTIONS'] = True
jwt = JWTManager(app)
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = "support@skedul.online"
app.config["MAIL_PASSWORD"] = "SupportSkedul1"
app.config["MAIL_DEFAULT_SENDER"] = "support@skedul.online"
app.config["MAIL_SUPPRESS_SEND"] = False
mail = Mail(app)


def sendEmail(recipient, subject, body):
    msg = Message(
        sender='support@skedul.online',
        recipients=[recipient],
        subject=subject,
        body=body
    )
    mail.send(msg)


app.sendEmail = sendEmail

api.add_resource(Properties, '/api/v2/properties')
api.add_resource(Property, '/api/v2/properties/<property_uid>')
api.add_resource(Users, '/api/v2/users')
api.add_resource(Login, '/api/v2/login')
api.add_resource(OwnerProfileInfo, '/api/v2/ownerProfileInfo')
api.add_resource(ManagerProfileInfo, '/api/v2/managerProfileInfo')
api.add_resource(TenantProfileInfo, '/api/v2/tenantProfileInfo')
api.add_resource(BusinessProfileInfo, '/api/v2/businessProfileInfo')
api.add_resource(Rentals, '/api/v2/rentals')
api.add_resource(Purchases, '/api/v2/purchases')
api.add_resource(Payments, '/api/v2/payments')
api.add_resource(UserPayments, '/api/v2/userPayments')
api.add_resource(OwnerProperties, '/api/v2/ownerProperties')
api.add_resource(ManagerProperties, '/api/v2/managerProperties')
api.add_resource(TenantProperties, '/api/v2/tenantProperties')
api.add_resource(Refresh, '/api/v2/refresh')
api.add_resource(Businesses, '/api/v2/businesses')
api.add_resource(Employees, '/api/v2/employees')
api.add_resource(MaintenanceRequests, '/api/v2/maintenanceRequests')
api.add_resource(MaintenanceRequestsandQuotes, '/api/v2/maintenanceRequestsandQuotes')
api.add_resource(MaintenanceQuotes, '/api/v2/maintenanceQuotes')
api.add_resource(Contracts, '/api/v2/contracts')
api.add_resource(PropertyInfo, '/api/v2/propertyInfo')
# api.add_resource(AvailableProperties,
#                  '/api/v2/availableProperties/<string:tenant_id>')
api.add_resource(AvailableProperties,
                 '/api/v2/availableProperties')
api.add_resource(PropertiesOwner,
                 '/api/v2/propertiesOwner')
api.add_resource(PropertiesOwnerDetail,
                 '/api/v2/propertiesOwnerDetail')
api.add_resource(Applications, '/api/v2/applications')
api.add_resource(UserSocialLogin, '/api/v2/userSocialLogin/<string:email>')
api.add_resource(UserSocialSignup, '/api/v2/userSocialSignup')
api.add_resource(LeaseTenants, "/leaseTenants")

if __name__ == '__main__':
    app.run(debug=True)
