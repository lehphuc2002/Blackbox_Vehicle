import os

def generate_html(customer_name, image_data):
    html_content = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Premium image gallery for {customer_name}">
        <title>{customer_name}'s Premium Gallery</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');
            
            :root {{
                --gradient-1: linear-gradient(135deg, #24C6DC, #514A9D);
                --gradient-2: linear-gradient(135deg, #fc466b, #3f5efb);
                --surface-1: #151C2C;
                --surface-2: #1E293B;
                --surface-3: #242F48;
                --text-primary: #FFFFFF;
                --text-secondary: #94A3B8;
                --accent: #60A5FA;
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Poppins', sans-serif;
                background: var(--surface-1);
                color: var(--text-primary);
                min-height: 100vh;
                line-height: 1.6;
                display: flex;
                flex-direction: column;
            }}

            .header {{
                position: relative;
                padding: 4rem 2rem;
                background: var(--surface-2);
                overflow: hidden;
            }}

            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: var(--gradient-1);
            }}

            h1 {{
                font-size: clamp(2.5em, 6vw, 4em);
                font-weight: 700;
                background: var(--gradient-2);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 1.5rem;
                text-align: center;
                letter-spacing: 2px;
            }}

            .gallery-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 2.5rem;
                padding: 4rem 2rem;
                max-width: 1600px;
                margin: 0 auto;
                width: 100%;
            }}

            .gallery-item {{
                position: relative;
                border-radius: 16px;
                overflow: hidden;
                background: var(--surface-3);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
            }}

            .gallery-item:hover {{
                transform: translateY(-8px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            }}

            .gallery-item img {{
                width: 100%;
                height: 300px;
                object-fit: cover;
                transition: transform 0.4s ease;
            }}

            .gallery-item:hover img {{
                transform: scale(1.05);
            }}

            .gallery-item .metadata {{
                padding: 1rem;
                background: rgba(0, 0, 0, 0.8);
                color: var(--text-secondary);
                position: absolute;
                bottom: 0;
                width: 100%;
                font-size: 0.9em;
                transform: translateY(100%);
                transition: transform 0.3s ease;
            }}

            .gallery-item:hover .metadata {{
                transform: translateY(0);
            }}

            .modal {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                z-index: 1000;
                overflow: auto;
                padding: 2rem;
            }}

            .modal-content {{
                max-width: 90%;
                max-height: 90vh;
                margin: auto;
                display: block;
                cursor: zoom-out;
            }}

            .modal-close {{
                position: fixed;
                top: 1rem;
                right: 1rem;
                color: var(--text-primary);
                font-size: 2rem;
                cursor: pointer;
                background: var(--surface-3);
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.3s ease;
            }}

            .modal-close:hover {{
                background: var(--surface-2);
            }}

            footer {{
                padding: 2rem;
                text-align: center;
                background: var(--surface-2);
                color: var(--text-secondary);
                margin-top: auto;
            }}

            .footer-logo {{
                font-weight: bold;
                background: var(--gradient-1);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            @media (max-width: 768px) {{
                .gallery-container {{
                    padding: 2rem 1rem;
                    gap: 1.5rem;
                }}

                .header {{
                    padding: 3rem 1rem;
                }}

                .modal {{
                    padding: 1rem;
                }}
            }}
        </style>
    </head>
    <body>
        <header class="header">
            <h1>{customer_name}'s Gallery</h1>
        </header>
        <div class="gallery-container">
'''

    # Loop through images and add them to the gallery
    for url, time, _ in image_data:
        html_content += f'''
            <div class="gallery-item" onclick="openModal('{url}')">
                <img src="{url}" alt="Gallery image" loading="lazy">
                <div class="metadata">
                    <p>Uploaded on: {time}</p>
                </div>
            </div>
'''
    
    # Add modal and close the HTML content
    html_content += '''
        </div>
        <div id="imageModal" class="modal" onclick="closeModal()">
            <span class="modal-close">&times;</span>
            <img class="modal-content" id="modalImage">
        </div>
        <footer>
            <p>Powered by <span class="footer-logo">Firebase Gallery</span></p>
        </footer>
        <script>
            function openModal(imageSrc) {
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImage');
                modal.style.display = 'flex';
                modalImg.src = imageSrc;
                document.body.style.overflow = 'hidden';
            }

            function closeModal() {
                const modal = document.getElementById('imageModal');
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }

            // Close modal with Escape key
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    closeModal();
                }
            });
        </script>
    </body>
    </html>
    '''

    # Define the path to save the HTML file in the public folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    public_folder_path = os.path.join(current_dir, "public", f"{customer_name}_gallery.html")

    # Save the HTML file
    with open(public_folder_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Gallery HTML for {customer_name} created. You can view it at 'public/{customer_name}_gallery.html'.")