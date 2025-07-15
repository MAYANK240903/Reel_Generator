from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import re

class TranscriptExtractor:
    def __init__(self):
        print("TranscriptExtractor initialized.")

    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        print(f"Extracting video ID from URL: {url}")
        # Handle various YouTube URL formats
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                print(f"Found video ID: {match.group(1)}")
                return match.group(1)
        print("No video ID found.")
        return None

    def get_transcript(self, video_url):
        """Get transcript with timestamps"""
        print(f"Getting transcript for video URL: {video_url}")
        try:
            video_id = self.extract_video_id(video_url)
            if not video_id:
                print("Invalid YouTube URL for transcript.")
                return None, "Invalid YouTube URL"
            
            # Get transcript list
            print(f"Fetching transcript list for video ID: {video_id}")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get English transcript first
            transcript = None
            try:
                print("Trying to find English transcript...")
                transcript = transcript_list.find_transcript(['en'])
            except Exception as e:
                print(f"English transcript not found: {e}")
                try:
                    # Try auto-generated English
                    print("Trying to find auto-generated English transcript...")
                    transcript = transcript_list.find_generated_transcript(['en'])
                except Exception as e:
                    print(f"Auto-generated English transcript not found: {e}")
                    # Get first available transcript
                    try:
                        print("Trying to get first available transcript...")
                        transcript = next(iter(transcript_list))
                    except Exception as e:
                        print(f"No transcript available: {e}")
                        return None, "No transcript available"
            
            # Fetch the transcript data
            print("Fetching transcript data...")
            transcript_data = transcript.fetch()
            print(f"Fetched {len(transcript_data)} transcript entries.")

            # Convert to list of dictionaries if needed
            formatted_data = []
            for entry in transcript_data:
                if hasattr(entry, '__dict__'):
                    # It's an object, convert to dict
                    formatted_data.append({
                        'text': entry.text,
                        'start': entry.start,
                        'duration': entry.duration
                    })
                else:
                    # It's already a dict
                    formatted_data.append(entry)
            print(f"Formatted transcript data with {len(formatted_data)} entries.")
            return formatted_data, None
            
        except Exception as e:
            print(f"Transcript error: {str(e)}")
            return None, f"Transcript error: {str(e)}"

    def get_video_info(self, video_url):
        """Get video metadata"""
        try:
            print(f"Attempting to fetch video info for URL: {video_url}")
            
            # Extract video ID first
            video_id = self.extract_video_id(video_url)
            if not video_id:
                print("Invalid YouTube URL for video info.")
                return {
                    'title': "Invalid YouTube URL",
                    'duration': 0,
                    'author': "Unknown",
                    'description': "Could not parse YouTube URL",
                    'thumbnail_url': "",
                    'views': 0,
                    'rating': 0,
                    'error': "Invalid URL format"
                }
            
            # For now, let's use basic info since pytube is having issues
            # We'll construct minimal info from the video ID
            print(f"Returning basic video info for video ID: {video_id}")
            return {
                'title': f"YouTube Video {video_id}",
                'duration': 0,  # Will be determined when downloading
                'author': "YouTube Creator",
                'description': "Video from YouTube",
                'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'views': 0,
                'rating': 0,
                'video_id': video_id,
                'url': video_url
            }
            
        except Exception as e:
            print(f"Error in get_video_info: {str(e)}")
            return {
                'title': "Video Title Unavailable",
                'duration': 0,
                'author': "Unknown",
                'description': "Error fetching video info",
                'thumbnail_url': "",
                'views': 0,
                'rating': 0,
                'error': str(e)
            }