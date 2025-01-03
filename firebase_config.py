import firebase_admin
from firebase_admin import credentials

# Initialize Firebase Admin SDK with your credentials
cred = credentials.Certificate("exercease-d82ad-firebase-adminsdk-2e77p-ba3b9e9f3a.json")
firebase_admin.initialize_app(cred)
