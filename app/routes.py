from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.face_utils import process_image, save_face_encoding, find_matching_face, allowed_file

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        label = request.form.get('label')
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if not label:
            flash('Please provide a label', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            encoding, face_count = process_image(filepath)
            
            if face_count == 0:
                flash('No face detected in the image', 'danger')
            elif face_count > 1:
                flash('Multiple faces detected. Please upload an image with a single face', 'danger')
            elif encoding is not None:
                save_face_encoding(str(current_user.id), label, filename, encoding)
                flash('Face registered successfully!', 'success')
                return redirect(url_for('main.home'))
                
            os.remove(filepath)  # Clean up the uploaded file
            
        else:
            flash('Invalid file type', 'danger')
            
    return render_template('register_face.html')

@main.route('/verify-face', methods=['GET', 'POST'])
@login_required
def verify_face():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            encoding, face_count = process_image(filepath)
            
            if face_count == 0:
                flash('No face detected in the image', 'danger')
            elif face_count > 1:
                flash('Multiple faces detected. Please upload an image with a single face', 'danger')
            elif encoding is not None:
                label, user_id = find_matching_face(encoding)
                if label:
                    flash(f'Match found! This is {label}', 'success')
                else:
                    flash('No matching face found', 'info')
                    
            os.remove(filepath)  # Clean up the uploaded file
            
        else:
            flash('Invalid file type', 'danger')
            
    return render_template('verify_face.html')
