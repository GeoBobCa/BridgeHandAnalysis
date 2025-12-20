BridgeMaster/
│
├── .env                    # [FILE] API Keys.
├── .gitignore              # [FILE] Git ignore rules.
├── main.py                 # [FILE] App entry point.
├── requirements.txt        # [FILE] Dependencies.
│
├── data/                   # [FOLDER] Local Data.
│   ├── bridge_master.db
│   └── archives/
│
├── docs/                   # [FOLDER] Reference Material & Manuals
│   ├── architecture/       # [SUBFOLDER] Technical details.
│   │   ├── folder_structure.md  # (Save this tree here!)
│   │   └── database_schema.md
│   │
│   └── user_guides/        # [SUBFOLDER] How-to files.
│       ├── getting_started.md
│       └── importing_hands.md
│
├── inputs/                 # [FOLDER] Dropbox for LIN/PBN files.
│
├── src/                    # [FOLDER] Source Code.
│   ├── core/
│   │   ├── bridge_math.py
│   │   ├── parsers.py
│   │   ├── database.py
│   │   └── ai_orchestrator.py
│   │
│   ├── ui/
│   │   ├── main_window.py
│   │   └── widgets/
│   │
│   └── utils/
│       ├── logger.py
│       └── paths.py
│
└── tests/                  # [FOLDER] Unit Tests.