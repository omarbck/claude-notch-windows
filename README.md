# Claude Notch for Windows

Barre flottante affichant ton usage Claude en temps réel, inspirée de [claude-notch](https://github.com/acenaut/claude-notch) (macOS).

## Ce que ça fait

- Barre fine et transparente collée en haut de l'écran, toujours visible
- Affiche **Session %** et **Weekly %** en couleur (vert → orange → rouge)
- Survol de la barre → panneau étendu avec barres de progression pour Session, Weekly, Sonnet, Opus
- Clic droit → Rafraîchir / Settings / Quitter
- Drag possible pour déplacer la barre horizontalement
- Refresh automatique toutes les 60 secondes

## Installation

### Prérequis

- **Python 3.10+** → https://python.org (coche "Add to PATH" à l'installation)
- Un compte Claude Pro / Max / Team

### Lancer

1. Télécharge ou clone ce dossier
2. Double-clique sur **`setup.bat`** (installe les dépendances + lance l'app)
3. La fenêtre de configuration s'ouvre : colle ta `sessionKey`

Pour les lancements suivants, utilise **`run.bat`**.

## Récupérer ta sessionKey

1. Ouvre **chrome.exe** et va sur **claude.ai**, connecte-toi
2. Appuie sur **F12** (DevTools)
3. Onglet **Application** → **Cookies** → `https://claude.ai`
4. Cherche la ligne `sessionKey`, copie la valeur (commence par `sk-ant-...`)
5. Colle-la dans la fenêtre de config de Claude Notch

> Ta session key est stockée localement dans `~/.claude_notch.json`. Elle n'est jamais envoyée ailleurs que directement à `claude.ai`.

## Démarrage automatique avec Windows

Pour que Claude Notch se lance au démarrage :

1. Appuie sur `Win + R`, tape `shell:startup`, valide
2. Crée un raccourci vers `run.bat` dans ce dossier

## Structure

```
claude_notch.py   — App principale
requirements.txt  — Dépendances Python
setup.bat         — Installation + premier lancement
run.bat           — Lancement sans console
README.md         — Ce fichier
```

## Dépendances

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — UI moderne
- [requests](https://requests.readthedocs.io) — Appels API

## Notes

- Fonctionne sur tout PC Windows (pas besoin d'une encoche physique)
- La barre est placée en haut au centre de l'écran par défaut
- L'API utilisée est la même que celle de `claude.ai/settings/usage`
- Non affilié à Anthropic
