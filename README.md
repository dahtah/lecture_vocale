# 🔊 Lecture vocale

Application web de synthèse vocale pensée pour les enfants en difficulté de lecture. Codée intégralement avec l'aide de Mistral Vibe.

Tape ou colle un texte, écoute-le à voix haute avec **surlignage mot par mot** synchronisé à la parole.

## ✨ Fonctionnalités

- **Édition et lecture dans la même zone** (contenteditable)
- **Surlignage mot par mot** synchronisé avec la voix
- **Deux moteurs** :
  - 🖥️ **Voix du navigateur** — local, hors ligne, gratuit (API `speechSynthesis`)
  - ☁️ **Voix cloud** — haute qualité neuronale (Amazon Polly via Puter.js), gratuit, sans clé API
- **Sélection de voix** (locale ou cloud) avec priorité aux voix françaises haute qualité
- **Contrôle de la vitesse** de lecture (0.5× → 1.5×)
- **Lecture / Pause / Arrêt**
- Détection automatique de Chrome/Linux (sans voix locale) → bascule sur le cloud

## 🚀 Utilisation

### Option 1 : ouvrir directement

Ouvre le fichier `lecture-voix.html` dans un navigateur (Chrome, Firefox, Edge, Safari).

### Option 2 : servir en local

```bash
cd lecture-voix-local
python3 -m http.server 8000
```

Puis ouvre [http://localhost:8000/lecture-voix.html](http://localhost:8000/lecture-voix.html).

### Option 3 : hébergement statique

L'application est un fichier HTML unique, sans build ni dépendance npm.  
Elle peut être hébergée sur n'importe quel hébergeur statique :  
**GitHub Pages**, Netlify, Vercel, Cloudflare Pages, etc.

## 🌐 Déploiement sur GitHub Pages

1. Crée un dépôt public sur GitHub.
2. Renomme `lecture-voix.html` en `index.html` et pousse-le à la racine :
  ```bash
   git init
   mv lecture-voix.html index.html
   git add index.html README.md
   git commit -m "Lecture vocale — app statique"
   git branch -M main
   git remote add origin https://github.com/<ton-user>/<ton-repo>.git
   git push -u origin main
  ```
3. Active GitHub Pages : **Settings → Pages → Deploy from branch → main**.
4. Ton app est en ligne sur `https://<ton-user>.github.io/<ton-repo>/`.

## 🔧 Fonctionnement technique


| Élément             | Détail                                                                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Moteur local        | API `speechSynthesis` du navigateur, surlignage via événements `onboundary` (fallback minuté à 150 mots/min)                                        |
| Moteur cloud        | [Puter.js](https://js.puter.com/v2/) → Amazon Polly, retourne un `HTMLAudioElement`, surlignage via `requestAnimationFrame` sur `audio.currentTime` |
| Contrôle de vitesse | Local : `utterance.rate`. Cloud : `audio.playbackRate` (modifie aussi légèrement la hauteur)                                                        |
| Limite cloud        | 3000 caractères par appel Puter.js                                                                                                                  |
| Dépendance externe  | uniquement le script `https://js.puter.com/v2/` (CDN)                                                                                               |


## ⚠️ Notes

- Le moteur cloud nécessite une **connexion Internet** (Puter.js parle directement à Polly/OpenAI depuis le navigateur — aucune clé API à gérer).
- **Chrome sur Linux** ne fournit pas de voix locales par défaut ; l'app bascule automatiquement sur le moteur cloud.
- `audio.playbackRate` ralentit/accélère la voix cloud mais **modifie aussi le pitch**. À des vitesses modérées (0.7×–1.3×) c'est peu perceptible.

## 📄 Licence

Libre d'utilisation et de modification.
