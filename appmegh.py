#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install flask opencv-python pillow numpy


# In[16]:


from flask import Flask, render_template_string, jsonify, request, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import cv2
import os
import uuid

# It's a good practice to separate configurations from your main code.
class Config:
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simple Image Editor</title>
<link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>

<div class="container">
  <h2>Simple Image Editor</h2>

  <form id="imageForm">
    <input type="file" id="imageInput" name="file" accept="image/*" required onchange="uploadImage()"><br><br>

    <label for="brightness">Brightness:</label>
    <input type="range" id="brightness" name="brightness" min="0" max="100" value="50" oninput="applyFilters()"><br><br>

    <label for="contrast">Contrast:</label>
    <input type="range" id="contrast" name="contrast" min="0" max="100" value="50" oninput="applyFilters()"><br><br>

    <label for="rotate">Rotate (degrees):</label>
    <input type="range" id="rotate" name="rotate" min="0" max="360" value="0" oninput="applyFilters()"><br><br>
    
    <label for="grayscale">Grayscale:</label>
    <input type="range" id="grayscale" name="grayscale" min="0" max="100" value="0" oninput="applyFilters()"><br><br>

    
    <!-- Download Button - Initially hidden -->
    <a id="downloadLink" style="display:none;" download="edited_image.png">
      <button type="button">Download Image</button>
    </a>
  </form>

  <img id="imagePreview" alt="Image preview will appear here after upload.">
</div>

<script>
function uploadImage() {
    let formData = new FormData(document.getElementById('imageForm'));
formData.append('filename', document.getElementById('imageForm').dataset.filename);

// Add the grayscale value to the form data
let grayscale = document.getElementById('grayscale').value;
formData.append('grayscale', grayscale);

    let imageInput = document.getElementById('imageInput');

    if (imageInput.files.length > 0) {
        formData.append('file', imageInput.files[0]);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('imageForm').dataset.filename = data.filename;
            applyFilters(); // Apply default filters and show image
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        alert('Please select an image to upload.');
    }
}

function applyFilters() {
    if (!document.getElementById('imageForm').dataset.filename) {
        return; // Don't try to apply filters if no image is uploaded
    }

    let formData = new FormData(document.getElementById('imageForm'));
    formData.append('filename', document.getElementById('imageForm').dataset.filename);

    fetch('/edit', {
        method: 'POST',
        body: formData
    })
    .then(response => response.blob())
    .then(blob => {
        let downloadLink = document.getElementById('downloadLink');
        let blobUrl = URL.createObjectURL(blob);
        updateImagePreview(blobUrl);
        downloadLink.href = blobUrl;
        downloadLink.style.display = 'block'; // Show the download link
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function updateImagePreview(blobUrl) {
    let imagePreview = document.getElementById('imagePreview');
    imagePreview.src = blobUrl;
}
</script>

</body>
</html>


"""


# It's a good practice to separate configurations from your main code.
class Config:
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # UUID is used to avoid file name collision.
        filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({'filename': file_path})

    return jsonify({'error': 'File type not allowed'}), 400

def allowed_file(filename):
    # Check for allowed file extensions
    return '.' in filename and            filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/edit', methods=['POST'])
def edit_image():
    filename = request.form['filename']

    # Validate that the filename exists
    if not os.path.isfile(filename):
        return jsonify({'error': 'File not found'}), 404

    # Extract and convert form data to appropriate types
    try:
        brightness = float(request.form['brightness'])
        contrast = float(request.form['contrast'])
        rotate = float(request.form['rotate'])
        # Extract grayscale value
        grayscale = float(request.form.get('grayscale', 0))

    except (ValueError, KeyError) as e:
        return jsonify({'error': 'Invalid input parameters'}), 400

    image = Image.open(filename)
    adjusted_image = adjust_image(image, brightness, contrast, rotate, grayscale)


    # We should save the edited image as a new file to avoid potential conflicts with concurrent requests
    edited_filename = f"edited_{os.path.basename(filename)}"
    edited_path = os.path.join(app.config['UPLOAD_FOLDER'], edited_filename)
    adjusted_image.save(edited_path, 'PNG')

    return send_file(edited_path, mimetype='image/png', as_attachment=True, attachment_filename=edited_filename)

def adjust_image(image, brightness=50, contrast=50, rotate=0, grayscale=0):
    # Adjust the slider range from 0-100 to an appropriate scale for brightness and contrast
    brightness = ((brightness / 100.0) * 2) - 1  # Scale from 0-100 to -1 to 1
    contrast = contrast / 50.0  # Scale from 0-100 to 0 to 2
    
    if image.mode not in ('L', 'RGB'):
        image = image.convert('RGB')

    img_array = np.array(image)

    if img_array.dtype != np.uint8:
        img_array = img_array.astype(np.uint8)

    img_array = cv2.convertScaleAbs(img_array, alpha=contrast, beta=brightness * 255) # Adjusted for the new scale

    if rotate != 0:
        img_array = Image.fromarray(img_array)
        img_array = img_array.rotate(rotate, expand=True)
        img_array = np.array(img_array)
    
    # Apply grayscale if the slider is more than 0
    if grayscale > 0:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        if grayscale < 100:
            # If grayscale is not full (100), then blend with the original image
            original = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            img_array = cv2.addWeighted(original, (100 - grayscale) / 100.0, cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR), grayscale / 100.0, 0)
    
    return Image.fromarray(img_array)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




