import pyrebase
import os
from datetime import datetime
from html_generator import generate_html

MAX_IMAGES = 4  # Maximum number of images to keep

def delete_image(storage, db, customer_folder, image_info, local_folder_path):
    """Helper function to delete images from both Firebase and local storage"""
    try:
        # Delete from Firebase Storage
        storage.delete(f"{customer_folder}/{image_info['key'].replace('_', '.')}")
        
        # Delete from Firebase Database
        db.child("uploaded_images").child(customer_folder).child(image_info['key']).remove()
        
        # Delete from local storage
        local_image_path = os.path.join(local_folder_path, image_info['key'].replace('_', '.'))
        if os.path.exists(local_image_path):
            os.remove(local_image_path)
            print(f"Deleted {image_info['key'].replace('_', '.')} from local storage and Firebase")
        else:
            print(f"Local file {image_info['key'].replace('_', '.')} not found")
            
    except Exception as e:
        print(f"Error deleting {image_info['key']}: {str(e)}")

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

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_folder = os.path.join(current_dir, "image")

    for customer_folder in os.listdir(image_folder):
        customer_path = os.path.join(image_folder, customer_folder)
        
        if os.path.isdir(customer_path):
            # Get existing images from Firebase
            existing_images = db.child("uploaded_images").child(customer_folder).get().val() or {}
            
            # Convert existing images to list for sorting
            existing_image_list = []
            for key, value in existing_images.items():
                existing_image_list.append({
                    'key': key,
                    'url': value['url'],
                    'ctime': value['ctime'],
                    'uploaded_time': value['uploaded_time']
                })
            
            # Sort existing images by upload time
            existing_image_list.sort(key=lambda x: x['uploaded_time'])

            # Get new images to upload
            new_images = []
            for image_file in os.listdir(customer_path):
                if image_file.endswith(('.png', '.jpg', '.jpeg')):
                    local_image_path = os.path.join(customer_path, image_file)
                    image_key = image_file.replace('.', '_')
                    local_image_ctime = os.path.getctime(local_image_path)
                    
                    # Check if image is new
                    if image_key not in existing_images or existing_images[image_key]['ctime'] != local_image_ctime:
                        new_images.append((local_image_path, image_file, image_key, local_image_ctime))

            # Calculate how many old images to remove
            total_images = len(existing_image_list) + len(new_images)
            images_to_remove = max(0, total_images - MAX_IMAGES)

            # Remove oldest images if needed
            for i in range(images_to_remove):
                if existing_image_list:
                    oldest_image = existing_image_list.pop(0)
                    delete_image(storage, db, customer_folder, oldest_image, customer_path)

            # Upload new images
            image_data = []
            for local_path, image_file, image_key, local_ctime in new_images:
                storage_path = f"{customer_folder}/{image_file}"
                
                # Upload the image
                storage.child(storage_path).put(local_path)
                print(f"Uploaded {image_file} to Firebase Storage for {customer_folder}")

                # Get the image URL
                image_url = storage.child(storage_path).get_url(None)
                uploaded_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Store in Firebase Database
                db.child("uploaded_images").child(customer_folder).child(image_key).set({
                    "url": image_url,
                    "ctime": local_ctime,
                    "uploaded_time": uploaded_time
                })

                image_data.append((image_url, uploaded_time, image_key))

                # Delete local image after successful upload if total images exceed MAX_IMAGES
                if len(existing_image_list) + len(image_data) > MAX_IMAGES:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        print(f"Deleted {image_file} from local storage after upload")

            # Add remaining existing images to image_data
            for img in existing_image_list:
                image_data.append((img['url'], img['uploaded_time'], img['key']))

            # Sort final image data by upload time
            image_data.sort(key=lambda x: x[1])
            
            # Generate HTML with updated image data
            generate_html(customer_folder, image_data)

            # Clean up any excess local images
            local_images = [f for f in os.listdir(customer_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
            if len(local_images) > MAX_IMAGES:
                local_images.sort(key=lambda x: os.path.getctime(os.path.join(customer_path, x)))
                for old_image in local_images[:-MAX_IMAGES]:
                    old_image_path = os.path.join(customer_path, old_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                        print(f"Cleaned up excess local image: {old_image}")

    print("Gallery HTML for all customers created.")
    
def main():    
    try:
        upload_images_and_generate_html() 
    except KeyboardInterrupt:
        print("Program stopped by user")

if __name__ == "__main__":
    main()