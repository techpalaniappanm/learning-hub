import os
import argparse
import whisperx
import datetime
import torch # WhisperX relies on PyTorch

def format_timestamp(seconds):
    """Converts seconds to HH:MM:SS.mmm format."""
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds_val = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{seconds_val:02}.{milliseconds:03}"

def transcribe_and_diarize_with_whisperx(audio_path, output_dir, hf_token=None, whisper_model_name="base", device=None, compute_type="float16"):
    """
    Performs transcription and speaker diarization using WhisperX.

    Args:
        audio_path (str): Path to the input audio file.
        output_dir (str): Directory to save the transcript.
        hf_token (str, optional): Hugging Face authentication token for pyannote.audio (used by WhisperX diarization).
                                   Defaults to None (will try to use environment variable or cached login).
        whisper_model_name (str, optional): Whisper model name (e.g., "tiny", "base", "small", "medium", "large-v2", "large-v3").
                                           Defaults to "base".
        device (str, optional): Device to run models on (e.g., "cuda" or "cpu").
                                Defaults to "cuda" if available, else "cpu".
        compute_type (str, optional): Compute type for Whisper model (e.g., "float16", "int8", "float32").
                                     "float16" is good for speed on GPU. "int8" for further optimization.
    """
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at {audio_path}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    if device == "cuda" and compute_type not in ["float16", "int8"]:
        print(f"Warning: For CUDA device, 'float16' or 'int8' compute_type is recommended for better performance. Using '{compute_type}'.")
    elif device == "cpu" and compute_type == "float16":
        print("Warning: 'float16' compute_type is not typically recommended for CPU. Defaulting to 'float32' for CPU or consider 'int8'.")
        if compute_type == "float16": compute_type = "float32" # WhisperX might handle this, but good to be aware.


    # 1. Load Audio
    print(f"Loading audio from: {audio_path}")
    try:
        audio = whisperx.load_audio(audio_path)
    except Exception as e:
        print(f"Error loading audio: {e}")
        print("Ensure ffmpeg is installed and in your system's PATH.")
        return

    # 2. Transcribe with Whisper
    print(f"Loading Whisper model: {whisper_model_name} (compute_type: {compute_type})")
    try:
        # Note: WhisperX loads models from Hugging Face Transformers or local paths if specified.
        # For standard OpenAI Whisper models, it often uses faster-whisper backend.
        model = whisperx.load_model(whisper_model_name, device, compute_type=compute_type)
        print("Whisper model loaded. Starting transcription...")
        result = model.transcribe(audio, batch_size=16) # Adjust batch_size based on your VRAM
        print("Transcription complete.")
    except Exception as e:
        print(f"Error during transcription with WhisperX: {e}")
        return
    finally:
        # Clean up model from memory if you need to free VRAM for next steps (especially diarization)
        if 'model' in locals():
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # 3. Align Whisper output for accurate word timestamps
    print("Aligning transcription...")
    try:
        # Ensure the model used for alignment is available or downloadable
        # For some languages, alignment models might need to be downloaded separately if not cached
        align_model, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result_aligned = whisperx.align(result["segments"], align_model, metadata, audio, device, return_char_alignments=False)
        print("Alignment complete.")
    except Exception as e:
        print(f"Error during alignment: {e}")
        print("This might be due to missing alignment models for the detected language or an issue with the audio.")
        # Fallback: use original segments if alignment fails, though speaker assignment will be less precise.
        result_aligned = result
    finally:
        if 'align_model' in locals():
            del align_model
        if 'metadata' in locals():
            del metadata
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


    # 4. Speaker Diarization
    print("Starting speaker diarization...")
    if hf_token is None:
        print("Warning: No Hugging Face token provided for diarization. WhisperX will try to use a default or cached token.")
        print("For 'pyannote/speaker-diarization-3.1', a token is usually required.")

    try:
        # For pyannote.audio based diarization (default in WhisperX if token is provided or models are accessible)
        diarization_pipeline = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        # You can also specify min_speakers and max_speakers if known:
        # diarize_segments = diarization_pipeline(audio, min_speakers=min_speakers, max_speakers=max_speakers)
        diarize_segments = diarization_pipeline(audio_path) # Pass audio_path or the loaded audio object
        print("Speaker diarization complete.")
    except Exception as e:
        print(f"Error during speaker diarization: {e}")
        print("Ensure you have accepted the terms for 'pyannote/speaker-diarization-3.1' and 'pyannote/segmentation-3.0' on Hugging Face Hub,")
        print("and have a valid Hugging Face token if needed, or that the diarization models are accessible.")
        diarize_segments = None # Proceed without speaker labels if diarization fails

    # 5. Assign speaker labels to word-level segments
    if diarize_segments is not None and "segments" in result_aligned and result_aligned["segments"]:
        print("Assigning speakers to words...")
        try:
            result_with_speakers = whisperx.assign_word_speakers(diarize_segments, result_aligned)
            print("Speaker assignment complete.")
        except Exception as e:
            print(f"Error assigning speakers to words: {e}")
            result_with_speakers = result_aligned # Fallback to non-diarized aligned result
    else:
        print("Skipping speaker assignment due to previous errors or no segments.")
        result_with_speakers = result_aligned


    # 6. Format output
    output_lines = []
    if "segments" in result_with_speakers and result_with_speakers["segments"]:
        current_speaker = None
        current_text_parts = []
        current_start_time = None

        for segment in result_with_speakers["segments"]:
            # Segments from assign_word_speakers often represent continuous speech from one speaker
            # Words within these segments have their own start/end and text
            
            segment_speaker = segment.get('speaker', 'UNKNOWN_SPEAKER')
            # Use the start of the first word in the segment as the bullet point time
            # or the segment's start time if no words are present (should not happen with assign_word_speakers)
            segment_start_time = segment.get('start')
            
            # Collect all words in the segment to form the text for this speaker's turn
            words_text = "".join([word_info.get('word', '') for word_info in segment.get('words', [])]).strip()
            # WhisperX word outputs might have leading/trailing spaces; strip() and re-join carefully if needed.
            # The 'word' field usually has spaces already, so direct join is often okay.

            if not words_text: # Skip if segment has no text
                continue

            if current_speaker is None: # First segment
                current_speaker = segment_speaker
                current_start_time = segment_start_time
                current_text_parts.append(words_text)
            elif segment_speaker == current_speaker: # Same speaker continues
                current_text_parts.append(words_text) # Append with a space if needed, but WhisperX words often include them
            else: # Speaker change
                if current_text_parts and current_start_time