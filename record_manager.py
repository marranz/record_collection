import json
import os
import requests
import shutil
import re
import time
from typing import List, Dict, Optional, Any # Added type hinting for clarity

# Default file paths (can be overridden in the class constructor)
DEFAULT_DATABASE_FILE = "record_collection.json"
DEFAULT_HTML_FILE = "record_collection.html"
DEFAULT_COVERS_DIR = "covers"

class RecordCollectionManager:
    """Manages a record collection, including metadata, cover art, and HTML export."""

    def __init__(self,
                 database_file: str = DEFAULT_DATABASE_FILE,
                 html_file: str = DEFAULT_HTML_FILE,
                 covers_dir: str = DEFAULT_COVERS_DIR):
        """
        Initializes the RecordCollectionManager.

        Args:
            database_file: Path to the JSON file for storing collection data.
            html_file: Path to the HTML file for exporting the collection.
            covers_dir: Directory to store downloaded cover art images.
        """
        self.database_file = database_file
        self.html_file = html_file
        self.covers_dir = covers_dir
        self.collection: List[Dict[str, Any]] = [] # Initialize collection

        # Ensure covers directory exists
        os.makedirs(self.covers_dir, exist_ok=True)
        print(f"Using database: {self.database_file}")
        print(f"Using HTML file: {self.html_file}")
        print(f"Using covers directory: {self.covers_dir}")

        # Load existing collection on initialization
        self.load_collection()

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Removes or replaces characters unsafe for filenames."""
        # Remove characters that are definitely not allowed including backslash
        name = re.sub(r'[\/*?:"<>|]', "", name)
        # Replace spaces with underscores (optional, but common)
        name = name.replace(" ", "_")
        # Limit length if necessary (optional)
        max_len = 100
        return name[:max_len]

    def _download_and_save_image(self, image_url: str, base_filename: str) -> Optional[str]:
        """Downloads an image from a URL, determines extension, and saves it."""
        if not image_url or not base_filename:
            return None

        file_extension = ".jpg" # Default extension declared early
        filepath = os.path.join(self.covers_dir, f"{base_filename}{file_extension}") # Default filepath

        try:
            print(f"Attempting to download from URL: {image_url}")
            # Try to get a more reliable extension via HEAD request
            try:
                head_response = requests.head(image_url, timeout=5, allow_redirects=True)
                head_response.raise_for_status()
                content_type = head_response.headers.get('content-type')
                if content_type:
                    content_type = content_type.lower()
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        file_extension = ".jpg"
                    elif 'png' in content_type:
                        file_extension = ".png"
                    elif 'gif' in content_type:
                        file_extension = ".gif"
                    elif 'webp' in content_type:
                         file_extension = ".webp"
                    else: # Fallback to parsing URL if content-type is unhelpful
                        parsed_ext = os.path.splitext(image_url.split('?')[0])[1]
                        if parsed_ext and len(parsed_ext) <= 5:
                            file_extension = parsed_ext
                else: # Fallback if no content-type
                     parsed_ext = os.path.splitext(image_url.split('?')[0])[1]
                     if parsed_ext and len(parsed_ext) <= 5:
                         file_extension = parsed_ext

            except requests.exceptions.RequestException as head_err:
                 print(f"Warning: HEAD request failed ({head_err}), guessing extension from URL.")
                 parsed_ext = os.path.splitext(image_url.split('?')[0])[1]
                 if parsed_ext and len(parsed_ext) <= 5:
                     file_extension = parsed_ext

            # Final filename and filepath based on determined extension
            filename = f"{base_filename}{file_extension}"
            filepath = os.path.join(self.covers_dir, filename)

            # Avoid re-downloading if the exact file already exists
            if os.path.exists(filepath):
                print(f"Cover file {filepath} already exists. Using existing file.")
                return filepath

            # Proceed with download
            print(f"Downloading image to {filepath}...")
            img_response = requests.get(image_url, stream=True, timeout=15)
            img_response.raise_for_status()

            # Save the image to the file
            os.makedirs(self.covers_dir, exist_ok=True) # Ensure directory exists just in case
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(img_response.raw, f)

            print(f"Image saved successfully to {filepath}")
            return filepath

        except requests.exceptions.RequestException as e:
            print(f"Error downloading image from {image_url}: {e}")
            return None
        except IOError as e:
            # Filepath might be based on the default extension if HEAD failed early
            print(f"Error saving image file {filepath}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during image download/save: {e}")
            return None

    def download_album_cover(self, artist: str, album: str) -> Optional[str]:
        """Attempts to find and download album cover from iTunes API."""
        if not artist or not album:
             print("Artist and Album are required to search for cover art.")
             return None

        print(f"Searching for cover art for '{album}' by {artist}...")

        safe_artist = self._sanitize_filename(artist)
        safe_album = self._sanitize_filename(album)
        filename_base = f"{safe_artist}_{safe_album}"

        search_term = f"{artist} {album}"
        # Prioritize higher resolution artwork URLs
        artwork_keys = ['artworkUrl1000', 'artworkUrl600', 'artworkUrl100']

        try:
            # Optional: Add a small delay if running in loops frequently
            # time.sleep(0.5)

            response = requests.get(
                "https://itunes.apple.com/search",
                params={"term": search_term, "entity": "album", "limit": 1},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data['resultCount'] > 0:
                result = data['results'][0]
                image_url = None
                # Find the best available artwork URL
                for key in artwork_keys:
                     if key in result:
                        image_url = result[key]
                        # Attempt to replace lower res segment with higher res if needed
                        image_url = image_url.replace('100x100bb', '600x600bb')
                        break # Use the first one found (highest priority)

                if image_url:
                    # Use the helper function to download and save
                    return self._download_and_save_image(image_url, filename_base)
                else:
                    print("Could not find a valid image URL in API response.")
                    return None
            else:
                print("No results found on iTunes Store.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Error during iTunes API search: {e}")
            return None
        except json.JSONDecodeError:
            print("Error decoding iTunes API response.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during cover search: {e}")
            return None

    def load_collection(self):
        """Loads the record collection from the JSON file."""
        if os.path.exists(self.database_file):
            try:
                with open(self.database_file, 'r', encoding='utf-8') as f:
                    self.collection = json.load(f)
                    print(f"Loaded {len(self.collection)} records from {self.database_file}")
            except json.JSONDecodeError:
                print(f"Error: Could not decode {self.database_file}. Starting with an empty collection.")
                self.collection = []
            except Exception as e:
                 print(f"Error loading {self.database_file}: {e}. Starting with an empty collection.")
                 self.collection = []
        else:
            print(f"Database file {self.database_file} not found. Starting with an empty collection.")
            self.collection = []

    def save_collection(self):
        """Saves the current record collection to the JSON file."""
        try:
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(self.collection, f, indent=4, ensure_ascii=False)
            print(f"Collection saved successfully to {self.database_file}!")
        except IOError as e:
            print(f"Error saving collection to {self.database_file}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during saving: {e}")

    def add_record(self, artist: str, album: str, genre: str, year: str, format_type: str, notes: str = "") -> Dict[str, Any]:
        """Adds a new record to the collection and attempts to download cover art."""
        cover_path = None
        if artist and album: # Only try if we have artist and album
            cover_path = self.download_album_cover(artist, album)

        record = {
            "artist": artist,
            "album": album,
            "genre": genre,
            "year": year,
            "format": format_type,
            "notes": notes,
            "cover_path": cover_path # Store the cover path (can be None)
        }
        self.collection.append(record)
        print(f"Added '{album}' by {artist} to your collection.")
        if not cover_path:
            print("(Could not automatically download cover art)")
        return record # Return the added record

    def get_collection(self) -> List[Dict[str, Any]]:
         """Returns the current collection."""
         return self.collection

    def find_record_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Finds a record by its zero-based index."""
        if 0 <= index < len(self.collection):
            return self.collection[index]
        else:
            # It's better practice for the function finding the record
            # to report the error, rather than relying on the caller.
            print(f"Error: Index {index} is out of bounds (valid range 0-{len(self.collection)-1}).")
            return None

    def search_records(self, search_term: str, search_key: str) -> List[Dict[str, Any]]:
        """Searches the collection based on a key and term."""
        search_term = search_term.strip().lower()
        results = []
        # Define valid keys upfront
        valid_keys = ["artist", "album", "genre", "year"]
        if search_key not in valid_keys:
             print(f"Invalid search key: {search_key}. Use one of: {', '.join(valid_keys)}.")
             return []

        if search_key == 'year':
            results = [record for record in self.collection if search_term == record.get('year', '').lower()]
        else:
            # Case-insensitive search for string fields
            results = [record for record in self.collection if search_term in record.get(search_key, '').lower()]

        return results

    def update_record(self, index: int, new_data: Dict[str, Any], manage_cover: bool = False, manual_cover_url: Optional[str] = None) -> bool:
        """
        Updates an existing record by index.

        Args:
            index: The zero-based index of the record to update.
            new_data: A dictionary containing the fields to update (e.g., {"artist": "New Artist", "cover_path": None}).
                      Only keys present in the dictionary will be updated.
            manage_cover: If True, attempt to automatically download cover based on updated artist/album.
                          This is ignored if 'cover_path' is explicitly in new_data or manual_cover_url is provided.
            manual_cover_url: If provided, attempt to download cover from this URL (overrides auto-download and new_data['cover_path']).

        Returns:
            True if the update was successful, False otherwise.
        """
        record = self.find_record_by_index(index) # Use the find method which includes bounds check
        if record is None:
            return False # Error already printed by find_record_by_index

        old_cover_path = record.get('cover_path')
        updated_record_data = record.copy() # Work on a copy first

        # --- Cover Art Handling Logic ---
        # Determine the final cover path based on priority:
        # 1. Manual URL
        # 2. Explicit 'cover_path' in new_data (e.g., setting to None)
        # 3. Automatic download (if manage_cover is True)
        # 4. Keep old path

        final_cover_path = old_cover_path # Default: keep old path
        cover_action_taken = False # Flag to track if cover logic was triggered

        current_artist = new_data.get('artist', record.get('artist')) # Use new artist if provided, else old
        current_album = new_data.get('album', record.get('album'))   # Use new album if provided, else old

        # Priority 1: Manual URL
        if manual_cover_url:
            cover_action_taken = True
            if current_artist and current_album:
                print("Attempting manual cover download...")
                base_filename = f"{self._sanitize_filename(current_artist)}_{self._sanitize_filename(current_album)}"
                new_manual_cover_path = self._download_and_save_image(manual_cover_url, base_filename)
                if new_manual_cover_path:
                    final_cover_path = new_manual_cover_path
                    print(f"Using manually downloaded cover: {final_cover_path}")
                else:
                    print("(Manual cover download failed)")
                    # Optionally revert to old path or None if failure should clear it?
                    # For now, failure means we proceed to next priority or keep old.
                    final_cover_path = old_cover_path # Revert to old on failure
            else:
                 print("Cannot download manual cover without Artist and Album.")

        # Priority 2: Explicit 'cover_path' in new_data
        elif 'cover_path' in new_data:
             cover_action_taken = True
             final_cover_path = new_data['cover_path'] # Directly set path (could be None)
             print(f"Explicitly setting cover path to: {final_cover_path}")

        # Priority 3: Automatic download
        elif manage_cover:
            cover_action_taken = True
            if current_artist and current_album:
                print("Attempting automatic cover download...")
                new_auto_cover_path = self.download_album_cover(current_artist, current_album)
                if new_auto_cover_path:
                    final_cover_path = new_auto_cover_path
                    print(f"Using automatically downloaded cover: {final_cover_path}")
                else:
                    # If auto was attempted but failed, clear the path
                    final_cover_path = None
                    print("(Automatic cover download failed or no cover found, clearing path)")
            else:
                print("Cannot automatically download cover without Artist and Album.")
                # Keep old path if artist/album missing for auto download
                final_cover_path = old_cover_path


        # --- Update standard fields (excluding cover_path handled above) ---
        for key, value in new_data.items():
            if key != 'cover_path':
                updated_record_data[key] = value

        # Set the final determined cover path
        updated_record_data['cover_path'] = final_cover_path

        # --- Clean up old file if a *different* cover is being set ---
        if final_cover_path != old_cover_path and old_cover_path and os.path.exists(old_cover_path):
             try:
                 print(f"Removing old cover file: {old_cover_path}")
                 os.remove(old_cover_path)
             except OSError as e:
                 print(f"Warning: Could not remove old cover file {old_cover_path}: {e}")

        # --- Apply updates to the actual record in the collection ---
        self.collection[index] = updated_record_data

        print(f"Record at index {index} updated successfully!")
        return True


    def delete_record(self, index: int) -> bool:
        """Deletes a record by index and its associated cover file."""
        # Check bounds before trying to pop
        if not (0 <= index < len(self.collection)):
            print(f"Error: Index {index} is out of bounds (valid range 0-{len(self.collection)-1}).")
            return False

        try:
            deleted_record = self.collection.pop(index) # Now safe to pop

            # Attempt to delete associated cover file
            cover_path = deleted_record.get('cover_path')
            if cover_path and os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                    print(f"Deleted associated cover file: {cover_path}")
                except OSError as e:
                    print(f"Warning: Could not delete cover file {cover_path}: {e}")

            print(f"Deleted '{deleted_record.get('album', 'N/A')}' by {deleted_record.get('artist', 'N/A')}.")
            return True
        except Exception as e: # Catch unexpected errors during pop or file access
            print(f"An error occurred during deletion: {e}")
            # If pop succeeded but file deletion failed, the record is still gone from collection.
            # Consider if restoration logic is needed, but usually not for CLI tools.
            return False

    def sort_collection(self, sort_key: str = 'artist'):
        """Sorts the record collection by a specified key (default: artist, case-insensitive)."""
        if not self.collection:
            print("Your collection is empty. Nothing to sort.")
            return
        valid_keys = ['artist', 'album', 'genre', 'year']
        if sort_key not in valid_keys:
             print(f"Invalid sort key: {sort_key}. Use one of: {', '.join(valid_keys)}.")
             return

        try:
            # Use a lambda function for case-insensitive sorting for string keys
            if sort_key in ['artist', 'album', 'genre']:
                 self.collection.sort(key=lambda record: record.get(sort_key, '').lower())
            elif sort_key == 'year':
                 # Sort by year (handle potential non-numeric years gracefully by treating them as 0)
                 self.collection.sort(key=lambda record: int(record.get(sort_key, 0)) if record.get(sort_key, '').isdigit() else 0)

            print(f"Collection sorted by {sort_key}.")
        except Exception as e:
            print(f"An error occurred during sorting: {e}")


    def find_and_download_missing_covers(self) -> tuple[int, int]:
        """
        Scans the collection for missing covers and attempts to download them.

        Returns:
            A tuple containing (number_of_missing_covers_found, number_successfully_downloaded).
        """
        if not self.collection:
            print("Your collection is empty. Nothing to check.")
            return 0, 0

        print("\n--- Checking for Missing Album Covers ---")
        missing_count = 0
        downloaded_count = 0
        checked_count = 0

        # Iterate over indices to safely update the list item
        for i in range(len(self.collection)):
            record = self.collection[i] # Get current state of record
            checked_count += 1
            cover_path = record.get('cover_path')
            artist = record.get('artist')
            album = record.get('album')
            needs_download = False

            if not cover_path:
                needs_download = True
                print(f"Record '{album}' by {artist} has no cover path set.")
            elif not os.path.exists(cover_path):
                needs_download = True
                print(f"Cover file missing for '{album}' by {artist} (Path: {cover_path}).")

            if needs_download:
                missing_count += 1
                if artist and album:
                    print(f"Attempting to download cover for '{album}' by {artist}...")
                    new_cover_path = self.download_album_cover(artist, album)
                    if new_cover_path:
                        # Directly update the record in the collection list
                        self.collection[i]['cover_path'] = new_cover_path
                        downloaded_count += 1
                        print(f"Successfully downloaded cover for '{album}'.")
                    else:
                        print(f"Failed to download cover for '{album}'.")
                    print("-" * 10)
                else:
                    print(f"Skipping download for '{album}' - missing Artist or Album name.")
                    print("-" * 10)

        print("\n--- Missing Cover Check Complete ---")
        print(f"Checked {checked_count} records.")
        print(f"Found {missing_count} records needing covers.")
        print(f"Successfully downloaded {downloaded_count} new covers.")
        if downloaded_count > 0:
            print("Remember to save the collection to keep the updated cover paths!")
        return missing_count, downloaded_count

    def generate_html_list(self) -> str:
        """Generates an HTML list snippet of the record collection."""
        if not self.collection:
            return "<p>Your collection is empty.</p>"

        html_list = "<ul>\n"
        html_file_dir = os.path.dirname(self.html_file) # Get directory of HTML file for relative paths

        for record in self.collection:
            html_list += f"  <li>\n"
            cover_path = record.get('cover_path')
            # Check if path exists AND the file exists on disk
            if cover_path and os.path.exists(cover_path):
                 # Calculate relative path from HTML file location to cover file
                 try:
                     # Ensure both paths are absolute for reliable relative path calculation
                     abs_html_dir = os.path.abspath(html_file_dir or '.')
                     abs_cover_path = os.path.abspath(cover_path)
                     display_path = os.path.relpath(abs_cover_path, start=abs_html_dir)
                 except ValueError:
                     # Handle cases like different drives on Windows
                     display_path = cover_path # Fallback to original path

                 # Replace backslashes with forward slashes for HTML src attribute
                 display_path = display_path.replace("\\", "/")


                 html_list += f'    <img src="{display_path}" alt="{record.get("album", "Cover")} Cover" width="100" style="float: right; margin-left: 15px; border: 1px solid #eee;"><br>\n'
            html_list += f"    <strong>Artist:</strong> {record.get('artist', 'N/A')}<br>\n"
            html_list += f"    <strong>Album:</strong> {record.get('album', 'N/A')}<br>\n"
            html_list += f"    <strong>Genre:</strong> {record.get('genre', 'N/A')}<br>\n"
            html_list += f"    <strong>Year:</strong> {record.get('year', 'N/A')}<br>\n"
            html_list += f"    <strong>Format:</strong> {record.get('format', 'N/A')}<br>\n"
            if record.get('notes'):
                html_list += f"    <strong>Notes:</strong> {record['notes']}<br>\n"
            html_list += '    <div style="clear: both;"></div>\n'
            html_list += f"  </li>\n"
        html_list += "</ul>\n"
        return html_list

    def generate_html_file_content(self) -> str:
        """Generates the full HTML file content for the collection."""
        html_content = "<!DOCTYPE html>\n"
        html_content += "<html lang=\"en\">\n"
        html_content += "<head>\n"
        html_content += "    <meta charset=\"UTF-8\">\n"
        html_content += "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        html_content += "    <title>Record Collection</title>\n"
        html_content += "<style>\n"
        html_content += "body { font-family: 'Arial', sans-serif; background-color: #f9f9f9; margin: 0; padding: 0; }\n"
        html_content += "h1 { text-align: center; color: #333; padding: 20px 0; border-bottom: 1px solid #ddd; }\n"
        html_content += "ul { list-style-type: none; padding: 0; max-width: 800px; margin: 20px auto; }\n"
        html_content += "li { margin-bottom: 15px; border-bottom: 1px solid #eee; background-color: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; overflow: hidden; }\n"
        html_content += "li:hover { transform: translateY(-4px); box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); }\n"
        html_content += "li img { float: right; margin-left: 15px; border: 1px solid #eee; border-radius: 4px; max-width: 100px; height: auto; }\n" # Added max-width
        html_content += "strong { font-weight: 600; color: #2c3e50; }\n"
        html_content += "p { text-align: center; font-size: 1.1em; color: #666; padding: 10px; }\n"
        html_content += "</style>\n"
        html_content += "</head>\n"
        html_content += "<body>\n"
        html_content += "    <h1>My Record Collection</h1>\n"
        html_content += self.generate_html_list() # Call the instance method
        html_content += "</body>\n"
        html_content += "</html>\n"
        return html_content

    def save_html_file(self):
        """Generates and saves the HTML file to disk."""
        html_content = self.generate_html_file_content()
        try:
            with open(self.html_file, "w", encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML file saved to {self.html_file}")
        except IOError as e:
            print(f"Error saving HTML file {self.html_file}: {e}")


# --- Command Line Interface (Separate from the class) ---

def display_record(record: Dict[str, Any], index: Optional[int] = None):
     """Helper function to display a single record nicely."""
     prefix = f"{index+1}. " if index is not None else ""
     print(f"{prefix}Artist: {record.get('artist', 'N/A')}")
     print(f"   Album: {record.get('album', 'N/A')}")
     print(f"   Genre: {record.get('genre', 'N/A')}")
     print(f"   Year: {record.get('year', 'N/A')}")
     print(f"   Format: {record.get('format', 'N/A')}")
     if record.get('notes'):
         print(f"   Notes: {record['notes']}")
     cover_path = record.get('cover_path')
     if cover_path and os.path.exists(cover_path):
          print(f"   Cover: {cover_path}")
     elif cover_path:
          print(f"   Cover: {cover_path} (File missing!)")
     else:
          print(f"   Cover: Missing")
     print("-" * 20)

# --- run_cli function definition needs to be HERE, after the class and helper function ---
def run_cli():
    """Runs the command-line interface for the record manager."""
    # Instantiate the manager - NOW the class is defined
    manager = RecordCollectionManager()

    while True:
        print("\n--- Record Collection Manager ---")
        print("1. Add Record")
        print("2. View Collection")
        print("3. Search Collection")
        print("4. Edit Record")
        print("5. Delete Record")
        print("6. Sort Collection by Artist")
        print("7. Generate HTML File")
        print("8. Find Missing Covers")
        print("9. Delete Cover File Only")
        print("10. Save and Exit")

        choice = input("Enter your choice: ").strip()

        # --- Add Record ---
        if choice == '1':
            print("\n--- Add New Record ---")
            artist = input("Enter artist: ").strip()
            album = input("Enter album title: ").strip()
            genre = input("Enter genre: ").strip()
            year = input("Enter release year: ").strip()
            format_type = input("Enter format (LP, 7\", CD, etc.): ").strip()
            notes = input("Enter any notes (optional): ").strip()
            if artist and album: # Basic validation
                 manager.add_record(artist, album, genre, year, format_type, notes)
            else:
                 print("Artist and Album cannot be empty.")

        # --- View Collection ---
        elif choice == '2':
            collection = manager.get_collection()
            if not collection:
                print("Your collection is empty.")
            else:
                print("\n--- Your Record Collection ---")
                for i, record in enumerate(collection):
                    display_record(record, i)

        # --- Search Collection ---
        elif choice == '3':
            print("\n--- Search Collection ---")
            print("Search by: 1. Artist | 2. Album | 3. Genre | 4. Year")
            search_choice = input("Enter search type (1-4): ").strip()
            search_term = input("Enter search term: ").strip()
            search_key = None
            if search_choice == '1': search_key = 'artist'
            elif search_choice == '2': search_key = 'album'
            elif search_choice == '3': search_key = 'genre'
            elif search_choice == '4': search_key = 'year'
            else: print("Invalid search type.")

            if search_key and search_term:
                results = manager.search_records(search_term, search_key)
                if results:
                    print("\n--- Search Results ---")
                    for record in results:
                        display_record(record) # Display without index
                else:
                    print("No records found matching your search.")
            elif search_key:
                 print("Search term cannot be empty.")

        # --- Edit Record ---
        elif choice == '4':
             print("\n--- Edit Record ---")
             collection = manager.get_collection()
             if not collection:
                 print("Collection is empty, cannot edit.")
                 continue
             # List records for user selection
             for i, record in enumerate(collection):
                 print(f"{i+1}. {record.get('artist', 'N/A')} - {record.get('album', 'N/A')}")
             try:
                 index_str = input("Enter the number of the record to edit: ").strip()
                 index_to_edit = int(index_str) - 1

                 # Use the manager's find method which handles bounds checking
                 record_to_edit = manager.find_record_by_index(index_to_edit)

                 if record_to_edit:
                     print("\n--- Editing Record ---")
                     display_record(record_to_edit, index_to_edit) # Show current details
                     print("Enter new values (leave blank to keep current):")
                     new_data = {}
                     # Define editable fields
                     editable_keys = ["artist", "album", "genre", "year", "format", "notes"]
                     for key in editable_keys:
                         current_value = record_to_edit.get(key, '')
                         user_input = input(f"{key.capitalize()} [{current_value}]: ").strip()
                         # Only add to new_data if user provided input
                         if user_input:
                             new_data[key] = user_input

                     # Cover Management Input
                     manage_cover_choice = input("Attempt automatic cover download? (y/n): ").strip().lower()
                     manage_cover = manage_cover_choice == 'y'
                     manual_url = input("Enter manual cover URL (leave blank to skip): ").strip()

                     # Call update_record with collected data
                     manager.update_record(index_to_edit, new_data, manage_cover, manual_url or None)
                 # else: Error message already printed by find_record_by_index

             except ValueError:
                 print("Invalid input. Please enter a number.")
             except Exception as e:
                 print(f"An error occurred during editing: {e}")

        # --- Delete Record ---
        elif choice == '5':
            print("\n--- Delete Record ---")
            collection = manager.get_collection()
            if not collection:
                print("Collection is empty, cannot delete.")
                continue
            # List records for user selection
            for i, record in enumerate(collection):
                 print(f"{i+1}. {record.get('artist', 'N/A')} - {record.get('album', 'N/A')}")
            try:
                index_str = input("Enter the number of the record to delete: ").strip()
                index_to_delete = int(index_str) - 1

                # Check index validity *before* asking for confirmation
                if 0 <= index_to_delete < len(collection):
                    # Confirm deletion
                    confirm = input(f"Are you sure you want to delete record {index_to_delete + 1}? (y/n): ").strip().lower()
                    if confirm == 'y':
                        if manager.delete_record(index_to_delete):
                             print("Deletion successful.")
                        # else: Error message printed by delete_record
                    else:
                        print("Deletion cancelled.")
                else:
                    # Use the same error message as find_record_by_index for consistency
                    print(f"Error: Index {index_to_delete} is out of bounds (valid range 0-{len(collection)-1}).")

            except ValueError:
                print("Invalid input. Please enter a number.")
            except Exception as e: # Catch any unexpected errors during the process
                 print(f"An error occurred during deletion process: {e}")

        # --- Sort Collection ---
        elif choice == '6':
            manager.sort_collection(sort_key='artist')
            # Optionally view after sorting:
            # collection = manager.get_collection()
            # if collection:
            #     print("\n--- Sorted Collection ---")
            #     for i, record in enumerate(collection):
            #         display_record(record, i)

        # --- Generate HTML ---
        elif choice == '7':
            print("\n--- Generate HTML File ---")
            manager.save_html_file()

        # --- Find Missing Covers ---
        elif choice == '8':
             print("\n--- Find Missing Covers ---")
             manager.find_and_download_missing_covers()

        # --- Delete Cover File Only ---
        elif choice == '9':
            print("\n--- Delete Cover File Only ---")
            collection = manager.get_collection()
            if not collection:
                print("Collection is empty.")
                continue
            # List records for user selection
            for i, record in enumerate(collection):
                 print(f"{i+1}. {record.get('artist', 'N/A')} - {record.get('album', 'N/A')} (Cover: {record.get('cover_path', 'None')})")
            try:
                index_str = input("Enter the number of the record whose cover you want to delete: ").strip()
                index_to_delete_cover = int(index_str) - 1

                # Use find_record_by_index for validation
                record_to_modify = manager.find_record_by_index(index_to_delete_cover)

                if record_to_modify:
                    cover_path = record_to_modify.get('cover_path')

                    if not cover_path:
                        print(f"Record {index_to_delete_cover + 1} does not have a cover path set.")
                        continue # Go back to main menu

                    # Check if file exists before attempting deletion
                    if os.path.exists(cover_path):
                        confirm = input(f"Are you sure you want to delete the cover file '{cover_path}' for record {index_to_delete_cover + 1}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            try:
                                os.remove(cover_path)
                                print(f"Deleted cover file: {cover_path}")
                                # Now update the record to remove the path
                                if manager.update_record(index_to_delete_cover, {'cover_path': None}): # Pass None specifically
                                     print(f"Removed cover path from record {index_to_delete_cover + 1}.")
                                     print("Remember to save the collection (Option 10) to persist this change.")
                                else:
                                     # This case should be less likely if index was valid, but handle defensively
                                     print(f"Error: Failed to update record {index_to_delete_cover + 1} after deleting file.")
                            except OSError as e:
                                print(f"Error deleting file {cover_path}: {e}")
                            except Exception as e: # Catch potential errors during update_record
                                print(f"An unexpected error occurred: {e}")
                        else:
                            print("Cover deletion cancelled.")
                    else:
                         # File path exists in record but not on disk
                         print(f"Cover file '{cover_path}' not found on disk.")
                         confirm_remove_path = input(f"Remove this missing path from record {index_to_delete_cover + 1}? (y/n): ").strip().lower()
                         if confirm_remove_path == 'y':
                              if manager.update_record(index_to_delete_cover, {'cover_path': None}):
                                   print(f"Removed missing cover path from record {index_to_delete_cover + 1}.")
                                   print("Remember to save the collection (Option 10) to persist this change.")
                              else:
                                   print(f"Error: Failed to update record {index_to_delete_cover + 1}.")
                         else:
                              print("Path removal cancelled.")
                # else: Error message already printed by find_record_by_index

            except ValueError:
                print("Invalid input. Please enter a number.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        # --- Save and Exit ---
        elif choice == '10':
            print("\n--- Save and Exit ---")
            manager.save_collection()
            print("Exiting program.")
            break
        # --- Invalid Choice ---
        else:
            print("Invalid choice. Please try again.")

# --- Main execution block ---
if __name__ == "__main__":
    # This ensures the CLI runs only when the script is executed directly
    run_cli()
