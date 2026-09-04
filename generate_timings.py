#!/usr/bin/env python3
"""
Script pour générer des fichiers de timings avec WhisperX ou aeneas pour les textes présélectionnés.

Utilisation:
    python3 generate_timings.py Cachin
    python3 generate_timings.py --all
    python3 generate_timings.py --use-aeneas Cachin  # Utiliser aeneas pour l'alignement forcé

Prérequis: whisperx, torch OU aeneas
"""

import os
import re
import json
import sys
import argparse
import tempfile
from pathlib import Path

# Import whisperx (sera chargé de manière paresseuse si non disponible)
try:
    import whisperx
except ImportError:
    whisperx = None

# Vérifier si aeneas est disponible
try:
    import aeneas
    from aeneas.tools.execute_task import ExecuteTaskCLI
    AENEAS_AVAILABLE = True
except ImportError:
    AENEAS_AVAILABLE = False

DONNEES_DIR = Path("donnees")
WHISPERX_MODEL = "base"
WHISPERX_DEVICE = "cpu"

# Variables globales pour les modèles WhisperX (chargés une seule fois)
whisperx_model = None
whisperx_align_model = None
whisperx_align_metadata = None


def parse_textes_md(filepath):
    """Parse textes.md et retourne {titre: contenu}.
    
    Nettoie le contenu en supprimant les séparateurs markdown (---) et les lignes vides.
    """
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    sections = re.split(r'^#\s+', content, flags=re.MULTILINE)[1:]
    textes = {}
    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        title = lines[0].strip()
        # Filtrer les lignes pour enlever les séparateurs markdown et les lignes vides
        content_lines = []
        for line in lines[1:]:
            stripped = line.strip()
            # Ignorer les lignes qui sont juste des séparateurs markdown
            if stripped in ['---', '***', '___', '']:
                continue
            content_lines.append(stripped)
        content = '\n'.join(content_lines).strip()
        if title and content:
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            textes[safe_title] = {'original_title': title, 'content': content}
    return textes


def get_audio_filename(title):
    safe = re.sub(r'[^\w\s-]', '', title).strip()
    safe = re.sub(r'\s+', '_', safe)
    return f"{safe}.wav"


def get_timings_filename(title):
    safe = re.sub(r'[^\w\s-]', '', title).strip()
    safe = re.sub(r'\s+', '_', safe)
    return f"{safe}.json"


def load_whisperx_models():
    """Charge les modèles WhisperX (une seule fois).
    
    WhisperX utilise deux modèles :
    - Un modèle Whisper pour la transcription initiale
    - Un modèle d'alignement (Wav2Vec2) pour affiner les timings
    
    Retourne : (model, align_model, align_metadata)
    """
    global whisperx_model, whisperx_align_model, whisperx_align_metadata
    if whisperx_model is None:
        if whisperx is None:
            raise ImportError("whisperx n'est pas installé. Installez-le avec: uv pip install whisperx")
        
        print("  Chargement des modèles WhisperX base...")
        whisperx_model = whisperx.load_model(WHISPERX_MODEL, device=WHISPERX_DEVICE, language="fr")
        
        # Charger le modèle d'alignement pour le français
        # load_align_model retourne (align_model, align_metadata)
        print("  Chargement du modèle d'alignement...")
        whisperx_align_model, whisperx_align_metadata = whisperx.load_align_model(
            language_code="fr", 
            device=WHISPERX_DEVICE
        )
    return whisperx_model, whisperx_align_model, whisperx_align_metadata


def split_text_into_words(text):
    """Split le texte en mots en respectant la ponctuation."""
    import re
    # Split sur les whitespace mais garder la ponctuation avec les mots
    # Utiliser regex pour trouver tous les mots (incluant apostrophes, tirets, etc.)
    words = re.findall(r"\S+", text)
    return words


def align_original_with_timings(original_text, whisper_words):
    """Aligne les mots originaux avec les timings Whisper.
    
    Args:
        original_text: Le texte original
        whisper_words: Liste de dicts avec 'start', 'end', 'text' des mots détectés par Whisper
    
    Returns:
        Liste de dicts avec 'text' (mot original), 'start', 'end'
    
    Note: Cette fonction est conservée pour compatibilité, mais utilisez 
    align_original_with_timings_preserve_duration() pour une meilleure précision.
    """
    return align_original_with_timings_preserve_duration(original_text, whisper_words, None)


def text_similarity(word1, word2):
    """Calcule un score de similarité entre deux mots (0-1).
    
    Utilise une combinaison de :
    - Similarité des caractères communs
    - Longueur similaire
    - Prefixe/suffixe commun
    """
    if not word1 or not word2:
        return 0.0
    
    word1_lower = word1.lower()
    word2_lower = word2.lower()
    
    # Caractères communs
    common_chars = len(set(word1_lower) & set(word2_lower))
    max_chars = max(len(word1_lower), len(word2_lower))
    char_similarity = common_chars / max_chars if max_chars > 0 else 0.0
    
    # Longueur similaire
    len_ratio = 1.0 - abs(len(word1_lower) - len(word2_lower)) / max(len(word1_lower), len(word2_lower), 1)
    
    # Prefixe commun
    min_len = min(len(word1_lower), len(word2_lower))
    prefix_match = 0
    for i in range(min_len):
        if word1_lower[i] == word2_lower[i]:
            prefix_match += 1
        else:
            break
    # Utiliser min_len pour le ratio de prefixe (car on compare jusqu'à min_len)
    prefix_similarity = prefix_match / min_len if min_len > 0 else 0.0
    
    # Score combiné (poids ajustables)
    return 0.4 * char_similarity + 0.3 * len_ratio + 0.3 * prefix_similarity


def align_with_reference(original_words, whisper_word_timings):
    """Aligne les mots originaux avec les timings whisperX.
    
    Utilise un algorithme de programmation dynamique pour trouver
    la meilleure correspondance entre les deux séquences.
    
    Args:
        original_words: Liste des mots du texte original
        whisper_word_timings: Liste de dicts {text, start, end} de whisperX
    
    Returns:
        Liste de dicts {text: original, start, end} avec les timings alignés
    """
    num_orig = len(original_words)
    num_whisper = len(whisper_word_timings)
    
    # Si les deux ont la même longueur, alignement direct
    if num_orig == num_whisper:
        return [{
            "text": orig_word,
            "start": whisper_word_timings[i]["start"],
            "end": whisper_word_timings[i]["end"]
        } for i, orig_word in enumerate(original_words)]
    
    # Si whisper a plus de mots, regrouper les mots whisper
    if num_whisper > num_orig:
        return _align_group_whisper(original_words, whisper_word_timings)
    
    # Si whisper a moins de mots, distribuer les mots originaux
    if num_whisper < num_orig:
        return _align_split_original(original_words, whisper_word_timings)
    
    # Default
    return whisper_word_timings


def _align_group_whisper(original_words, whisper_word_timings):
    """Aligne quand whisperX a PLUS de mots que l'original.
    
    Regroupe les mots whisperX pour correspondre aux mots originaux.
    """
    orig_idx = 0
    whisper_idx = 0
    result = []
    
    while orig_idx < len(original_words) and whisper_idx < len(whisper_word_timings):
        orig_word = original_words[orig_idx]
        
        # Trouver les mots whisperX qui correspondent à ce mot original
        best_match_idx = whisper_idx
        best_score = text_similarity(orig_word, whisper_word_timings[whisper_idx]["text"])
        
        # Regarder devant pour trouver une meilleure correspondance
        lookahead = min(5, len(whisper_word_timings) - whisper_idx)
        for j in range(1, lookahead + 1):
            if whisper_idx + j >= len(whisper_word_timings):
                break
            score = text_similarity(orig_word, whisper_word_timings[whisper_idx + j]["text"])
            if score > best_score:
                best_score = score
                best_match_idx = whisper_idx + j
        
        # Si bonne correspondance trouvée, prendre tous les mots jusqu'à là
        if best_score > 0.5:  # Seuil arbitraire
            start = whisper_word_timings[whisper_idx]["start"]
            end = whisper_word_timings[best_match_idx]["end"]
            result.append({
                "text": orig_word,
                "start": start,
                "end": end
            })
            whisper_idx = best_match_idx + 1
            orig_idx += 1
        else:
            # Pas de bonne correspondance, prendre le mot whisperX actuel
            result.append({
                "text": orig_word,
                "start": whisper_word_timings[whisper_idx]["start"],
                "end": whisper_word_timings[whisper_idx]["end"]
            })
            whisper_idx += 1
            orig_idx += 1
    
    # Ajouter les mots originaux restants
    while orig_idx < len(original_words):
        if result:
            last_end = result[-1]["end"]
            result.append({
                "text": original_words[orig_idx],
                "start": last_end,
                "end": last_end + 0.1
            })
        else:
            result.append({
                "text": original_words[orig_idx],
                "start": 0.0,
                "end": 0.1
            })
        orig_idx += 1
    
    return result


def _align_split_original(original_words, whisper_word_timings):
    """Aligne quand whisperX a MOINS de mots que l'original.
    
    Stratégie : Distribuer les mots originaux dans les intervalles whisperX.
    Chaque mot whisperX peut correspondre à plusieurs mots originaux.
    """
    num_orig = len(original_words)
    num_whisper = len(whisper_word_timings)
    
    if num_whisper == 0:
        # Aucune transcription whisperX, retourner les mots originaux avec timings estimés
        return [{"text": word, "start": 0, "end": 0.1} for word in original_words]
    
    if num_orig == 0:
        return []
    
    # Calculer la durée totale
    total_duration = whisper_word_timings[-1]["end"]
    
    # Créer une matrice de correspondance
    score_matrix = []
    for i in range(num_orig):
        row = []
        for j in range(num_whisper):
            row.append(text_similarity(original_words[i], whisper_word_timings[j]["text"]))
        score_matrix.append(row)
    
    # Algorithme : Distribuer les mots originaux dans les intervalles whisperX
    # en utilisant les scores de similarité
    result = []
    orig_idx = 0
    whisper_idx = 0
    
    while orig_idx < num_orig and whisper_idx < num_whisper:
        whisper_start = whisper_word_timings[whisper_idx]["start"]
        whisper_end = whisper_word_timings[whisper_idx]["end"]
        interval_duration = whisper_end - whisper_start
        
        # Trouver combien de mots originaux correspondent à cet intervalle
        # en regardant les scores de similarité
        best_orig_indices = []
        best_total_score = 0
        
        # Essayer de regrouper 1, 2 ou 3 mots originaux pour ce mot whisperX
        for group_size in range(1, min(4, num_orig - orig_idx + 1)):
            group_indices = list(range(orig_idx, orig_idx + group_size))
            total_score = sum(score_matrix[i][whisper_idx] for i in group_indices)
            
            if total_score > best_total_score:
                best_total_score = total_score
                best_orig_indices = group_indices
        
        # Si on a trouvé une bonne correspondance
        if best_total_score > 0.3 * len(best_orig_indices):
            # Distribuer les mots originaux dans cet intervalle
            sub_duration = interval_duration / len(best_orig_indices)
            for k, orig_i in enumerate(best_orig_indices):
                sub_start = whisper_start + k * sub_duration
                sub_end = whisper_start + (k + 1) * sub_duration
                result.append({
                    "text": original_words[orig_i],
                    "start": sub_start,
                    "end": sub_end
                })
            orig_idx += len(best_orig_indices)
            whisper_idx += 1
        else:
            # Pas de bonne correspondance, prendre le mot original actuel
            # et l'associer au mot whisperX actuel
            result.append({
                "text": original_words[orig_idx],
                "start": whisper_start,
                "end": whisper_end
            })
            orig_idx += 1
            whisper_idx += 1
    
    # Ajouter les mots originaux restants
    while orig_idx < num_orig:
        if result:
            last_end = result[-1]["end"]
            result.append({
                "text": original_words[orig_idx],
                "start": last_end,
                "end": last_end + 0.1
            })
        else:
            result.append({
                "text": original_words[orig_idx],
                "start": 0.0,
                "end": 0.1
            })
        orig_idx += 1
    
    return result


def align_original_with_timings_preserve_duration(original_text, whisper_words, audio_duration=None):
    """Aligne les mots originaux avec les timings Whisper/WhisperX en préservant la durée totale.
    
    Args:
        original_text: Le texte original
        whisper_words: Liste de dicts avec 'start', 'end', 'text' des mots détectés
        audio_duration: Durée totale de l'audio (optionnel, pour forcer la fin)
    
    Returns:
        Liste de dicts avec 'text' (mot original), 'start', 'end'
    
    Stratégie:
    - Si nombre de mots identique: alignement direct
    - Si whisper a plus de mots: regrouper les mots whisper pour correspondre aux mots originaux
    - Si whisper a moins de mots: distribuer les mots originaux dans les intervalles whisper,
      mais étirer le dernier intervalle pour atteindre audio_duration
    """
    original_words = split_text_into_words(original_text)
    num_orig = len(original_words)
    num_whisper = len(whisper_words)
    
    # Si pas de mots whisper, retourner les mots originaux avec des timings estimés
    if num_whisper == 0:
        if audio_duration and num_orig > 0:
            sub_duration = audio_duration / num_orig
            return [{
                "text": word,
                "start": i * sub_duration,
                "end": (i + 1) * sub_duration
            } for i, word in enumerate(original_words)]
        return [{"text": word, "start": 0, "end": 0.1} for word in original_words]
    
    # Si les nombres correspondent, alignement direct
    if num_orig == num_whisper:
        return [{
            "text": orig_word,
            "start": whisper_words[i]["start"],
            "end": whisper_words[i]["end"]
        } for i, orig_word in enumerate(original_words)]
    
    # Calculer la durée totale des mots whisper
    whisper_duration = whisper_words[-1]["end"]
    
    # Déterminer le facteur d'étirement nécessaire pour atteindre audio_duration
    stretch_factor = 1.0
    if audio_duration is not None and audio_duration > 0:
        stretch_factor = audio_duration / whisper_duration if whisper_duration > 0 else 1.0
    
    # Cas 1: whisper a plus de mots que l'original (regrouper)
    if num_whisper > num_orig:
        # Regrouper les mots whisper: plusieurs mots whisper → un mot original
        result = []
        whisper_index = 0
        for orig_word in original_words:
            # Trouver combien de mots whisper correspondent à ce mot original
            words_per_orig = num_whisper / num_orig
            num_to_group = max(1, round(words_per_orig))
            
            # Ne pas dépasser
            num_to_group = min(num_to_group, num_whisper - whisper_index)
            
            if num_to_group > 0:
                start = whisper_words[whisper_index]["start"] * stretch_factor
                end = whisper_words[whisper_index + num_to_group - 1]["end"] * stretch_factor
                result.append({
                    "text": orig_word,
                    "start": start,
                    "end": end
                })
                whisper_index += num_to_group
        
        # Si des mots whisper restent, les ajouter au dernier
        if whisper_index < num_whisper:
            result[-1]["end"] = whisper_words[-1]["end"] * stretch_factor
        
        return result
    
    # Cas 2: whisper a moins de mots que l'original (distribuer)
    else:
        # Distribuer les mots originaux dans les intervalles whisper
        result = []
        orig_index = 0
        
        for i in range(num_whisper):
            start = whisper_words[i]["start"] * stretch_factor
            end = whisper_words[i]["end"] * stretch_factor
            interval_duration = end - start
            
            # Calculer combien de mots originaux dans cet intervalle
            expected_words_in_interval = (interval_duration / (whisper_duration * stretch_factor)) * num_orig
            num_words_here = max(1, round(expected_words_in_interval))
            num_words_here = min(num_words_here, num_orig - orig_index)
            
            if num_words_here > 0:
                sub_duration = interval_duration / num_words_here
                for j in range(num_words_here):
                    sub_start = start + j * sub_duration
                    sub_end = start + (j + 1) * sub_duration
                    result.append({
                        "text": original_words[orig_index + j],
                        "start": sub_start,
                        "end": sub_end
                    })
                orig_index += num_words_here
        
        # Ajouter les mots originaux restants avec étirement pour atteindre la fin
        while orig_index < num_orig:
            last_end = result[-1]["end"] if result else 0.0
            # Étirer jusqu'à la fin
            if audio_duration is not None:
                remaining_time = audio_duration - last_end
                if remaining_time > 0:
                    result.append({
                        "text": original_words[orig_index],
                        "start": last_end,
                        "end": last_end + remaining_time
                    })
                    orig_index += 1
                    continue
            # Durée arbitraire sinon
            result.append({
                "text": original_words[orig_index],
                "start": last_end,
                "end": last_end + 0.1
            })
            orig_index += 1
        
        return result


def generate_timings_with_aeneas(text, audio_path, output_path):
    """Génère un fichier de timings avec aeneas (alignement forcé).
    
    aeneas utilise un algorithme d'alignement forcé qui produit des timings très précis
    pour chaque mot du texte original.
    
    Args:
        text: Texte original à aligner
        audio_path: Chemin vers le fichier audio
        output_path: Chemin vers le fichier de sortie JSON
    
    Returns:
        bool: True si succès, False sinon
    """
    if not AENEAS_AVAILABLE:
        print("  ✗ aeneas non disponible. Installez-le avec: pip install aeneas")
        return False
    
    try:
        print(f"  Traitement avec aeneas: '{text[:50]}...'")
        
        # Segmenter le texte en mots (un mot par ligne)
        # Filtrer les séparateurs markdown et lignes vides
        original_words = split_text_into_words(text)
        # Supprimer les tokens qui sont des séparateurs markdown
        filtered_words = []
        for word in original_words:
            if word.strip() in ['---', '***', '___', '~~~']:
                continue
            filtered_words.append(word)
        text_with_words = '\n'.join(filtered_words)
        original_words = filtered_words
        
        # Créer un fichier texte temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_file:
            txt_file.write(text_with_words)
            txt_path = txt_file.name
        
        try:
            # Exécuter aeneas via ExecuteTaskCLI
            # Note: cli.run() appelle sys.exit(), donc on l'intercepte
            import sys
            original_exit = sys.exit
            aeneas_exit_code = [None]  # Variable pour stocker le code de sortie
            
            def mock_exit(code=0):
                aeneas_exit_code[0] = code
                raise Exception(f"aeneas_exit_{code}")
            
            sys.exit = mock_exit
            
            try:
                cli = ExecuteTaskCLI()
                args = [
                    "dummy",  # Nom de programme factice
                    str(audio_path),
                    str(txt_path),
                    "task_language=fra|is_text_type=plain|os_task_file_format=txtm",
                    "/tmp/aeneas_temp.txtm"
                ]
                
                cli.run(args, show_help=False)
                
            except Exception as e:
                if str(e).startswith("aeneas_exit_"):
                    # C'est l'exception que nous avons levée pour intercepter sys.exit
                    exit_code = int(str(e).replace("aeneas_exit_", ""))
                    if exit_code != 0:
                        print(f"  ✗ Erreur aeneas (code: {exit_code})")
                        return False
                else:
                    # Une vraie erreur
                    raise
            finally:
                # Rétablir sys.exit
                sys.exit = original_exit
            
            # Lire le fichier txtm généré
            if not os.path.exists("/tmp/aeneas_temp.txtm"):
                print("  ✗ Fichier de sortie aeneas introuvable")
                return False
            
            # Parser le fichier txtm
            aeneas_words = []
            with open("/tmp/aeneas_temp.txtm", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('"', 2)
                    if len(parts) >= 3:
                        metadata = parts[0].strip().split()
                        word_text = parts[1]
                        if len(metadata) >= 3:
                            start = float(metadata[1])
                            end = float(metadata[2])
                            aeneas_words.append({
                                "text": word_text,
                                "start": start,
                                "end": end
                            })
            
            # Corriger les séquences de mots avec des timings problématiques
            # aeneas peut produire des groupes de mots qui partagent le même point de départ
            # mais ont des fins différentes, créant des durées anormalement courtes
            # Exemple: "qui", "ont", "du", "givre" à [5.76, 5.77] + "à" à [5.76, 6.40]
            # Solution: 
            # 1. D'abord, regrouper tous les mots consécutifs avec le même start et redistribuer
            # 2. Ensuite, corriger les mots isolés avec une durée < 20ms
            
            MIN_DURATION_THRESHOLD = 0.05  # Seuil pour déclencher la redistribution de groupe
            MIN_DURATION_ABSOLUTE = 0.02  # Durée minimale absolue pour un mot (20ms)
            
            # Étape 1: Corriger les groupes de mots avec le même start
            i = 0
            while i < len(aeneas_words):
                current_start = aeneas_words[i]['start']
                
                # Trouver tous les mots consécutifs qui partagent ce même start
                group_members = [i]
                j = i + 1
                while j < len(aeneas_words) and aeneas_words[j]['start'] == current_start:
                    group_members.append(j)
                    j += 1
                
                # Si on a un groupe (2+ mots avec le même start)
                if len(group_members) > 1:
                    # Vérifier si ce groupe contient des mots avec des durées trop courtes
                    has_short_durations = any(
                        aeneas_words[k]['end'] - aeneas_words[k]['start'] < MIN_DURATION_THRESHOLD
                        for k in group_members
                    )
                    
                    if has_short_durations:
                        # Trouver la fin maximale dans le groupe
                        group_max_end = max(aeneas_words[k]['end'] for k in group_members)
                        
                        # Trouver le prochain mot avec un start différent
                        next_idx = j
                        if next_idx < len(aeneas_words):
                            next_normal_start = aeneas_words[next_idx]['start']
                            
                            # Calculer l'intervalle total disponible
                            start_time = current_start
                            available_duration = next_normal_start - start_time
                            num_words = len(group_members)
                            
                            # Répartir équitablement
                            sub_duration = available_duration / num_words
                            for idx, member_idx in enumerate(group_members):
                                aeneas_words[member_idx]['start'] = start_time + idx * sub_duration
                                aeneas_words[member_idx]['end'] = start_time + (idx + 1) * sub_duration
                            
                            i = next_idx
                            continue
                
                i += 1
            
            # Étape 2: Corriger les mots isolés avec une durée < 20ms
            # Étendre le mot pour qu'il ait au moins MIN_DURATION_ABSOLUTE
            # en empiétant sur l'intervalle suivant si nécessaire
            i = 0
            while i < len(aeneas_words):
                duration = aeneas_words[i]['end'] - aeneas_words[i]['start']
                if duration > 0 and duration < MIN_DURATION_ABSOLUTE:
                    needed_extension = MIN_DURATION_ABSOLUTE - duration
                    
                    if i + 1 < len(aeneas_words):
                        next_start = aeneas_words[i+1]['start']
                        available_before_next = next_start - aeneas_words[i]['end']
                        
                        if available_before_next >= needed_extension:
                            # Assez d'espace avant le prochain mot, étendre
                            aeneas_words[i]['end'] += needed_extension
                        else:
                            # Pas assez d'espace, prendre ce qui est disponible
                            # et réduire la durée du mot suivant si nécessaire
                            aeneas_words[i]['end'] = next_start
                            
                            # Si on a quand même pas assez, empiéter sur le mot suivant
                            if aeneas_words[i]['end'] - aeneas_words[i]['start'] < MIN_DURATION_ABSOLUTE:
                                extra_needed = MIN_DURATION_ABSOLUTE - (aeneas_words[i]['end'] - aeneas_words[i]['start'])
                                aeneas_words[i]['end'] += extra_needed
                                # Déplacer le start du mot suivant
                                aeneas_words[i+1]['start'] += extra_needed
                                # Et ajuster son end aussi
                                aeneas_words[i+1]['end'] += extra_needed
                    else:
                        # Dernier mot, étendre à MIN_DURATION_ABSOLUTE
                        aeneas_words[i]['end'] = aeneas_words[i]['start'] + MIN_DURATION_ABSOLUTE
                
                i += 1
            
            # Nettoyer le fichier temporaire txtm
            if os.path.exists("/tmp/aeneas_temp.txtm"):
                os.unlink("/tmp/aeneas_temp.txtm")
            
            # Calculer la durée audio (à partir du dernier mot)
            audio_duration = aeneas_words[-1]['end'] if aeneas_words else 0
            
            # Vérifier que le nombre de mots correspond
            if len(aeneas_words) != len(original_words):
                print(f"  ⚠️  Nombre de mots différent: original={len(original_words)}, aeneas={len(aeneas_words)}")
                # Dans ce cas, on garde les résultats aeneas car ils sont déjà alignés avec le texte
            
            # Sauvegarder
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"words": aeneas_words, "audio_duration": audio_duration}, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ {output_path} ({len(aeneas_words)} mots, durée: {audio_duration:.1f}s)")
            return True
            
        finally:
            # Nettoyer le fichier texte temporaire
            if os.path.exists(txt_path):
                os.unlink(txt_path)
                
    except Exception as e:
        print(f"  ✗ {output_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_timings_for_text(text, audio_path, output_path, use_aeneas=False):
    """Génère un fichier de timings avec WhisperX ou aeneas.
    
    Si use_aeneas=True, utilise aeneas pour l'alignement forcé (plus précis).
    Sinon, utilise WhisperX CLI.
    
    Utilise l'outil CLI whisperx pour obtenir les timings avec alignement amélioré,
    puis aligne ces timings avec les mots du texte original.
    """
    if use_aeneas:
        return generate_timings_with_aeneas(text, audio_path, output_path)
    
    try:
        import subprocess
        import tempfile
        
        print(f"  Traitement avec WhisperX: '{text[:50]}...'")
        
        # Utiliser la CLI whisperx qui gère correctement l'alignement
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_json_path = tmp_file.name
        
        try:
            # Appel à whisperx CLI
            whisperx_cli = '/home/simon/Repos/lecture_vocale/.venv/bin/whisperx'
            cmd = [
                whisperx_cli,
                str(audio_path),
                '--language', 'fr',
                '--output_format', 'json',
                '--output_dir', os.path.dirname(tmp_json_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd='/home/simon/Repos/lecture_vocale'
            )
            
            if result.returncode != 0:
                print(f"  ✗ Erreur whisperx: {result.stderr}")
                return False
            
            # Lire le résultat JSON généré par whisperx
            # Le fichier a le même nom que l'audio mais avec .json
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            whisperx_json_path = os.path.join(os.path.dirname(tmp_json_path), f"{base_name}.json")
            
            if not os.path.exists(whisperx_json_path):
                print(f"  ✗ Fichier JSON introuvable: {whisperx_json_path}")
                return False
            
            with open(whisperx_json_path, 'r', encoding='utf-8') as f:
                whisperx_data = json.load(f)
            
            # Extraire les mots de whisperx (qui utilise word_segments)
            whisperx_words = []
            for word_seg in whisperx_data.get('word_segments', []):
                whisperx_words.append({
                    "text": word_seg.get('word', ''),
                    "start": float(word_seg.get('start', 0)),
                    "end": float(word_seg.get('end', 0))
                })
            
            # Calculer la durée audio
            audio_duration = float(whisperx_data['segments'][-1]['end']) if whisperx_data['segments'] else 0
            
            # Aligner les mots originaux avec les timings whisperX
            # Utiliser l'alignement intelligent pour correspondre les mots
            original_words = split_text_into_words(text)
            words = align_with_reference(original_words, whisperx_words)
            
            # Sauvegarder
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"words": words, "audio_duration": audio_duration}, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ {output_path} ({len(words)} mots, durée: {audio_duration:.1f}s)")
            return True
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_json_path):
                os.unlink(tmp_json_path)
                
    except Exception as e:
        print(f"  ✗ {output_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_timings_for_school(school_name, use_aeneas=False):
    """Génère les timings pour une école."""
    school_dir = DONNEES_DIR / school_name
    textes_file = school_dir / "textes.md"
    audio_dir = school_dir / "audio"
    timings_dir = school_dir / "timings"
    timings_dir.mkdir(parents=True, exist_ok=True)
    
    if not textes_file.exists():
        print(f"⚠️  {textes_file} introuvable")
        return 0
    
    print(f"\n🏫 {school_name} {'(aeneas)' if use_aeneas else '(whisperx)'}")
    textes = parse_textes_md(textes_file)
    if not textes:
        print("  Aucun texte")
        return 0
    
    success = 0
    for safe_title, data in textes.items():
        audio_path = audio_dir / get_audio_filename(safe_title)
        timings_path = timings_dir / get_timings_filename(safe_title)
        
        if not audio_path.exists():
            print(f"  ⚠️  {audio_path} manquant")
            continue
        
        print(f"  '{data['original_title']}'...")
        if generate_timings_for_text(data['content'], audio_path, timings_path, use_aeneas=use_aeneas):
            success += 1
    return success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('school', nargs='?', default=None)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--use-aeneas', action='store_true', 
                        help='Utiliser aeneas pour l\'alignement forcé (plus précis)')
    args = parser.parse_args()
    
    if not DONNEES_DIR.exists():
        print(f"Erreur: {DONNEES_DIR} introuvable")
        sys.exit(1)
    
    total = 0
    schools = [d.name for d in DONNEES_DIR.iterdir() if d.is_dir()]
    
    if not schools:
        print("Aucune école")
        sys.exit(1)
    
    targets = [args.school] if args.school else schools
    if args.all:
        targets = schools
    
    # Vérifier que aeneas est disponible si demandé
    if args.use_aeneas and not AENEAS_AVAILABLE:
        print("❌ aeneas n'est pas disponible. Installez-le avec: pip install aeneas")
        sys.exit(1)
    
    for school in targets:
        total += generate_timings_for_school(school, use_aeneas=args.use_aeneas)
    
    print(f"\n✅ {total} fichiers générés")


if __name__ == "__main__":
    main()
