# Raw Source Datasets — Chakravyuha

These are the **publicly available reference datasets** we used as sources to build our custom preprocessed legal dataset.

## Datasets Downloaded

| # | File | Source | Records | Description |
|---|------|--------|---------|-------------|
| 1 | `hf_bns_definitions.json` | [navaneeth005/BNS_definitions](https://huggingface.co/datasets/navaneeth005/BNS_definitions) | 358 | All 358 BNS 2023 sections with legal definitions |
| 2 | `hf_ipc_bns_transformation.json` | [nandhakumarg/IPC_and_BNS_transformation](https://huggingface.co/datasets/nandhakumarg/IPC_and_BNS_transformation) | 563 | IPC-to-BNS section mapping with prompts/responses |
| 3 | `hf_ipc_sections_karan.json` | [karan842/ipc-sections](https://huggingface.co/datasets/karan842/ipc-sections) | 444 | IPC sections with Description, Offense, Punishment |
| 4 | `github_ipc_civictech.json` | [civictech-India/Indian-Law-Penal-Code-Json](https://github.com/civictech-India/Indian-Law-Penal-Code-Json) | 575 | Full IPC in JSON (chapter, section, description) |
| 5 | `hf_indian_law_viber.json` | [viber1/indian-law-dataset](https://huggingface.co/datasets/viber1/indian-law-dataset) | 24,607 | Indian law Q&A pairs (Instruction/Response format) |

## Government Sources (Authoritative References)

| Source | URL | Format |
|--------|-----|--------|
| India Code (Official) | https://www.indiacode.nic.in/handle/123456789/20062 | HTML |
| Ministry of Home Affairs | https://www.mha.gov.in/ | PDF (Gazette) |
| NCRB BNS 2023 | https://www.ncrb.gov.in/ | PDF |
| PRS India (Bill Tracker) | https://prsindia.org/billtrack/the-bharatiya-nyaya-second-sanhita-2023 | HTML/PDF |

## How We Used These

1. **IPC sections** sourced from civictech-India JSON + karan842 HuggingFace dataset
2. **BNS 2023 sections** sourced from navaneeth005/BNS_definitions + official Gazette of India
3. **IPC-to-BNS mapping** cross-referenced from nandhakumarg/IPC_and_BNS_transformation
4. **Preprocessed** into our custom structured schema (see `data/bns_sections.json`, `data/ipc_sections.json`)
5. **Augmented** with keywords, bailable/cognizable flags, defence strategies — manually curated from bare act text
6. **Embedded** into ChromaDB vector database using SentenceTransformer (all-MiniLM-L6-v2)
