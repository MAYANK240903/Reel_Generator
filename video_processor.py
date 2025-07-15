from pytube import YouTube
import yt_dlp
import ffmpeg
import os
import json
import subprocess
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import config

class VideoProcessor:
    def __init__(self):
        print("VideoProcessor initialized.")
        self.temp_dir = config.TEMP_DIR
        self.output_dir = config.OUTPUT_DIR
    
    def download_video(self, video_url):
        print(f"Starting download_video with URL: {video_url}")
        try:
            output_path = os.path.join(self.temp_dir, 'source_video.mp4')
            print(f"Output path for download: {output_path}")
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            print(f"yt-dlp options: {ydl_opts}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Downloading video from: {video_url}")
                ydl.download([video_url])
            if os.path.exists(output_path):
                print(f"Video downloaded successfully to: {output_path}")
                return output_path, None
            else:
                print("Download completed but file not found")
                return None, "Download completed but file not found"
        except Exception as e:
            print(f"yt-dlp download error: {str(e)}")
            try:
                print("Trying pytube as fallback...")
                yt = YouTube(video_url)
                video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                if not video_stream:
                    print("No progressive mp4 stream found, trying adaptive...")
                    video_stream = yt.streams.filter(adaptive=True, file_extension='mp4').order_by('resolution').desc().first()
                video_path = video_stream.download(output_path=self.temp_dir, filename='source_video.mp4')
                print(f"Video downloaded with pytube to: {video_path}")
                return video_path, None
            except Exception as pytube_error:
                print(f"Both yt-dlp and pytube failed. yt-dlp: {str(e)}, pytube: {str(pytube_error)}")
                return None, f"Both yt-dlp and pytube failed. yt-dlp: {str(e)}, pytube: {str(pytube_error)}"
    
    def get_video_info(self, video_path):
        print(f"Getting video info for: {video_path}")
        try:
            probe = ffmpeg.probe(video_path)
            print(f"ffmpeg probe result: {probe}")
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                info = {
                    'width': int(video_stream['width']),
                    'height': int(video_stream['height']),
                    'duration': float(probe['format']['duration']),
                    'fps': eval(video_stream['r_frame_rate'])
                }
                print(f"Extracted video info: {info}")
                return info
            print("No video stream found in probe.")
            return None
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None
    
    def extract_clip(self, video_path, start_time, end_time, output_name):
        print(f"Extracting clip: {video_path}, start: {start_time}, end: {end_time}, output: {output_name}")
        result, error = self.extract_clip_with_crop(video_path, start_time, end_time, output_name)
        if error:
            print(f"Simple extraction failed: {error}, trying with crop/scale...")
            result, error = self.extract_clip_with_crop(video_path, start_time, end_time, output_name)
        return result, error

    def extract_clip_simple(self, video_path, start_time, end_time, output_name):
        print(f"extract_clip_simple called with: {video_path}, {start_time}, {end_time}, {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            duration = end_time - start_time
            print(f"Output path: {output_path}, Duration: {duration}")
            os.makedirs(self.output_dir, exist_ok=True)
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
                '-y',
                output_path
            ]
            print(f"Running FFmpeg command: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"FFmpeg process return code: {process.returncode}")
            if process.returncode != 0:
                print(f"FFmpeg stderr: {process.stderr}")
                return None, f"FFmpeg error: {process.stderr}"
            if os.path.exists(output_path):
                print(f"Clip extracted successfully to: {output_path}")
                return output_path, None
            else:
                print("Clip extraction completed but file not found")
                return None, "Clip extraction completed but file not found"
        except Exception as e:
            print(f"Clip extraction error: {str(e)}")
            return None, f"Clip extraction error: {str(e)}"
    
    def extract_clip_with_crop(self, video_path, start_time, end_time, output_name):
        print(f"extract_clip_with_crop called with: {video_path}, {start_time}, {end_time}, {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            duration = end_time - start_time
            print(f"Output path: {output_path}, Duration: {duration}")
            video_info = self.get_video_info(video_path)
            print(f"Video info for cropping: {video_info}")
            if not video_info:
                print("Could not get video info for cropping.")
                return None, "Could not get video info"
            target_ratio = 9/16
            current_ratio = video_info['width'] / video_info['height']
            print(f"Target ratio: {target_ratio}, Current ratio: {current_ratio}")
            if current_ratio > target_ratio:
                new_width = int(video_info['height'] * target_ratio)
                x_offset = (video_info['width'] - new_width) // 2
                crop_params = f"{new_width}:{video_info['height']}:{x_offset}:0"
                print(f"Cropping sides: {crop_params}")
            else:
                new_height = int(video_info['width'] / target_ratio)
                y_offset = (video_info['height'] - new_height) // 2
                crop_params = f"{video_info['width']}:{new_height}:0:{y_offset}"
                print(f"Cropping top/bottom: {crop_params}")
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f"crop={crop_params},scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
            print(f"Running FFmpeg with crop: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"FFmpeg crop process return code: {process.returncode}")
            if process.returncode != 0:
                print(f"FFmpeg stderr: {process.stderr}")
                return None, f"FFmpeg error: {process.stderr}"
            if os.path.exists(output_path):
                print(f"Clip with crop extracted successfully to: {output_path}")
                return output_path, None
            else:
                print("Clip extraction with crop completed but file not found")
                return None, "Clip extraction completed but file not found"
        except Exception as e:
            print(f"Clip extraction with crop error: {str(e)}")
            return None, f"Clip extraction error: {str(e)}"
        
    def add_captions_with_ffmpeg(self, video_path, captions, output_name):
        print(f"add_captions_with_ffmpeg called with video_path: {video_path}, output_name: {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            drawtext_filters = []
            for i, caption in enumerate(captions):
                text = caption['text'].replace("'", "\\'").replace(":", "\\:")
                drawtext = (
                    f"drawtext="
                    f"text='{text}':"
                    f"fontfile=/System/Library/Fonts/Helvetica.ttc:"
                    f"fontsize=40:"
                    f"fontcolor=white:"
                    f"borderw=2:"
                    f"bordercolor=black:"
                    f"x=(w-text_w)/2:"
                    f"y=h-100:"
                    f"enable='between(t,{caption['start']},{caption['end']})'"
                )
                drawtext_filters.append(drawtext)
            filter_complex = ','.join(drawtext_filters)
            print(f"FFmpeg drawtext filter: {filter_complex}")
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, output_path,
                                 vf=filter_complex,
                                 vcodec='libx264',
                                 acodec='copy')
            ffmpeg.run(stream, overwrite_output=True)
            print(f"FFmpeg run completed for captions, output: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"add_captions_with_ffmpeg error: {str(e)}")
            return None, str(e)
    
    def add_captions_with_opencv(self, video_path, captions, output_name):
        print(f"add_captions_with_opencv called with video_path: {video_path}, output_name: {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            cap = cv2.VideoCapture(video_path)
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Video properties - FPS: {fps}, Width: {width}, Height: {height}")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            temp_video = os.path.join(self.temp_dir, 'temp_captioned.mp4')
            out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
            frame_count = 0
            current_time = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                active_caption = None
                for caption in captions:
                    if caption['start'] <= current_time <= caption['end']:
                        active_caption = caption
                        break
                if active_caption:
                    frame = self.add_text_to_frame(frame, active_caption['text'], width, height)
                out.write(frame)
                frame_count += 1
            cap.release()
            out.release()
            print(f"Frames processed: {frame_count}")
            video_stream = ffmpeg.input(temp_video)
            audio_stream = ffmpeg.input(video_path).audio
            output = ffmpeg.output(video_stream, audio_stream, output_path,
                                 vcodec='libx264',
                                 acodec='aac')
            ffmpeg.run(output, overwrite_output=True)
            print(f"FFmpeg run completed for OpenCV captions, output: {output_path}")
            os.remove(temp_video)
            print(f"Temp video {temp_video} removed.")
            return output_path, None
        except Exception as e:
            print(f"add_captions_with_opencv error: {str(e)}")
            return None, str(e)
    
    # def add_text_to_frame(self, frame, text, width, height):
    #     print(f"add_text_to_frame called with text: {text}")
    #     img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    #     draw = ImageDraw.Draw(img_pil)
    #     font_size = int(height * 0.20)
    #     try:
    #         font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
    #     except:
    #         try:
    #             font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", font_size)
    #         except:
    #             try:
    #                 font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    #             except:
    #                 font = ImageFont.load_default()
    #     print(f"Font size used: {font_size}, font: {font.path if hasattr(font, 'path') else font}")
    #     text_bbox = draw.textbbox((0, 0), text, font=font)
    #     text_width = text_bbox[2] - text_bbox[0]
    #     text_height = text_bbox[3] - text_bbox[1]
    #     x = (width - text_width) // 2
    #     y = height - int(height * 0.20) - text_height
    #     outline_width = 4
    #     for adj in range(-outline_width, outline_width+1):
    #         for adj2 in range(-outline_width, outline_width+1):
    #             draw.text((x+adj, y+adj2), text, font=font, fill=(0, 0, 0))
    #     draw.text((x, y), text, font=font, fill=(255, 255, 255))
    #     frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    #     return frame
    
    # def add_text_to_frame(self, frame, text, width, height):
    #     print(f"add_text_to_frame called with text: {text}")
    #     # Use a meme font (Impact or fallback to Helvetica if not available)
    #     font_size = 90  # Large for 9:16
    #     font_path = "/Library/Fonts/Impact.ttf"  # macOS Impact font path
    #     try:
    #         font = ImageFont.truetype(font_path, font_size)
    #     except:
    #         try:
    #             font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    #         except:
    #             font = ImageFont.load_default()
    #     # Wrap text to max 2 lines and fit width
    #     max_width_ratio = 0.92
    #     words = text.split()
    #     lines = []
    #     current_line = ""
    #     while words:
    #         word = words.pop(0)
    #         test_line = (current_line + " " + word).strip()
    #         test_bbox = ImageDraw.Draw(Image.new("RGB", (width, height))).textbbox((0, 0), test_line, font=font)
    #         test_width = test_bbox[2] - test_bbox[0]
    #         if test_width > width * max_width_ratio and current_line:
    #             lines.append(current_line)
    #             current_line = word
    #         else:
    #             current_line = test_line
    #         if len(lines) == 1 and not words:
    #             lines.append(current_line)
    #     if current_line and len(lines) < 2:
    #         lines.append(current_line)
    #     if len(lines) > 2:
    #         # Merge to two lines and add ellipsis if needed
    #         all_words = text.split()
    #         half = len(all_words) // 2
    #         lines = [' '.join(all_words[:half]), ' '.join(all_words[half:])]
    #         for idx, line in enumerate(lines):
    #             test_bbox = ImageDraw.Draw(Image.new("RGB", (width, height))).textbbox((0, 0), line, font=font)
    #             test_width = test_bbox[2] - test_bbox[0]
    #             max_chars = int((width * max_width_ratio) / (font_size * 0.6))
    #             if test_width > width * max_width_ratio or len(line) > max_chars:
    #                 lines[idx] = line[:max_chars-3] + '...'
    #     text_wrapped = '\n'.join(lines[:2])

    #     img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    #     draw = ImageDraw.Draw(img_pil)
    #     # Colorful "gradient" effect: cycle colors per line
    #     color_list = [(255,81,47), (240,152,25), (31,162,255), (168,255,120), (249,83,198), (67,233,123), (56,249,215), (255,95,109)]
    #     outline_width = 6
    #     y = height - 250
    #     for i, line in enumerate(text_wrapped.split('\n')):
    #         text_bbox = draw.textbbox((0, 0), line, font=font)
    #         text_width = text_bbox[2] - text_bbox[0]
    #         text_height = text_bbox[3] - text_bbox[1]
    #         x = (width - text_width) // 2
    #         line_y = y + i * (text_height + 10)
    #         # Draw black border for meme style
    #         for adj in range(-outline_width, outline_width+1):
    #             for adj2 in range(-outline_width, outline_width+1):
    #                 draw.text((x+adj, line_y+adj2), line, font=font, fill=(0,0,0))
    #         # Draw main text in colorful style
    #         draw.text((x, line_y), line, font=font, fill=color_list[i % len(color_list)])
    #     frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    #     return frame
    def add_text_to_frame(self, frame, text, width, height):
        print(f"add_text_to_frame called with text: {text}")
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        # Use a big font size: 12% of video height
        font_size = int(height * 0.05)
        # Try Impact, then Arial Bold, then Helvetica, then default
        font = None
        font_paths = [
            "/Library/Fonts/Impact.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, font_size)
                print(f"Loaded font: {path} size: {font_size}")
                break
            except Exception as e:
                continue
        if font is None:
            font = ImageFont.load_default()
            print("Loaded default font.")

        # Wrap text to max 2 lines and fit width
        max_width_ratio = 0.92
        words = text.split()
        lines = []
        current_line = ""
        while words:
            word = words.pop(0)
            test_line = (current_line + " " + word).strip()
            test_bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = test_bbox[2] - test_bbox[0]
            if test_width > width * max_width_ratio and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
            if len(lines) == 1 and not words:
                lines.append(current_line)
        if current_line and len(lines) < 2:
            lines.append(current_line)
        if len(lines) > 2:
            # Merge to two lines and add ellipsis if needed
            all_words = text.split()
            half = len(all_words) // 2
            lines = [' '.join(all_words[:half]), ' '.join(all_words[half:])]
            for idx, line in enumerate(lines):
                test_bbox = draw.textbbox((0, 0), line, font=font)
                test_width = test_bbox[2] - test_bbox[0]
                max_chars = int((width * max_width_ratio) / (font_size * 0.6))
                if test_width > width * max_width_ratio or len(line) > max_chars:
                    lines[idx] = line[:max_chars-3] + '...'
        text_wrapped = '\n'.join(lines[:2])

        # Draw text with thick black outline for meme style
        outline_width = 6
        y = height - int(height * 0.25)
        for i, line in enumerate(text_wrapped.split('\n')):
            text_bbox = draw.textbbox((0, 0), line, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (width - text_width) // 2
            line_y = y + i * (text_height + 10)
            # Draw outline
            for adj in range(-outline_width, outline_width+1):
                for adj2 in range(-outline_width, outline_width+1):
                    draw.text((x+adj, line_y+adj2), line, font=font, fill=(0,0,0))
            # Draw main text
            draw.text((x, line_y), line, font=font, fill=(255,255,255))
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return frame
    def add_captions(self, video_path, captions, output_name):
        print(f"add_captions called with video_path: {video_path}, output_name: {output_name}")
        print(f"Captions to add: {captions}")
        result, error = self.add_captions_with_ffmpeg(video_path, captions, output_name)
        print(f"Result from add_captions_with_ffmpeg: {result}, Error: {error}")
        if error:
            print(f"FFmpeg method failed: {error}, trying OpenCV method")
            result, error = self.add_captions_with_opencv(video_path, captions, output_name)
            print(f"Result from add_captions_with_opencv: {result}, Error: {error}")
        return result, error
    
    def apply_filters(self, video_path, filters, output_name):
        print(f"apply_filters called with video_path: {video_path}, filters: {filters}, output_name: {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            filter_list = []
            if 'color_style' in filters:
                style = filters['color_style']
                print(f"Applying color style: {style}")
                if style == 'vintage':
                    filter_list.append('curves=vintage')
                elif style == 'vibrant':
                    filter_list.append('eq=saturation=1.3:brightness=0.1')
                elif style == 'dark':
                    filter_list.append('eq=brightness=-0.1:contrast=1.2')
            if 'speed' in filters:
                speed = filters['speed']
                print(f"Applying speed: {speed}")
                filter_list.append(f'setpts={1/speed}*PTS')
            stream = ffmpeg.input(video_path)
            if filter_list:
                stream = ffmpeg.filter(stream, 'vf', ','.join(filter_list))
            stream = ffmpeg.output(stream, output_path,
                                 vcodec='libx264',
                                 acodec='aac')
            ffmpeg.run(stream, overwrite_output=True)
            print(f"Filters applied, output: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"apply_filters error: {str(e)}")
            return None, str(e)
        
    def enhance_video_quality(self, video_path, output_name, enhancements):
        print(f"enhance_video_quality called with video_path: {video_path}, output_name: {output_name}, enhancements: {enhancements}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            filters = []
            if enhancements.get('stabilize', False):
                print("Applying stabilization filter")
                filters.append('deshake')
            if enhancements.get('denoise', False):
                print("Applying denoise filter")
                filters.append('nlmeans=s=1.0')
            if enhancements.get('sharpen', False):
                print("Applying sharpen filter")
                filters.append('unsharp=5:5:1.0:5:5:0.0')
            if enhancements.get('enhance_colors', False):
                print("Applying color enhancement filter")
                filters.append('eq=saturation=1.2:brightness=0.05:contrast=1.1')
            if enhancements.get('auto_levels', False):
                print("Applying auto-levels filter")
                filters.append('normalize')
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', ','.join(filters) if filters else 'copy',
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                '-y', output_path
            ]
            print(f"Running FFmpeg for enhancement: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Enhancement FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Enhancement error: {process.stderr}")
                return None, f"Enhancement error: {process.stderr}"
            print(f"Enhanced video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"enhance_video_quality error: {str(e)}")
            return None, str(e)

    def apply_cinematic_crop(self, video_path, output_name, aspect_ratio='9:16'):
        print(f"apply_cinematic_crop called with video_path: {video_path}, output_name: {output_name}, aspect_ratio: {aspect_ratio}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            video_info = self.get_video_info(video_path)
            print(f"Video info for cinematic crop: {video_info}")
            if not video_info:
                print("Could not get video info for cinematic crop")
                return None, "Could not get video info"
            width = video_info['width']
            height = video_info['height']
            if aspect_ratio == '9:16':
                target_width = int(height * 9 / 16)
                x_offset = (width - target_width) // 2
                crop_filter = f"crop={target_width}:{height}:{x_offset}:0"
                print(f"Cinematic crop filter: {crop_filter}")
            else:
                crop_filter = f"crop={width}:{height}:0:0"
                print(f"Default crop filter: {crop_filter}")
            vignette = "vignette=PI/4"
            filter_complex = f"{crop_filter},{vignette},scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}"
            print(f"Filter complex for cinematic crop: {filter_complex}")
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '20',
                '-c:a', 'copy',
                '-y', output_path
            ]
            print(f"Running FFmpeg for cinematic crop: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Cinematic crop FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Cinematic crop error: {process.stderr}")
                return None, f"Cinematic crop error: {process.stderr}"
            print(f"Cinematic cropped video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"apply_cinematic_crop error: {str(e)}")
            return None, str(e)

    def add_smooth_transitions(self, video_path, output_name, transition_type='fade'):
        print(f"add_smooth_transitions called with video_path: {video_path}, output_name: {output_name}, transition_type: {transition_type}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            fade_duration = 0.5
            video_info = self.get_video_info(video_path)
            print(f"Video info for transitions: {video_info}")
            duration = video_info['duration']
            if transition_type == 'fade':
                filter_complex = (
                    f"fade=t=in:st=0:d={fade_duration},"
                    f"fade=t=out:st={duration-fade_duration}:d={fade_duration}"
                )
                print(f"Fade filter complex: {filter_complex}")
            elif transition_type == 'slide':
                filter_complex = (
                    f"split[main][copy];"
                    f"[copy]scale=iw:ih,setpts=PTS-STARTPTS[scaled];"
                    f"[main][scaled]overlay=x='if(lt(t,{fade_duration}),-W+W*t/{fade_duration},0)':y=0"
                )
                print(f"Slide filter complex: {filter_complex}")
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '20',
                '-c:a', 'copy',
                '-y', output_path
            ]
            print(f"Running FFmpeg for transitions: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Transitions FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Transition error: {process.stderr}")
                return None, f"Transition error: {process.stderr}"
            print(f"Transitions added video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"add_smooth_transitions error: {str(e)}")
            return None, str(e)
        
    def add_professional_captions(self, video_path, captions, output_name, style='modern'):
        print(f"add_professional_captions called with video_path: {video_path}, output_name: {output_name}, style: {style}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            styles = {
                'modern': {
                    'fontsize': 50,
                    'fontcolor': 'white',
                    'borderw': 3,
                    'bordercolor': 'black',
                    'shadowx': 2,
                    'shadowy': 2,
                    'font': 'Arial-Bold'
                },
                'minimal': {
                    'fontsize': 45,
                    'fontcolor': 'white',
                    'borderw': 0,
                    'shadowx': 1,
                    'shadowy': 1,
                    'font': 'Helvetica'
                },
                'bold': {
                    'fontsize': 60,
                    'fontcolor': 'yellow',
                    'borderw': 4,
                    'bordercolor': 'black',
                    'shadowx': 3,
                    'shadowy': 3,
                    'font': 'Arial-Black'
                }
            }
            style_config = styles.get(style, styles['modern'])
            print(f"Using style config: {style_config}")
            drawtext_filters = []
            for i, caption in enumerate(captions):
                text = caption['text'].replace("'", "\\'").replace(":", "\\:")
                drawtext = (
                    f"drawtext="
                    f"text='{text}':"
                    f"fontsize={style_config['fontsize']}:"
                    f"fontcolor={style_config['fontcolor']}:"
                    f"borderw={style_config['borderw']}:"
                    f"bordercolor={style_config.get('bordercolor', 'black')}:"
                    f"shadowx={style_config['shadowx']}:"
                    f"shadowy={style_config['shadowy']}:"
                    f"x=(w-text_w)/2:"
                    f"y=h-100-50*exp(-(t-{caption['start']})*5):"
                    f"alpha='if(between(t,{caption['start']},{caption['end']}),min(1,(t-{caption['start']})*3),0)'"
                )
                drawtext_filters.append(drawtext)
            filter_complex = ','.join(drawtext_filters)
            print(f"FFmpeg drawtext filter for professional captions: {filter_complex}")
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '18',
                '-c:a', 'copy',
                '-y', output_path
            ]
            print(f"Running FFmpeg for professional captions: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Professional captions FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print("Professional captions failed, falling back to OpenCV captions.")
                return self.add_captions_with_opencv(video_path, captions, output_name)
            print(f"Professional captions added video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"add_professional_captions error: {str(e)}")
            return None, str(e)

    def add_background_music(self, video_path, music_path, output_name, volume=0.3):
        print(f"add_background_music called with video_path: {video_path}, music_path: {music_path}, output_name: {output_name}, volume: {volume}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            video_info = self.get_video_info(video_path)
            duration = video_info['duration']
            print(f"Video duration for background music: {duration}")
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', music_path,
                '-filter_complex', 
                f"[1:a]volume={volume},aloop=loop=-1:size=2e+09[music];"
                f"[0:a][music]amix=inputs=2:duration=first[audio]",
                '-map', '0:v',
                '-map', '[audio]',
                '-t', str(duration),
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y', output_path
            ]
            print(f"Running FFmpeg for background music: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Background music FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Music addition error: {process.stderr}")
                return None, f"Music addition error: {process.stderr}"
            print(f"Background music added video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"add_background_music error: {str(e)}")
            return None, str(e)

    def enhance_audio(self, video_path, output_name):
        print(f"enhance_audio called with video_path: {video_path}, output_name: {output_name}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            audio_filters = [
                'highpass=f=100',
                'lowpass=f=8000',
                'loudnorm=I=-16:TP=-1.5:LRA=11',
                'acompressor=threshold=0.5:ratio=3:attack=5:release=50'
            ]
            print(f"Audio filters: {audio_filters}")
            cmd = [
                'ffmpeg', '-i', video_path,
                '-af', ','.join(audio_filters),
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y', output_path
            ]
            print(f"Running FFmpeg for audio enhancement: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Audio enhancement FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Audio enhancement error: {process.stderr}")
                return None, f"Audio enhancement error: {process.stderr}"
            print(f"Audio enhanced video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"enhance_audio error: {str(e)}")
            return None, str(e)
    
    # def transcript_to_captions(self, transcript_data, max_words=4):
    #     captions = []
    #     for entry in transcript_data:
    #         words = entry['text'].split()
    #         n = len(words)
    #         if n == 0:
    #             continue
    #         chunk_duration = entry['duration'] / ((n + max_words - 1) // max_words)
    #         for i in range(0, n, max_words):
    #             chunk_words = words[i:i+max_words]
    #             chunk_text = ' '.join(chunk_words)
    #             chunk_start = entry['start'] + (i // max_words) * chunk_duration
    #             chunk_end = chunk_start + chunk_duration
    #             captions.append({
    #                 "text": chunk_text,
    #                 "start": chunk_start,
    #                 "end": chunk_end
    #             })
    #     return captions
    # def transcript_to_captions(self, transcript_data, max_words=4):
    # # Flatten all transcript entries into a list of (word, start, end)
    #     words_with_times = []
    #     for entry in transcript_data:
    #         words = entry['text'].split()
    #         if not words:
    #             continue
    #         word_count = len(words)
    #         # Distribute timing evenly for each word in this entry
    #         word_duration = entry['duration'] / word_count
    #         for i, word in enumerate(words):
    #             word_start = entry['start'] + i * word_duration
    #             word_end = word_start + word_duration
    #             words_with_times.append((word, word_start, word_end))

    #     # Group into captions of max_words
    #     captions = []
    #     i = 0
    #     while i < len(words_with_times):
    #         group = words_with_times[i:i+max_words]
    #         caption_text = ' '.join([w[0] for w in group])
    #         caption_start = group[0][1]
    #         caption_end = group[-1][2]
    #         captions.append({
    #             "text": caption_text,
    #             "start": caption_start,
    #             "end": caption_end
    #         })
    #         i += max_words
    #     return captions
    
    def transcript_to_captions(self, transcript_data, window=1.0):
        """
        Groups transcript words into captions by time window (default 1s).
        Each caption contains all words spoken in that window.
        """
        # Flatten transcript into (word, start, end) tuples
        words_with_times = []
        for entry in transcript_data:
            words = entry['text'].split()
            if not words:
                continue
            word_count = len(words)
            word_duration = entry['duration'] / word_count
            for i, word in enumerate(words):
                word_start = entry['start'] + i * word_duration
                word_end = word_start + word_duration
                words_with_times.append((word, word_start, word_end))

        if not words_with_times:
            return []

        # Group words by window (e.g., every 1.0s)
        captions = []
        group = []
        group_start = words_with_times[0][1]
        group_end = group_start + window
        for word, start, end in words_with_times:
            # If word starts after current group window, close group and start new
            if start >= group_end and group:
                captions.append({
                    "text": ' '.join([w[0] for w in group]),
                    "start": group[0][1],
                    "end": group[-1][2]
                })
                group = []
                group_start = start
                group_end = group_start + window
            group.append((word, start, end))
        # Add last group
        if group:
            captions.append({
                "text": ' '.join([w[0] for w in group]),
                "start": group[0][1],
                "end": group[-1][2]
            })

        return captions

    def apply_color_grading(self, video_path, output_name, preset='vibrant'):
        print(f"apply_color_grading called with video_path: {video_path}, output_name: {output_name}, preset: {preset}")
        try:
            output_path = os.path.join(self.output_dir, output_name)
            presets = {
                'vibrant': 'eq=saturation=1.3:brightness=0.05:contrast=1.1,vibrance=intensity=0.3',
                'cinematic': 'curves=preset=darker,eq=saturation=0.9:contrast=1.2',
                'vintage': 'curves=vintage,colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131',
                'cool': 'colorbalance=rs=-0.1:gs=0:bs=0.1:rm=-0.1:gm=0:bm=0.1:rh=-0.1:gh=0:bh=0.1',
                'warm': 'colorbalance=rs=0.1:gs=0:bs=-0.1:rm=0.1:gm=0:bm=-0.1:rh=0.1:gh=0:bh=-0.1',
                'black_white': 'hue=s=0',
                'dramatic': 'eq=contrast=1.3:brightness=-0.05:saturation=1.1,unsharp=5:5:1.5:5:5:0.0'
            }
            filter_string = presets.get(preset, presets['vibrant'])
            print(f"Color grading filter string: {filter_string}")
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', filter_string,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '18',
                '-c:a', 'copy',
                '-y', output_path
            ]
            print(f"Running FFmpeg for color grading: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Color grading FFmpeg return code: {process.returncode}")
            if process.returncode != 0:
                print(f"Color grading error: {process.stderr}")
                return None, f"Color grading error: {process.stderr}"
            print(f"Color graded video saved to: {output_path}")
            return output_path, None
        except Exception as e:
            print(f"apply_color_grading error: {str(e)}")
            return None, str(e)