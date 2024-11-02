import pyrebase
import os
from datetime import datetime
from .html_generator import generate_html

MAX_IMAGES = 4  # Maximum number of images to keep

def upload_images_and_generate_html():
    # Firebase configuration
    firebaseConfig = {
        "apiKey": "AIzaSyDRnj7oobx_i4e9nmlb4zAOIUfqYl4wZ7c",
        "authDomain": "black-box-image-push.firebaseapp.com",
        "projectId": "black-box-image-push",
        "storageBucket": "black-box-image-push.appspot.com",
        "messagingSenderId": "591859800194",
        "appId": "1:591859800194:web:f5c3ddb401da5e7e1bfc9b",
        "measurementId": "G-MJX0XYGH78",
        "databaseURL": "https://black-box-image-push-default-rtdb.asia-southeast1.firebasedatabase.app"
    }

    # Initialize Firebase
    firebase = pyrebase.initialize_app(firebaseConfig)
    storage = firebase.storage()
    db = firebase.database()

    # Path to your images
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_folder = os.path.join(current_dir, "image")

    # Loop through each customer's folder
    for customer_folder in os.listdir(image_folder):
        customer_path = os.path.join(image_folder, customer_folder)
        
        if os.path.isdir(customer_path):  # Check if it's a folder
            image_data = []

            # Check existing images from Firebase Database (if stored previously)
            existing_images = db.child("uploaded_images").child(customer_folder).get().val() or {}

            # Loop through images inside each customer folder
            for image_file in os.listdir(customer_path):
                if image_file.endswith(('.png', '.jpg', '.jpeg')):
                    local_image_path = os.path.join(customer_path, image_file)
                    storage_path = f"{customer_folder}/{image_file}"

                    # Replace invalid characters in the image file name for Firebase path
                    image_key = image_file.replace('.', '_')

                    # Check if the image is already uploaded by comparing local and Firebase metadata
                    local_image_ctime = os.path.getctime(local_image_path)
                    if image_key in existing_images and existing_images[image_key]['ctime'] == local_image_ctime:
                        print(f"{image_file} already exists in Firebase Storage, skipping upload.")
                        image_data.append((existing_images[image_key]['url'], existing_images[image_key]['uploaded_time'], image_key))
                    else:
                        # Upload the image
                        storage.child(storage_path).put(local_image_path)
                        print(f"Uploaded {image_file} to Firebase Storage for {customer_folder}")

                        # Get the image URL and creation time
                        image_url = storage.child(storage_path).get_url(None)
                        uploaded_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        # Store image info in the database
                        db.child("uploaded_images").child(customer_folder).child(image_key).set({
                            "url": image_url,
                            "ctime": local_image_ctime,
                            "uploaded_time": uploaded_time
                        })

                        image_data.append((image_url, uploaded_time, image_key))

            # # Ensure image_data contains only the last MAX_IMAGES images
            # if len(image_data) > MAX_IMAGES:
            #     # Sort by uploaded_time to get the oldest images
            #     image_data.sort(key=lambda x: x[1])  # Sort by uploaded time
            #     while len(image_data) > MAX_IMAGES:
            #         oldest_image = image_data.pop(0)  # Remove the oldest image from the list
            #         # Delete from Firebase
            #         db.child("uploaded_images").child(customer_folder).child(oldest_image[2]).remove()
            #         storage.delete(f"{customer_folder}/{oldest_image[2].replace('_', '.')}")
            #         # Delete from local storage
            #         local_image_to_delete = os.path.join(customer_path, oldest_image[2].replace('_', '.'))
            #         if os.path.exists(local_image_to_delete):
            #             os.remove(local_image_to_delete)
            #             print(f"Deleted old image {oldest_image[2]} from local storage and Firebase")

            # Generate HTML with updated image data (only the last MAX_IMAGES images)
            generate_html(customer_folder, image_data)

    print("Gallery HTML for all customers created.")
    
def main():    
    try:
        upload_images_and_generate_html() 
    except KeyboardInterrupt:
        print("Program stopped by user")

if __name__ == "__main__":
    main()
