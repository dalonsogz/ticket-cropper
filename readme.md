# Ticket Cropping App

A Python application for cropping tickets from scanned grayscale images. The app allows users to navigate through images, zoom, and scroll, with automatic detection of the ticket area for easy cropping. The cropped images can then be saved with a new name.

## Features

- **Image Navigation**: Easily browse through the images.
- **Zoom**: Zoom in and out of the images for better detail.
- **Auto-Detection**: The app automatically detects the area of the ticket for cropping.
- **Manual Selection**: Users can also manually select the area to crop.
- **Save Cropped Images**: Save the cropped ticket area with a new file name.
- **Exit**: Quick exit from the application.

## Requirements

- Python 3.x
- PyQt5
- OpenCV (for image processing)
- NumPy (for image manipulation)

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/ticket-cropping-app.git
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:

   ```bash
   python app.py
   ```

2. Navigate between images using the arrow keys or buttons.

3. Zoom in and out with the mouse scroll or the zoom buttons.

4. The app will attempt to auto-detect the ticket area for cropping, but you can also manually select the cropping area.

5. After selecting the desired area, click "Save" to save the cropped ticket image with a new name.

## Notes

- This app works best with grayscale images where the text is clear and contrast is sufficient for detection.
- Manual cropping may be required for images with poor auto-detection.

