from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
from transcript_extractor import TranscriptExtractor
from video_processor import VideoProcessor
from reel_generator import ReelGenerator
import config
from algo import rank_timestamps

app = Flask(__name__)
CORS(app)

# Initialize components

print("Initializing TranscriptExtractor...")
transcript_extractor = TranscriptExtractor()
print("Initializing VideoProcessor...")
video_processor = VideoProcessor()
print("Initializing ReelGenerator...")
reel_generator = ReelGenerator()

# ...existing code...

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    """Analyze video and suggest reel segments"""
    try:
        print("Received request for /api/analyze")
        data = request.json
        print(f"Request data: {data}")
        video_url = data.get('video_url')
        
        if not video_url:
            print("No video URL provided")
            return jsonify({'error': 'No video URL provided'}), 400
        
        # Get video info
        print(f"Fetching video info for URL: {video_url}")
        video_info = transcript_extractor.get_video_info(video_url)
        if not video_info:
            print("Could not fetch video info")
            return jsonify({'error': 'Could not fetch video info'}), 400
        
        # Check if there was an error but we still got some info
        if 'error' in video_info:
            print(f"Warning: Video info fetch had issues: {video_info['error']}")
        
        # Get transcript
        print("Extracting transcript...")
        transcript_data, error = transcript_extractor.get_transcript(video_url)
        if error:
            print(f"Transcript error: {error}")
            return jsonify({'error': f'Transcript error: {error}'}), 400
        
        # If we have no transcript data, we can't analyze
        if not transcript_data:
            print("No transcript available for this video")
            return jsonify({'error': 'No transcript available for this video'}), 400
        
        # Analyze with AI
        print("Analyzing transcript with AI...")
        segments, error = reel_generator.analyze_transcript(transcript_data, video_info)
        if error:
            print(f"AI analysis error: {error}")
        print(f"Segments: {segments}")
        ranked_segments = rank_timestamps(segments)
        print(f"Ranked segments: {ranked_segments}")

        return jsonify({
            'video_info': video_info,
            'segments': segments,
            'ranked_segments': ranked_segments
        })
        
    except Exception as e:
        print(f"Error in analyze_video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ...existing code...
# Add this endpoint to your app.py for testing
@app.route('/api/list-reels', methods=['GET'])
def list_reels():
    """List all available reels (for debugging)"""
    try:
        print("Listing all reels in output directory...")
        reel_files = os.listdir(config.OUTPUT_DIR)
        reels = []
        
        for file in reel_files:
            if file.endswith('.mp4'):
                # Extract reel_id from filename
                if 'reel_' in file:
                    reel_id = file.replace('reel_', '').replace('.mp4', '').replace('final_', '')
                    reels.append({
                        'filename': file,
                        'reel_id': reel_id,
                        'size': os.path.getsize(os.path.join(config.OUTPUT_DIR, file)) / (1024 * 1024),  # Size in MB
                    })
        
        print(f"Found {len(reels)} reels.")
        return jsonify({
            'reels': reels,
            'count': len(reels)
        })
        
    except Exception as e:
        print(f"Error in list_reels: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-reel', methods=['POST'])
def generate_reel():
    """Generate top 3 reels from video using ranked segments"""
    try:
        print("Received request for /api/generate-reel")
        data = request.json
        print(f"Request data: {data}")
        video_url = data.get('video_url')
        add_captions = data.get('add_captions', True)

        if not video_url:
            print("Missing video_url")
            return jsonify({'error': 'Missing video_url'}), 400

        # 1. Download video
        print(f"Downloading video from URL: {video_url}")
        video_path, error = video_processor.download_video(video_url)
        if error:
            print(f"Download error: {error}")
            return jsonify({'error': f'Download error: {error}'}), 400
        

        # 2. Extract transcript
        print("Extracting transcript...")
        transcript_data, error = transcript_extractor.get_transcript(video_url)
        if error or not transcript_data:
            print(f"Transcript error: {error or 'No transcript'}")
            return jsonify({'error': f'Transcript error: {error or 'No transcript'}'}), 400

        # 3. Get video info
        print("Fetching video info...")
        video_info = transcript_extractor.get_video_info(video_url)
        if not video_info:
            print("Could not fetch video info")
            return jsonify({'error': 'Could not fetch video info'}), 400

        # 4. Analyze segments
        print("Analyzing transcript with AI...")
        segments, error = reel_generator.analyze_transcript(transcript_data, video_info)
        if error or not segments:
            print(f"AI analysis error: {error or 'No segments'}")
            return jsonify({'error': f'AI analysis error: {error or 'No segments'}'}), 400

        # 5. Rank segments
        print("Ranking segments...")
        ranked_segments = rank_timestamps(segments)
        print(f"Ranked segments: {ranked_segments}")
        top_segments = ranked_segments[:1]

        output_reels = []
        for idx, segment in enumerate(top_segments):
            print(f"Processing segment {idx+1}: {segment}")
            reel_id = str(uuid.uuid4())
            reel_filename = f'reel_{reel_id}.mp4'

            # 6. Clip video for this segment
            print(f"Extracting clip for segment {idx+1}...")
            clip_path, error = video_processor.extract_clip(
                video_path,
                segment['start_time'],
                segment['end_time'],
                reel_filename
            )
            if error:
                print(f"Clip extraction error: {error}")
                output_reels.append({
                    'error': f'Clip extraction error: {error}',
                    'segment': segment
                })
                continue

            # 7. Optionally add captions
            caption_debug_info = {
                'captions_requested': add_captions,
                'captions_generated': False,
                'captions_added': False,
                'caption_count': 0,
                'errors': []
            }
            if add_captions:
                print(f"Generating captions for segment {idx+1}...")
                # Filter transcript for this segment
                segment_transcript = [
                    entry for entry in transcript_data
                    if segment['start_time'] <= entry['start'] <= segment['end_time']
                ]
                if segment_transcript:
                    captions = video_processor.transcript_to_captions(segment_transcript)
                    if error:
                        print(f"Caption generation error: {error}")
                        caption_debug_info['errors'].append(f"Caption generation error: {error}")
                    elif not captions:
                        print("No captions generated")
                        caption_debug_info['errors'].append("No captions generated")
                    else:
                        print(f"Generated {len(captions)} captions.")
                        caption_debug_info['captions_generated'] = True
                        caption_debug_info['caption_count'] = len(captions)
                        # Adjust timings
                        for caption in captions:
                            caption['start'] -= segment['start_time']
                            caption['end'] -= segment['start_time']
                        for i in range(len(captions) - 1):
                            captions[i]['end'] = min(captions[i]['end'], captions[i+1]['start'] - 0.05)
                            if captions[i]['end'] <= captions[i]['start']:
                                captions[i]['end'] = captions[i]['start'] + 0.1
                        # Add captions to video
                        print("Adding captions to video...")
                        final_path, error = video_processor.add_captions(
                            clip_path,
                            captions,
                            f'final_{reel_filename}'
                        )
                        if not error:
                            print("Captions added successfully.")
                            caption_debug_info['captions_added'] = True
                            clip_path = final_path
                        else:
                            print(f"Caption addition error: {error}")
                            caption_debug_info['errors'].append(f"Caption addition error: {error}")

            output_reels.append({
                'reel_id': reel_id,
                'reel_path': clip_path,
                'segment': segment,
                'caption_debug': "sjsjsjsjsjsj",
                'download_url': f"/api/download/{clip_path.split('/')[-1]}",
            })

        # Clean up original video
        if os.path.exists(video_path):
            print(f"Removing original video: {video_path}")
            os.remove(video_path)

        print("Returning response for /api/generate-reel")
        return jsonify({
            'success': True,
            'top_reels': output_reels,
            'video_info': video_info,
        })

    except Exception as e:
        print(f"Error in generate_reel: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<reel_id>', methods=['GET'])
def download_reel(reel_id):
    """Download generated reel"""
    try:
        print(f"Received request to download reel: {reel_id}")
        # Find the reel file
        reel_files = [f for f in os.listdir(config.OUTPUT_DIR) if reel_id in f]
        
        if not reel_files:
            print("Reel not found")
            return jsonify({'error': 'Reel not found'}), 404
        
        reel_path = os.path.join(config.OUTPUT_DIR, reel_files[0])
        print(f"Sending file: {reel_path}")
        return send_file(
            reel_path,
            as_attachment=True,
            download_name=f'reel_{reel_id}.mp4',
            mimetype='video/mp4'
        )
        
    except Exception as e:
        print(f"Error in download_reel: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/customize-reel', methods=['POST'])
def customize_reel():
    """Apply custom modifications to reel"""
    try:
        print("Received request for /api/customize-reel")
        data = request.json
        print(f"Request data: {data}")
        reel_id = data.get('reel_id')
        customizations = data.get('customizations', {})
        
        # This endpoint can be extended to apply various customizations
        # like filters, effects, music, etc.
        
        print(f"Applying customizations: {customizations} to reel_id: {reel_id}")
        return jsonify({
            'success': True,
            'message': 'Customizations applied',
            'reel_id': reel_id
        })
        
    except Exception as e:
        print(f"Error in customize_reel: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Add quality enhancement options to generate-reel endpoint
@app.route('/api/generate-reel-hq', methods=['POST'])
def generate_high_quality_reel():
    """Generate high-quality reel with enhancements"""
    try:
        print("Received request for /api/generate-reel-hq")
        data = request.json
        print(f"Request data: {data}")
        video_url = data.get('video_url')
        segment = data.get('segment')
        style_preferences = data.get('style_preferences', {})
        add_captions = data.get('add_captions', True)
        quality_enhancements = data.get('quality_enhancements', {
            'stabilize': True,
            'enhance_colors': True,
            'auto_levels': True,
            'denoise': False,
            'sharpen': True
        })
        caption_style = data.get('caption_style', 'modern')
        add_transitions = data.get('add_transitions', True)
        add_music = data.get('add_music', False)
        music_url = data.get('music_url', None)
        
        if not video_url or not segment:
            print("Missing required parameters")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Download video
        print(f"Downloading video from URL: {video_url}")
        video_path, error = video_processor.download_video(video_url)
        if error:
            print(f"Download error: {error}")
            return jsonify({'error': f'Download error: {error}'}), 400
        
        # Generate unique filename
        reel_id = str(uuid.uuid4())
        reel_filename = f'reel_hq_{reel_id}.mp4'
        
        # Extract clip with cinematic crop
        print("Extracting clip with cinematic crop...")
        clip_path, error = video_processor.extract_clip(
            video_path,
            segment['start_time'],
            segment['end_time'],
            'temp_clip.mp4'
        )
        if error:
            print(f"Clip extraction error: {error}")
            return jsonify({'error': f'Clip extraction error: {error}'}), 400
        
        # Apply cinematic crop
        print("Applying cinematic crop...")
        crop_path, error = video_processor.apply_cinematic_crop(
            clip_path,
            'temp_crop.mp4',
            aspect_ratio='9:16'
        )
        if error:
            print(f"Cinematic crop error: {error}, using uncropped clip.")
            crop_path = clip_path  # Fallback to uncropped
        
        # Enhance video quality
        print("Enhancing video quality...")
        enhanced_path, error = video_processor.enhance_video_quality(
            crop_path,
            'temp_enhanced.mp4',
            quality_enhancements
        )
        if error:
            print(f"Enhancement error: {error}, using cropped path.")
            enhanced_path = crop_path  # Fallback
        
        current_path = enhanced_path
        
        # Add transitions
        if add_transitions:
            print("Adding transitions...")
            transition_path, error = video_processor.add_smooth_transitions(
                current_path,
                'temp_transitions.mp4',
                transition_type='fade'
            )
            if not error:
                print("Transitions added.")
                current_path = transition_path
            else:
                print(f"Transition error: {error}")
        
        # Add captions with professional styling
        if add_captions:
            print("Adding professional captions...")
            transcript_data, _ = transcript_extractor.get_transcript(video_url)
            
            segment_transcript = [
                entry for entry in transcript_data
                if segment['start_time'] <= entry['start'] <= segment['end_time']
            ]
            
            if segment_transcript:
                captions, error = reel_generator.generate_captions(segment_transcript)
                if captions:
                    for caption in captions:
                        caption['start'] -= segment['start_time']
                        caption['end'] -= segment['start_time']
                    
                    caption_path, error = video_processor.add_professional_captions(
                        current_path,
                        captions,
                        'temp_captions.mp4',
                        style=caption_style
                    )
                    if not error:
                        print("Professional captions added.")
                        current_path = caption_path
                    else:
                        print(f"Caption error: {error}")
        
        # Add background music if requested
        if add_music and music_url:
            print("Adding background music...")
            # Download music
            music_path, error = video_processor.download_audio(music_url)
            if not error:
                music_path, error = video_processor.add_background_music(
                    current_path,
                    music_path,
                    'temp_music.mp4',
                    volume=0.2
                )
                if not error:
                    print("Background music added.")
                    current_path = music_path
                else:
                    print(f"Music addition error: {error}")
            else:
                print(f"Music download error: {error}")
        
        # Enhance audio
        print("Enhancing audio...")
        final_path, error = video_processor.enhance_audio(
            current_path,
            reel_filename
        )
        if error:
            print(f"Audio enhancement error: {error}, using current path.")
            final_path = current_path  # Fallback
        
        # Get enhancement suggestions
        print("Getting enhancement suggestions from AI...")
        enhancements, _ = reel_generator.enhance_reel_idea(segment, style_preferences)
        
        # Clean up temporary files
        print("Cleaning up temporary files...")
        temp_files = [
            video_path, clip_path, crop_path, enhanced_path,
            'temp_transitions.mp4', 'temp_captions.mp4', 'temp_music.mp4'
        ]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                print(f"Removing temp file: {temp_file}")
                os.remove(temp_file)
        
        print("Returning response for /api/generate-reel-hq")
        return jsonify({
            'success': True,
            'reel_id': reel_id,
            'reel_path': final_path,
            'title': segment.get('title', ''),
            'caption': segment.get('caption', ''),
            'hashtags': segment.get('hashtags', []),
            'enhancements': enhancements,
            'quality_settings': quality_enhancements
        })
        
    except Exception as e:
        print(f"Error in generate_high_quality_reel: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server on port 5000...")
    app.run(debug=True, port=5000)