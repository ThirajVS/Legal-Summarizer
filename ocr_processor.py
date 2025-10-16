import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
from typing import Optional
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class OCRProcessor:
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
    
    async def extract_text(self, file_path: str) -> str:
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return await self._extract_from_pdf(file_path)
        elif file_ext in self.supported_formats:
            return await self._extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    async def _extract_from_image(self, image_path: str) -> str:
        
        try:
            img = cv2.imread(image_path)
            preprocessed = self._preprocess_image(img)
            pil_image = Image.fromarray(preprocessed)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            return text
        except Exception as e:
            print(f"OCR error: {e}")
            raise
    
    async def _extract_from_pdf(self, pdf_path: str) -> str:
        
        try:
            pages = pdf2image.convert_from_path(pdf_path, dpi=300)
            extracted_text = ""
            for i, page in enumerate(pages):
                print(f"Processing page {i+1}/{len(pages)}")
                page_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                preprocessed = self._preprocess_image(page_cv)
                pil_image = Image.fromarray(preprocessed)
                text = pytesseract.image_to_string(pil_image)
                extracted_text += text + "\n\n"
            return extracted_text
        except Exception as e:
            print(f"PDF OCR error: {e}")
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        deskewed = self._deskew(thresh)
        return deskewed
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    
    def extract_tables(self, image_path: str):
        pass
