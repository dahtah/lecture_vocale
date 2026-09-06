# 🔊 Lecture Vocale

Application web pour aider les enfants à suivre une lecture audio avec **surlignage mot-par-mot synchronisé**. Développée avec l'aide de Mistral Vibe.

## ✨ Fonctionnalités

### 📖 Interface Utilisateur
- **Sélection par école** 
- **Menu des textes** : Chargement dynamique depuis les fichiers `textes.md`
- **Zone de texte** : Affichage du texte sélectionné (lecture seule pour les textes présélectionnés)
- **Mode "Nouveau texte"** : Pour entrer un texte personnalisé
- **Contrôles de lecture** : Play, Pause, Stop
- **Contrôle de vitesse** : Slider pour ajuster la vitesse de lecture (0.5× à 2×)

### 🎯 Surlignage mot-par-mot
- **Alignement automatique** : Alignement forcé avec aeneas (alignement texte-audio)
- **Synchronisation temps réel** : Surlignage exact pendant la lecture
- **Gestion de la vitesse** : Fonctionne correctement à toutes les vitesses
- **Fallback intelligent** : Estimation de durée si les timings ne sont pas disponibles

### 🔊 Génération de contenu
- **Audio** : Généré avec Piper TTS
- **Timings** : Générés avec aeneas pour un alignement forcé texte-audio parfait
- **Correction automatique** : Les mots avec des durées trop courtes sont étendus à 20ms minimum

## 🚀 Utilisation

### Lancer l'application

```bash
cd lecture_vocale
python3 -m http.server 8000
```

Puis ouvrez [http://localhost:8000](http://localhost:8000) dans votre navigateur.

### Ajouter un nouveau texte

1. Modifier `donnees/{ecole}/textes.md` avec le format :
   ```markdown
   # Titre du texte
   
   Contenu du texte ici...
   ```

2. Générer l'audio :
   ```bash
   python3 generate_audio.py {ecole}
   ```

3. Générer les timings (avec aeneas) :
   ```bash
   python3 generate_timings.py --use-aeneas {ecole}
   ```

4. L'interface web chargera automatiquement les nouveaux textes et timings

## 📁 Structure du projet

```
lecture_vocale/
├── index.html              # Interface web principale
├── generate_audio.py       # Génération des fichiers audio (Piper TTS)
├── generate_timings.py     # Génération des timings (aeneas)
├── test_whisper_timings.py # Tests pour whisperX
├── pyproject.toml          # Dépendances Python
├── STATUS.md              # État du projet
├── README.md              # Ce fichier
└── donnees/
    ├── Cachin/
    │   ├── textes.md        # Textes source
    │   ├── audio/          # Fichiers .wav générés
    │   └── timings/        # Fichiers .json de timings
    └── Robespierre/
        ├── textes.md
        ├── audio/
        └── timings/
```

## 🛠️ Technologies

### Backend (Génération)
- **Python 3.12+**
- **aeneas** : Alignement forcé texte-audio (méthode principale)
- **whisperX** : Reconnaissance vocale avec alignement (méthode alternative)
- **Piper TTS** : Synthèse vocale pour générer les fichiers audio
- **torch** : Backend pour WhisperX

### Frontend
- **Vanilla JavaScript** : Pas de framework nécessaire
- **Web Audio API** : Pour la lecture audio
- **CSS moderne** : Design adapté aux enfants

### Dépendances

Installer les dépendances :
```bash
uv pip install -r pyproject.toml
```

Ou avec pip :
```bash
pip install aeneas piper-tts torch
```

## 🔧 Commandes utiles

### Générer tout
```bash
# Générer les audios et timings pour toutes les écoles
python3 generate_audio.py --all
python3 generate_timings.py --use-aeneas --all
```

### Générer pour une école spécifique
```bash
python3 generate_audio.py Cachin
python3 generate_timings.py --use-aeneas Cachin
```

### Comparer les méthodes
```bash
# Avec aeneas (recommandé, plus précis)
python3 generate_timings.py --use-aeneas Cachin

# Avec whisperX (alternative)
python3 generate_timings.py Cachin
```

## ⚡ Performances

- **Génération audio** : ~1-2s par mot avec Piper TTS
- **Génération timings** : ~20-30s par fichier avec aeneas
- **Surlignage** : Temps réel, précis au millième de seconde

## 📊 Précision des timings

Avec **aeneas** (alignement forcé) :
- ✅ Pas d'erreurs de transcription (utilise le texte original)
- ✅ Timings parfaits pour chaque mot
- ✅ Durée audio exactement correspondante
- ✅ Tous les mots ont au moins 20ms de durée

Avec **whisperX** (reconnaissance vocale) :
- ⚠️ Peut avoir des erreurs de transcription
- ⚠️ Nécessite un alignement avec le texte original
- ✅ Timings généralement bons

## 🎓 Cas d'usage pédagogique

- **Aide à la lecture** : Les enfants suivent le texte en temps réel
- **Compréhension** : Meilleure association entre le texte écrit et l'oral
- **Autonomie** : Les enfants peuvent écouter et suivre à leur rythme
- **Accessibilité** : Adapté aux enfants avec des difficultés de lecture

## 📄 Licence

Libre d'utilisation et de modification. Développé avec l'aide de Mistral Vibe.

## 🙏 Remerciements

- **Mistral AI** : Pour le développement de Mistral Vibe
- **ReadBeyond** : Pour le projet aeneas
- **Rhasspy** : Pour Piper TTS
