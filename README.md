Prerequisites                                                                                                     
                                                                                                                    
  - Python 3.10+                                                                                                    
  - Node.js 18+                                                                                                     
  - Ollama installed and running

  Steps

  1. Clone the repo
  git clone https://github.com/Cryptxnaut/SIGNAL.git
  cd SIGNAL

  2. Start Ollama + pull the model
  ollama pull qwen2.5:72b
  ollama serve

  3. Backend (new terminal)
  cd backend
  pip install -r requirements.txt
  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  4. Frontend (new terminal)
  cd frontend
  npm install
  npm start

  5. Open http://localhost:3000

  ---
  Optional: Use the ASUS GX10 for the LLM (faster)

  # In a separate terminal — keep open
  ssh -L 11434:localhost:11434 asus@<gx10-ip>
  Then run steps 3-5 as normal. SIGNAL will automatically use the GX10's Qwen model.
