import os
from datetime import datetime

def generate_html(customer_name, image_data):
    customer_name_on_web = customer_name.replace("_", " ").title()
    current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    html_content = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Professional Vehicle Monitoring System - {customer_name}">
        <title>Vehicle Monitoring - {customer_name}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            
            :root {{
                --primary-color: #1a56db;
                --secondary-color: #1e429f;
                --background: #f3f4f6;
                --surface-1: #ffffff;
                --surface-2: #f8fafc;
                --header-bg: #1e3a8a;
                --text-primary: #1f2937;
                --text-secondary: #4b5563;
                --text-light: #ffffff;
                --border-color: #e5e7eb;
                --accent: #3b82f6;
                --warning: #dc2626;
                --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Roboto', sans-serif;
                background: var(--background);
                color: var(--text-primary);
                line-height: 1.5;
                display: flex;
                flex-direction: column;
                min-height: 100vh;
            }}

            .header {{
                background: var(--header-bg);
                color: var(--text-light);
                padding: 1.5rem 2rem;
                box-shadow: var(--shadow-md);
            }}

            .header-content {{
                max-width: 1400px;
                margin: 0 auto;
            }}

            .dashboard-info {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                flex-wrap: wrap;
                gap: 1rem;
            }}

            .dashboard-title {{
                flex: 1;
            }}

            .dashboard-meta {{
                text-align: right;
                font-size: 0.875rem;
                color: #93c5fd;
            }}

            h1 {{
                font-size: 1.75rem;
                font-weight: 500;
                margin-bottom: 0.5rem;
            }}

            .subtitle {{
                color: #93c5fd;
                font-size: 1rem;
                font-weight: 400;
            }}

            .main-content {{
                max-width: 1400px;
                margin: 2rem auto;
                padding: 0 2rem;
            }}

            .stats-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}

            .stat-card {{
                background: var(--surface-1);
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: var(--shadow-sm);
                border: 1px solid var(--border-color);
            }}

            .stat-title {{
                color: var(--text-secondary);
                font-size: 0.875rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            .stat-value {{
                font-size: 1.5rem;
                font-weight: 500;
                color: var(--primary-color);
                margin-top: 0.5rem;
            }}

            .gallery-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 1.5rem;
            }}

            .gallery-item {{
                background: var(--surface-1);
                border-radius: 8px;
                overflow: hidden;
                box-shadow: var(--shadow-sm);
                border: 1px solid var(--border-color);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}

            .gallery-item:hover {{
                transform: translateY(-2px);
                box-shadow: var(--shadow-md);
            }}

            .image-container {{
                position: relative;
                padding-top: 66.67%; /* 3:2 aspect ratio */
            }}

            .gallery-item img {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }}

            .metadata {{
                padding: 1rem;
                background: var(--surface-2);
                border-top: 1px solid var(--border-color);
            }}

            .metadata-time {{
                color: var(--text-secondary);
                font-size: 0.875rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .speed-tag {{
                background: var(--warning);
                color: white;
                padding: 0.25rem 0.75rem;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 500;
            }}

            .modal {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.85);
                z-index: 1000;
                padding: 2rem;
            }}

            .modal-content {{
                max-width: 90%;
                max-height: 90vh;
                margin: auto;
                display: block;
                border-radius: 4px;
            }}

            .modal-close {{
                position: fixed;
                top: 1.5rem;
                right: 1.5rem;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 1.5rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: background-color 0.2s ease;
            }}

            .modal-close:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}

            footer {{
                margin-top: auto;
                padding: 1.5rem;
                background: var(--surface-1);
                border-top: 1px solid var(--border-color);
                text-align: center;
                color: var(--text-secondary);
            }}

            .footer-content {{
                max-width: 1400px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 1rem;
            }}

            .footer-logo {{
                font-weight: 500;
                color: var(--primary-color);
            }}

            @media (max-width: 768px) {{
                .header {{
                    padding: 1rem;
                }}

                .main-content {{
                    padding: 0 1rem;
                    margin: 1rem auto;
                }}

                .dashboard-info {{
                    flex-direction: column;
                    align-items: flex-start;
                }}

                .dashboard-meta {{
                    text-align: left;
                }}

                .gallery-container {{
                    gap: 1rem;
                }}

                .modal {{
                    padding: 1rem;
                }}
            }}
        </style>
    </head>
    <body>
        <header class="header">
            <div class="header-content">
                <div class="dashboard-info">
                    <div class="dashboard-title">
                        <h1>Vehicle Speed Monitoring System</h1>
                        <p class="subtitle">Monitoring Report for {customer_name_on_web}</p>
                    </div>
                    <div class="dashboard-meta">
                        <div>Report Generated: {current_date}</div>
                        <div>System ID: VMS-{hash(customer_name)%1000:03d}</div>
                    </div>
                </div>
            </div>
        </header>

        <main class="main-content">
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-title">Total Violations</div>
                    <div class="stat-value">{len(image_data)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Latest Detection</div>
                    <div class="stat-value">{image_data[-1][1] if image_data else 'N/A'}</div>
                </div>
            </div>

            <div class="gallery-container">
'''

    # Loop through images and add them to the gallery
    for url, time, _ in image_data:
        html_content += f'''
            <article class="gallery-item" onclick="openModal('{url}')">
                <div class="image-container">
                    <img src="{url}" alt="Speed violation capture" loading="lazy">
                </div>
                <div class="metadata">
                    <div class="metadata-time">
                        <span>{time}</span>
                        <span class="speed-tag">Speed Violation</span>
                    </div>
                </div>
            </article>
'''
    
    # Add modal and close the HTML content
    html_content += '''
            </div>
        </main>

        <div id="imageModal" class="modal" onclick="closeModal()">
            <button class="modal-close" aria-label="Close modal">&times;</button>
            <img class="modal-content" id="modalImage" alt="Enlarged capture">
        </div>

        <footer>
            <div class="footer-content">
                <div>
                    <span class="footer-logo">Advanced Traffic Management System</span>
                </div>
                <div>
                    Powered by Vehicle Monitoring Technologies
                </div>
            </div>
        </footer>

        <script>
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');

            function openModal(imageSrc) {
                modal.style.display = 'flex';
                modalImg.src = imageSrc;
                document.body.style.overflow = 'hidden';
            }

            function closeModal() {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }

            // Close modal with Escape key
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape') closeModal();
            });

            // Close modal when clicking outside the image
            modal.addEventListener('click', e => {
                if (e.target === modal) closeModal();
            });

            // Prevent modal close when clicking on the image

            modalImg.addEventListener('click', e => {
                    e.stopPropagation();
            });

            // Lazy loading for gallery images
            document.addEventListener('DOMContentLoaded', () => {
                const lazyImages = document.querySelectorAll('img[loading="lazy"]');
                
                if ('IntersectionObserver' in window) {
                    const imageObserver = new IntersectionObserver((entries, observer) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                const img = entry.target;
                                img.src = img.src; // Trigger load
                                observer.unobserve(img);
                            }
                        });
                    });

                    lazyImages.forEach(img => imageObserver.observe(img));
                }

                // Add animation to stats
                const statValues = document.querySelectorAll('.stat-value');
                statValues.forEach(stat => {
                    stat.style.opacity = '0';
                    stat.style.transform = 'translateY(10px)';
                    
                    setTimeout(() => {
                        stat.style.transition = 'all 0.5s ease';
                        stat.style.opacity = '1';
                        stat.style.transform = 'translateY(0)';
                    }, 100);
                });
            });

            // Add smooth scroll behavior
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });

            // Handle window resize for responsive modal
            window.addEventListener('resize', () => {
                if (modal.style.display === 'flex') {
                    const viewportHeight = window.innerHeight;
                    const imageHeight = modalImg.offsetHeight;
                    
                    if (imageHeight > viewportHeight * 0.9) {
                        modalImg.style.height = '90vh';
                        modalImg.style.width = 'auto';
                    } else {
                        modalImg.style.height = 'auto';
                        modalImg.style.width = '90%';
                    }
                }
            });
        </script>
    </body>
    </html>
    '''
    # Define the path to save the HTML file in the public folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    public_folder_path = os.path.join(current_dir, "public", f"{customer_name}_monitoring.html")

    # Save the HTML file
    with open(public_folder_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Monitoring dashboard for {customer_name} created at 'public/{customer_name}_monitoring.html'")