from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime

# Import your modules
from vad import VoiceActivityDetector
from stt import SpeechToText
from tts import TextToSpeech
from turn_manager import TurnManager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
vad = VoiceActivityDetector()
stt = SpeechToText()
tts = TextToSpeech()

def generate_simple_response(user_text):
    """
    Simple rule-based responses (placeholder for LLM)
    """
    text_lower = user_text.lower().strip()
    
    if not text_lower:
        return "I didn't catch that. Could you repeat?"
    
    # Greetings
    if any(word in text_lower for word in ["hello", "hi", "hey"]):
        return "Hello! How can I help you today?"
    
    # Time
    if "time" in text_lower:
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."
    
    # Date
    if "date" in text_lower or "today" in text_lower:
        current_date = datetime.now().strftime("%B %d, %Y")
        return f"Today is {current_date}."
    
    # Weather
    if "weather" in text_lower:
        return "I don't have access to weather data yet, but I can hear you clearly!"
    
    # Name
    if "your name" in text_lower or "who are you" in text_lower:
        return "I'm a voice assistant built from scratch using WebSockets!"
    
    # Help
    if "help" in text_lower:
        return "I can respond to greetings, tell you the time and date, or just repeat what you say!"
    
    # Thank you
    if "thank" in text_lower:
        return "You're welcome!"
    
    # Goodbye
    if any(word in text_lower for word in ["bye", "goodbye", "see you"]):
        return "Goodbye! Have a great day!"
    
    # Default - echo with confirmation
    return f"You said: {user_text}"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 WebSocket connected")
    
    # Initialize turn manager for this connection
    turn_manager = TurnManager()
    
    try:
        while True:
            message = await websocket.receive()

            # Handle binary audio data
            if message.get("bytes"):
                audio_bytes = message["bytes"]
                
                # Step 1: Voice Activity Detection
                is_speech_ended, audio_chunk = vad.process_audio(audio_bytes)
                
                if is_speech_ended and audio_chunk:
                    print(f"🎤 Speech segment complete: {len(audio_chunk)} bytes")
                    
                    # Check if it's user's turn to speak
                    if not turn_manager.is_user_turn():
                        print("⏸️ Assistant is speaking, buffering user audio...")
                        turn_manager.buffer_user_audio(audio_chunk)
                        continue
                    
                    # Step 2: Speech to Text
                    transcript = await stt.transcribe(audio_chunk)
                    
                    if transcript:
                        print(f"👤 User: {transcript}")
                        
                        # Send transcript to frontend
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "user",
                            "text": transcript
                        })
                        
                        # Step 3: Generate Response (Simple rules, no LLM)
                        response_text = generate_simple_response(transcript)
                        print(f"🤖 Assistant: {response_text}")
                        
                        # Send response text to frontend
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "assistant",
                            "text": response_text
                        })
                        
                        # Switch turn to assistant
                        turn_manager.set_assistant_turn()
                        
                        # Step 4: Text to Speech
                        audio_response = await tts.synthesize(response_text)
                        
                        if audio_response:
                            # Send audio in chunks
                            chunk_size = 4096
                            total_sent = 0
                            
                            for i in range(0, len(audio_response), chunk_size):
                                chunk = audio_response[i:i + chunk_size]
                                await websocket.send_bytes(chunk)
                                total_sent += len(chunk)
                                await asyncio.sleep(0.01)  # Smooth streaming
                            
                            print(f"✅ Sent {total_sent} bytes of audio")
                            
                            # Signal end of response
                            await websocket.send_json({
                                "type": "audio_end"
                            })
                            
                            # Switch turn back to user
                            turn_manager.set_user_turn()
                
                else:
                    # Silence detected
                    if vad.is_speech_ended():
                        print("🔇 Speech segment ended")

            # Handle text messages (commands, status updates)
            elif message.get("text"):
                data = json.loads(message["text"])
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "clear_buffer":
                    vad.clear_buffer()
                    turn_manager.reset()
                    await websocket.send_json({"type": "buffer_cleared"})
                
                elif msg_type == "user_stopped_speaking":
                    # Frontend detected user stopped speaking
                    turn_manager.set_assistant_turn()
                
                print(f"💬 Received: {data}")

    except WebSocketDisconnect:
        print("🔴 WebSocket disconnected")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close()
        except:
            pass

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Voice Assistant WebSocket Server",
        "endpoints": {
            "websocket": "/ws",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "components": {
            "vad": "ok",
            "stt": "ok",
            "tts": "ok"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)