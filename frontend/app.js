// ======== DOM Elements ========
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusDiv = document.getElementById("status");
const levelDiv = document.getElementById("level");
const transcriptDiv = document.getElementById("transcript");
const rings = document.querySelectorAll(".ring");

// ======== Globals ========
let socket;
let audioContext;
let source;
let inputWorkletNode;
let analyser;
let dataArray;
let isRecording = false;

// ======== Audio Playback Queue ========
let playQueue = [];
let isPlaying = false;

// ======== Start Recording ========
startBtn.onclick = async () => {
  if (isRecording) return;

  try {
    updateStatus("🔄 Initializing...");

    audioContext = new AudioContext({ sampleRate: 16000 });

    if (audioContext.state === "suspended") {
      await audioContext.resume();
      console.log("✅ AudioContext resumed");
    }

    socket = new WebSocket("ws://localhost:8000/ws");
    socket.binaryType = "arraybuffer";

    socket.onopen = () => {
      console.log("✅ WebSocket connected");
      updateStatus("🟢 Connected - Listening...");
    };

    socket.onerror = (error) => {
      console.error("❌ WebSocket error:", error);
      updateStatus("❌ Connection error");
    };

    socket.onclose = () => {
      console.log("🔴 WebSocket closed");
      updateStatus("🔴 Disconnected");
      stopRecording();
    };

    // Handle incoming messages
    socket.onmessage = (event) => {
      // 1️⃣ Handle text / JSON
      if (typeof event.data === "string") {
        try {
          const data = JSON.parse(event.data);
          handleJsonMessage(data);
        } catch {
          console.log("📝 Text:", event.data);
          addTranscript(event.data);
        }
        return;
      }

      // 2️⃣ Handle binary audio ONLY
      if (event.data instanceof ArrayBuffer) {
        playAudioNew(event.data);
      }
    };

    // Get microphone access
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 16000,
        channelCount: 1,
      },
    });

    // Setup voice animation
    setupVoiceAnimation(stream);

    // Load audio input worklet
    await audioContext.audioWorklet.addModule("audio-input-worklet.js");
    console.log("✅ Audio worklet loaded");

    // Create audio pipeline
    source = audioContext.createMediaStreamSource(stream);
    inputWorkletNode = new AudioWorkletNode(
      audioContext,
      "audio-input-processor"
    );

    // Handle audio from worklet
    inputWorkletNode.port.onmessage = (event) => {
      const float32 = event.data;

      // Send to backend
      if (socket && socket.readyState === WebSocket.OPEN) {
        const pcm16 = float32ToPCM16(float32);
        socket.send(pcm16);
      }
    };

    // Connect audio nodes
    source.connect(inputWorkletNode);

    isRecording = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    updateStatus("🎤 Recording...");
  } catch (error) {
    console.error("❌ Error starting:", error);
    updateStatus("❌ Error: " + error.message);
    alert("Failed to start: " + error.message);
  }
};

// ======== Stop Recording ========
stopBtn.onclick = () => {
  stopRecording();
};

function playAudio(pcmBuffer) {
  const pcm16 = new Int16Array(pcmBuffer);
  const float32 = new Float32Array(pcm16.length);

  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / 32768;
  }

  const buffer = audioContext.createBuffer(1, float32.length, 16000);
  buffer.getChannelData(0).set(float32);

  const src = audioContext.createBufferSource();
  src.buffer = buffer;
  src.connect(audioContext.destination);
  src.start();
}

function playAudioNew(pcmBuffer) {
  if (!pcmBuffer || pcmBuffer.byteLength === 0) return;

  const pcm16 = new Int16Array(pcmBuffer);
  if (pcm16.length === 0) return;

  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / 32768;
  }

  const buffer = audioContext.createBuffer(1, float32.length, 16000);
  buffer.getChannelData(0).set(float32);

  const src = audioContext.createBufferSource();
  src.buffer = buffer;
  src.connect(audioContext.destination);
  src.start();
}

function stopRecording() {
  if (!isRecording) return;

  console.log("⏹️ Stopping recording...");

  // Disconnect audio nodes
  if (inputWorkletNode) {
    inputWorkletNode.disconnect();
    inputWorkletNode = null;
  }

  if (source) {
    source.disconnect();

    // Stop all tracks
    const stream = source.mediaStream;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    source = null;
  }

  // Close WebSocket
  if (socket) {
    socket.close();
    socket = null;
  }

  // Close AudioContext
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  // Clear playback queue
  playQueue = [];
  isPlaying = false;

  isRecording = false;
  startBtn.disabled = false;
  stopBtn.disabled = true;
  updateStatus("⏸️ Stopped");
}

// ======== Audio Playback ========
function playAudioQueue() {
  if (isPlaying || playQueue.length === 0) return;

  isPlaying = true;
  const float32 = playQueue.shift();

  try {
    const buffer = audioContext.createBuffer(1, float32.length, 16000);
    buffer.getChannelData(0).set(float32);

    const bufferSource = audioContext.createBufferSource();
    bufferSource.buffer = buffer;
    bufferSource.connect(audioContext.destination);

    bufferSource.onended = () => {
      isPlaying = false;
      if (playQueue.length > 0) {
        playAudioQueue();
      } else {
        updateStatus("🎤 Listening...");
      }
    };

    updateStatus("🔊 Speaking...");
    bufferSource.start();
  } catch (error) {
    console.error("❌ Playback error:", error);
    isPlaying = false;
  }
}

// ======== JSON Message Handler ========
function handleJsonMessage(data) {
  console.log("📩 Message:", data);

  switch (data.type) {
    case "transcript":
      const prefix = data.role === "user" ? "👤 USER:" : "🤖 AI:";
      addTranscript(`${prefix} ${data.text}`, data.role);
      break;

    case "audio_end":
      console.log("✅ Audio playback complete");
      break;

    case "buffer_cleared":
      console.log("🧹 Buffer cleared");
      break;

    case "pong":
      console.log("🏓 Pong received");
      break;

    default:
      console.log("❓ Unknown message type:", data.type);
  }
}

// ======== Helper Functions ========

// Convert Float32 to PCM16
function float32ToPCM16(float32Array) {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm16.buffer;
}

// Update status display
function updateStatus(message) {
  if (statusDiv) {
    statusDiv.textContent = message;
  }
  console.log("📊 Status:", message);
}

// Add transcript to display
function addTranscript(text, role = null) {
  if (!transcriptDiv) return;

  const p = document.createElement("p");
  p.textContent = text;
  p.style.marginBottom = "8px";

  // Color code by role
  if (role === "user" || text.includes("USER:")) {
    p.style.color = "#00e5ff";
  } else if (role === "assistant" || text.includes("AI:")) {
    p.style.color = "#00ff88";
  }

  transcriptDiv.appendChild(p);
  transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
}

// Setup voice animation
function setupVoiceAnimation(stream) {
  const audioCtx = new AudioContext();
  const src = audioCtx.createMediaStreamSource(stream);

  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  dataArray = new Uint8Array(analyser.frequencyBinCount);

  src.connect(analyser);

  animateRings();

  // Optional: Show volume level
  setInterval(() => {
    if (!analyser) return;

    analyser.getByteTimeDomainData(dataArray);
    const rms = Math.sqrt(
      dataArray.reduce((sum, v) => sum + Math.pow((v - 128) / 128, 2), 0) /
        dataArray.length
    );

    if (levelDiv) {
      const percent = Math.min(100, Math.round(rms * 100));
      levelDiv.textContent = `Mic Level: ${percent}%`;
    }
  }, 100);
}

// Animate rings based on audio
function animateRings() {
  if (!analyser) return;

  analyser.getByteFrequencyData(dataArray);
  const volume = dataArray.reduce((sum, v) => sum + v, 0) / dataArray.length;

  rings.forEach((ring) => {
    const scale = 0.6 + volume / 300;
    ring.style.transform = `scale(${scale})`;
  });

  requestAnimationFrame(animateRings);
}

// ======== Keyboard Shortcuts ========
document.addEventListener("keydown", (e) => {
  // Space to start/stop
  if (e.code === "Space" && !e.repeat) {
    e.preventDefault();
    if (isRecording) {
      stopRecording();
    } else {
      startBtn.click();
    }
  }

  // Escape to stop
  if (e.code === "Escape" && isRecording) {
    stopRecording();
  }
});

// ======== Cleanup on page unload ========
window.addEventListener("beforeunload", () => {
  if (isRecording) {
    stopRecording();
  }
});

console.log("✅ Voice Assistant loaded");
console.log("💡 Shortcuts: Space = start/stop, Escape = stop");
