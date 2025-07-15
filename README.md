# Reel_Generator

## Setup Instructions

### 1. Add Your Gemini API Key

- Open the `.env` file in the project root.
- Paste your Gemini API key as follows (replace with your actual key):

  ```
  GEMINI_API_KEY=your-gemini-api-key-here
  ```

### 2. Install Dependencies

- Make sure you have Python 3.8+ installed.
- Install all required packages using pip:

  ```sh
  pip install -r requirements.txt
  ```

### 3. Run the Flask Server

- Start the backend server with:

  ```sh
  python app.py
  ```

  The server will run on `http://localhost:5000`.

## API Usage

### Analyze a Video

- **Endpoint:** `POST /api/analyze`
- **Body:**  
  ```json
  {
    "video_url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
  }
  ```
- **Response:**  
  Returns video info, segments, and ranked segments.

### Generate Reels

- **Endpoint:** `POST /api/generate-reel`
- **Body:**  
  ```json
  {
    "video_url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
    "add_captions": true
  }
  ```
- **Response:**  
  Returns top 3 generated reels with download URLs.

### Download a Reel

- **Endpoint:** `GET /api/download/<reel_id>`
- **Response:**  
  Downloads the generated reel video.

### List All Reels

- **Endpoint:** `GET /api/list-reels`
- **Response:**  
  Lists all available reels in the output directory.

### Generate High-Quality Reel

- **Endpoint:** `POST /api/generate-reel-hq`
- **Body:**  
  ```json
  {
    "video_url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
    "segment": {
      "start_time": 10.0,
      "end_time": 40.0,
      "title": "Segment Title"
    },
    "add_captions": true,
    "quality_enhancements": {
      "stabilize": true,
      "enhance_colors": true,
      "auto_levels": true,
      "denoise": false,
      "sharpen": true
    }
  }
  ```
- **Response:**  
  Returns the enhanced reel and applied settings.

---

**Note:**  
- All output videos and reels are saved in the `output/` directory.
- Temporary files are stored in the `temp/` directory.
