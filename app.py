import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
# Import your manager class from the other file
from record_manager import RecordCollectionManager

# --- Configuration ---
# Use absolute paths for reliability, especially for templates and static files
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Define template and static folders relative to the app's base directory
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static') # Standard Flask static folder
# Define covers directory relative to base directory (assuming it's in the same main folder)
COVERS_DIR_NAME = 'covers' # Just the directory name
COVERS_DIR_PATH = os.path.join(BASE_DIR, COVERS_DIR_NAME)

# --- Flask App Initialization ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)
app.secret_key = 'your_very_secret_key' # Change this for production!

# --- Instantiate the Record Manager ---
# Pass the absolute path to the covers directory if needed by the manager logic
# (Assuming RecordCollectionManager uses the covers_dir path correctly)
manager = RecordCollectionManager(covers_dir=COVERS_DIR_PATH)

# --- Routes ---

@app.route('/')
def index():
    """Displays the entire record collection."""
    collection = manager.get_collection()
    # Pass the relative path prefix for covers to the template
    # This assumes covers are served via a specific route like /covers/<filename>
    return render_template('index.html', collection=collection, covers_prefix=f'/{COVERS_DIR_NAME}/')

@app.route('/add', methods=['GET', 'POST'])
def add_record_route():
    """Handles adding a new record via a web form."""
    if request.method == 'POST':
        try:
            artist = request.form['artist']
            album = request.form['album']
            genre = request.form['genre']
            year = request.form['year']
            format_type = request.form['format']
            notes = request.form.get('notes', '') # Use .get for optional fields

            if not artist or not album:
                flash('Artist and Album are required fields.', 'error')
            else:
                manager.add_record(artist, album, genre, year, format_type, notes)
                manager.save_collection() # Save after adding
                flash(f"Record '{album}' by {artist} added successfully!", 'success')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error adding record: {e}", 'error')
            # Optionally log the error e
        # If POST failed or had validation errors, fall through to render the form again
        return render_template('add_record.html', form_data=request.form) # Pass back form data

    # GET request: show the form
    return render_template('add_record.html', form_data={}) # Pass empty dict for initial load

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit_record_route(index):
    """Handles editing an existing record."""
    record = manager.find_record_by_index(index)
    if record is None:
        flash(f"Record with index {index} not found.", 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            new_data = {
                'artist': request.form['artist'],
                'album': request.form['album'],
                'genre': request.form['genre'],
                'year': request.form['year'],
                'format': request.form['format'],
                'notes': request.form.get('notes', '')
            }
            # Checkboxes might not be present if unchecked
            manage_cover = 'manage_cover' in request.form
            manual_url = request.form.get('manual_cover_url', '').strip()

            if not new_data['artist'] or not new_data['album']:
                 flash('Artist and Album are required fields.', 'error')
                 # Re-render edit form with current (failed) data
                 return render_template('edit_record.html', record=new_data, index=index, covers_prefix=f'/{COVERS_DIR_NAME}/')

            if manager.update_record(index, new_data, manage_cover, manual_url or None):
                manager.save_collection() # Save after successful update
                flash(f"Record {index + 1} updated successfully!", 'success')
            else:
                # update_record might print errors, but we can flash a generic one
                flash(f"Failed to update record {index + 1}.", 'error')

            return redirect(url_for('index'))

        except Exception as e:
            flash(f"Error updating record: {e}", 'error')
            # Re-render edit form with original record data on error
            return render_template('edit_record.html', record=record, index=index, covers_prefix=f'/{COVERS_DIR_NAME}/')

    # GET request: show the edit form pre-filled
    #return render_template('edit_record.html', record=record, index=index, covers_prefix=f'/{COVERS_DIR_NAME}/')
    return render_template('edit_record.html', record=record, index=index, covers_prefix='')

@app.route('/delete/<int:index>', methods=['POST'])
def delete_record_route(index):
    """Handles deleting a record."""
    record = manager.find_record_by_index(index) # Get record details for flash message
    if record:
        if manager.delete_record(index):
            manager.save_collection() # Save after successful delete
            flash(f"Record '{record.get('album', 'N/A')}' deleted successfully!", 'success')
        else:
            flash(f"Failed to delete record {index + 1}.", 'error')
    else:
        flash(f"Record with index {index} not found.", 'error')
    return redirect(url_for('index'))

@app.route('/delete_cover/<int:index>', methods=['POST'])
def delete_cover_route(index):
    """Handles deleting only the cover file for a record."""
    record = manager.find_record_by_index(index)
    if record:
        cover_path = record.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            try:
                os.remove(cover_path)
                # Update the record in the manager to remove the path
                if manager.update_record(index, {'cover_path': None}):
                    manager.save_collection() # Save the change
                    flash(f"Cover file for '{record.get('album', 'N/A')}' deleted and path removed.", 'success')
                else:
                     flash(f"Cover file deleted, but failed to update record path.", 'warning')

            except OSError as e:
                flash(f"Error deleting cover file {cover_path}: {e}", 'error')
            except Exception as e:
                 flash(f"An unexpected error occurred deleting cover: {e}", 'error')

        elif cover_path: # Path exists in record but file doesn't
             flash(f"Cover file '{cover_path}' not found on disk. Removing path from record.", 'warning')
             if manager.update_record(index, {'cover_path': None}):
                  manager.save_collection()
             else:
                  flash(f"Failed to remove missing cover path from record.", 'error')
        else:
            flash(f"Record '{record.get('album', 'N/A')}' has no cover path set.", 'info')
    else:
        flash(f"Record with index {index} not found.", 'error')

    return redirect(url_for('index'))

@app.route('/find_missing_covers', methods=['POST'])
def find_missing_covers_route():
    """Triggers the process to find and download missing covers."""
    try:
        missing, downloaded = manager.find_and_download_missing_covers()
        if downloaded > 0:
            manager.save_collection() # Save if new covers were downloaded
            flash(f"Checked for missing covers. Found {missing}, downloaded {downloaded}. Collection saved.", 'success')
        else:
            flash(f"Checked for missing covers. Found {missing}, downloaded {downloaded}.", 'info')
    except Exception as e:
        flash(f"Error finding missing covers: {e}", 'error')
    return redirect(url_for('index'))

# --- Route to serve cover images ---
@app.route(f'/{COVERS_DIR_NAME}/<path:filename>')
def serve_cover(filename):
    """Serves files from the covers directory."""
    # Use send_from_directory for security
    # It expects the directory *path* and the filename
    return send_from_directory(COVERS_DIR_PATH, filename)


# --- Main execution ---
if __name__ == '__main__':
    # Ensure the covers directory exists (Flask doesn't create it automatically for serving)
    os.makedirs(COVERS_DIR_PATH, exist_ok=True)
    # Run the app in debug mode (convenient for development)
    # Use host='0.0.0.0' to make it accessible on your network
    app.run(debug=True, host='0.0.0.0', port=8888)
