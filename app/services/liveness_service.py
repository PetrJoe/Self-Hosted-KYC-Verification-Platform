"""
Liveness detection service for biometric verification.
Detects whether a biometric sample is from a live person.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import math

logger = logging.getLogger(__name__)


class LivenessService:
    """
    Service for detecting liveness in biometric samples.
    Uses passive and active techniques to ensure the person is live.
    """

    def __init__(self):
        # Load face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # Load eye detection for blink detection
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

    async def detect_liveness(self, video_path: Path, liveness_type: str = "passive") -> Dict[str, Any]:
        """
        Detect liveness in video sample.

        Args:
            video_path: Path to video file
            liveness_type: "passive" or "active"

        Returns:
            Dict with liveness detection results
        """
        try:
            if liveness_type == "active":
                return await self._active_liveness_detection(video_path)
            else:
                return await self._passive_liveness_detection(video_path)

        except Exception as e:
            logger.error(f"Liveness detection failed: {e}")
            return {
                'liveness_detected': False,
                'liveness_score': 0.0,
                'confidence': 0.0,
                'method': liveness_type,
                'error': str(e)
            }

    async def _passive_liveness_detection(self, video_path: Path) -> Dict[str, Any]:
        """
        Passive liveness detection using video analysis.
        Analyzes motion, texture, and other passive indicators.
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")

            frames = []
            frame_count = 0
            max_frames = 50

            # Read frames
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % 2 == 0:  # Sample every other frame
                    frames.append(frame)

                frame_count += 1

            cap.release()

            if len(frames) < 3:
                return {
                    'liveness_detected': False,
                    'liveness_score': 0.0,
                    'confidence': 0.0,
                    'method': 'passive',
                    'reason': 'Insufficient frames'
                }

            # Analyze passive indicators
            motion_score = self._analyze_motion(frames)
            texture_score = self._analyze_texture(frames)
            blur_score = self._analyze_blur(frames)

            # Weighted combination
            liveness_score = (
                motion_score * 0.4 +
                texture_score * 0.4 +
                blur_score * 0.2
            )

            # Threshold for liveness
            is_live = liveness_score >= 0.6

            confidence = min(liveness_score * 1.2, 1.0) if is_live else liveness_score * 0.8

            return {
                'liveness_detected': is_live,
                'liveness_score': liveness_score,
                'confidence': confidence,
                'method': 'passive',
                'indicators': {
                    'motion': motion_score,
                    'texture': texture_score,
                    'blur': blur_score
                }
            }

        except Exception as e:
            logger.error(f"Passive liveness detection error: {e}")
            return {
                'liveness_detected': False,
                'liveness_score': 0.0,
                'confidence': 0.0,
                'method': 'passive',
                'error': str(e)
            }

    async def _active_liveness_detection(self, video_path: Path) -> Dict[str, Any]:
        """
        Active liveness detection using challenge-response.
        Analyzes specific actions like blinking, head movement, etc.
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")

            frames = []
            frame_count = 0
            max_frames = 100

            # Read frames
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                frame_count += 1

            cap.release()

            if len(frames) < 10:
                return {
                    'liveness_detected': False,
                    'liveness_score': 0.0,
                    'confidence': 0.0,
                    'method': 'active',
                    'reason': 'Insufficient frames for active analysis'
                }

            # Detect active liveness cues
            blink_score = await self._detect_blinking(frames)
            head_movement_score = self._detect_head_movement(frames)

            # For active liveness, we expect some activity
            # This is simplified - in real implementation, you'd check for specific cues
            active_score = max(blink_score, head_movement_score)

            # Higher threshold for active liveness
            is_live = active_score >= 0.7
            confidence = active_score * 1.1 if is_live else active_score * 0.9

            return {
                'liveness_detected': is_live,
                'liveness_score': active_score,
                'confidence': confidence,
                'method': 'active',
                'indicators': {
                    'blinking': blink_score,
                    'head_movement': head_movement_score
                }
            }

        except Exception as e:
            logger.error(f"Active liveness detection error: {e}")
            return {
                'liveness_detected': False,
                'liveness_score': 0.0,
                'confidence': 0.0,
                'method': 'active',
                'error': str(e)
            }

    def _analyze_motion(self, frames: List[np.ndarray]) -> float:
        """Analyze motion between frames to detect live video."""
        if len(frames) < 2:
            return 0.0

        try:
            # Convert frames to grayscale
            gray_frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]

            motion_scores = []

            # Calculate optical flow between consecutive frames
            for i in range(len(gray_frames) - 1):
                flow = cv2.calcOpticalFlowFarneback(
                    gray_frames[i], gray_frames[i+1], None, 0.5, 3, 15, 3, 5, 1.2, 0
                )

                # Calculate magnitude of motion
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                motion_score = np.mean(mag)

                # Normalize and scale
                motion_scores.append(min(motion_score / 10.0, 1.0))

            avg_motion = np.mean(motion_scores)

            # Live video typically has some motion
            # Too little motion might indicate a still image
            # Too much motion might indicate video replay or poor quality
            if 0.1 <= avg_motion <= 0.8:
                return avg_motion
            elif avg_motion < 0.1:
                return avg_motion * 2  # Penalize too little motion
            else:
                return 0.5  # Cap excessive motion

        except Exception as e:
            logger.warning(f"Motion analysis failed: {e}")
            return 0.5  # Neutral score

    def _analyze_texture(self, frames: List[np.ndarray]) -> float:
        """Analyze texture consistency across frames."""
        if len(frames) < 3:
            return 0.0

        try:
            texture_scores = []

            for frame in frames:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Calculate variance of Laplacian (focus measure)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

                # Normalize (higher values = sharper image)
                texture_score = min(laplacian_var / 500.0, 1.0)
                texture_scores.append(texture_score)

            avg_texture = np.mean(texture_scores)

            # Live videos typically have consistent texture patterns
            # Very low texture might indicate poor quality video
            return max(avg_texture, 0.3)  # Minimum confidence

        except Exception as e:
            logger.warning(f"Texture analysis failed: {e}")
            return 0.5

    def _analyze_blur(self, frames: List[np.ndarray]) -> float:
        """Analyze blur levels to detect video replay attacks."""
        if len(frames) < 1:
            return 0.0

        try:
            blur_scores = []

            for frame in frames:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Calculate blur using Laplacian variance
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

                # Very low blur might indicate compressed/replayed video
                # Very high blur might indicate motion blur (acceptable)
                normalized_blur = min(blur_score / 100.0, 1.0)
                blur_scores.append(normalized_blur)

            avg_blur = np.mean(blur_scores)

            # Prefer moderate blur levels (not too sharp, not too blurry)
            if 0.3 <= avg_blur <= 0.9:
                return avg_blur
            elif avg_blur < 0.3:
                return avg_blur * 1.5  # Penalize too blurry (likely replay)
            else:
                return 0.8  # High blur is acceptable (motion blur)

        except Exception as e:
            logger.warning(f"Blur analysis failed: {e}")
            return 0.5

    async def _detect_blinking(self, frames: List[np.ndarray]) -> float:
        """Detect eye blinking pattern in frames."""
        try:
            blink_patterns = []

            for frame in frames:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect faces first
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

                if len(faces) == 0:
                    continue

                # Use the first (largest) face
                x, y, w, h = faces[0]

                # Region of interest for eyes (upper half of face)
                roi_gray = gray[y:y+h//2, x:x+w]
                roi_color = frame[y:y+h//2, x:x+w]

                # Detect eyes
                eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 3)

                # Heuristic: fewer eyes detected might indicate blinking
                eye_count = len(eyes)
                blink_score = max(0, 3 - eye_count) / 3.0  # 0-1 scale
                blink_patterns.append(blink_score)

            if blink_patterns:
                # Look for blink pattern (alternating high/low)
                avg_blink = np.mean(blink_patterns)
                variation = np.std(blink_patterns)

                # High variation suggests blinking
                blink_confidence = min((avg_blink + variation) / 2.0, 1.0)

                return blink_confidence

            return 0.0

        except Exception as e:
            logger.warning(f"Blink detection failed: {e}")
            return 0.0

    def _detect_head_movement(self, frames: List[np.ndarray]) -> float:
        """Detect head movement patterns."""
        try:
            face_positions = []

            for frame in frames:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

                if len(faces) > 0:
                    x, y, w, h = faces[0]  # Use largest face
                    center_x, center_y = x + w//2, y + h//2
                    face_positions.append((center_x, center_y))

            if len(face_positions) < 5:
                return 0.0

            # Calculate movement variance
            positions = np.array(face_positions)
            position_variance = np.var(positions, axis=0)

            # Average variance in x and y directions
            movement_score = np.mean(position_variance) / 1000.0  # Normalize

            # Scale to 0-1 range
            movement_score = min(movement_score * 10.0, 1.0)

            return movement_score

        except Exception as e:
            logger.warning(f"Head movement detection failed: {e}")
            return 0.0


# Global service instance
liveness_service = LivenessService()