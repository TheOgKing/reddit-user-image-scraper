import os
import time
import requests
import zipfile
import pickle
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

COOKIE_FILE = "reddit_cookies.pkl"
CHECKPOINT_FILE = "checkpoint.json"

# Function to fetch user posts from Reddit API
def fetch_user_posts(username):
    headers = {'User-Agent': 'Mozilla/5.0'}
    after = ''
    images = []
    
    while True:
        url = f'https://www.reddit.com/user/{username}/submitted.json?limit=100&after={after}'
        response = requests.get(url, headers=headers)
        data = response.json()
        posts = data['data']['children']
        
        if len(posts) == 0:
            break
        
        for post in posts:
            post_data = post['data']
            image_url = post_data['url']
            if image_url.endswith(('jpg', 'jpeg', 'png', 'gif')):
                images.append(image_url)
        
        after = data['data']['after']
        if not after:
            break
    
    return images

# Download images and zip them, with progress display and checkpointing
def download_images(images, folder_name, start_index, num_to_download, checkpoint_data):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    
    total_images = len(images)
    print(f"Found {total_images} images. Downloading {num_to_download} images...")

    for i in range(start_index, start_index + num_to_download):
        image_url = images[i]
        img_data = requests.get(image_url).content
        filename = os.path.join(folder_name, f'image_{i+1}.{image_url.split(".")[-1]}')
        with open(filename, 'wb') as handler:
            handler.write(img_data)

        # Update checkpoint data after each image download
        if checkpoint_data is not None:
            checkpoint_data['current_image_index'] = i + 1
            save_checkpoint(checkpoint_data)

        # Display download progress
        print(f'Downloading {i+1}/{num_to_download} images', end='\r')

    # Create ZIP file
    zip_filename = f'{folder_name}.zip'
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for foldername, subfolders, filenames in os.walk(folder_name):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zipf.write(file_path, os.path.basename(file_path))
    
    print(f"\nDownloaded and zipped {num_to_download} images to {zip_filename}")

# Function to save cookies after logging in
def save_cookies(driver, filepath):
    with open(filepath, 'wb') as file:
        pickle.dump(driver.get_cookies(), file)

# Function to load cookies into the browser
def load_cookies(driver, filepath):
    with open(filepath, 'rb') as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)

# Function to save checkpoint data
def save_checkpoint(data):
    with open(CHECKPOINT_FILE, 'w') as file:
        json.dump(data, file)

# Function to load checkpoint data
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as file:
            return json.load(file)
    return None

# Function to clear checkpoint data
def clear_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

# Process images for a specific Reddit user
def process_user(driver, reddit_username, checkpoint_data=None):
    print(f"Fetching images for u/{reddit_username}...")
    images = fetch_user_posts(reddit_username)

    if images:
        total_images = len(images)
        if checkpoint_data:
            start_index = checkpoint_data.get('current_image_index', 0)
            print(f"Resuming from image {start_index+1}/{total_images}...")
        else:
            start_index = 0
            print(f"Total {total_images} images found.")
        
        num_to_download = int(input(f"How many images do you want to download (max {total_images - start_index})? "))
        num_to_download = min(num_to_download, total_images - start_index)  # Ensure user doesn't download more than available

        # If in multiple mode, make sure we are saving the correct checkpoint
        if checkpoint_data and checkpoint_data.get('mode') == 'multiple':
            checkpoint_data['current_user'] = reddit_username
            checkpoint_data['current_image_index'] = start_index
        else:
            # For single user mode
            checkpoint_data = {
                'mode': 'single',
                'current_user': reddit_username,
                'current_image_index': start_index
            }

        # Download images and zip them in a folder
        download_images(images, reddit_username, start_index, num_to_download, checkpoint_data)

        # If in single mode, clear checkpoint after successful download
        if checkpoint_data['mode'] == 'single':
            clear_checkpoint()
    else:
        print(f"No images found for u/{reddit_username}.")

# Handle processing multiple users with correct checkpointing
def continue_multiple_users(driver, users_queue, current_user, checkpoint_data):
    # Process the current user if any
    if current_user:
        print(f"Resuming with user: u/{current_user}")
        process_user(driver, current_user, checkpoint_data)

        # Clear current_user after processing
        current_user = None
        checkpoint_data['current_user'] = None
        checkpoint_data['current_image_index'] = 0

    # Continue with the remaining users in the queue
    while users_queue:
        current_user = users_queue.pop(0)
        print(f"Processing user: u/{current_user}")
        checkpoint_data['current_user'] = current_user
        process_user(driver, current_user, checkpoint_data)

        # Reset image index for the next user
        checkpoint_data['current_image_index'] = 0
        checkpoint_data['users_queue'] = users_queue

        save_checkpoint(checkpoint_data)

    # Clear the checkpoint after all users are processed
    clear_checkpoint()

# Main function to handle login and scraping
def main():
    # Load checkpoint if exists
    checkpoint_data = load_checkpoint()
    if checkpoint_data:
        resume = input("Script did not end correctly last time. Continue from where it left off? (1 = Yes, 2 = No): ")
        if resume == '1':
            mode = checkpoint_data.get('mode')
            if mode == 'single':
                reddit_username = checkpoint_data.get('current_user')
                if reddit_username:
                    process_user(None, reddit_username, checkpoint_data)
                else:
                    print("Error: No user found in checkpoint data.")
                return
            elif mode == 'multiple':
                users_queue = checkpoint_data.get('users_queue', [])
                current_user = checkpoint_data.get('current_user')
                continue_multiple_users(None, users_queue, current_user, checkpoint_data)
                return
        else:
            clear_checkpoint()

    # Set up Selenium (Chromium WebDriver)
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Check if cookies file exists
    if os.path.exists(COOKIE_FILE):
        # Open Reddit and load cookies
        driver.get("https://www.reddit.com")
        time.sleep(2)  # Wait for page to load
        load_cookies(driver, COOKIE_FILE)
        driver.refresh()  # Refresh the page to apply cookies
        time.sleep(5)  # Wait for the page to reload after applying cookies

        # Check if login was successful
        if "login" in driver.current_url:
            print("Cookies have expired or login is required. Please log in again.")
            driver.get("https://www.reddit.com/login")
            input("Log in manually and press Enter after completing login...")  # Manual login prompt
            save_cookies(driver, COOKIE_FILE)  # Save the cookies after manual login
        else:
            print("Logged in using saved cookies.")
    else:
        # Perform manual login and save cookies
        driver.get("https://www.reddit.com/login")
        input("Log in manually and press Enter after completing login...")
        save_cookies(driver, COOKIE_FILE)

    # Choose between single user and multiple users
    mode = input("Enter '1' for single user or '2' for multiple users: ")

    if mode == '1':
        # Single user mode
        input("Navigate to the user's profile page and press ENTER to continue...")

        # Extract the username from the URL
        current_url = driver.current_url
        if "/user/" not in current_url:
            print("Error: Please navigate to a Reddit user's profile page.")
        else:
            reddit_username = current_url.split("/user/")[1].split("/")[0]
            print(f"Detected Reddit user: {reddit_username}")
            process_user(driver, reddit_username)

    elif mode == '2':
        # Multiple user mode (queue)
        users_queue = []
        while True:
            input("Navigate to a user's profile page and press ENTER to add them to the queue...")

            # Extract the username from the URL
            current_url = driver.current_url
            if "/user/" not in current_url:
                print("Error: Please navigate to a Reddit user's profile page.")
                continue

            reddit_username = current_url.split("/user/")[1].split("/")[0]
            print(f"Added u/{reddit_username} to the queue.")
            users_queue.append(reddit_username)

            more_users = input("Add another user? (y/n): ")
            if more_users.lower() != 'y':
                break

        # Save initial checkpoint for multiple user mode
        checkpoint_data = {
            'mode': 'multiple',
            'users_queue': users_queue,
            'current_user': None,
            'current_image_index': 0
        }
        save_checkpoint(checkpoint_data)

        continue_multiple_users(driver, users_queue, None, checkpoint_data)

    # Close the driver
    driver.quit()

if __name__ == "__main__":
    main()
