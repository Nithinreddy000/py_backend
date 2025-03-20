import numpy as np
import os
import sys

# Create OCR wrapper class that tries multiple OCR systems
class MultiOCR:
    def __init__(self, use_gpu=False):
        self.readers = []
        self.reader_names = []
        
        # Try to initialize EasyOCR
        try:
            import easyocr
            model_dir = "/root/.EasyOCR/model"
            print("Initializing EasyOCR...")
            easy_reader = easyocr.Reader(['en'], gpu=use_gpu, 
                            model_storage_directory=model_dir, 
                            download_enabled=False,  # Don't download again
                            user_network_directory=model_dir, 
                            recog_network="english_g2")
            
            # Define wrapper to standardize output format
            def easy_wrapper(image, **kwargs):
                return easy_reader.readtext(image, **kwargs)
                
            self.readers.append(easy_wrapper)
            self.reader_names.append("EasyOCR")
            print("EasyOCR initialized successfully")
        except Exception as e:
            print(f"Error initializing EasyOCR: {e}")
        
        # Try to initialize PaddleOCR
        try:
            from paddleocr import PaddleOCR
            print("Initializing PaddleOCR...")
            paddle_reader = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=use_gpu)
            
            # Define wrapper to standardize output format
            def paddle_wrapper(image, **kwargs):
                results = paddle_reader.ocr(image, cls=True)
                # Convert PaddleOCR format to EasyOCR format
                standardized = []
                if results and len(results) > 0 and results[0]:
                    for line in results[0]:
                        if len(line) == 2:  # bbox, (text, confidence)
                            bbox, (text, conf) = line
                            # PaddleOCR returns 4 points, EasyOCR wants 4 points too
                            standardized.append([bbox, text, conf])
                return standardized
                
            self.readers.append(paddle_wrapper)
            self.reader_names.append("PaddleOCR")
            print("PaddleOCR initialized successfully")
        except Exception as e:
            print(f"Error initializing PaddleOCR: {e}")
        
        # Add a fallback OCR using OpenCV + Tesseract if available
        try:
            import pytesseract
            import cv2
            
            def tesseract_wrapper(image, **kwargs):
                # Convert to grayscale if needed
                if len(image.shape) == 3:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                else:
                    gray = image
                    
                # Apply threshold to get binary image
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                
                # Perform OCR
                data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
                
                # Convert to EasyOCR format
                results = []
                for i in range(len(data["text"])):
                    if data["text"][i].strip():
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        # Create bbox in format [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                        bbox = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                        conf = float(data["conf"][i]) / 100.0
                        results.append([bbox, data["text"][i], conf])
                return results
                
            self.readers.append(tesseract_wrapper)
            self.reader_names.append("Tesseract")
            print("Tesseract OCR initialized successfully")
        except Exception as e:
            print(f"Tesseract not available: {e}")
        
        # Always add a dummy reader as final fallback
        def dummy_wrapper(image, **kwargs):
            return []
            
        self.readers.append(dummy_wrapper)
        self.reader_names.append("Dummy")
        
        print(f"MultiOCR initialized with {len(self.readers)} readers: {self.reader_names}")
    
    def readtext(self, image, **kwargs):
        """Try all readers in sequence until one works."""
        for i, (reader, name) in enumerate(zip(self.readers, self.reader_names)):
            try:
                results = reader(image, **kwargs)
                if results:  # Only return if we got actual results
                    print(f"Using {name} OCR results: {len(results)} items found")
                    return results
            except Exception as e:
                print(f"Error with {name} OCR: {e}")
                # Continue to next reader
        
        # If all readers failed, return empty list
        return []

# Test the MultiOCR class if run directly
if __name__ == "__main__":
    import cv2
    import time
    import tempfile
    
    # Create a test image
    test_img = np.zeros((100, 200), dtype=np.uint8)
    cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
    test_path = os.path.join(tempfile.gettempdir(), "multiocr_test.jpg")
    cv2.imwrite(test_path, test_img)
    
    # Initialize MultiOCR
    ocr = MultiOCR(use_gpu=False)
    
    # Test it
    start_time = time.time()
    results = ocr.readtext(test_path)
    elapsed = time.time() - start_time
    
    print(f"MultiOCR test results: {results}")
    print(f"OCR completed in {elapsed:.2f} seconds") 