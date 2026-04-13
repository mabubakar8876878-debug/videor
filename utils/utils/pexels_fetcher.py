import os
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class PexelsFetcher:
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.api_url = "https://api.pexels.com/videos/search"
        
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY not set in environment")
    
    def fetch_videos(self, keywords: List[str], stock_query: str, 
                     min_duration: int = 3, per_page: int = 3) -> List[Dict]:
        """
        Step 3: Fetch HD videos from Pexels based on keywords
        """
        videos = []
        
        # Try primary stock query first
        search_terms = [stock_query] + keywords
        
        for query in search_terms:
            if len(videos) >= per_page:
                break
            
            try:
                response = requests.get(
                    self.api_url,
                    headers={"Authorization": self.api_key},
                    params={
                        "query": query,
                        "per_page": per_page,
                        "orientation": "both"
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for video in data.get('videos', []):
                        if len(videos) >= per_page:
                            break
                        
                        # Filter by duration and quality
                        duration = video.get('duration', 0)
                        if duration < min_duration:
                            continue
                        
                        # Get best quality video file
                        video_files = video.get('video_files', [])
                        best_file = self._select_best_quality(video_files)
                        
                        if best_file:
                            videos.append({
                                "id": video.get('id'),
                                "url": best_file['link'],
                                "width": best_file['width'],
                                "height": best_file['height'],
                                "duration": duration,
                                "quality": best_file['quality'],
                                "thumbnail": video.get('image')
                            })
                
                logger.info(f"Fetched {len(videos)} videos for query: {query}")
                
            except Exception as e:
                logger.error(f"Error fetching videos for '{query}': {e}")
        
        return videos[:per_page]
    
    def _select_best_quality(self, video_files: List[Dict]) -> Dict:
        """Select best quality video (HD preferred)"""
        if not video_files:
            return None
        
        # Prioritize HD (720p or higher)
        hd_files = [f for f in video_files if f.get('height', 0) >= 720]
        
        if hd_files:
            return sorted(hd_files, key=lambda x: x.get('height', 0), reverse=True)[0]
        
        # Fallback to highest available quality
        return sorted(video_files, key=lambda x: x.get('height', 0), reverse=True)[0]
