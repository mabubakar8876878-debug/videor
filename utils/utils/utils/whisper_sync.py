import os
import logging
from typing import Dict, List
from transformers import pipeline
import librosa
import numpy as np

logger = logging.getLogger(__name__)

class WhisperSync:
    def __init__(self):
        self.device = "cuda" if os.getenv("USE_GPU") == "1" else "cpu"
        logger.info(f"Loading Whisper model on {self.device}")
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            device=self.device
        )
    
    def extract_timestamps(self, audio_path: str) -> Dict:
        """
        Step 4: Extract word-level timestamps from audio using Whisper
        """
        try:
            logger.info(f"Processing audio: {audio_path}")
            
            # Load audio
            waveform, sr = librosa.load(audio_path, sr=16000)
            
            # Run Whisper with return_timestamps
            result = self.pipe(
                waveform,
                return_timestamps="word",
                chunk_length_s=30,
                stride_length_s=5
            )
            
            # Extract word-level timestamps
            words_data = []
            
            if "chunks" in result:
                for chunk in result["chunks"]:
                    words_data.append({
                        "word": chunk["text"],
                        "start": chunk["timestamp"][0],
                        "end": chunk["timestamp"][1]
                    })
            else:
                # Fallback if chunks not available
                text = result.get("text", "")
                duration = len(waveform) / sr
                words = text.split()
                word_duration = duration / len(words) if words else 0
                
                for i, word in enumerate(words):
                    words_data.append({
                        "word": word,
                        "start": i * word_duration,
                        "end": (i + 1) * word_duration
                    })
            
            logger.info(f"Extracted {len(words_data)} words with timestamps")
            
            return {
                "full_text": result.get("text", ""),
                "words": words_data,
                "duration": len(waveform) / sr
            }
            
        except Exception as e:
            logger.error(f"Error extracting timestamps: {e}")
            raise
    
    def align_with_script(self, script_lines: List[str], 
                         timestamps: Dict) -> List[Dict]:
        """
        Step 5: Align audio timestamps with script lines
        """
        try:
            words = timestamps["words"]
            alignment = []
            
            word_idx = 0
            
            for line_idx, line in enumerate(script_lines):
                line_words = line.split()
                
                if word_idx >= len(words):
                    logger.warning(f"Not enough words in audio for line {line_idx}")
                    break
                
                start_time = words[word_idx]["start"]
                line_end_idx = min(word_idx + len(line_words), len(words))
                
                if line_end_idx > word_idx:
                    end_time = words[line_end_idx - 1]["end"]
                else:
                    end_time = start_time + 2.0  # Default duration
                
                duration = end_time - start_time
                
                alignment.append({
                    "scene": line_idx + 1,
                    "text": line,
                    "start": start_time,
                    "end": end_time,
                    "duration": duration,
                    "words": words[word_idx:line_end_idx]
                })
                
                word_idx = line_end_idx
                
                logger.info(f"Scene {line_idx + 1}: {start_time:.2f}s - {end_time:.2f}s")
            
            return alignment
            
        except Exception as e:
            logger.error(f"Error aligning audio with script: {e}")
            raise
