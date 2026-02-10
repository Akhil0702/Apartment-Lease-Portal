from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
import os
import certifi

ca = certifi.where()

apartment = Flask(__name__, template_folder='templates', static_folder='static')
UPLOAD_FOLDER = os.path.join(apartment.root_path, 'static', 'uploads')  # Use os.path.join to get the absolute path
apartment.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

apartment.config["MONGO_URI"] = "mongodb+srv://akhilreddy:Akhil%40123@cluster0.aofa5.mongodb.net/apartment-app"
apartment.config['JWT_SECRET_KEY'] = "adb"
apartment.secret_key = 'apartment'

mongo = PyMongo(apartment, tlsCAFile=ca)

jwt = JWTManager(apartment)

# Import routes after creating the app
from app.routes import auth_routes, admin_routes, manager_routes, tenant_routes, apartment_routes, application_routes, lease_routes

if __name__ == "__main__":
    apartment.run(host='0.0.0.0', port=5000, debug=True)
