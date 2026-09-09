#!/usr/bin/env python3
"""
Script pour générer des fichiers audio avec Piper TTS pour les textes présélectionnés.

Utilisation:
    # Générer pour une école spécifique
    python3 generate_audio.py Cachin

    # Générer pour toutes les écoles
    python3 generate_audio.py --all

Prérequis:
    - Package piper-tts installé
    - Modèle Piper dans models/ (ex: fr_FR-gilles-low.onnx)
    - Fichiers textes.md dans donnees/{ecole}/
"""

import os
import re
import sys
import argparse
import wave
from pathlib import Path

# Configuration
#MODEL_PATH = Path("models/fr_FR-gilles-low.onnx")
MODEL_PATH = Path("models/fr_FR-siwis-medium.onnx")
DONNEES_DIR = Path("donnees")

# Piper voice object (loaded once)
piper_voice = None


def parse_textes_md(filepath):
    """Parse un fichier textes.md et retourne un dict {titre: contenu}."""
    if not filepath.exists():
        print(f"Erreur: {filepath} introuvable")
        return {}
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split par les titres # et ignorer la première partie (avant le premier #)
    sections = re.split(r'^#\s+', content, flags=re.MULTILINE)[1:]
    
    textes = {}
    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        title = lines[0].strip()
        content = '\n'.join(lines[1:]).strip()
        if title and content:
            # Nettoyer le titre : remplacer les caractères spéciaux pour le nom de fichier
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'\s+', '_', safe_title)
            textes[safe_title] = {
                'original_title': title,
                'content': content
            }
    
    return textes


def load_piper_voice(model_path):
    """Charge le modèle Piper une fois."""
    global piper_voice
    if piper_voice is None:
        import piper
        config_path = model_path.with_suffix(".onnx.json")
        if not config_path.exists():
            config_path = None
        piper_voice = piper.PiperVoice.load(
            model_path=str(model_path),
            config_path=str(config_path) if config_path else None,
            use_cuda=False
        )
    return piper_voice


def generate_audio(text, output_path, model_path):
    """Génère un fichier audio avec Piper TTS en utilisant l'API Python."""
    global piper_voice
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Charger le modèle si ce n'est pas déjà fait
        voice = load_piper_voice(model_path)
        
        # Générer l'audio directement avec l'API Python
        with wave.open(str(output_path), 'wb') as wav_file:
            voice.synthesize_wav(
                text=text,
                wav_file=wav_file,
                set_wav_format=True
            )
        
        if not output_path.exists():
            print(f"Erreur: {output_path} non généré")
            return False
        
        print(f"✓ Généré: {output_path} ({output_path.stat().st_size / 1024:.1f} Ko)")
        return True
        
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_for_school(school_name):
    """Génère les fichiers audio pour une école."""
    school_dir = DONNEES_DIR / school_name
    textes_file = school_dir / "textes.md"
    audio_dir = school_dir / "audio"
    
    if not textes_file.exists():
        print(f"⚠️  {textes_file} introuvable, passage à l'école suivante")
        return 0
    
    print(f"\n🏫 École: {school_name}")
    textes = parse_textes_md(textes_file)
    
    if not textes:
        print(f"  Aucun texte trouvé dans {textes_file}")
        return 0
    
    success = 0
    for safe_title, data in textes.items():
        output_path = audio_dir / f"{safe_title}.wav"
        print(f"  Génération de '{data['original_title']}'...")
        
        if generate_audio(data['content'], output_path, MODEL_PATH):
            success += 1
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Générer des fichiers audio avec Piper TTS')
    parser.add_argument('school', nargs='?', default=None, help='Nom de l école (ex: Cachin)')
    parser.add_argument('--all', action='store_true', help='Générer pour toutes les écoles')
    args = parser.parse_args()
    
    print("Génération des fichiers audio avec Piper TTS...")
    print(f"Modèle: {MODEL_PATH}")
    print()
    
    # Vérifications
    if not MODEL_PATH.exists():
        print(f"Erreur: Modèle introuvable à {MODEL_PATH}")
        sys.exit(1)
    
    if not DONNEES_DIR.exists():
        print(f"Erreur: Dossier {DONNEES_DIR} introuvable")
        sys.exit(1)
    
    # Charger le modèle Piper
    try:
        load_piper_voice(MODEL_PATH)
        print("Modèle Piper chargé avec succès")
    except Exception as e:
        print(f"Erreur lors du chargement du modèle Piper: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    total_success = 0
    
    if args.all:
        # Trouver tous les sous-dossiers dans donnees/
        schools = [d.name for d in DONNEES_DIR.iterdir() if d.is_dir()]
        if not schools:
            print(f"Erreur: Aucun sous-dossier trouvé dans {DONNEES_DIR}")
            sys.exit(1)
        
        for school in schools:
            total_success += generate_for_school(school)
    elif args.school:
        total_success += generate_for_school(args.school)
    else:
        # Par défaut : première école trouvée
        schools = [d.name for d in DONNEES_DIR.iterdir() if d.is_dir()]
        if schools:
            total_success += generate_for_school(schools[0])
        else:
            print("Erreur: Aucune école trouvée")
            sys.exit(1)
    
    print()
    print(f"✅ Résultat: {total_success} fichiers audio générés")


if __name__ == "__main__":
    main()
