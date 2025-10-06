"""
Face recognition service for biometric verification.
Handles face detection, embedding generation, and similarity comparison.
"""

import cv2
import numpy as np
import torch
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import io

# Import face recognition models
try:
    from facenet_pytorch import MTCNN, InceptionResnetV1
    FACENET_AVAILABLE = True
except ImportError:
    FACENET_AVAILABLE = False
    logging.getLogger(__name__).warning("FaceNet not available. Using basic OpenCV fallback.")

logger = logging.getLogger(__name__)


class FaceService:
    """Service for face detection and recognition using ML models."""

    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.mtcnn = None
        self.resnet = None

        if FACENET_AVAILABLE:
            self._load_models()
        else:
            logger.warning("FaceNet models not available, using OpenCV Haar cascades")
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

    def _load_models(self):
        """Load FaceNet models for face detection and recognition."""
        try:
            # Load MTCNN for face detection
            self.mtcnn = MTCNN(
                image_size=160, margin=0, min_face_size=20,
                thresholds=[0.6, 0.7, 0.7], factor=0.709, post_process=True,
                device=self.device
            )

            # Load Inception ResNet for face embeddings
            self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

            logger.info(f"Face recognition models loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load face models: {e}")
            FACENET_AVAILABLE = False

    async def extract_face_from_document(self, image_path: Path) -> Dict[str, Any]:
        """
        Extract face from identity document.

        Args:
            image_path: Path to document image

        Returns:
            Dict with face detection results and embedding
        """
        try:
            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            if FACENET_AVAILABLE and self.mtcnn and self.resnet:
                return await self._extract_with_facenet(image_rgb)
            else:
                return await self._extract_with_opencv(image_rgb)

        except Exception as e:
            logger.error(f"Face extraction from document failed: {e}")
            return {
                'face_detected': False,
                'confidence': 0.0,
                'embedding': None,
                'error': str(e)
            }

    async def extract_face_from_selfie(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract best face from selfie video.

        Args:
            video_path: Path to selfie video

        Returns:
            Dict with face detection results and embedding
        """
        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")

            frames = []
            embeddings = []
            confidences = []

            # Process up to 30 frames
            max_frames = 30
            frame_count = 0

            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                # Skip frames to get better variety
                if frame_count % 3 == 0:  # Process every 3rd frame
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    if FACENET_AVAILABLE and self.mtcnn and self.resnet:
                        result = await self._extract_with_facenet(frame_rgb)
                    else:
                        result = await self._extract_with_opencv(frame_rgb)

                    if result['face_detected']:
                        frames.append(frame_rgb)
                        embeddings.append(result['embedding'])
                        confidences.append(result['confidence'])

                frame_count += 1

            cap.release()

            if not embeddings:
                return {
                    'face_detected': False,
                    'confidence': 0.0,
                    'embedding': None,
                    'error': 'No faces detected in video'
                }

            # Select best face (highest confidence)
            best_idx = np.argmax(confidences)

            return {
                'face_detected': True,
                'confidence': confidences[best_idx],
                'embedding': embeddings[best_idx],
                'frame_count': len(embeddings)
            }

        except Exception as e:
            logger.error(f"Face extraction from selfie failed: {e}")
            return {
                'face_detected': False,
                'confidence': 0.0,
                'embedding': None,
                'error': str(e)
            }

    async def _extract_with_facenet(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """Extract face using FaceNet models."""
        try:
            # Detect face
            with torch.no_grad():
                boxes, probs = self.mtcnn.detect(image_rgb)

            if boxes is None or len(boxes) == 0:
                return {'face_detected': False, 'confidence': 0.0, 'embedding': None}

            # Use the face with highest probability
            best_prob_idx = np.argmax(probs)
            box = boxes[best_prob_idx]
            prob = probs[best_prob_idx]

            # Extract face region
            face = self.mtcnn.extract(image_rgb, boxes, save_path=None)[best_prob_idx]

            if face is None:
                return {'face_detected': False, 'confidence': 0.0, 'embedding': None}

            # Generate embedding
            with torch.no_grad():
                face_tensor = torch.unsqueeze(face, 0).to(self.device)
                embedding = self.resnet(face_tensor).cpu().numpy().flatten()

            return {
                'face_detected': True,
                'confidence': float(prob),
                'embedding': embedding.tolist(),
                'bbox': box.tolist()
            }

        except Exception as e:
            logger.error(f"FaceNet extraction failed: {e}")
            return {'face_detected': False, 'confidence': 0.0, 'embedding': None, 'error': str(e)}

    async def _extract_with_opencv(self, image_rgb: np.ndarray) -> Dict[str, Any]:
        """Extract face using OpenCV Haar cascades (fallback)."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            if len(faces) == 0:
                return {'face_detected': False, 'confidence': 0.0, 'embedding': None}

            # Use largest face
            largest_face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = largest_face

            # Extract face region
            face_roi = image_rgb[y:y+h, x:x+w]

            # Simple embedding (just average pixel values for demo)
            # In real implementation, you'd use a proper face embedding model
            embedding = np.mean(face_roi.reshape(-1, 3), axis=0).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize

            confidence = 0.5  # Low confidence for OpenCV fallback

            return {
                'face_detected': True,
                'confidence': confidence,
                'embedding': embedding.tolist(),
                'bbox': [x, y, w, h]
            }

        except Exception as e:
            logger.error(f"OpenCV extraction failed: {e}")
            return {'face_detected': False, 'confidence': 0.0, 'embedding': None, 'error': str(e)}

    async def compare_faces(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compare two face embeddings and return similarity score.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            if not embedding1 or not embedding2 or len(embedding1) != len(embedding2):
                return 0.0

            # Convert to numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)

            # Normalize embeddings
            emb1_norm = emb1 / np.linalg.norm(emb1)
            emb2_norm = emb2 / np.linalg.norm(emb2)

            # Calculate cosine similarity
            similarity = np.dot(emb1_norm, emb2_norm)

            # Ensure similarity is between 0 and 1
            similarity = max(0.0, min(1.0, similarity))

            return float(similarity)

        except Exception as e:
            logger.error(f"Face comparison failed: {e}")
            return 0.0


# Global service instance
face_service = FaceService()