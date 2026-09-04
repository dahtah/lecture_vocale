#!/usr/bin/env python3
"""Test de faisabilité WhisperX avec alignement amélioré"""

import whisperx
import json
import time

# Charger les modèles WhisperX
print("Chargement des modèles WhisperX base...")
start_load = time.time()
model = whisperx.load_model("base", device="cpu", language="fr")
align_model, align_metadata = whisperx.load_align_model(language_code="fr", device="cpu")
load_time = time.time() - start_load
print(f"Modèles chargés en {load_time:.1f}s")

# Fichier audio de test (court)
audio_path = "/home/simon/Repos/lecture_vocale/donnees/Cachin/audio/Exercice_Jour_1.wav"
print(f"\nTraitement de: {audio_path}")

# Transcrire avec WhisperX
start_transcribe = time.time()
result = model.transcribe(
    audio_path,
    language="fr"
)
transcribe_time = time.time() - start_transcribe
print(f"Transcription terminée en {transcribe_time:.1f}s")

# Aligner avec WhisperX pour des timings précis
# load_align_model retourne (align_model, align_metadata)
start_align = time.time()
aligned_result = whisperx.align(
    result["segments"],
    model,  # modèle WhisperX
    align_metadata,  # align_metadata (pas align_model)
    audio_path,
    device="cpu"
)
align_time = time.time() - start_align
print(f"Alignement terminé en {align_time:.1f}s")

# Afficher les segments
print(f"\nNombre de segments: {len(aligned_result['segments'])}")
for i, segment in enumerate(aligned_result["segments"]):
    print(f"  Segment {i}: {segment['start']:.1f}s - {segment['end']:.1f}s")
    print(f"    Texte: {segment['text'][:80]}...")
    
# Extraire les mots alignés
all_words = []
for segment in aligned_result["segments"]:
    for word in segment.get("words", []):
        all_words.append({
            "text": word["word"],
            "start": float(word["start"]),
            "end": float(word["end"])
        })

audio_duration = float(aligned_result["segments"][-1]["end"]) if aligned_result["segments"] else 0

print(f"\nMots détectés: {len(all_words)}")
print(f"Durée audio: {audio_duration:.2f}s")
print(f"\nPremiers 10 mots:")
for word in all_words[:10]:
    print(f"  {word['start']:.2f}s - {word['end']:.2f}s: {word['text']}")

# Sauvegarder un exemple
output_path = "/tmp/whisper_test_output.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"words": all_words, "audio_duration": audio_duration}, f, indent=2, ensure_ascii=False)
print(f"\n✓ Résultat sauvegardé dans {output_path}")

# Tester avec le fichier long
print("\n" + "="*60)
print("Test avec le fichier long (Larbre_qui_chante.wav)...")
long_audio = "/home/simon/Repos/lecture_vocale/donnees/Cachin/audio/Larbre_qui_chante.wav"
start_long = time.time()
result_long = model.transcribe(
    long_audio,
    language="fr"
)
long_time = time.time() - start_long

# Alignement pour le fichier long
start_align_long = time.time()
aligned_result_long = whisperx.align(
    result_long["segments"],
    model,  # modèle WhisperX
    align_metadata,  # align_metadata (pas align_model)
    long_audio,
    device="cpu"
)
align_long_time = time.time() - start_align_long

all_words_long = []
for segment in aligned_result_long["segments"]:
    for word in segment.get("words", []):
        all_words_long.append({
            "text": word["word"],
            "start": float(word["start"]),
            "end": float(word["end"])
        })

audio_duration_long = float(aligned_result_long["segments"][-1]["end"]) if aligned_result_long["segments"] else 0

print(f"Fichier long traité en {long_time:.1f}s (transcription) + {align_long_time:.1f}s (alignement)")
print(f"Mots détectés: {len(all_words_long)}")
print(f"Durée audio: {audio_duration_long:.2f}s")
print(f"Premiers 5 mots: {all_words_long[:5]}")

print("\n✅ Test WhisperX terminé avec succès !")
