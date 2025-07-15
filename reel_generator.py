# import google.generativeai as genai
import json
import config
from google import genai

print("Initializing Gemini client...")
client = genai.Client(api_key="AIzaSyBpaR4xZuEqNNk0K6hkud2OQW8usHkUe14")

class ReelGenerator:
    # def __init__(self):
        # genai.configure(api_key=config.GEMINI_API_KEY)
        # self.model = genai.GenerativeModel('gemini-pro')
    
    def analyze_transcript(self, transcript_data, video_info):
        """Analyze transcript and identify interesting segments"""
        print("Analyzing transcript...")
        # Prepare transcript text with timestamps
        transcript_text = ""
        for entry in transcript_data:
            transcript_text += f"[{entry['start']:.1f}s] {entry['text']}\n"
        print(f"Transcript text prepared: {transcript_text[:200]}...")  # Print first 200 chars
        
        prompt = f"""
        Analyze this video transcript and identify the most interesting, engaging, and viral-worthy segments for creating short reels.
        
        Video Title: {video_info['title']}
        Video Author: {video_info['author']}
        
        Transcript:
        {transcript_text}
        
        Please identify 5 best segments that would make great 30-second reels. For each segment:
        1. Provide the start and end timestamp
        2. Explain why this segment is interesting
        3. Suggest a catchy title for the reel
        4. Provide engaging caption text
        5. Suggest relevant keywords, add spaces whenever there is a combination of two, generate comma sperated list
        
        Return the response in JSON format:
        {{
            "segments": [
                {{
                    "start_time": float,
                    "end_time": float,
                    "reason": "string",
                    "title": "string",
                    "caption": "string",
                    "hashtags": ["string"]
                }}
            ]
        }}
        """
        
        try:
            print("Sending prompt to Gemini for segment analysis...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
            )   
            print("Received response from Gemini.")
            # response = self.model.generate_content(prompt)
            
            # Parse JSON from response
            json_str = response.text
            print(f"Raw response text: {json_str[:200]}...")  # Print first 200 chars
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            print(f"Extracted JSON string: {json_str[:200]}...")  # Print first 200 chars
            
            segments = json.loads(json_str)
            print(f"Parsed segments: {segments}")
            return segments['segments'], None
            
        except Exception as e:
            print(f"Error in analyze_transcript: {e}")
            return None, str(e)
    
    def generate_captions(self, transcript_segment):
        """Generate stylized captions for a segment"""
        print("Generating captions...")
        print(f"Transcript segment: {transcript_segment}")
        prompt = f"""
        Create short, punchy captions for this video segment that will appear on screen.
        Make them engaging and easy to read on mobile devices.
        
        Transcript segment:
        {transcript_segment}
        
        Rules:
        - Each caption should be 1-3 words maximum
        - Use emphasis (capitals) for important words
        - Make it engaging and dynamic
        
        Return as JSON:
        {{
            "captions": [
                {{
                    "text": "string",
                    "start": float,
                    "end": float
                }}
            ]
        }}
        """
        
        try:
            print("Sending prompt to Gemini for caption generation...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
            ) 
            print("Received response from Gemini for captions.")
            json_str = response.text
            print(f"Raw response text: {json_str[:200]}...")  # Print first 200 chars
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            print(f"Extracted JSON string: {json_str[:200]}...")  # Print first 200 chars
            
            captions = json.loads(json_str)
            print(f"Parsed captions: {captions}")
            return captions['captions'], None
            
        except Exception as e:
            print(f"Error in generate_captions: {e}")
            return None, str(e)
    
    def enhance_reel_idea(self, segment_info, style_preferences):
        """Enhance reel with AI suggestions based on style preferences"""
        print("Enhancing reel idea...")
        print(f"Segment info: {segment_info}")
        print(f"Style preferences: {style_preferences}")
        prompt = f"""
        Enhance this reel concept based on the following style preferences:
        
        Original segment: {segment_info}
        Style preferences: {style_preferences}
        
        Provide enhanced suggestions for:
        1. Visual effects to add
        2. Music/sound suggestions
        3. Transition ideas
        4. Color grading style
        5. Text animation style
        
        Return as JSON:
        {{
            "enhancements": {{
                "visual_effects": ["string"],
                "music_mood": "string",
                "transitions": ["string"],
                "color_style": "string",
                "text_animation": "string"
            }}
        }}
        """
        
        try:
            print("Sending prompt to Gemini for enhancement suggestions...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
            )
            print("Received response from Gemini for enhancements.")
            json_str = response.text
            print(f"Raw response text: {json_str[:200]}...")  # Print first 200 chars
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            print(f"Extracted JSON string: {json_str[:200]}...")  # Print first 200 chars
            
            enhancements = json.loads(json_str)
            print(f"Parsed enhancements: {enhancements}")
            return enhancements, None
            
        except Exception as e:
            print(f"Error in enhance_reel_idea: {e}")
            return None, str(e)