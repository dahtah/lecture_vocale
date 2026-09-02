#!/usr/bin/env python3
"""
Script pour générer des fichiers audio avec Piper TTS pour les textes présélectionnés.

Utilisation:
    # Générer pour une école spécifique
    python3 generate_audio.py Cachin

    # Générer pour toutes les écoles
    python3 generate_audio.py --all

Prérequis:
    - Piper CLI accessible dans PATH ou PIPE_BINARY définie
    - Modèle Piper dans models/ (ex: fr_FR-gilles-low.onnx)
    - Fichiers textes.md dans donnees/{ecole}/
"""

import os
import re
import subprocess
import sys
import argparse
from pathlib import Path

# Configuration
MODEL_PATH = Path("models/fr_FR-gilles-low.onnx")
DONNEES_DIR = Path("donnees")
PIPER_BINARY = os.getenv("PIPER_BINARY", "/tmp/piper/piper")


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
        
        if generate_audio(data['content'], output_path, MODEL_PATH, PIPER_BINARY):
            success += 1
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Générer des fichiers audio avec Piper TTS')
    parser.add_argument('school', nargs='?', default=None, help='Nom de l école (ex: Cachin)')
    parser.add_argument('--all', action='store_true', help='Générer pour toutes les écoles')
    args = parser.parse_args()
    
    print("Génération des fichiers audio avec Piper TTS...")
    print(f"Modèle: {MODEL_PATH}")
    print(f"Piper CLI: {PIPER_BINARY}")
    print()
    
    # Vérifications
    if not MODEL_PATH.exists():
        print(f"Erreur: Modèle introuvable à {MODEL_PATH}")
        sys.exit(1)
    
    if not Path(PIPER_BINARY).exists():
        print(f"Erreur: Piper CLI introuvable à {PIPER_BINARY}")
        sys.exit(1)
    
    if not DONNEES_DIR.exists():
        print(f"Erreur: Dossier {DONNEES_DIR} introuvable")
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
