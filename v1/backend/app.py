import os
import uuid
import subprocess
import sys
import logging
import json # Kept for potential future use, but not strictly needed for the CSV logic
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename 

# Import necessary libraries that were used in the working version
import shutil
import pandas as pd
from typing import Optional # Used for type hinting, though not critical for function

# Set up logging for easier debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. Instantiate the Flask app first
app = Flask(__name__)

# 2. CRITICAL PATH FIX: Define paths relative to the Project Root
# Path(__file__).parent is the 'backend' folder. We use .parent.parent 
# to get to the 'CampaignIQ' directory (the project root).
PROJECT_ROOT = Path(__file__).parent.parent

# Define directories relative to the Project Root
BASE_OUTPUT_DIR = PROJECT_ROOT / 'outputs'
TEMP_DIR = PROJECT_ROOT / 'uploads'
SCRIPT_PATH = PROJECT_ROOT / 'backend' / 'causal_impact.py' 

# Ensure the necessary directories exist upon startup
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Configuration for file upload
ALLOWED_EXTENSIONS = {'csv'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """
    Handles file upload, executes the causal analysis script, and returns the 
    results in the 'stats' structure the frontend expects.
    """
    # --- File Upload and Setup ---
    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'message': 'Invalid file type. Only CSV allowed.'}), 400

    # 1. Setup paths and save uploaded file
    session_id = str(uuid.uuid4())
    data_filename = f"{session_id}_{secure_filename(file.filename)}"
    data_path = TEMP_DIR / data_filename
    session_output_dir = BASE_OUTPUT_DIR / session_id
    
    try:
        file.save(str(data_path))
        session_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created output directory: {session_output_dir.absolute()}")
    except Exception as e:
        logging.error(f"Error saving file or creating directory: {e}")
        return jsonify({"message": f"Server setup failed: {e}"}), 500

    # Define absolute paths for script arguments
    output_path_str = str(session_output_dir.absolute())
    data_path_str = str(data_path.absolute())
    script_path_str = str(SCRIPT_PATH.absolute()) 
    
    # 3. Execute the Python script
    try:
        command = [
            'python', script_path_str, 
            '--data', data_path_str,
            '--outdir', output_path_str, # Pass the ABSOLUTE output path
            '--plots' 
        ]
        
        logging.info(f"Executing Analysis Command: {' '.join(command)}")
        
        # Run the subprocess
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=False # Set to False to handle error checking manually below
        )
        
        logging.info(f"Analysis Script STDOUT:\n{result.stdout}")

        if result.returncode != 0:
            error_msg = (
                f"Analysis script failed (Exit Code {result.returncode}).\n"
                f"--- Script STDERR/Error Log ---\n{result.stderr}\n---------------------\n"
                "The analysis script crashed."
            )
            logging.error(error_msg)
            raise RuntimeError(error_msg)
            
        # --- Read Results from CSV ---
        # NOTE: Reverting to the logic that reads the CSV output file.
        summary_file_path = session_output_dir / 'causal_impact_summary.csv'
        report_path = session_output_dir / 'report.md'
        
        if not summary_file_path.exists():
            raise FileNotFoundError(f"Analysis outputs (causal_impact_summary.csv) were not generated. Path: {summary_file_path.absolute()}")

        summary_df = pd.read_csv(summary_file_path)
        # Using the AIPW result as the primary metric
        aipw_result = summary_df[summary_df['Method'].str.contains('AIPW')].iloc[0]
        
        # Read Report Preview
        report_content = "Report not found."
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

        # --- Prepare Key Stats for Frontend (CRITICAL FIX FOR TYPERROR) ---
        # The frontend expects a 'stats' object containing 'effectiveness'
        # We assume the CSV stores the ATE as a decimal (0.05) or a percentage (5.0)
        ate_pp = aipw_result['ATE_pp']
        ci_lower_pp = aipw_result['CI_lower_pp']
        
        # Determine effectiveness string
        confidence = 0.95
        effectiveness = 'High' if ci_lower_pp > 0 and ate_pp > 0 else ('Medium' if ate_pp > 0 else 'Low')
        
        key_stats = {
            # NOTE: We return the raw numbers, the frontend can format them.
            'ate': ate_pp / 100.0, # Convert percentage point (e.g., 5.0) back to decimal (0.05)
            'confidence': confidence,
            'effectiveness': effectiveness # The missing field!
        }

        # --- Clean Up and Success Return ---
        os.remove(data_path)

        return jsonify({
            'status': 'success',
            'runId': session_id,
            'stats': key_stats, # <--- THIS IS THE STRUCTURE THE FRONTEND EXPECTS
            'reportPreview': report_content[:300] + '...'
        }), 200
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logging.error(f"FATAL ANALYSIS ERROR (Run {session_id}): {error_msg}")
        
        # Clean up files in case of failure
        shutil.rmtree(session_output_dir, ignore_errors=True)
        if data_path.exists():
             os.remove(data_path)
             
        # Return a valid JSON error response
        return jsonify({'status': 'error', 'message': error_msg}), 500


@app.route('/api/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    """
    Serves the requested output file from the session-specific output directory.
    This replaces the old download route logic.
    """
    file_path = BASE_OUTPUT_DIR / session_id / secure_filename(filename)
    
    if not file_path.exists():
        logging.warning(f"File not found during download attempt: {file_path.absolute()}")
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    # Determine MIME type
    suffix = file_path.suffix.lower()
    if suffix in ['.png', '.jpg', '.jpeg']:
        mimetype = f'image/{suffix[1:]}'
    elif suffix == '.csv':
        mimetype = 'text/csv'
    elif suffix == '.md':
        mimetype = 'text/markdown'
    else:
        mimetype = 'application/octet-stream'

    logging.info(f"Serving file: {file_path.absolute()}")
    return send_file(
        str(file_path.absolute()),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    ) 

@app.route('/api/download_all/<session_id>', methods=['GET'])
def download_all(session_id):
    """
    Compresses all generated files for a given session_id into a ZIP archive and serves it.
    """
    session_output_dir = BASE_OUTPUT_DIR / session_id
    
    if not session_output_dir.exists():
        logging.warning(f"Session directory not found for batch download: {session_output_dir.absolute()}")
        return jsonify({'status': 'error', 'message': 'Analysis results not found for this session.'}), 404

    try:
        # Define the base path for the temporary ZIP file in the TEMP_DIR
        temp_zip_path_base = TEMP_DIR / f'CampaignIQ_Report_{session_id}'
        
        # Create the ZIP archive
        # base_name: The name and path of the archive to create (without .zip extension)
        # format: 'zip'
        # root_dir: The directory to start the archival process from (we use the parent of the output dir)
        # base_dir: The directory inside the root_dir to archive (the session folder itself)
        archive_path = shutil.make_archive(
            base_name=str(temp_zip_path_base), 
            format='zip', 
            root_dir=session_output_dir.parent, # Starts from 'outputs' directory
            base_dir=session_output_dir.name    # Archives the specific session folder (e.g., 'abc-123')
        )
        
        logging.info(f"Created ZIP archive at: {archive_path}")

        # Send the created ZIP file
        response = send_file(
            archive_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"CampaignIQ_Report_{session_id}.zip"
        )
        
        # Schedule the clean up of the generated ZIP file *after* it's been sent.
        # Note: In a production Flask app, you'd use @app.after_request, but 
        # in this environment, relying on os.remove() after the response object is returned is the simplest approach.
        @response.call_on_close
        def cleanup_zip():
            try:
                os.remove(archive_path)
                logging.info(f"Cleaned up temporary ZIP archive: {archive_path}")
            except Exception as cleanup_e:
                logging.warning(f"Failed to clean up temporary ZIP archive: {cleanup_e}")

        return response
        
    except Exception as e:
        error_msg = f"Batch download failed: {str(e)}"
        logging.error(f"Error during ZIP creation/serving: {error_msg}")
        # Clean up potential partial zip file if it exists
        zip_file_to_cleanup = f"{str(temp_zip_path_base)}.zip"
        if os.path.exists(zip_file_to_cleanup):
            os.remove(zip_file_to_cleanup)
            logging.info(f"Cleaned up partial ZIP archive: {zip_file_to_cleanup}")

        return jsonify({'status': 'error', 'message': error_msg}), 500


if __name__ == '__main__':
    logging.info(f"Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True)
