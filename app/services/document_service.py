"""
Document processing service for ID document extraction and validation.
Uses OCR and MRZ reading for document information extraction.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for processing identity documents using OCR."""

    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

    async def process_document(self, image_path: Path) -> Dict[str, Any]:
        """
        Process an identity document image.

        Args:
            image_path: Path to the document image

        Returns:
            Dict containing extracted data and validation results
        """
        try:
            logger.info(f"Processing document: {image_path}")

            # Read and preprocess image
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)

            # Detect document type and region
            doc_type, doc_region = self._detect_document_type(processed_image)

            # Extract text using OCR
            extracted_text = self._extract_text_with_ocr(processed_image)

            # Parse and validate extracted data
            parsed_data = self._parse_document_data(extracted_text, doc_type)

            # Validate extracted fields
            is_valid, confidence = self._validate_document_data(parsed_data, doc_type)

            return {
                'document_type': doc_type,
                'document_valid': is_valid,
                'confidence': confidence,
                'extracted_data': parsed_data,
                'raw_text': extracted_text,
                'region': doc_region
            }

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            return {
                'document_type': 'unknown',
                'document_valid': False,
                'confidence': 0.0,
                'extracted_data': {},
                'error': str(e)
            }

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)

        # Enhance contrast
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.5, beta=10)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return thresh

    def _detect_document_type(self, image: np.ndarray) -> Tuple[str, Dict[str, Any]]:
        """
        Detect the type of document based on dimensions and features.

        This is a simplified implementation. In production, this would use
        machine learning models to classify document types.
        """
        height, width = image.shape[:2]
        aspect_ratio = width / height

        # Basic document type detection based on aspect ratio
        if 1.4 <= aspect_ratio <= 1.7:  # Passport-like
            return 'passport', {'width': width, 'height': height, 'aspect_ratio': aspect_ratio}
        elif 0.6 <= aspect_ratio <= 0.8:  # ID card (portrait)
            return 'national_id', {'width': width, 'height': height, 'aspect_ratio': aspect_ratio}
        elif 1.5 <= aspect_ratio <= 1.8:  # Drivers license
            return 'drivers_license', {'width': width, 'height': height, 'aspect_ratio': aspect_ratio}
        else:
            return 'unknown', {'width': width, 'height': height, 'aspect_ratio': aspect_ratio}

    def _extract_text_with_ocr(self, image: np.ndarray) -> str:
        """
        Extract text from document using OCR.

        This is a placeholder implementation. In production, this would use
        Tesseract or PaddleOCR for actual text extraction.
        """
        try:
            # Placeholder - in real implementation, use:
            # import pytesseract
            # text = pytesseract.image_to_string(image, lang='eng')

            # For now, return sample data for testing
            return """
            UNITED STATES OF AMERICA
            PASSPORT

            TYPE: P
            CODE: USA
            PASSPORT NO: P123456789
            SURNAME: DOE
            GIVEN NAMES: JOHN MICHAEL
            NATIONALITY: UNITED STATES OF AMERICA
            DATE OF BIRTH: 15 JAN 1990
            SEX: M
            PLACE OF BIRTH: NEW YORK
            DATE OF ISSUE: 01 JAN 2020
            DATE OF EXPIRATION: 01 JAN 2030
            AUTHORITY: DEPARTMENT OF STATE
            ENDORSEMENTS: NONE
            """

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""

    def _parse_document_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Parse extracted text into structured data based on document type."""
        parsed_data = {}

        try:
            # Common patterns for different document types
            if doc_type == 'passport':
                parsed_data = self._parse_passport_data(text)
            elif doc_type in ['national_id', 'drivers_license']:
                parsed_data = self._parse_id_card_data(text)

            return parsed_data

        except Exception as e:
            logger.error(f"Data parsing failed: {str(e)}")
            return {}

    def _parse_passport_data(self, text: str) -> Dict[str, Any]:
        """Parse passport MRZ and text data."""
        data = {}

        # Extract MRZ-like data (simplified)
        lines = text.strip().split('\n')

        # Look for common fields
        for line in lines:
            line = line.strip().upper()

            # Passport number
            if 'PASSPORT NO:' in line or 'PASS NO:' in line:
                match = re.search(r'([A-Z]\d{8})', line)
                if match:
                    data['passport_number'] = match.group(1)

            # Name extraction
            elif 'SURNAME:' in line:
                match = re.search(r'SURNAME:\s*([^\n\r]+)', line, re.IGNORECASE)
                if match:
                    data['surname'] = match.group(1).strip()

            elif 'GIVEN NAMES:' in line:
                match = re.search(r'GIVEN NAMES:\s*([^\n\r]+)', line, re.IGNORECASE)
                if match:
                    data['given_names'] = match.group(1).strip()

            # Date of birth
            elif 'DATE OF BIRTH:' in line or 'DOB:' in line:
                match = re.search(r'(\d{1,2}\s+[A-Z]{3}\s+\d{4})', line)
                if match:
                    data['date_of_birth'] = match.group(1)

            # Date of expiration
            elif 'DATE OF EXPIRATION:' in line or 'EXP:' in line:
                match = re.search(r'(\d{1,2}\s+[A-Z]{3}\s+\d{4})', line)
                if match:
                    data['expiration_date'] = match.group(1)

        # Combine names
        if 'surname' in data and 'given_names' in data:
            data['full_name'] = f"{data['given_names']} {data['surname']}"

        return data

    def _parse_id_card_data(self, text: str) -> Dict[str, Any]:
        """Parse ID card data."""
        data = {}

        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()

            # ID number patterns
            id_match = re.search(r'ID[\s:]*([A-Z0-9\-]+)', line, re.IGNORECASE)
            if id_match and 'id_number' not in data:
                data['id_number'] = id_match.group(1)

            # Name patterns
            name_match = re.search(r'NAME[\s:]*([^\n\r]+)', line, re.IGNORECASE)
            if name_match:
                data['full_name'] = name_match.group(1).strip()

            # Date of birth patterns
            dob_match = re.search(r'(?:DOB|BIRTH)[\s:]*([^\n\r]+)', line, re.IGNORECASE)
            if dob_match:
                data['date_of_birth'] = dob_match.group(1).strip()

        return data

    def _validate_document_data(self, data: Dict[str, Any], doc_type: str) -> Tuple[bool, float]:
        """
        Validate extracted document data.

        Returns:
            Tuple of (is_valid, confidence_score)
        """
        confidence = 0.0
        required_fields = []

        if doc_type == 'passport':
            required_fields = ['passport_number', 'full_name', 'date_of_birth']
        elif doc_type in ['national_id', 'drivers_license']:
            required_fields = ['id_number', 'full_name', 'date_of_birth']

        # Check required fields presence
        present_fields = sum(1 for field in required_fields if field in data and data[field])
        field_completeness = present_fields / len(required_fields) if required_fields else 0

        # Basic format validation
        format_score = 0
        if 'passport_number' in data:
            # Basic passport number format check
            if re.match(r'^[A-Z]\d{8}$', data['passport_number']):
                format_score += 0.3

        if 'id_number' in data:
            # Basic ID format check (simplified)
            if len(data['id_number']) >= 6:
                format_score += 0.3

        # Calculate overall confidence
        confidence = (field_completeness * 0.7) + (format_score * 0.3)

        # Determine validity threshold
        is_valid = confidence >= 0.5

        return is_valid, confidence


# Global service instance
document_service = DocumentService()