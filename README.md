# WildlifeGuard

AI-powered wildlife detection, multi-object tracking, observable behaviour analysis, and farm encounter-risk assessment from uploaded camera-trap videos.

## Features

- **Video Ingestion & Storage:** Secure upload pipeline (MP4, AVI, MOV, MKV) with UUID-based storage, metadata extraction (FPS, resolution, duration), and thumbnail generation.
- **Video Management & Cleanup:** Delete videos with automated cascading cleanup across database records, extracted frames, thumbnails, and annotated overlays.
- **Interactive Farm Boundary Editor:** Canvas overlay allows users to draw and save custom polygonal farm boundaries directly on video frames.
- **Wildlife Detection & Classification:** Frame extraction with configurable sampling rates, crop classification, and confidence scoring.
- **Multi-Object Tracking (ByteIoUTracker):** Persistent ID assignment across frames, trajectory mapping, net displacement, and pixel velocity calculation.
- **Observable Behaviour Model:** Rule-based trajectory analysis classifying states such as `Stationary`, `Walking`, `Running`, and `Rapid Approach`.
- **Physical Risk Assessment Engine:** Proximity-to-boundary metrics, directional approach vectors, and movement dynamics mapped to risk levels (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) with factor breakdowns.
- **Annotated Video Rendering:** Overlay rendering bounding boxes, track IDs, trajectory trails, and risk tags directly onto output video.
- **Dual-Video Playback Synchronization:** Side-by-side player comparing original camera-trap footage with AI overlays in lockstep with synchronized play, pause, and seeking.
- **Data Export & Reporting:** One-click download of comprehensive analysis reports in both CSV and JSON formats for ecological research and farm records.
- **Frontend Dashboard & Analytics:** React + TypeScript + Tailwind CSS interface featuring interactive video player, animal trajectory inspector modal, chronological risk events timeline, searchable filters, and aggregate analytics charts (Recharts).

---

## Disclaimer

This system provides an AI-assisted assessment of observable wildlife movement and proximity patterns. It does not determine an animal's intentions or guarantee that an animal is dangerous. Risk scores are estimates and should not replace human judgment or expert wildlife guidance.

---

## How to Run the Software

### 1. Prerequisites
- **Python 3.10+** (tested on Python 3.13)
- **Node.js 18+** & **npm**
- **FFmpeg / OpenCV** dependencies

---

### 2. Backend Setup & Run

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Activate the virtual environment:
   - **Windows (Command Prompt / PowerShell):**
     ```cmd
     .venv\Scripts\activate
     ```
     *(If using PowerShell and script execution is restricted, run: `powershell -ExecutionPolicy Bypass` or execute `.venv\Scripts\python.exe -m uvicorn ...` directly)*
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```

3. (Optional) If setting up fresh, install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   *Alternative direct command on Windows:*
   ```cmd
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. Verify backend is running:
   - Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
   - Interactive Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 3. Frontend Setup & Run

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```

3. Start the Vite development server:
   - **Windows (Command Prompt or PowerShell):**
     ```cmd
     npm run dev
     ```
     *(Or `npm.cmd run dev` if PowerShell scripts are disabled)*

4. Open your browser at:
   - **[http://localhost:5173](http://localhost:5173)**

---

### 4. Running the Tests

To run the automated backend test suite (33 unit & integration tests covering geometry, tracking, behavior, risk engine, uploads, video deletion, report export, and end-to-end pipeline):

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v
```

To verify the TypeScript frontend build:
```bash
cd frontend
npm run build
```
