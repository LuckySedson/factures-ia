CREATE DATABASE factures_db ENCODING 'UTF8';

CREATE TABLE fournisseurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    nom_normalise VARCHAR(255) NOT NULL UNIQUE,
    adresse TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    nom_fichier_original VARCHAR(255) NOT NULL,
    chemin_stockage TEXT NOT NULL,
    type_document VARCHAR(20) NOT NULL
        CHECK (type_document IN ('pdf_texte', 'pdf_scan', 'image')),
    hash_sha256 CHAR(64) NOT NULL UNIQUE,
    texte_ocr TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE factures (
    id SERIAL PRIMARY KEY,
    document_id INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    fournisseur_id INT REFERENCES fournisseurs(id) ON DELETE SET NULL,
    numero_facture VARCHAR(100),
    date_facture DATE,
    montant_ht NUMERIC(12, 2),
    tva NUMERIC(12, 2),
    montant_ttc NUMERIC(12, 2),
    devise CHAR(3) DEFAULT 'EUR',
    statut VARCHAR(30) NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN (
            'en_attente', 'a_verifier', 'doublon_suspect',
            'validee_auto', 'validee_manuelle', 'rejetee'
        )),
    score_confiance REAL CHECK (score_confiance BETWEEN 0 AND 1),
    duree_traitement_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP
);

CREATE UNIQUE INDEX uq_facture_validee
    ON factures (fournisseur_id, numero_facture)
    WHERE statut IN ('validee_auto', 'validee_manuelle');

CREATE INDEX idx_factures_doublon ON factures (fournisseur_id, numero_facture);
CREATE INDEX idx_factures_statut ON factures (statut);

CREATE TABLE champs_extraits (
    id SERIAL PRIMARY KEY,
    facture_id INT NOT NULL REFERENCES factures(id) ON DELETE CASCADE,
    nom_champ VARCHAR(30) NOT NULL
        CHECK (nom_champ IN (
            'fournisseur', 'numero_facture', 'date_facture',
            'montant_ht', 'tva', 'montant_ttc'
        )),
    valeur_extraite TEXT,
    valeur_corrigee TEXT,
    confiance REAL CHECK (confiance BETWEEN 0 AND 1),
    methode VARCHAR(10) NOT NULL CHECK (methode IN ('regex', 'llm', 'docling')),
    UNIQUE (facture_id, nom_champ)
);

CREATE TABLE anomalies (
    id SERIAL PRIMARY KEY,
    facture_id INT NOT NULL REFERENCES factures(id) ON DELETE CASCADE,
    type_anomalie VARCHAR(30) NOT NULL
        CHECK (type_anomalie IN (
            'incoherence_montant', 'doublon_exact', 'doublon_metier',
            'champ_manquant', 'faible_confiance'
        )),
    details TEXT,
    facture_liee_id INT REFERENCES factures(id) ON DELETE SET NULL,
    resolue BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logs_traitement (
    id SERIAL PRIMARY KEY,
    facture_id INT REFERENCES factures(id) ON DELETE CASCADE,
    etape VARCHAR(50) NOT NULL
        CHECK (etape IN ('RECEPTION', 'OCR', 'EXTRACTION_REGEX', 'EXTRACTION_LLM', 'VERIFICATION_METIER')),
    temps_execution_ms INT,
    statut_execution VARCHAR(20) NOT NULL CHECK (statut_execution IN ('succes', 'erreur')),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mesures_temps_manuel (
    id SERIAL PRIMARY KEY,
    reference_facture VARCHAR(100) NOT NULL,
    operateur VARCHAR(50) NOT NULL,
    duree_secondes INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);