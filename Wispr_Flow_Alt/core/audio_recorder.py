"""
Audio recording module with microphone capture and Voice Activity Detection (VAD).
"""

import time
import queue
import logging
import tempfile
import threading
from math import gcd
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd
import scipy.signal
from scipy.io import wavfile

logger = logging.getLogger(__name__)

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

from config import (
    SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD, SILENCE_DURATION,
    MAX_RECORDING_SECONDS, NOISE_CANCELLATION_ENABLED,
    NOISE_HIGHPASS_CUTOFF, NOISE_REDUCTION_PROP
)

class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        silence_threshold: float = SILENCE_THRESHOLD,
        silence_duration: float = SILENCE_DURATION,
        max_duration: float = MAX_RECORDING_SECONDS,
        noise_cancellation: Optional[bool] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.noise_cancellation = (
            noise_cancellation if noise_cancellation is not None else NOISE_CANCELLATION_ENABLED
        )

        self.audio_queue = queue.Queue()
        self.is_recording = False
        self._stop_event = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self._recorded_chunks = []
        self._record_start_time = 0.0
        self._actual_sample_rate = sample_rate
        self._actual_channels = channels

    def _find_best_input_parameters(self) -> Tuple[Optional[int], int, int]:
        """
        Dynamically negotiates a compatible input device, sample rate, and channel count.
        Essential on Windows (WASAPI) where devices reject 16kHz or 1-channel capture.
        Returns: (device_index, actual_sample_rate, actual_channels)
        """
        try:
            default_dev_idx = sd.default.device[0]
        except Exception:
            default_dev_idx = None

        candidate_devices = []
        if default_dev_idx is not None and default_dev_idx >= 0:
            candidate_devices.append(default_dev_idx)

        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if idx not in candidate_devices and dev.get("max_input_channels", 0) > 0:
                    candidate_devices.append(idx)
        except Exception as e:
            logger.warning(f"Failed querying audio devices: {e}")

        if not candidate_devices:
            raise RuntimeError("No audio input devices found. Please connect a microphone and ensure access is enabled.")

        for dev_idx in candidate_devices:
            try:
                dev_info = sd.query_devices(dev_idx, "input")
            except Exception:
                continue

            native_rate = int(dev_info.get("default_samplerate", 48000))
            max_in_channels = int(dev_info.get("max_input_channels", 1))
            native_channels = max(1, min(2, max_in_channels))

            # Strategy / order of preference:
            # 1. Target settings (16kHz mono) - ideal, zero resampling needed
            # 2. Target rate, native channels (16kHz stereo)
            # 3. Native rate, mono (e.g. 48kHz mono)
            # 4. Native rate, native channels (e.g. 48kHz stereo) - standard Windows WASAPI
            # 5. Standard fallback rates: 48000, 44100
            param_trials = [
                (self.sample_rate, self.channels),
                (self.sample_rate, native_channels),
                (native_rate, 1),
                (native_rate, native_channels),
                (48000, native_channels),
                (48000, 1),
                (44100, native_channels),
                (44100, 1),
            ]

            seen = set()
            unique_trials = []
            for rate, ch in param_trials:
                if (rate, ch) not in seen and ch <= max_in_channels:
                    seen.add((rate, ch))
                    unique_trials.append((rate, ch))

            for rate, ch in unique_trials:
                try:
                    sd.check_input_settings(device=dev_idx, samplerate=rate, channels=ch, dtype="float32")
                    logger.info(f"Selected input device {dev_idx} ('{dev_info.get('name', 'Mic')}') with {rate}Hz, {ch}ch.")
                    return dev_idx, rate, ch
                except Exception:
                    continue

        # If check_input_settings failed for all combinations, fallback to default device native format
        dev_idx = candidate_devices[0]
        try:
            dev_info = sd.query_devices(dev_idx, "input")
            return dev_idx, int(dev_info.get("default_samplerate", 48000)), max(1, min(2, int(dev_info.get("max_input_channels", 1))))
        except Exception:
            return dev_idx, 48000, 1

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback from sounddevice stream. Real-time downmixes to mono float32."""
        if status:
            logger.debug(f"Audio stream status notice: {status}")
        if self.is_recording:
            try:
                # indata shape is (frames, channels)
                if indata.ndim > 1 and indata.shape[1] > 1:
                    mono = np.mean(indata, axis=1, dtype=np.float32)
                else:
                    mono = indata.flatten().astype(np.float32)
                self.audio_queue.put(mono)
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")

    def start_recording(self):
        """Starts audio recording on a background thread with hardware negotiation."""
        if self.is_recording:
            return

        self._recorded_chunks.clear()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Negotiate compatible hardware parameters
        device_idx, actual_rate, actual_channels = self._find_best_input_parameters()
        self._actual_sample_rate = actual_rate
        self._actual_channels = actual_channels

        try:
            self._stream = sd.InputStream(
                device=device_idx,
                samplerate=actual_rate,
                channels=actual_channels,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=0,
            )
            self._stream.start()
            self.is_recording = True
            self._stop_event.clear()
            self._record_start_time = time.time()
            logger.info(f"Audio stream started: device={device_idx}, rate={actual_rate}Hz, channels={actual_channels}")
        except Exception as e:
            self.is_recording = False
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            logger.error(f"Failed to start audio recording stream: {e}", exc_info=True)
            raise

    def stop_recording(self) -> Tuple[Optional[np.ndarray], float]:
        """
        Stops recording, resamples audio to self.sample_rate (16kHz) if needed,
        and returns the concatenated mono audio numpy array along with duration in seconds.
        """
        if not self.is_recording:
            return None, 0.0

        self.is_recording = False
        self._stop_event.set()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
            finally:
                self._stream = None

        # Drain remaining items from the queue
        while not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get_nowait()
                self._recorded_chunks.append(chunk)
            except queue.Empty:
                break

        if not self._recorded_chunks:
            return None, 0.0

        audio_data = np.concatenate(self._recorded_chunks, axis=0).flatten()

        # Resample to target sample rate (16kHz) if captured at another rate (e.g. 48kHz, 44.1kHz)
        if self._actual_sample_rate and self._actual_sample_rate != self.sample_rate:
            try:
                g = gcd(int(self.sample_rate), int(self._actual_sample_rate))
                up = int(self.sample_rate // g)
                down = int(self._actual_sample_rate // g)
                audio_data = scipy.signal.resample_poly(audio_data, up, down).astype(np.float32)
            except Exception as e:
                logger.warning(f"resample_poly failed, falling back to resample: {e}")
                target_len = int(len(audio_data) * self.sample_rate / self._actual_sample_rate)
                audio_data = scipy.signal.resample(audio_data, target_len).astype(np.float32)

        # Preprocess: noise cancellation, volume normalization, and silence trimming
        audio_data = self.preprocess_audio(
            audio_data,
            sample_rate=self.sample_rate,
            enable_noise_cancellation=self.noise_cancellation,
            highpass_cutoff=NOISE_HIGHPASS_CUTOFF,
            prop_decrease=NOISE_REDUCTION_PROP,
        )
        duration = len(audio_data) / self.sample_rate
        return audio_data, duration

    def set_noise_cancellation(self, enabled: bool):
        """Toggles real-time noise cancellation on or off."""
        self.noise_cancellation = enabled

    @staticmethod
    def preprocess_audio(
        audio: np.ndarray,
        sample_rate: int = 16000,
        enable_noise_cancellation: bool = True,
        highpass_cutoff: float = 80.0,
        prop_decrease: float = NOISE_REDUCTION_PROP,
    ) -> np.ndarray:
        """
        Multi-stage audio cleanup optimized for both close-up and far-field distant speech:
        1. 80Hz Butterworth high-pass filter: eliminates AC hum, HVAC rumble, desk vibrations.
        2. Gentle spectral noise gating: suppresses ambient background fan noise, hiss, and room tone
           without attenuating distant speech formants or non-English phonemes.
        3. Far-Field Speech AGC & RMS Normalization: lifts quiet/distant speech up to standard
           conversational speech level (~ -16 dBFS) with soft-limiting to prevent digital clipping.
        4. Non-destructive silence trimming: preserves generous 500ms buffers around active speech.
        """
        if len(audio) == 0:
            return audio

        processed = audio.astype(np.float32)

        # 1. Multi-Stage Noise Cancellation (gentle spectral gating to preserve speech harmonics)
        if enable_noise_cancellation and len(processed) >= int(sample_rate * 0.15):
            try:
                # A. 80Hz High-Pass filter
                sos = scipy.signal.butter(4, highpass_cutoff, btype='highpass', fs=sample_rate, output='sos')
                processed = scipy.signal.sosfilt(sos, processed).astype(np.float32)

                # B. Gentle Stationary Spectral Noise Reduction (tuned to preserve far-field phonemes)
                if NOISEREDUCE_AVAILABLE:
                    effective_prop = min(prop_decrease, 0.45)
                    processed = nr.reduce_noise(
                        y=processed,
                        sr=sample_rate,
                        stationary=True,
                        prop_decrease=effective_prop
                    ).astype(np.float32)
            except Exception:
                processed = audio.astype(np.float32)

        # 2. Far-Field Automatic Gain Control (AGC) & Speech RMS Normalization
        # Target conversational speech RMS is ~0.12 (-16 dBFS)
        rms = float(np.sqrt(np.mean(processed ** 2)))
        peak = float(np.max(np.abs(processed))) if len(processed) > 0 else 0.0

        if rms > 1e-4:
            target_rms = 0.12
            # Calculate gain needed to bring distant voice to conversational level
            if rms < 0.08:
                # Voice is distant/quiet: apply progressive gain with maximum 14x boost
                gain = min(target_rms / rms, 14.0)
                processed = (processed * gain).astype(np.float32)
                peak = float(np.max(np.abs(processed)))
            
            # Apply smooth soft-limiting if peak exceeds 0.85 to avoid harsh digital distortion
            if peak > 0.85:
                # Soft knee compression using tanh
                processed = (np.tanh(processed / 0.85) * 0.85).astype(np.float32)
            elif peak > 0.005 and peak < 0.70:
                # Modest peak lift if headroom remains
                processed = (processed * (0.85 / peak)).astype(np.float32)

        # 3. Gentle dead-air trimming leaving generous 500ms buffer to preserve trailing syllables
        if len(processed) > int(sample_rate * 1.5):
            silence_level = 0.002
            active = np.where(np.abs(processed) > silence_level)[0]
            if len(active) > 0:
                pad = int(sample_rate * 0.5)
                start_i = max(0, active[0] - pad)
                end_i = min(len(processed), active[-1] + pad)
                processed = processed[start_i:end_i]

        return processed



    def record_until_silence_or_stop(self, stop_check_callback=None) -> Tuple[Optional[np.ndarray], float]:
        """
        Monitors incoming audio for silence. Stops automatically when silence
        persists longer than self.silence_duration or when stop_check_callback() returns True.
        """
        self.start_recording()
        silence_start_time = None
        has_spoken = False
        min_speech_frames = int(self.sample_rate * 0.3) # At least 300ms of sound before silence triggers
        accumulated_frames = 0

        while self.is_recording:
            if stop_check_callback and stop_check_callback():
                break

            if (time.time() - self._record_start_time) > self.max_duration:
                break

            try:
                chunk = self.audio_queue.get(timeout=0.1)
                self._recorded_chunks.append(chunk)
                accumulated_frames += len(chunk)

                # Compute RMS energy of this chunk
                rms = np.sqrt(np.mean(chunk**2))
                
                if rms > self.silence_threshold:
                    has_spoken = True
                    silence_start_time = None
                elif has_spoken and accumulated_frames > min_speech_frames:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif (time.time() - silence_start_time) >= self.silence_duration:
                        # Silence threshold exceeded, finish recording
                        break
            except queue.Empty:
                continue

        return self.stop_recording()

    @staticmethod
    def save_wav(audio_data: np.ndarray, sample_rate: int = SAMPLE_RATE) -> str:
        """Saves float32 numpy audio to a temporary 16-bit PCM WAV file and returns its path."""
        # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
        clipped = np.clip(audio_data, -1.0, 1.0)
        int16_data = (clipped * 32767).astype(np.int16)
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wavfile.write(temp_file.name, sample_rate, int16_data)
        temp_file.close()
        return temp_file.name
