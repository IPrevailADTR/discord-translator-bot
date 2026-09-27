# Guide d'Installation du Bot de Traduction Discord (Version Render)

Ce guide explique comment installer le bot de traduction Discord sur Render en utilisant la version package. C'est plus simple que la version précédente !

---

## 1. Prérequis
- Un compte Discord avec droits d'administrateur sur le serveur
- Un compte GitHub ([https://github.com/](https://github.com/))
- Un compte Render ([https://render.com/](https://render.com/))
- Un navigateur web (Chrome, Firefox, Safari, etc.)

> 💡 **Note importante** : Tu n'as pas besoin d'installer Python ou d'autres outils sur ton ordinateur. Tout se passe directement sur Render (mais tu dois passer par GitHub pour les fichiers du projet).

---

## 2. Créer une Application et un Bot Discord

1. Va sur [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique sur "New Application"
3. Donne un nom à l'application (ex: "Trad-Bot")
4. Dans le menu à gauche, clique sur "Bot" puis sur "Add Bot"
5. Clique sur "Reset Token" et copie le Token (garde-le secret !)
6. Active les permissions suivantes :
   - PRESENCE INTENT
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT

---

## 3. Inviter le Bot sur ton Serveur Discord

1. Dans le menu à gauche, clique sur "OAuth2" > "URL Generator"
2. Coche les cases :
   - bot
   - applications.commands
3. Dans "Bot Permissions", coche :
   - VIEW CHANNELS
   - SEND MESSAGES
   - READ MESSAGE HISTORY
   - USE SLASH COMMANDS
4. Copie le lien généré en bas, ouvre-le dans ton navigateur, et invite le bot sur ton serveur.

---

## 4. Préparer le Dépôt GitHub

1. Crée un nouveau dépôt GitHub (ou utilise un existant)
2. Ajoute un fichier `requirements.txt` avec :
   ```
   discord-trad-bot==X.Y.Z
   ```
   (remplace X.Y.Z par la dernière version du package)
3. Ajoute un fichier `main.py` avec :
   ```python
   from discord_trad_bot import run_bot

   if __name__ == "__main__":
       run_bot()
   ```
4. Pousse ces fichiers sur GitHub (commit + push)

---

## 5. Créer un Service Web Render

1. Va sur [https://dashboard.render.com/](https://dashboard.render.com/)
2. Clique sur "New +" > "Web Service"
3. Connecte ton compte GitHub si ce n'est pas déjà fait
4. Sélectionne ton dépôt et la branche

---

## 6. Configurer le Service
- **Environnement** : Python 3 (Render détecte automatiquement via `requirements.txt`)
- **Build Command** : (laisse vide, Render utilisera `pip install -r requirements.txt` par défaut)
- **Start Command** : `python main.py`

---

## 7. Définir les Variables d'Environnement
1. Dans le dashboard Render, va dans l'onglet "Environment" de ton service
2. Ajoute :
   - DISCORD_TOKEN (colle ici le token de ton bot Discord)
   - GOOGLE_TRANSLATE_API_KEY (laisse vide ou mets un texte bidon)

---

## 8. Déployer et Lancer le Bot

1. Clique sur "Create Web Service"
2. Attends la fin du build et du déploiement
3. Vérifie les logs pour voir si tout fonctionne
4. Si tout est ok, ton bot sera en ligne et connecté à ton serveur Discord !

---

## 9. Mettre à Jour le Bot

Quand une nouvelle version est disponible :
1. Modifie simplement le numéro de version dans `requirements.txt` sur GitHub
2. Pousse le changement (commit + push)
3. Render mettra à jour automatiquement le bot

---

## 10. Utiliser le Bot

Les commandes restent les mêmes :
- `!setlang fr` : Définir ta langue
- `!mylang` : Voir ta langue actuelle
- `!languages` : Voir les langues supportées
- `!settranschannel` : Définir le canal de traduction

---

## Besoin d'Aide ?

- Demande à Pierre ou envoie une capture d'écran du problème !

---

**Bon jeu et bonnes traductions !** 🎮🌍 