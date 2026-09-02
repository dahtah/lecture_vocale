#!/usr/bin/env python3
"""
Script pour générer des fichiers audio avec Piper TTS pour les textes présélectionnés.

Utilisation:
    python3 generate_audio.py

Prérequis:
    - Piper CLI accessible dans PATH ou PIPE_BINARY définie
    - Modèle Piper dans models/ (ex: fr_FR-gilles-low.onnx)
    - Fichier textes.md avec des textes séparés par #
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Configuration
MODEL_PATH = Path("models/fr_FR-gilles-low.onnx")
TEXTES_FILE = Path("textes.md")
AUDIO_DIR = Path("audio")
PIPER_BINARY = os.getenv("PIPER_BINARY", "/tmp/piper/piper")


def parse_textes_md():
    """Parse textes.md et retourne un dict {titre: contenu}."""
    if not TEXTES_FILE.exists():
        print(f"Erreur: {TEXTES_FILE} introuvable")
        sys.exit(1)
    
    with open(TEXTES_FILE, "r", encoding="utf-8") as f:
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


def generate_audio(text, output_path, model_path, piper_binary):
    """Génère un fichier audio avec Piper TTS."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Écrire le texte dans un fichier temporaire
    with open("/tmp/piper_input.txt", "w", encoding="utf-8") as f:
        f.write(text)
    
    cmd = [
        piper_binary,
        "-m", str(model_path),
        "-f", str(output_path),
    ]
    
    try:
        with open("/tmp/piper_input.txt", "r", encoding="utf-8") as fin:
            result = subprocess.run(
                cmd,
                stdin=fin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
        
        if result.returncode != 0:
            print(f"Erreur Piper: {result.stderr}")
            return False
        
        if not output_path.exists():
            print(f"Erreur: {output_path} non généré")
            return False
        
        print(f"✓ Généré: {output_path} ({output_path.stat().st_size / 1024:.1f} Ko)")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"Timeout pour {output_path}")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def main():
    print("Génération des fichiers audio avec Piper TTS...")
    print(f"Modèle: {MODEL_PATH}")
    print(f"Fichier source: {TEXTES_FILE}")
    print(f"Dossier de sortie: {AUDIO_DIR}")
    print(f"Piper CLI: {PIPER_BINARY}")
    print()
    
    # Vérifications
    if not MODEL_PATH.exists():
        print(f"Erreur: Modèle introuvable à {MODEL_PATH}")
        sys.exit(1)
    
    if not Path(PIPER_BINARY).exists():
        print(f"Erreur: Piper CLI introuvable à {PIPER_BINARY}")
        sys.exit(1)
    
    # Parser textes.md
    textes = parse_textes_md()
    print(f"Trouvé {len(textes)} textes dans {TEXTES_FILE}")
    print()
    
    # Générer les fichiers audio
    success = 0
    failed = 0
    
    for safe_title, data in textes.items():
        output_path = AUDIO_DIR / f"{safe_title}.wav"
        print(f"Génération de '{data['original_title']}'...")
        
        if generate_audio(data['content'], output_path, MODEL_PATH, PIPER_BINARY):
            success += 1
        else:
            failed += 1
    
    print()
    print(f"Résultat: {success} succès, {failed} échecs")
    
    if failed == 0:
        print("\n✓ Tous les fichiers audio ont été générés!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
