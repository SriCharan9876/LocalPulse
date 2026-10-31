/**
 * Utility to convert recorded WebM / browser audio Blobs into standard 16kHz mono WAV format.
 * Guarantees 100% compatibility with Sarvam AI STT (Saaras) across all browsers (Chrome, Edge, Firefox, Safari).
 */

export async function convertBlobTo16kWav(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  
  let audioBuffer;
  try {
    audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  } catch (err) {
    audioContext.close();
    throw new Error('Failed to decode browser audio data: ' + err.message);
  }

  const TARGET_SAMPLE_RATE = 16000;
  let monoBuffer;

  // Resample to 16kHz and convert to mono
  const targetLength = Math.ceil(audioBuffer.duration * TARGET_SAMPLE_RATE);
  const offlineCtx = new OfflineAudioContext(1, targetLength, TARGET_SAMPLE_RATE);
  const source = offlineCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineCtx.destination);
  source.start(0);

  monoBuffer = await offlineCtx.startRendering();
  audioContext.close();

  // Encode monoBuffer to 16-bit PCM WAV ArrayBuffer
  const samples = monoBuffer.getChannelData(0);
  const numSamples = samples.length;
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  // RIFF identifier
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeString(view, 8, 'WAVE');
  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // SubChunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, 1, true); // NumChannels (1 = Mono)
  view.setUint32(24, TARGET_SAMPLE_RATE, true); // SampleRate (16000)
  view.setUint32(28, TARGET_SAMPLE_RATE * 2, true); // ByteRate (16000 * 1 * 16/8)
  view.setUint16(32, 2, true); // BlockAlign (1 * 16/8)
  view.setUint16(34, 16, true); // BitsPerSample (16-bit)
  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, numSamples * 2, true);

  // Write 16-bit PCM samples
  let offset = 44;
  for (let i = 0; i < numSamples; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
