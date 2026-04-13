import gradio as gr
import os
import tempfile
from pathlib import Path
import logging
from utils.ai_analyzer import AIAnalyzer
from utils.pexels_fetcher import PexelsFetcher
from utils.whisper_sync import WhisperSync
from utils.video_renderer import VideoRenderer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoEditorApp:
    def __init__(self):
        self.ai_analyzer = AIAnalyzer()
        self.pexels_fetcher = PexelsFetcher()
        self.whisper_sync = WhisperSync()
        self.video_renderer = VideoRenderer()
        self.temp_dir = tempfile.mkdtemp()
        
    def process_script(self, script_text):
        """Step 1: Split script into scenes"""
        if not script_text or script_text.strip() == "":
            return "Error: Script is empty", None
        
        lines = [line.strip() for line in script_text.split('\n') if line.strip()]
        return f"Split into {len(lines)} scenes", lines
    
    def analyze_keywords(self, lines):
        """Step 2: Generate AI keywords for each line"""
        if not lines:
            return "Error: No lines to analyze", None
        
        try:
            results = []
            for i, line in enumerate(lines):
                logger.info(f"Analyzing scene {i+1}: {line}")
                analysis = self.ai_analyzer.analyze_line(line)
                results.append(analysis)
            return "Keywords generated successfully", results
        except Exception as e:
            logger.error(f"Keyword analysis failed: {e}")
            return f"Error: {str(e)}", None
    
    def fetch_videos(self, analysis_results):
        """Step 3: Fetch videos from Pexels"""
        if not analysis_results:
            return "Error: No analysis results", None
        
        try:
            videos = []
            for i, analysis in enumerate(analysis_results):
                logger.info(f"Fetching videos for scene {i+1}")
                scene_videos = self.pexels_fetcher.fetch_videos(
                    analysis['keywords'],
                    analysis['stock_query']
                )
                videos.append(scene_videos)
            return "Videos fetched successfully", videos
        except Exception as e:
            logger.error(f"Video fetching failed: {e}")
            return f"Error: {str(e)}", None
    
    def process_audio(self, audio_file):
        """Step 4: Process audio and extract timestamps"""
        if not audio_file:
            return "Error: No audio file uploaded", None
        
        try:
            logger.info("Processing audio with Whisper")
            timestamps = self.whisper_sync.extract_timestamps(audio_file)
            return "Audio processed successfully", timestamps
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return f"Error: {str(e)}", None
    
    def align_audio_script(self, script_lines, timestamps):
        """Step 5: Align audio with script"""
        if not script_lines or not timestamps:
            return "Error: Missing script or audio data", None
        
        try:
            alignment = self.whisper_sync.align_with_script(
                script_lines,
                timestamps
            )
            return "Audio-script alignment complete", alignment
        except Exception as e:
            logger.error(f"Alignment failed: {e}")
            return f"Error: {str(e)}", None
    
    def generate_video(self, videos, alignment, audio_file, format_type):
        """Steps 6-8: Generate final video"""
        if not videos or not alignment or not audio_file:
            return "Error: Missing video, alignment, or audio data", None
        
        try:
            logger.info(f"Generating video in {format_type} format")
            
            # Step 6: Add text overlays (handled in renderer)
            # Step 7: Edit videos
            # Step 8: Render final output
            
            output_path = self.video_renderer.create_video(
                videos=videos,
                alignment=alignment,
                audio_path=audio_file,
                format_type=format_type,
                output_dir=self.temp_dir
            )
            
            return "Video generated successfully", output_path
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return f"Error: {str(e)}", None

# Initialize app
app = VideoEditorApp()

# Gradio Interface
def create_interface():
    with gr.Blocks(title="AI Video Editor - Pictory AI Clone") as interface:
        gr.Markdown("# 🎬 AI Automatic Video Editor")
        gr.Markdown("Transform your script and voice into a fully edited video!")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Step 1: Script Input")
                script_input = gr.Textbox(
                    label="Paste Your Script",
                    placeholder="Enter your script here. Each line will become a scene...",
                    lines=10,
                    max_lines=50
                )
                parse_btn = gr.Button("📝 Parse Script", variant="primary")
                script_output = gr.Textbox(label="Status", interactive=False)
                script_lines_state = gr.State([])
            
            with gr.Column(scale=1):
                gr.Markdown("### Step 4: Audio Upload")
                audio_input = gr.Audio(
                    label="Upload Voice Audio",
                    type="filepath",
                    format="wav"
                )
                process_audio_btn = gr.Button("🎵 Process Audio", variant="primary")
                audio_output = gr.Textbox(label="Status", interactive=False)
                timestamps_state = gr.State(None)
        
        with gr.Row():
            gr.Markdown("### Step 2-3: AI Analysis & Video Fetching")
            analyze_btn = gr.Button("🤖 Analyze & Fetch Videos", variant="primary", scale=1)
            analysis_output = gr.Textbox(label="Status", interactive=False)
            analysis_state = gr.State(None)
            videos_state = gr.State(None)
        
        with gr.Row():
            gr.Markdown("### Step 5: Audio-Script Alignment")
            align_btn = gr.Button("⚙️ Align Audio with Script", variant="primary")
            align_output = gr.Textbox(label="Status", interactive=False)
            alignment_state = gr.State(None)
        
        with gr.Row():
            gr.Markdown("### Step 6-8: Generate Video")
            with gr.Column():
                format_choice = gr.Radio(
                    choices=["1080x1920 (Vertical)", "1920x1080 (Landscape)"],
                    value="1080x1920 (Vertical)",
                    label="Output Format"
                )
            with gr.Column():
                render_btn = gr.Button("🎥 Render Video", variant="primary", scale=1)
        
        render_output = gr.Textbox(label="Render Status", interactive=False)
        
        with gr.Row():
            gr.Markdown("### Step 9: Video Output")
            video_output = gr.Video(label="Video Preview")
        
        with gr.Row():
            download_btn = gr.Button("⬇️ Download Video", variant="primary")
            regenerate_btn = gr.Button("🔄 Regenerate", variant="secondary")
        
        # Event handlers
        def parse_script_handler(script):
            status, lines = app.process_script(script)
            return status, lines
        
        def analyze_handler(lines):
            status, analysis = app.analyze_keywords(lines)
            status2, videos = app.fetch_videos(analysis)
            return f"{status}\n{status2}", analysis, videos
        
        def process_audio_handler(audio):
            status, timestamps = app.process_audio(audio)
            return status, timestamps
        
        def align_handler(lines, timestamps):
            status, alignment = app.align_audio_script(lines, timestamps)
            return status, alignment
        
        def render_handler(videos, alignment, audio, format_type):
            if not audio:
                return "Error: No audio file provided", None
            
            fmt = "vertical" if "Vertical" in format_type else "landscape"
            status, video_path = app.generate_video(videos, alignment, audio, fmt)
            return status, video_path
        
        # Connect event handlers
        parse_btn.click(
            parse_script_handler,
            inputs=[script_input],
            outputs=[script_output, script_lines_state]
        )
        
        process_audio_btn.click(
            process_audio_handler,
            inputs=[audio_input],
            outputs=[audio_output, timestamps_state]
        )
        
        analyze_btn.click(
            analyze_handler,
            inputs=[script_lines_state],
            outputs=[analysis_output, analysis_state, videos_state]
        )
        
        align_btn.click(
            align_handler,
            inputs=[script_lines_state, timestamps_state],
            outputs=[align_output, alignment_state]
        )
        
        render_btn.click(
            render_handler,
            inputs=[videos_state, alignment_state, audio_input, format_choice],
            outputs=[render_output, video_output]
        )
        
        regenerate_btn.click(
            lambda: (None, None),
            outputs=[script_input, audio_input]
        )
        
        return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)
