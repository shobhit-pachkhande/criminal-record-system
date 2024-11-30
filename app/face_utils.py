import face_recognition
import numpy as np
from PIL import Image
import os
from app import db
from bson.binary import Binary
import pickle
import cv2

def process_image(image_path):
    """Process an image and return face encodings"""
    # Load the image
    image = face_recognition.load_image_file(image_path)
    
    # Find all face locations in the image
    face_locations = face_recognition.face_locations(image)
    
    if len(face_locations) != 1:
        return None, len(face_locations)
    
    # Get face encodings
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    if face_encodings:
        return face_encodings[0], 1
    return None, 0

def save_face_encoding(user_id, label, image_path, encoding):
    """Save face encoding to MongoDB"""
    encoding_binary = Binary(pickle.dumps(encoding))
    
    face_data = {
        'user_id': user_id,
        'label': label,
        'image_path': image_path,
        'encoding': encoding_binary
    }
    
    db.face_encodings.insert_one(face_data)

def find_matching_face(encoding):
    """Find matching face in the database"""
    all_faces = db.face_encodings.find()
    
    for face in all_faces:
        stored_encoding = pickle.loads(face['encoding'])
        # Compare faces with a tolerance of 0.6
        if face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.6)[0]:
            return face['label'], face['user_id']
    
    return None, None

def allowed_file(filename):
    """Check if the file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_frame(frame):
    """Process a video frame and return it with face recognition results"""
    # Convert the image from BGR color (OpenCV) to RGB color
    rgb_frame = frame[:, :, ::-1]
    
    # Find all face locations in the frame
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Draw results on the frame
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # Try to match the face
        label, _ = find_matching_face(face_encoding)
        
        # Draw a rectangle around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Draw the name below the face
        if label:
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        else:
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.putText(frame, 'Unknown', (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
    
    return frame
