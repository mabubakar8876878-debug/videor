import os
import logging
import subprocess
import tempfile
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def create_video(self, videos: List[List[Dict]], alignment: List[Dict],
                    audio_path: str, format_type: str, output_dir: str) -> str:
        """
        Steps 6-8: Create final video with captions, transitions, and audio
        """
        try:
            # Determine output dimensions
            if format_type == "vertical":
                width, height = 1080, 1920
            else:
                width, height = 1920, 1080
            
            fps = 30
            
            # Step 1: Download video clips
            logger.info("Downloading video clips...")
            downloaded_clips = self._download_clips(videos, alignment)
            
            # Step 2: Trim clips to match audio duration
            logger.info("Trimming clips to audio duration...")
            trimmed_clips = self._trim_clips(downloaded_clips, alignment)
            
            # Step 3: Create captions/text overlays
            logger.info("Creating text overlays...")
            caption_clips = self._create_captions(alignment, width, height)
            
            # Step 4: Concatenate and add transitions
            logger.info("Building video composition...")
            concat_script = self._build_concat_script(
                trimmed_clips,
                caption_clips,
                alignment,
                width,
                height
            )
            
            # Step 5: Render final video with FFmpeg
            logger.info("Rendering final video with FFmpeg...")
            output_path = os.path.join(
                output_dir,
                f"output_{format_type}.mp4"
            )
            
            self._render_with_ffmpeg(
                concat_script,
                audio_path,
                output_path,
                width,
                height,
                fps
            )
            
            logger.info(f"Video created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating video: {e}")
            raise
    
    def _download_clips(self, videos: List[List[Dict]], 
                       alignment: List[Dict]) -> List[str]:
        """Download video clips from URLs"""
        downloaded = []
        
        for scene_idx, scene_videos in enumerate(videos):
            if scene_idx >= len(alignment):
                break
            
            if not scene_videos:
                logger.warning(f"No videos for scene {scene_idx + 1}")
                continue
            
            # Use first (best) video
            video = scene_videos[0]
            url = video.get("url")
            
            if not url:
                continue
            
            try:
                logger.info(f"Downloading video for scene {scene_idx + 1}")
                
                output_file = os.path.join(
                    self.temp_dir,
                    f"scene_{scene_idx + 1}.mp4"
                )
                
                response = requests.get(url, timeout=30, stream=True)
                
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                downloaded.append(output_file)
                
            except Exception as e:
                logger.error(f"Error downloading clip {scene_idx + 1}: {e}")
        
        return downloaded
    
    def _trim_clips(self, clips: List[str], alignment: List[Dict]) -> List[str]:
        """Trim video clips to match audio duration"""
        trimmed = []
        
        for i, clip_path in enumerate(clips):
            if i >= len(alignment):
                break
            
            duration = alignment[i]["duration"]
            output_path = os.path.join(
                self.temp_dir,
                f"trimmed_{i + 1}.mp4"
            )
            
            try:
                logger.info(f"Trimming clip {i + 1} to {duration:.2f}s")
                
                cmd = [
                    "ffmpeg",
                    "-i", clip_path,
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-y",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
                trimmed.append(output_path)
                
            except Exception as e:
                logger.error(f"Error trimming clip {i + 1}: {e}")
        
        return trimmed
    
    def _create_captions(self, alignment: List[Dict], 
                        width: int, height: int) -> List[str]:
        """Create text overlay images for captions"""
        caption_files = []
        
        for scene in alignment:
            text = scene["text"]
            
            try:
                # Create blank image with text
                img = Image.new('RGBA', (width, height), (0, 0, 0, 200))
                draw = ImageDraw.Draw(img)
                
                # Try to load a nice font
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
                except:
                    font = ImageFont.load_default()
                
                # Draw text with shadow
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (width - text_width) // 2
                y = height - 200
                
                # Shadow
                draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 255))
                # Main text
                draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
                
                caption_path = os.path.join(
                    self.temp_dir,
                    f"caption_{scene['scene']}.png"
                )
                img.save(caption_path)
                caption_files.append(caption_path)
                
            except Exception as e:
                logger.error(f"Error creating caption: {e}")
        
        return caption_files
    
    def _build_concat_script(self, clips: List[str], captions: List[str],
                           alignment: List[Dict], width: int, 
                           height: int) -> str:
        """Build FFmpeg concat demuxer script"""
        script_lines = []
        
        for i, (clip_path, caption_path) in enumerate(zip(clips, captions)):
            script_lines.append(f"file '{os.path.abspath(clip_path)}'")
            script_lines.append(f"file '{os.path.abspath(caption_path)}'")
            
            if i < len(clips) - 1:
                # Add transition clip
                script_lines.append("duration 0.5")
        
        script_path = os.path.join(self.temp_dir, "concat.txt")
        with open(script_path, 'w') as f:
            f.write('\n'.join(script_lines))
        
        return script_path
    
    def _render_with_ffmpeg(self, concat_script: str, audio_path: str,
                          output_path: str, width: int, height: int,
                          fps: int):
        """Render final video using FFmpeg"""
        try:
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_script,
                "-i", audio_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:a", "aac",
                "-b:a", "128k",
                "-r", str(fps),
                "-y",
                output_path
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
        except Exception as e:
            logger.error(f"Error rendering video: {e}")
            raise
