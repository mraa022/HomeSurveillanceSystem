

from flask import Flask, request, render_template, redirect, url_for, session,jsonify
import firebase_admin
from firebase_admin import credentials, storage, auth
from datetime import datetime, timedelta
import pytz
from uuid import uuid4
import cv2
import numpy as np
import requests
import urllib.request
from deepface import DeepFace
import os

import ssl

ssl._create_default_https_context = ssl._create_stdlib_context

def display_image(image_data):
    # Convert the file content to an image
    image_array = np.frombuffer(image_data, np.uint8)
    gray_image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)

def verify_user(email, password):
    api_key = os.getenv('API_KEY')  # Your Firebase Web API key
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'

    data = {
        'email': email,
        'password': password,
        'returnSecureToken': True
    }

    response = requests.post(url, json=data)
    result = response.json()

    if 'idToken' in result:
        return True
    else:
        return False
    


app = Flask(__name__)
app.secret_key = os.getenv('API_KEY')  # Replace with a real secret key
# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': os.getenv('STORAGE_BUCKET')  # Replace with your Firebase storage bucket
})

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("welcome.html")

@app.route("/captured_faces")
def list_faces():
    bucket = storage.bucket()
    
    # List all files in the 'images' folder
    blobs = bucket.list_blobs(prefix='final/')
    
    # Get file information
    files = []
    for blob in blobs:
        # Get file creation time
        if blob.name != 'final/': # don't want to include the /final folder in the list of images
            creation_time = datetime.fromtimestamp(blob.time_created.timestamp(), pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
            files.append({
                'url': blob.generate_signed_url(expiration=timedelta(hours=1)),
                'creation_time': creation_time
            })
    return render_template('captured_list.html', images=files)


@app.route('/wanted_faces')
def wanted_list():

    bucket = storage.bucket()
    
    # List all files in the 'images' folder
    blobs = bucket.list_blobs(prefix='faces/')
    
    # Get file information
    files = []
    for blob in blobs:
        # Get file creation time
        if blob.name != 'faces/': # don't want to include the /final folder in the list of images
            creation_time = datetime.fromtimestamp(blob.time_created.timestamp(), pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
            files.append({
                'url': blob.generate_signed_url(expiration=timedelta(hours=1)),
                'creation_time': creation_time
            })
    return render_template('wanted_list.html', images=files)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if verify_user(email, password):
            session['user'] = email  # Store user email in session
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials', 401
    
    return render_template('login.html')
    

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))




def upload_file_to_firebase(file, destination_blob_name):
    """Uploads a file to Firebase Storage."""
    bucket = storage.bucket()
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file.stream, content_type=file.content_type)
    # blob.make_public()
    print(f'File {file.filename} uploaded to {destination_blob_name}.')
    print(f'Public URL: {blob.public_url}')


@app.route('/upload', methods=['POST','GET'])
def upload():
    if request.method == "POST":
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            destination_blob_name = f'faces/{file.filename}'
            upload_file_to_firebase(file, destination_blob_name)
            return 'File uploaded successfully'
        return  redirect(url_for('wanted_list'))
    else:
        return render_template('add_face.html') 






def get_signed_url(blob, expiration):
    try:
        return blob.generate_signed_url(expiration=expiration)
    except Exception as e:
        print(f"Error generating signed URL for blob {blob.name}: {e}")
        return None
    
def read_image_from_url(url):
    try:
        with urllib.request.urlopen(url) as resp:
            img_array = np.array(bytearray(resp.read()), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
    except Exception as e:
        print(f"Error reading image from URL {url}: {e}")
        return None
#

def send_sms():
    pass
@app.route('/alert', methods=['POST'])
def alert():
    image_data = request.data
    image_array = np.frombuffer(image_data, np.uint8)
    color_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR) # img of person.

    bucket = storage.bucket()
    
    # List all files in the 'images' folder
    blobs = bucket.list_blobs(prefix='final/')
    for blob in blobs:
        img_url = get_signed_url(blob, expiration=timedelta(hours=1))
        img = read_image_from_url(img_url) # img taken by camera.
        if img is not None:
        # Read the image from the URL 
            result = DeepFace.verify(img,color_img,enforce_detection=False)
            if result['verified']:
                send_sms()


    return "True"

@app.route('/search', methods=['POST',"GET"])
def search():
    if request.method == "POST":
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        matches = []
        if file.filename == '':
            return redirect(request.url)
        if file:
            # put file in a cv2 color image
            file_bytes = file.read()
            # Convert the byte stream into a numpy array
            np_img = np.frombuffer(file_bytes, np.uint8)
            # Decode the numpy array into a color image
            reference = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            

            bucket = storage.bucket()
    
            # List all files in the 'images' folder
            blobs = bucket.list_blobs(prefix='final/')
            for blob in blobs:
                img_url = get_signed_url(blob, expiration=timedelta(hours=1))
                img = read_image_from_url(img_url) # img taken by camera.
                if img is not None:
                # Read the image from the URL 
                    result = DeepFace.verify(img,reference,enforce_detection=False)
                    print(result)
                    if result['verified']:
                        creation_time = datetime.fromtimestamp(blob.time_created.timestamp(), pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
                        matches.append({
                            'url': blob.generate_signed_url(expiration=timedelta(hours=1)),
                            'creation_time': creation_time,
                            "thresh_hold":(1-result['distance'])*100
                        })
                    
        return jsonify({"matches": matches})

    else:
        return render_template('search.html') 


@app.route('/matches')
def matches():
    return render_template('matches.html')

if __name__ == '__main__':
    app.run(port=8000, debug=True)
