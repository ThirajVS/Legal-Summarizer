import whisper
import os
from typing import Optional

class AudioProcessor:
    
    def __init__(self, model_size: str = 'base'):
        
        print(f" Loading Whisper {model_size} model...")
        self.model = whisper.load_model(model_size)
        print(" Whisper model loaded")
        
        self.supported_formats = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    
    async def transcribe(self, audio_path: str, language: str = 'en') -> str:
        
        file_ext = os.path.splitext(audio_path)[1].lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_ext}")
        
        try:
            print(f" Transcribing audio: {audio_path}")
            
            result = self.model.transcribe(
                audio_path,
                language=language,
                task='transcribe',
                verbose=False
            )
            
            text = result['text']
            
            print(f" Transcription complete: {len(text)} characters")
            
            return text
            
        except Exception as e:
            print(f" Transcription error: {e}")
            raise
    
    def transcribe_with_timestamps(self, audio_path: str):
        
        result = self.model.transcribe(
            audio_path,
            word_timestamps=True
        )
        
        return result['segments']
    
    def detect_language(self, audio_path: str) -> str:
        
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
        
        _, probs = self.model.detect_language(mel)
        detected_lang = max(probs, key=probs.get)
        
        return detected_lang
    
    def transcribe_multilingual(self, audio_path: str) -> str:
        
        detected_lang = self.detect_language(audio_path)
        print(f" Detected language: {detected_lang}")
        
        return self.transcribe(audio_path, language=detected_lang)
