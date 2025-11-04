# api.py
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from main import run_full_pipeline # <-- IMPORT YOUR FUNCTION

app = Flask(__name__)

# Set a folder for uploads. RunPod provides /tmp/
UPLOAD_FOLDER = '/tmp/video_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/process_video', methods=['POST'])
def handle_video_upload():
    if 'video' not in request.files:
        return jsonify({"status": "error", "message": "No video file part"}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    # 1. Save the uploaded video to a temp path
    filename = secure_filename(file.filename)
    temp_video_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_video_path)

    # 2. Call your main function with that path
    # This is the long-running task
    result = run_full_pipeline(temp_video_path)

    # 3. Clean up the temp file
    try:
        os.remove(temp_video_path)
    except Exception as e:
        print(f"Warning: could not remove temp file {temp_video_path}: {e}")
    
    # 4. Return the result
    if result['status'] == 'success':
        # The 'data' field already contains a JSON string
        # To return proper JSON, we must load it back into a dict
        import json
        result['data'] = json.loads(result['data'])
        return jsonify(result)
    else:
        return jsonify(result), 500

# This part is NOT used by Gunicorn, but good for local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)