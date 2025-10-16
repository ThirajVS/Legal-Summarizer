from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import uuid
import asyncio
import glob
from preprocessing import PreprocessingModule
from summarizer import summarize_text
from ocr_processor import OCRProcessor
from audio_processor import AudioProcessor

app = FastAPI(title="Legal Summarizer API", version="Offline-1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

preprocessing_module = PreprocessingModule()
ocr_processor = OCRProcessor()
audio_processor = AudioProcessor()

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

processing_queue = asyncio.Queue()

async def agentic_processor():
    print("Agentic processor active")
    while True:
        try:
            file_data = await processing_queue.get()
            case_id = file_data['case_id']
            file_path = file_data['file_path']
            file_type = file_data['file_type']

            print(f"Processing {case_id} ({file_type})")

            if file_type in ['pdf', 'image']:
                extracted_text = await ocr_processor.extract_text(file_path)
            elif file_type == 'audio':
                extracted_text = await audio_processor.transcribe(file_path)
            elif file_type == 'text':
                if file_path.endswith(".docx"):
                    from docx import Document
                    doc = Document(file_path)
                    extracted_text = "\n".join([p.text for p in doc.paragraphs])
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        extracted_text = f.read()
            else:
                raise Exception("Unsupported file type during processing")

            cleaned_text = preprocessing_module.clean_text(extracted_text)
            summary = summarize_text(cleaned_text)

            result_path = os.path.join(DATA_DIR, f"{case_id}_summary.txt")
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(summary)

            print(f"Completed {case_id}")
        except Exception as e:
            print(f"Error processing {case_id if 'case_id' in locals() else ''}: {e}")
        finally:
            await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    print("Starting Offline Legal Summarizer API")
    asyncio.create_task(agentic_processor())
    print("System ready (no internet required)")

@app.get("/")
async def root():
    return {"service": "Legal Summarizer API (Offline)", "status": "running"}

@app.get("/api/cases")
async def list_cases():
    summaries = []
    for path in glob.glob(os.path.join(DATA_DIR, "*_summary.txt")):
        case_id = os.path.basename(path).split("_summary.txt")[0]
        summaries.append({
            "case_id": case_id,
            "file_name": case_id.split("-", 1)[-1],
            "summary_path": path
        })
    return {"cases": summaries}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        case_id = f"CASE-{datetime.now().year}-{str(uuid.uuid4())[:8]}"
        ext = file.filename.split('.')[-1].lower()

        if ext in ['txt', 'doc', 'docx']:
            file_type = 'text'
        elif ext in ['pdf', 'jpg', 'jpeg', 'png']:
            file_type = 'image'
        elif ext in ['mp3', 'wav', 'm4a']:
            file_type = 'audio'
        else:
            raise HTTPException(400, "Unsupported file type")

        save_path = os.path.join(UPLOAD_DIR, f"{case_id}_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(await file.read())

        await processing_queue.put({
            "case_id": case_id,
            "file_path": save_path,
            "file_type": file_type
        })

        return {"success": True, "case_id": case_id, "status": "queued"}

    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

@app.get("/api/result/{case_id}")
async def get_summary(case_id: str):
    result_path = os.path.join(DATA_DIR, f"{case_id}_summary.txt")
    if not os.path.exists(result_path):
        return JSONResponse(status_code=404, content={"error": "Case not processed yet"})
    with open(result_path, "r", encoding="utf-8") as f:
        summary = f.read()
    return {"case_id": case_id, "summary": summary}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
