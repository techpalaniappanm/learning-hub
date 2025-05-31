import os
import argparse
import whisper
from pyannote.audio import Pipeline
import datetime
import torch # pyannote.audio often relies on PyTorch
import re

def format_timestamp(seconds):
    """Converts seconds to HH:MM:SS.milliseconds format."""
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds_val = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{seconds_val:02}.{milliseconds:03}"

def speaker_diarization_and_transcription(audio_path, output_dir, hf_token=None, whisper_model_name="base", device=None):
    """
    Performs speaker diarization and transcription on an audio file.

    Args:
        audio_path (str): Path to the input audio file.
        output_dir (str): Directory to save the transcript.
        hf_token (str, optional): Hugging Face authentication token for pyannote.audio.
        whisper_model_name (str, optional): Whisper model name (e.g., "tiny", "base", "small", "medium", "large").
        device (str, optional): Device to run models on (e.g., "cuda" or "cpu").
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

    # 1. Speaker Diarization with pyannote.audio
    print("Starting speaker diarization...")
    try:
        # Use a specific version for reproducibility or remove for latest
        diarization_pipeline_name = "pyannote/speaker-diarization-3.1"
        print(f"Loading diarization pipeline: {diarization_pipeline_name}")
        if hf_token:
            diarization_pipeline = Pipeline.from_pretrained(
                diarization_pipeline_name,
                use_auth_token=hf_token
            ).to(torch.device(device))
        else:
            print("Attempting to load pyannote.audio pipeline without explicit token. Ensure you are logged in to Hugging Face CLI or have HF_TOKEN set.")
            diarization_pipeline = Pipeline.from_pretrained(
                diarization_pipeline_name
            ).to(torch.device(device))
        print("Diarization pipeline loaded.")
    except Exception as e:
        print(f"Error loading diarization pipeline: {e}")
        print("Please ensure you have accepted the user agreement for the model on Hugging Face Hub:")
        print(f"  - {diarization_pipeline_name}")
        print("  - And its dependencies (e.g., pyannote/segmentation-3.0)")
        print("And that you have a valid Hugging Face token set up if required.")
        return

    try:
        diarization = diarization_pipeline(audio_path, num_speakers=None) # Let pyannote detect number of speakers
        print("Speaker diarization complete.")
        # Store diarization results in a more accessible format
        speaker_segments = []
        for segment, track, speaker_label in diarization.itertracks(yield_label=True):
            speaker_segments.append({
                "start": segment.start,
                "end": segment.end,
                "speaker": speaker_label
            })
    except Exception as e:
        print(f"Error during diarization processing: {e}")
        return

    # 2. Transcription with Whisper
    print(f"Loading Whisper model: {whisper_model_name}...")
    try:
        whisper_model = whisper.load_model(whisper_model_name, device=device)
        print("Whisper model loaded.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return

    print("Starting transcription...")
    try:
        transcription_result = whisper_model.transcribe(audio_path, word_timestamps=True, fp16=torch.cuda.is_available()) # fp16 if cuda
        print("Transcription complete.")
    except Exception as e:
        print(f"Error during transcription: {e}")
        return

    # 3. Combine Diarization and Transcription
    print("Combining diarization and transcription...")
    output_lines = []

    if not transcription_result.get("segments"):
        print("No segments found in transcription.")
        if transcription_result.get("text"):
             output_lines.append(f"- [00:00:00.000 - UNKNOWN_SPEAKER] {transcription_result['text']}")
        else:
            print("No text transcribed.")
            return
    else:
        all_words = []
        for seg_info in transcription_result["segments"]:
            all_words.extend(seg_info.get("words", []))

        if not all_words:
            print("No words with timestamps found in transcription. Using segment-level matching.")
            # Fallback to segment-level transcription if no word timestamps
            for seg_info in transcription_result["segments"]:
                seg_start = seg_info['start']
                seg_end = seg_info['end']
                seg_text = seg_info['text'].strip()
                
                # Find dominant speaker for this segment
                best_speaker = "UNKNOWN_SPEAKER"
                max_overlap = 0
                seg_mid_time = seg_start + (seg_end - seg_start) / 2

                for speaker_seg in speaker_segments:
                    if speaker_seg['start'] <= seg_mid_time < speaker_seg['end']:
                        best_speaker = speaker_seg['speaker']
                        break # Found speaker for midpoint
                    # More robust overlap calculation if midpoint fails often
                    overlap_start = max(seg_start, speaker_seg['start'])
                    overlap_end = min(seg_end, speaker_seg['end'])
                    overlap_duration = overlap_end - overlap_start
                    if overlap_duration > max_overlap:
                        max_overlap = overlap_duration
                        best_speaker = speaker_seg['speaker']
                
                if seg_text:
                    formatted_time = format_timestamp(seg_start)
                    output_lines.append(f"- [{formatted_time} - {best_speaker}] {seg_text}")
        else:
            # Refined merging logic using word timestamps
            current_bullet_speaker = None
            current_bullet_text_parts = []
            current_bullet_start_time = None

            for i, word_data in enumerate(all_words):
                word_start = word_data['start']
                # Whisper's word output often has leading/trailing spaces, handle carefully
                word_text = word_data['word']


                # Find speaker for the current word's start time
                active_speaker = "UNKNOWN_SPEAKER"
                # Check midpoint of word for more robust speaker assignment
                word_mid_time = word_start + (word_data.get('end', word_start) - word_start) / 2
                for speaker_seg in speaker_segments:
                    if speaker_seg['start'] <= word_mid_time < speaker_seg['end']:
                        active_speaker = speaker_seg['speaker']
                        break
                
                if current_bullet_speaker is None: # Start of the first bullet
                    current_bullet_speaker = active_speaker
                    current_bullet_start_time = word_start
                    current_bullet_text_parts.append(word_text)
                elif active_speaker == current_bullet_speaker: # Same speaker, append text
                    current_bullet_text_parts.append(word_text)
                else: # Speaker changed, finalize previous bullet and start a new one
                    if current_bullet_text_parts:
                        full_text = "".join(current_bullet_text_parts).strip()
                        # Remove extra spaces that might result from Whisper's word spacing
                        full_text = re.sub(r'\s+', ' ', full_text)
                        if full_text:
                            formatted_time = format_timestamp(current_bullet_start_time)
                            output_lines.append(f"- [{formatted_time} - {current_bullet_speaker}] {full_text}")
                    
                    current_bullet_speaker = active_speaker
                    current_bullet_start_time = word_start
                    current_bullet_text_parts = [word_text]

            # Add the last bullet point
            if current_bullet_text_parts and current_bullet_speaker is not None and current_bullet_start_time is not None:
                full_text = "".join(current_bullet_text_parts).strip()
                full_text = re.sub(r'\s+', ' ', full_text)
                if full_text:
                    formatted_time = format_timestamp(current_bullet_start_time)
                    output_lines.append(f"- [{formatted_time} - {current_bullet_speaker}] {full_text}")

    # 4. Save to file
    base_filename = os.path.splitext(os.path.basename(audio_path))[0]
    output_filepath = os.path.join(output_dir, f"{base_filename}_transcript_diarized.txt")

    with open(output_filepath, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")

    print(f"\nTranscript saved to: {output_filepath}")
    print("\n--- Transcript Preview ---")
    for i, line in enumerate(output_lines[:10]): # Preview first 10 lines
        print(line)
    if len(output_lines) > 10:
        print(f"... and {len(output_lines) - 10} more lines.")
    print("--- End of Preview ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe an audio file with speaker diarization.")
    parser.add_argument("audio_file", help="Path to the audio file (e.g., wav, mp3, m4a).")
    parser.add_argument("output_dir", help="Directory to save the transcript file.")
    parser.add_argument("--hf_token", help="Hugging Face authentication token (optional). If not provided, attempts to use cached login or HF_TOKEN env var.", default=None)
    parser.add_argument("--whisper_model", help="Whisper model to use (tiny, base, small, medium, large, or larger variants like large-v2, large-v3). Default: base", default="base")
    parser.add_argument("--device", help="Device to use ('cuda' or 'cpu'). Default: auto-detect", default=None)

    args = parser.parse_args()

    speaker_diarization_and_transcription(
        args.audio_file,
        args.output_dir,
        hf_token=args.hf_token,
        whisper_model_name=args.whisper_model,
        device=args.device
    )

    