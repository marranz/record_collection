import json
import os

DATABASE_FILE = "record_collection.json"
HTML_FILE = "record_collection.html"

def load_collection():
    """Loads the record collection from the JSON file."""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error: Could not decode the database file. Starting with an empty collection.")
                return []
    return []

def save_collection(collection):
    """Saves the record collection to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(collection, f, indent=4)
    print("Collection saved successfully!")

def add_record(collection):
    """Adds a new record to the collection."""
    artist = input("Enter artist: ").strip()
    album = input("Enter album title: ").strip()
    genre = input("Enter genre: ").strip()
    year = input("Enter release year: ").strip()
    format = input("Enter format (LP, 7\", CD, etc.): ").strip()
    notes = input("Enter any notes (optional): ").strip()

    record = {
        "artist": artist,
        "album": album,
        "genre": genre,
        "year": year,
        "format": format,
        "notes": notes
    }
    collection.append(record)
    print(f"Added '{album}' by {artist} to your collection.")

def view_collection(collection):
    """Displays the entire record collection."""
    if not collection:
        print("Your collection is empty.")
        return

    print("\n--- Your Record Collection ---")
    for i, record in enumerate(collection):
        print(f"{i+1}. Artist: {record['artist']}")
        print(f"   Album: {record['album']}")
        print(f"   Genre: {record['genre']}")
        print(f"   Year: {record['year']}")
        print(f"   Format: {record['format']}")
        if record['notes']:
            print(f"   Notes: {record['notes']}")
        print("-" * 20)

def search_collection(collection):
    """Searches the collection based on different criteria."""
    if not collection:
        print("Your collection is empty.")
        return

    print("\n--- Search Options ---")
    print("1. Search by Artist")
    print("2. Search by Album Title")
    print("3. Search by Genre")
    print("4. Search by Year")
    choice = input("Enter your choice: ").strip()

    results = []
    search_term = input("Enter your search term: ").strip().lower()

    if choice == '1':
        results = [record for record in collection if search_term in record['artist'].lower()]
    elif choice == '2':
        results = [record for record in collection if search_term in record['album'].lower()]
    elif choice == '3':
        results = [record for record in collection if search_term in record['genre'].lower()]
    elif choice == '4':
        results = [record for record in collection if search_term == record['year']]
    else:
        print("Invalid choice.")
        return

    if results:
        print("\n--- Search Results ---")
        for record in results:
            print(f"Artist: {record['artist']}")
            print(f"Album: {record['album']}")
            print(f"Genre: {record['genre']}")
            print(f"Year: {record['year']}")
            print(f"Format: {record['format']}")
            if record['notes']:
                print(f"Notes: {record['notes']}")
            print("-" * 20)
    else:
        print("No records found matching your search term.")

def edit_record(collection):
    """Edits an existing record in the collection."""
    if not collection:
        print("Your collection is empty.")
        return

    view_collection(collection)
    try:
        index_to_edit = int(input("Enter the number of the record you want to edit: ")) - 1
        if 0 <= index_to_edit < len(collection):
            record = collection[index_to_edit]
            print("\n--- Editing Record ---")
            for key, value in record.items():
                new_value = input(f"Enter new value for {key} (leave blank to keep '{value}'): ").strip()
                if new_value:
                    record[key] = new_value
            print("Record updated successfully!")
        else:
            print("Invalid record number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def delete_record(collection):
    """Deletes a record from the collection."""
    if not collection:
        print("Your collection is empty.")
        return

    view_collection(collection)
    try:
        index_to_delete = int(input("Enter the number of the record you want to delete: ")) - 1
        if 0 <= index_to_delete < len(collection):
            deleted_record = collection.pop(index_to_delete)
            print(f"Deleted '{deleted_record['album']}' by {deleted_record['artist']}.")
        else:
            print("Invalid record number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def sort_collection_by_artist(collection):
    """Sorts the record collection by artist name."""
    if not collection:
        print("Your collection is empty.")
        return
    # Use the sorted() function with a lambda function as the key.
    # The lambda function extracts the artist name for comparison.
    sorted_collection = sorted(collection, key=lambda record: record['artist'].lower())
    print("Collection sorted by artist name.")
    return sorted_collection

def generate_html_list(collection):
    """Generates an HTML list of the record collection."""
    if not collection:
        return "<p>Your collection is empty.</p>"

    html_list = "<ul>\n"
    for record in collection:
        html_list += f"  <li>\n"
        html_list += f"    <strong>Artist:</strong> {record['artist']}<br>\n"
        html_list += f"    <strong>Album:</strong> {record['album']}<br>\n"
        html_list += f"    <strong>Genre:</strong> {record['genre']}<br>\n"
        html_list += f"    <strong>Year:</strong> {record['year']}<br>\n"
        html_list += f"    <strong>Format:</strong> {record['format']}<br>\n"
        if record['notes']:
            html_list += f"    <strong>Notes:</strong> {record['notes']}<br>\n"
        html_list += f"  </li>\n"
    html_list += "</ul>\n"
    return html_list

def generate_html_file(collection):
    """Generates a complete HTML file of the record collection."""
    html_content = "<!DOCTYPE html>\n"
    html_content += "<html lang=\"en\">\n"
    html_content += "<head>\n"
    html_content += "    <meta charset=\"UTF-8\">\n"
    html_content += "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    html_content += "    <title>Record Collection</title>\n"
    # You can add some basic styling here or link to an external stylesheet
    html_content += "<style>\n"
    html_content += "body { font-family: sans-serif; }\n"
    html_content += "ul { list-style-type: none; padding: 0; }\n"
    html_content += "li { margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 10px; }\n"
    html_content += "strong { font-weight: bold; }\n"
    html_content += "</style>\n"
    html_content += "</head>\n"
    html_content += "<body>\n"
    html_content += "    <h1>My Record Collection</h1>\n"
    html_content += generate_html_list(collection)  # Use the existing function
    html_content += "</body>\n"
    html_content += "</html>\n"
    return html_content

def save_html_file(html_content):
    """Saves the HTML content to a file."""
    with open(HTML_FILE, "w") as f:
        f.write(html_content)
    print(f"HTML file saved to {HTML_FILE}")

def main():
    """Main function to run the record collection manager."""
    record_collection = load_collection()

    while True:
        print("\n--- Record Collection Manager ---")
        print("1. Add Record")
        print("2. View Collection")
        print("3. Search Collection")
        print("4. Edit Record")
        print("5. Delete Record")
        print("6. Sort Collection by Artist")
        print("7. Generate HTML File")
        print("8. Save and Exit")

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            add_record(record_collection)
        elif choice == '2':
            view_collection(record_collection)
        elif choice == '3':
            search_collection(record_collection)
        elif choice == '4':
            edit_record(record_collection)
        elif choice == '5':
            delete_record(record_collection)
        elif choice == '6':
            record_collection = sort_collection_by_artist(record_collection)
        elif choice == '7':
            html_output = generate_html_file(record_collection) # Generate full HTML
            save_html_file(html_output)
        elif choice == '8':
            save_collection(record_collection)
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

