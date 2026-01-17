/**
 * Audio Input Worklet Processor
 * Captures microphone audio and sends it to the main thread
 */

class AudioInputProcessor extends AudioWorkletProcessor {
  constructor() {
    super();

    // Buffer size (in samples)
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;

    console.log("✅ AudioInputProcessor initialized");
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];

    // Check if we have input
    if (!input || input.length === 0) {
      return true;
    }

    // Get first channel (mono)
    const inputChannel = input[0];

    if (!inputChannel) {
      return true;
    }

    // Add samples to buffer
    for (let i = 0; i < inputChannel.length; i++) {
      this.buffer[this.bufferIndex++] = inputChannel[i];

      // When buffer is full, send it to main thread
      if (this.bufferIndex >= this.bufferSize) {
        // Create a copy to send
        const bufferCopy = new Float32Array(this.buffer);
        this.port.postMessage(bufferCopy);

        // Reset buffer
        this.bufferIndex = 0;
      }
    }

    // Keep processor alive
    return true;
  }
}

registerProcessor("audio-input-processor", AudioInputProcessor);
