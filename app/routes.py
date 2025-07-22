from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.face_utils import process_image, save_face_encoding, find_matching_face, allowed_file, process_frame, check_face_exists
import cv2
import base64
import re
from PIL import Image
import io
from flask import session

main = Blueprint('main', __name__)

# Global variable for camera
camera = None

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})
            
        file = request.files['file']
        label = request.form.get('label')
        crime = request.form.get('crime')  # Criminal record (optional, but should be included)
        address = request.form.get('address')  # Address (optional)
        date = request.form.get('date')  # Date of birth (optional)
        gender = request.form.get('gender')
        source = request.form.get('source', 'upload')  # 'upload' or 'webcam'
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
            
        if not label:
            return jsonify({'success': False, 'message': 'Please provide a label'})
            
        if file and (allowed_file(file.filename) or source == 'webcam'):
            # Save the file
            if source == 'webcam':
                filename = f'webcam_{label}_{current_user.id}.jpg'
            else:
                filename = secure_filename(file.filename)
                
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the image
            encoding, face_count = process_image(filepath)
            
            if face_count == 0:
                os.remove(filepath)
                return jsonify({'success': False, 'message': 'No face detected in the image'})
            elif face_count > 1:
                os.remove(filepath)
                return jsonify({'success': False, 'message': 'Multiple faces detected. Please upload an image with a single face'})
            elif encoding is not None:
                # Check if face already exists
                exists, existing_label, existing_user, _ , _ , _ , _ , _ , = check_face_exists(encoding)
                if exists:
                    os.remove(filepath)
                    message = f'This face is already registered as "{existing_label}"'
                    if source == 'webcam':
                        return jsonify({'success': False, 'message': message})
                    flash(message, 'warning')
                    return redirect(url_for('main.register_face'))
                
                # Face is new, save it
                save_face_encoding(str(current_user.id), label, filename, encoding , crime, address, date, gender)
                if source == 'webcam':
                    return jsonify({'success': True, 'message': 'Face registered successfully!'})
                flash('Face registered successfully!', 'success')
                return redirect(url_for('main.home'))
                
            os.remove(filepath)
            
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'})
            
    return render_template('register_face.html')

@main.route('/verify-face', methods=['GET', 'POST'])
@login_required
def verify_face():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})
            
        file = request.files['file']
        source = request.form.get('source', 'upload')  # 'upload' or 'webcam'
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
            
        if file and (allowed_file(file.filename) or source == 'webcam'):
            if source == 'webcam':
                filename = f'verify_webcam_{current_user.id}.jpg'
            else:
                filename = secure_filename(file.filename)
                
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            encoding, face_count = process_image(filepath)
            
            if face_count == 0:
                os.remove(filepath)
                return jsonify({'success': False, 'message': 'No face detected in the image'})
            elif face_count > 1:
                os.remove(filepath)
                return jsonify({'success': False, 'message': 'Multiple faces detected. Please upload an image with a single face'})
            elif encoding is not None:
                label, user_id, crime, address, date, gender ,image_url = find_matching_face(encoding)
                os.remove(filepath)
                
                if source == 'webcam':
                    # return jsonify({'match': bool(label), 'label': label if label else None})
                    return jsonify({
                        'match': bool(label),
                        'label': label,
                        'crime': crime,
                        'address': address,
                        'date': date,
                        'gender': gender,
                        'image_url': image_url  # Add image URL here to display the image
                    })
                               
                    
                if label:
                    flash(f'Match found! This is {label}', 'success')
                    session['face_details'] = {
                        'label': label,
                        'crime': crime,
                        'address': address,
                        'date': date,
                        'gender': gender,
                        'image_url':image_url
                    }

                    # Pass face details to the template
                    return redirect(url_for('main.criminalrecord', match=True))
                    
                else:
                    flash('No matching face found', 'info')
                return redirect(url_for('main.verify_face'))
                
            os.remove(filepath)
            
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'})
            
    return render_template('verify_face.html')

def gen_frames():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Process frame for face recognition
            processed_frame = process_frame(frame)
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@main.route('/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@main.route('/realtime-recognition')
@login_required
def realtime_recognition():
    return render_template('realtime.html')

@main.route('/stop_camera')
@login_required
def stop_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return '', 204

@main.route('/crimial_record_details')
@login_required
def criminalrecord():
    face_details = session.get('face_details')
    if face_details:
        return render_template('criminal_record_detail.html' , face_details=face_details, match=True)