# 📊 Plateforme d'Analyse du Risque de Crédit – Lending Club

Projet complet de Data Analytics réalisé à partir du jeu de données **Lending Club**, couvrant l'ensemble du cycle de traitement des données : de l'ingestion des données brutes jusqu'à la création de tableaux de bord interactifs sous Power BI.

---

# 🎯 Objectif du projet

L'objectif de ce projet est de construire une solution décisionnelle permettant d'analyser la performance d'un portefeuille de prêts et de suivre les principaux indicateurs liés au risque de crédit.

Le projet permet notamment de :

- Analyser les performances du portefeuille de prêts
- Suivre le volume des financements accordés
- Mesurer le taux de défaut
- Identifier les profils de prêts les plus risqués
- Construire des tableaux de bord interactifs pour faciliter la prise de décision

---

# 🏗️ Architecture du projet

Le projet suit une architecture moderne de type **Bronze / Silver / Gold**.

```
Données brutes (CSV)
        │
        ▼
Bronze
(Ingestion des données)
        │
        ▼
Silver
(Nettoyage & Transformation)
        │
        ▼
Gold
(Tables métiers prêtes à l'analyse)
        │
        ▼
Power BI
(Tableaux de bord interactifs)
```

---

# 📁 Structure du projet

```
ETL-LendingClub/
│
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── notebooks/
│
├── src/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── dashboards/
│   └── LendingClub.pbix
│
├── tests/
│
├── requirements.txt
│
└── README.md
```

---

# 📊 Tableau de bord Power BI

Le tableau de bord est composé de plusieurs pages d'analyse.

## 📌 1. Vue d'ensemble

- Nombre total de prêts
- Volume total financé
- Nombre total de défauts
- Taux de défaut
- Évolution mensuelle du taux de défaut
- Répartition des prêts par grade

---

## 📌 2. Analyse du portefeuille

- Répartition des prêts
- Analyse des montants financés
- Performance par grade
- Analyse des taux d'intérêt
- Répartition des prêts

---

## 📌 3. Analyse du risque de crédit

- Taux de défaut par période
- Analyse des défauts par grade
- Analyse des prêts en défaut
- Indicateurs de risque

---

## 📌 4. Analyse géographique

- Répartition des prêts par État
- Volume financé par région
- Analyse géographique des défauts

---

# 📈 Principaux indicateurs (KPIs)

- Nombre total de prêts
- Volume total financé
- Nombre total de défauts
- Taux de défaut
- Taux d'intérêt moyen
- Montant moyen des prêts
- Évolution mensuelle des financements

---

# 🛠️ Technologies utilisées

- Python
- Pandas
- NumPy
- SQL
- Power BI
- DAX
- Power Query
- Git
- GitHub

---

# ⚙️ Pipeline ETL

## Bronze

- Import des données
- Contrôle qualité
- Validation des données

## Silver

- Nettoyage des données
- Traitement des valeurs manquantes
- Transformation des variables
- Standardisation

## Gold

Création de tables optimisées pour l'analyse :

- credit_summary
- grade_performance
- geo_distribution
- vintage_analysis

---

# 📊 Fonctionnalités Power BI

- Tableaux de bord interactifs
- Mesures DAX
- Cartes KPI
- Graphiques dynamiques
- Segments (Slicers)
- Mise en forme conditionnelle
- Analyse temporelle

---

# 📷 Aperçu du tableau de bord

*(Ajouter ici les captures d'écran des différentes pages du dashboard.)*

---

# 💡 Compétences démontrées

- Développement de pipelines ETL
- Nettoyage et transformation des données
- Modélisation de données
- Analyse de données
- SQL
- Power BI
- DAX
- Business Intelligence
- Visualisation de données
- Analyse du risque de crédit

---

# 🚀 Améliorations futures

- Actualisation automatique des données
- Pipeline ETL incrémental
- Prédiction du risque par Machine Learning
- Prévision des défauts de paiement
- Tableau de bord en temps réel

---

# 👩‍💻 Auteur

**Nadia Kheira BELLAZREG**

Data Scientist | Data Analyst | Business Intelligence

📧 Ajouter votre adresse e-mail



🐙 GitHub : https://github.com/nadia-blzrg

---

## ⭐ N'hésitez pas à laisser une étoile si ce projet vous a intéressé !

Dataset :
Lending Club Loan Data (Kaggle)

Le fichier source n'est pas inclus dans ce dépôt en raison de sa taille (>2 Go).