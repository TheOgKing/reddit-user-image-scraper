# Reddit User Image Scraper

This script allows you to download and zip images from a Reddit user's submitted posts. It supports both single-user and multiple-user modes, and it saves checkpoints to resume downloading in case of interruptions.

## Features

- Fetches image URLs from a Reddit user's submissions (jpg, jpeg, png, gif).
- Supports multiple users and can resume downloads from where they left off after a shutdown.
- Saves cookies for Reddit login, allowing for a seamless login experience.
- Automatically zips downloaded images for easier storage.

## Requirements

Install the required Python packages using the following command:

  pip install -r requirements.txt

## Usage

1. Clone the repository or download the script.
2. Ensure you have Python installed on your machine.
3. nstall the required libraries using pip install -r requirements.txt.
4. Run the script using the following command

   python reddit_user_image_downloader.py


## Single User Mode

1. Select 1 when prompted to choose a mode.
2. Navigate to the Reddit user's profile page in the browser that opens.
3. Press ENTER to continue, and the script will automatically detect the user's profile.
4. Enter the number of images you want to download.
5. The script will download the images and zip them.

## Multiple Users Mode

1. Select 2 when prompted to choose a mode.
2. For each user, navigate to their Reddit profile page and press ENTER to add them to the queue.
3. Once you've added all users, the script will process each user and download the images.


## Checkpointing


If the script encounters an issue or is shut down, it will save the progress in a checkpoint.json file.
Upon restarting, it will ask if you want to continue from where you left off. If you choose to continue, the script will resume from the last downloaded image for each user.


## Cookies

The script stores login cookies in a file named reddit_cookies.pkl.
If the cookies expire or become invalid, the script will prompt you to log in again.
