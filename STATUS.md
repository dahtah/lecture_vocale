# État du projet - Lecture Vocale

## Dernière mise à jour : 2026-09-03

---

## 🎯 Objectif
Développer une application web permettant aux enfants de suivre une lecture audio avec surlignage mot-par-mot synchronisé.

---

## ✅ Fonctionnalités implémentées

### Backend / Génération de contenu
- [x] **Structure des données** : Dossier `donnees/` avec sous-dossiers par école (Cachin, Robespierre)
- [x] **Stockage des textes** : Fichiers `textes.md` avec séparation par titres (`#`)
- [x] **Génération audio** : `generate_audio.py` utilise Piper TTS pour créer des fichiers `.wav`
  - Modèle : `fr_FR-gilles-low.onnx`
  - 6 fichiers audio générés pour Cachin
  - 2 fichiers audio générés pour Robespierre
- [x] **Génération des timings** : `generate_timings.py` utilise WhisperX via CLI
  - 6 fichiers JSON générés pour Cachin (timings précis, décalage résolu)
  - 2 fichiers JSON générés pour Robespierre
  - Format : `{words: [{text, start, end}], audio_duration}`

### Frontend
- [x] **Interface utilisateur** : Design adapté aux enfants et enseignants
- [x] **Menu des écoles** : Sélection entre Cachin et Robespierre
- [x] **Menu des textes** : Chargement dynamique depuis `textes.md`
- [x] **Zone de texte** : Affichage du texte sélectionné (non éditable pour les textes présélectionnés)
- [x] **Option "Nouveau texte"** : Permet d'avoir un texte éditable
- [x] **Contrôles de lecture** : Play, Pause, Stop
- [x] **Surlignage mot-par-mot** :
  - `startCloudHighlight()` : Méthode d'estimation (fallback)
  - `startTimingsHighlight()` : Méthode avec timings précis
  - **Chargement automatique des timings** depuis les fichiers JSON pour les textes présélectionnés
- [x] **Gestion de la vitesse** : Slider pour ajuster la vitesse de lecture
- [x] **Avertissement** : Affiché si le moteur cloud (Puter.js) n'est pas disponible

### Frontend
- [x] **Interface utilisateur** : Design adapté aux enfants et enseignants
- [x] **Menu des écoles** : Sélection entre Cachin et Robespierre
- [x] **Menu des textes** : Chargement dynamique depuis `textes.md`
- [x] **Zone de texte** : Affichage du texte sélectionné (non éditable pour les textes présélectionnés)
- [x] **Option "Nouveau texte"** : Permet d'avoir un texte éditable
- [x] **Contrôles de lecture** : Play, Pause, Stop
- [x] **Surlignage mot-par-mot** :
  - `startCloudHighlight()` : Méthode d'estimation (fallback)
  - `startTimingsHighlight()` : Méthode avec timings précis
- [x] **Gestion de la vitesse** : Slider pour ajuster la vitesse de lecture
- [x] **Avertissement** : Affiché si le moteur cloud (Puter.js) n'est pas disponible

### Génération des timings
- **Méthode actuelle** : aeneas avec alignement forcé (plus précis que WhisperX)
- **Méthode alternative** : WhisperX (base) avec alignement dédié
- **Précision** : Timings au niveau des mots avec alignement parfait (aeneas) ou amélioré (WhisperX)
- **Alignement** : aeneas utilise le texte original directement, pas de reconnaissance vocale
- **Avantages aeneas** :
  - Pas d'erreurs de transcription (contrairement à Whisper/WhisperX)
  - Timings parfaits pour chaque mot
  - Durée audio exactement correspondante
- **Fallback** : Si pas de timings disponibles, utilise `estimateWordDurations()`

---

## ⚠️ Problèmes connus

### 1. **Décalage du surlignage**
**Statut** : ✅ **RÉSOLU** via migration vers aeneas

**Symptômes** (avant la correction) :
- Le surlignage mot-par-mot se décalait progressivement pendant la lecture
- Décalage de ~17-20 secondes sur les textes longs (ex: Larbre_qui_chante : 199,1s audio, dernier mot à 181,6s avec whisper)
- WhisperX améliorait la situation mais avait encore des erreurs de transcription

**Solution implémentée** : Migration de WhisperX vers aeneas pour l'alignement forcé
- aeneas utilise un algorithme d'alignement forcé texte-audio, pas de reconnaissance vocale
- Le texte original est utilisé directement, donc pas d'erreurs de transcription
- Timings au niveau des mots avec une précision parfaite
- **Résultat** : Le dernier mot finit exactement à la fin de l'audio (décalage = 0,0s)

**Vérification** :
- Après régénération avec `generate_timings.py --use-aeneas --all` :
  - Larbre_qui_chante: 558 mots, dernier mot à 199,64s (audio: 199,64s) ✅
  - Exercice_Jour_1: 238 mots, dernier mot à 82,08s (audio: 82,08s) ✅
  - Tous les autres fichiers: décalage résolu ✅
  - Aucun mot avec une durée nulle ✅

### 2. Reconnaissance vocale Whisper imparfaite
**Statut** : Résolu par alignement avec texte original

**Problème initial** : Whisper reconnaissait mal certains mots (ex: "Stragie" au lieu de "STRATEGIE")

**Solution** : `align_original_with_timings()` utilise les mots du texte original avec les timings Whisper/WhisperX

**Résultat** : Les fichiers JSON contiennent bien les mots originaux avec des timings précis

### 3. Nombre de mots différent entre original et Whisper
**Statut** : Résolu

**Problème** : Whisper segmente différemment (ex: "C'était" → ["C", "'", "était"])

**Solution** : Algorithme de distribution proportionnelle des timings

---

## 📁 Structure du projet

```
lecture_vocale/
├── index.html              # Interface web principale
├── generate_audio.py       # Génération des fichiers audio (Piper TTS)
├── generate_timings.py     # Génération des timings (WhisperX)
├── STATUS.md               # Ce fichier
└── donnees/
    ├── Cachin/
    │   ├── textes.md        # Textes source (markdown)
    │   ├── audio/           # Fichiers .wav générés par Piper
    │   │   ├── Larbre_qui_chante.wav
    │   │   ├── Exercice_Jour_1.wav
    │   │   └── ...
    │   └── timings/         # Fichiers .json générés par Whisper
    │       ├── Larbre_qui_chante.json
    │       ├── Exercice_Jour_1.json
    │       └── ...
    └── Robespierre/
        ├── textes.md
        ├── audio/
        │   └── Texte_*.wav
        └── timings/
            └── Texte_*.json
```

---

## 🔧 Outils et dépendances

### Dépendances Python
- `aeneas` - Alignement forcé texte-audio (méthode principale, plus précise)
- `whisperx` - Reconnaissance vocale avec timings améliorés (méthode alternative)
- `torch` - Backend pour WhisperX
- `piper` - Synthèse vocale (TTS)

### Dépendances JavaScript
- `puter.js` - API de synthèse vocale cloud (optionnel)

### Fichiers de modèles
- `models/fr_FR-gilles-low.onnx` - Modèle Piper pour le français

---


---

## 🎬 Workflow

1. **Ajout d'un nouveau texte** :
   - Modifier `donnees/{ecole}/textes.md` avec format `# Titre\n\nTexte...`
   - Exécuter `python3 generate_audio.py {ecole}` pour générer l'audio
   - Exécuter `python3 generate_timings.py --use-aeneas {ecole}` pour générer les timings (aeneas, plus précis)
   - Alternative: `python3 generate_timings.py {ecole}` pour utiliser WhisperX
   - L'interface web chargera automatiquement les timings depuis les fichiers JSON

2. **Lecture** :
   - Ouvrir `index.html` dans un navigateur
   - Sélectionner l'école et le texte
   - Cliquer sur Play

---

## 🔍 Debugging

### Vérifier les timings générés
```bash
# Lister les fichiers
ls -lh donnees/Cachin/timings/

# Inspecter un fichier
head -20 donnees/Cachin/timings/Larbre_qui_chante.json
```

### Tester la lecture
```bash
# Lancer le serveur
python3 -m http.server 8000

# Ouvrir dans le navigateur
# http://localhost:8000
```

### Tester WhisperX manuellement
```bash
# Après installation de whisperx:
uv pip install whisperx

# Tester la génération des timings
python3 generate_timings.py Cachin

# Tester un fichier spécifique (le script test peut être mis à jour)
python3 test_whisper_timings.py
```

---

## 🚀 Prochaines étapes

### Priorité 1 : Corriger le décalage du surlignage
- [x] Migrer vers [whisperX](https://github.com/m-bain/whisperX) plutôt que Whisper
- [ ] Tester la nouvelle version avec `python3 generate_timings.py --all`
- [ ] Couper le texte en paragraphes, faire le rendu audio et le calcul des timestamps par paragraphe pour ne pas accumuler l'erreur (si besoin après tests) 

### Priorité 2 : Améliorations futures
- [x] Charger le modèle WhisperX une seule fois (via CLI, optimisé)
- [ ] Ajouter un indicateur de progression pendant la génération
- [ ] Corriger les erreurs de reconnaissance de whisperX (ex: "Stragi" → "STRATEGIE")
  - Option: Utiliser une table de correspondance pour les mots connus
  - Option: Réimplémenter l'alignement avec une meilleure gestion des différences de longueur



---

## 🎯 Prochaine action immédiate
**Corriger le décalage du surlignage** - C'est le blocage principal pour la livraison.

### Solution implémentée : aeneas pour l'alignement forcé
- aeneas a été testé et intégré avec succès dans `generate_timings.py`
- Utilisation: `python3 generate_timings.py --use-aeneas Cachin`
- aeneas produit des timings au niveau des mots avec une précision parfaite
- Tous les fichiers ont été régénérés avec aeneas

### Résultats
- **Précision**: Les timings aeneas sont parfaitement alignés avec l'audio
- **Dernier mot**: Finir exactement à la fin de l'audio (ex: Larbre_qui_chante: dernier mot à 199.64s, audio: 199.64s)
- **Durée corrigée**: La durée audio est maintenant correcte (199.64s au lieu de 199.09s)
- **Mots valides**: Tous les mots ont une durée > 0 (correction des mots avec start=end)

Méthode de test recommandée :
1. Créer un fichier audio très court (2-3 mots)
2. Générer les timings avec aeneas : `python3 generate_timings.py --use-aeneas Cachin`
3. Vérifier que le surlignage est synchronisé avec Firefox DevTools
4. Tester avec Larbre_qui_chante à 101s (devrait être sur "comme si l'hiver")
