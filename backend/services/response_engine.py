"""Response engine — curated, safe legal guidance per scenario.

Each scenario has:
  - guidance: actionable steps the user should take
  - sections: relevant BNS/IPC section references
  - outcome: AI Judge predicted outcome
  - complaint_draft: auto-generated complaint text (if applicable)
  - severity: low / medium / high / critical
  - helplines: emergency numbers if relevant
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Response model ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LegalResponse:
    scenario: str
    title: str
    guidance: str
    sections: list[str]
    outcome: str
    severity: str
    complaint_draft: str = ""
    helplines: list[str] = field(default_factory=list)


# ── Scenario database ────────────────────────────────────────────────────────

SCENARIOS: dict[str, LegalResponse] = {
    # ── Documents / License ──────────────────────────────────────────────
    "lost_license": LegalResponse(
        scenario="lost_license",
        title="Lost Driving License",
        guidance=(
            "Don't worry — this is not a criminal matter.\n\n"
            "What to do:\n"
            "1. Apply for a duplicate license on the Parivahan portal (parivahan.gov.in)\n"
            "2. OR visit your nearest RTO office with an FIR/complaint copy\n"
            "3. Use DigiLocker for an instant digital copy of your license\n"
            "4. Carry the digital license until the duplicate arrives"
        ),
        sections=["Motor Vehicles Act Section 7 (Licensing)", "Rule 139 (Duplicate License)"],
        outcome="No legal issue. Duplicate can be obtained within 7-15 days.",
        severity="low",
    ),
    "lost_documents": LegalResponse(
        scenario="lost_documents",
        title="Lost Important Documents",
        guidance=(
            "Steps to recover lost documents:\n\n"
            "1. File a police complaint / FIR for the lost document\n"
            "2. Apply for a duplicate through the issuing authority\n"
            "3. For Aadhaar: Visit any Aadhaar enrollment center or use mAadhaar app\n"
            "4. For PAN: Apply on NSDL/UTI portal for duplicate\n"
            "5. For Passport: Apply on Passport Seva for re-issue\n"
            "6. Use DigiLocker for digital copies of most documents"
        ),
        sections=["IPC-468 (Forgery for cheating — if documents misused)"],
        outcome="No legal issue for the owner. If stolen, police will investigate misuse.",
        severity="low",
    ),

    # ── Traffic / Challan ────────────────────────────────────────────────
    "traffic_fine": LegalResponse(
        scenario="traffic_fine",
        title="Traffic Fine / Challan",
        guidance=(
            "What to do:\n\n"
            "1. If valid fine: Pay online at echallan.parivahan.gov.in or at traffic court\n"
            "2. If wrong fine: Contest it within 60 days at the traffic court\n"
            "3. Show digital license via DigiLocker if license was demanded\n"
            "4. If police is rude or demanding bribe: Note badge number, complain to SP office"
        ),
        sections=[
            "Motor Vehicles Act 2019 (Amended penalties)",
            "BNS-201 (Rash driving: Up to 6 months + fine)",
        ],
        outcome="Fine can be contested in traffic court. Pay or appear within 60 days.",
        severity="low",
        complaint_draft=(
            "To,\nThe Traffic Court Officer\n\n"
            "Subject: Contesting Traffic Challan\n\n"
            "Respected Sir/Madam,\n\n"
            "I wish to contest the traffic challan issued to me. "
            "I believe the fine was wrongly imposed because [state reason]. "
            "I request a hearing to present my case.\n\n"
            "Challan Number: [your challan number]\n"
            "Date of Issue: [date]\n"
            "Vehicle Number: [your vehicle number]\n\n"
            "Thanking you."
        ),
    ),
    "accident": LegalResponse(
        scenario="accident",
        title="Road Accident",
        guidance=(
            "IMMEDIATE STEPS:\n\n"
            "1. Call 112 (Emergency) or 108 (Ambulance) immediately\n"
            "2. Do NOT move severely injured persons\n"
            "3. Take photos/videos of the accident scene\n"
            "4. Note the other vehicle's number plate\n"
            "5. File an FIR at the nearest police station within 24 hours\n"
            "6. Get a medical report from the hospital\n"
            "7. For insurance: Intimate your insurer within 24 hours\n\n"
            "If hit-and-run: File FIR with vehicle description, police will trace via CCTV"
        ),
        sections=[
            "BNS-106 (Causing death by negligence: Up to 5 years)",
            "BNS-125 (Rash act endangering life: Up to 6 months)",
            "BNS-281 (Rash driving on public way)",
            "Motor Vehicles Act Section 134 (Duty to report accident)",
        ],
        outcome="Compensation can be claimed via Motor Accident Claims Tribunal (MACT). "
                "Criminal charges depend on severity and negligence.",
        severity="high",
        helplines=["112 (Emergency)", "108 (Ambulance)", "1073 (Road Accident)"],
    ),

    # ── Domestic / Family ────────────────────────────────────────────────
    "domestic_violence": LegalResponse(
        scenario="domestic_violence",
        title="Domestic Violence",
        guidance=(
            "You are NOT alone. Help is available.\n\n"
            "IMMEDIATE STEPS:\n"
            "1. Call 1091 (Women Helpline) or 112 (Emergency)\n"
            "2. Go to the nearest police station — they MUST register your complaint\n"
            "3. Apply for a Protection Order under DV Act Section 18\n"
            "4. You can get: Residence order, monetary relief, custody of children\n"
            "5. Free legal aid available through NALSA (call 15100)\n\n"
            "IMPORTANT: You do NOT need to leave your home. "
            "The court can order the abuser to stay away."
        ),
        sections=[
            "Protection of Women from Domestic Violence Act 2005",
            "BNS-85 (Cruelty by husband/relatives: Up to 3 years)",
            "BNS-74 (Assault: Up to 3 months)",
        ],
        outcome="Protection order usually granted within 3 days. Abuser can be removed from home. "
                "Criminal case + civil remedies both available.",
        severity="critical",
        complaint_draft=(
            "To,\nThe Protection Officer / SHO\n[Nearest Police Station]\n\n"
            "Subject: Complaint of Domestic Violence\n\n"
            "Respected Sir/Madam,\n\n"
            "I, [your name], am facing domestic violence from [abuser's name and relationship]. "
            "The incidents include [describe: physical abuse / verbal abuse / economic abuse / "
            "threats]. This has been happening since [approximate date].\n\n"
            "I request:\n"
            "1. Immediate protection under the DV Act 2005\n"
            "2. Registration of FIR under relevant sections\n"
            "3. Protection order to prevent further violence\n\n"
            "I am attaching [medical reports / photos / any evidence] as proof.\n\n"
            "Date: [date]\nSignature: [your name]"
        ),
        helplines=["1091 (Women Helpline)", "181 (Women Helpline)", "112 (Emergency)", "15100 (NALSA Legal Aid)"],
    ),
    "dowry": LegalResponse(
        scenario="dowry",
        title="Dowry Harassment",
        guidance=(
            "Dowry demand is a CRIMINAL offence.\n\n"
            "What to do:\n"
            "1. Call 1091 (Women Helpline)\n"
            "2. File FIR under BNS Section 85 + Dowry Prohibition Act\n"
            "3. Preserve evidence: messages, recordings, witness statements\n"
            "4. Apply for protection order under DV Act\n"
            "5. Free legal aid: Call NALSA at 15100"
        ),
        sections=[
            "Dowry Prohibition Act 1961 (Penalty: Up to 5 years + fine)",
            "BNS-85 (Cruelty by husband: Up to 3 years)",
            "BNS-80 (Dowry death: 7 years to life imprisonment)",
        ],
        outcome="Arrest without warrant possible. Non-bailable in dowry death cases.",
        severity="critical",
        helplines=["1091 (Women Helpline)", "15100 (NALSA)"],
    ),
    "divorce": LegalResponse(
        scenario="divorce",
        title="Divorce / Separation",
        guidance=(
            "Types of divorce in India:\n\n"
            "1. Mutual Consent (Section 13B Hindu Marriage Act / Section 10A Special Marriage Act)\n"
            "   - Both parties agree, 6-month cooling period, fastest route\n"
            "2. Contested Divorce\n"
            "   - Grounds: cruelty, desertion (2+ years), adultery, mental disorder\n"
            "   - Takes 1-3 years typically\n\n"
            "Your rights:\n"
            "- Maintenance / alimony during and after proceedings\n"
            "- Child custody based on child's welfare\n"
            "- Right to matrimonial property\n"
            "- Free legal aid if needed (NALSA 15100)"
        ),
        sections=[
            "Hindu Marriage Act Section 13 (Grounds for divorce)",
            "BNS-85 (If cruelty involved)",
            "Hindu Adoption and Maintenance Act (Maintenance rights)",
        ],
        outcome="Mutual consent divorce: 6-18 months. Contested: 1-3 years. "
                "Maintenance is granted based on income disparity.",
        severity="medium",
    ),
    "child_custody": LegalResponse(
        scenario="child_custody",
        title="Child Custody",
        guidance=(
            "Child custody is decided based on the child's best interest.\n\n"
            "Key principles:\n"
            "1. Children under 5: Generally with the mother\n"
            "2. Older children: Court considers child's wishes\n"
            "3. Both parents have visitation rights\n"
            "4. File custody petition in Family Court\n"
            "5. Interim custody can be granted during proceedings"
        ),
        sections=[
            "Hindu Minority and Guardianship Act 1956",
            "Guardians and Wards Act 1890",
        ],
        outcome="Court prioritizes child welfare. Joint custody becoming more common.",
        severity="medium",
    ),

    # ── Criminal ─────────────────────────────────────────────────────────
    "theft": LegalResponse(
        scenario="theft",
        title="Theft / Robbery",
        guidance=(
            "What to do:\n\n"
            "1. File FIR at the nearest police station immediately\n"
            "2. If phone stolen: Block the IMEI — call 14422 or use ceir.gov.in\n"
            "3. Preserve CCTV footage, witness contacts\n"
            "4. For insurance claims, get a certified FIR copy\n"
            "5. Zero FIR: You can file at ANY police station, not just the local one"
        ),
        sections=[
            "BNS-303 (Theft: Up to 3 years + fine)",
            "BNS-309 (Robbery: Up to 10 years + fine)",
            "BNS-305 (Theft in dwelling house: Up to 7 years)",
        ],
        outcome="Police must register FIR. Investigation follows. Stolen property may be recovered.",
        severity="medium",
        complaint_draft=(
            "To,\nThe SHO\n[Police Station Name]\n\n"
            "Subject: FIR for Theft\n\n"
            "Respected Sir/Madam,\n\n"
            "I wish to report a theft. On [date] at approximately [time], "
            "at [location], my [describe items stolen] was/were stolen. "
            "[Describe circumstances — e.g., I was in a market when my phone was snatched].\n\n"
            "Estimated value of stolen property: Rs [amount]\n\n"
            "I request registration of FIR and investigation.\n\n"
            "Date: [date]\nSignature: [your name]\nContact: [phone number]"
        ),
    ),
    "assault": LegalResponse(
        scenario="assault",
        title="Assault / Physical Harm",
        guidance=(
            "IMMEDIATE STEPS:\n\n"
            "1. Get medical treatment first — go to a hospital\n"
            "2. Get a medico-legal certificate (MLC) from the hospital\n"
            "3. File FIR at the nearest police station\n"
            "4. Take photos of injuries\n"
            "5. Note witness details\n\n"
            "The hospital MUST treat you first, FIR formalities can follow."
        ),
        sections=[
            "BNS-115 (Voluntarily causing hurt: Up to 1 year + fine)",
            "BNS-117 (Grievous hurt: Up to 7 years + fine)",
            "BNS-74 (Criminal force / assault: Up to 3 months)",
        ],
        outcome="Assault is cognizable — police must register FIR. Compensation can be claimed.",
        severity="high",
        helplines=["112 (Emergency)", "108 (Ambulance)"],
    ),
    "cheating_fraud": LegalResponse(
        scenario="cheating_fraud",
        title="Cheating / Fraud / Scam",
        guidance=(
            "What to do:\n\n"
            "1. For online/UPI fraud: Call 1930 (Cyber Crime Helpline) IMMEDIATELY\n"
            "   — Faster you report, higher chance of recovery\n"
            "2. File complaint on cybercrime.gov.in\n"
            "3. File FIR at police station (or cyber cell)\n"
            "4. Block your cards/accounts if financial fraud\n"
            "5. Preserve all evidence: screenshots, messages, transaction IDs\n"
            "6. For bank fraud: Complain to bank + RBI Ombudsman"
        ),
        sections=[
            "BNS-318 (Cheating: Up to 3 years + fine)",
            "BNS-319 (Cheating and dishonestly inducing delivery: Up to 7 years)",
            "IT Act Section 66C (Identity theft: Up to 3 years)",
            "IT Act Section 66D (Cheating by personation using computer: Up to 3 years)",
        ],
        outcome="FIR is mandatory. For UPI fraud, banks must resolve within 10 days if reported within 3 days.",
        severity="high",
        complaint_draft=(
            "To,\nThe Cyber Cell / SHO\n[Police Station]\n\n"
            "Subject: Complaint of Online Fraud\n\n"
            "Respected Sir/Madam,\n\n"
            "I am a victim of online fraud. On [date], I was cheated of Rs [amount] "
            "through [method: UPI/bank transfer/fake website]. "
            "The transaction details are:\n"
            "- Transaction ID: [ID]\n"
            "- Amount: Rs [amount]\n"
            "- Platform: [UPI app / bank / website]\n"
            "- Suspect's details: [phone/UPI ID/account if known]\n\n"
            "I have already reported to [1930 helpline / bank]. "
            "I request immediate investigation and fund recovery.\n\n"
            "Attached: [Screenshots / transaction proof]\n\n"
            "Date: [date]\nSignature: [your name]"
        ),
        helplines=["1930 (Cyber Crime)", "cybercrime.gov.in"],
    ),
    "cyber_crime": LegalResponse(
        scenario="cyber_crime",
        title="Cyber Crime",
        guidance=(
            "What to do:\n\n"
            "1. Report on cybercrime.gov.in (National Cyber Crime Portal)\n"
            "2. Call 1930 (Cyber Crime Helpline)\n"
            "3. File FIR at the nearest police station or cyber cell\n"
            "4. Preserve all digital evidence — DO NOT delete anything\n"
            "5. Take screenshots with timestamps\n"
            "6. For morphed photos/harassment: Report to platform + police"
        ),
        sections=[
            "IT Act Section 66 (Computer-related offences: Up to 3 years)",
            "IT Act Section 66C (Identity theft)",
            "IT Act Section 67 (Publishing obscene material: Up to 5 years first offence)",
            "BNS-351 (Criminal intimidation)",
        ],
        outcome="Cyber crimes are investigated by cyber cells. Platform takedown can be ordered by court.",
        severity="high",
        helplines=["1930 (Cyber Crime)", "cybercrime.gov.in"],
    ),
    "defamation": LegalResponse(
        scenario="defamation",
        title="Defamation / False Accusations",
        guidance=(
            "Defamation can be both civil and criminal in India.\n\n"
            "What to do:\n"
            "1. Collect evidence: screenshots, recordings, witness statements\n"
            "2. Send a legal notice demanding retraction and apology\n"
            "3. File criminal complaint under BNS-356 at Magistrate court\n"
            "4. File civil suit for damages in District Court\n"
            "5. For online defamation: Report to platform + cyber cell"
        ),
        sections=[
            "BNS-356 (Defamation: Up to 2 years + fine)",
            "IT Act Section 66A (Struck down, but 67 may apply for online cases)",
        ],
        outcome="Criminal defamation is compoundable. Civil suit can award damages.",
        severity="medium",
    ),
    "murder_threat": LegalResponse(
        scenario="murder_threat",
        title="Death Threats",
        guidance=(
            "TAKE THIS SERIOUSLY.\n\n"
            "1. Call 112 (Emergency) if in immediate danger\n"
            "2. File FIR immediately — this is a cognizable offence\n"
            "3. Preserve evidence: messages, recordings, witnesses\n"
            "4. Request police protection if threats are ongoing\n"
            "5. Courts can order protection/restraining orders"
        ),
        sections=[
            "BNS-351 (Criminal intimidation: Up to 2 years)",
            "BNS-351(3) (Threat of death: Up to 7 years)",
        ],
        outcome="Non-bailable if threat to life. Police must provide protection.",
        severity="critical",
        helplines=["112 (Emergency)", "100 (Police)"],
    ),
    "kidnapping": LegalResponse(
        scenario="kidnapping",
        title="Kidnapping / Missing Person",
        guidance=(
            "IMMEDIATE STEPS:\n\n"
            "1. Call 112 (Emergency) immediately\n"
            "2. File FIR — police MUST register it for missing person\n"
            "3. File missing person report on Track Child Portal (for children)\n"
            "4. Share recent photos with police\n"
            "5. No need to wait 24 hours — this is a myth\n\n"
            "Police is REQUIRED to act immediately for missing children."
        ),
        sections=[
            "BNS-137 (Kidnapping: Up to 7 years + fine)",
            "BNS-140 (Kidnapping for ransom: Up to death penalty)",
        ],
        outcome="Police must launch search immediately. Cognizable and non-bailable offence.",
        severity="critical",
        helplines=["112 (Emergency)", "1098 (Childline)", "100 (Police)"],
    ),
    "sexual_harassment": LegalResponse(
        scenario="sexual_harassment",
        title="Sexual Harassment",
        guidance=(
            "What to do:\n\n"
            "At workplace:\n"
            "1. Complain to Internal Complaints Committee (ICC) — every company with 10+ employees MUST have one\n"
            "2. Complaint must be filed within 3 months of incident\n"
            "3. ICC must complete inquiry within 90 days\n\n"
            "Outside workplace:\n"
            "1. File FIR at police station\n"
            "2. Call 1091 (Women Helpline)\n"
            "3. File complaint on SHe-box portal (shebox.nic.in)"
        ),
        sections=[
            "POSH Act 2013 (Sexual Harassment of Women at Workplace)",
            "BNS-75 (Sexual harassment: Up to 3 years + fine)",
            "BNS-78 (Stalking: Up to 3 years first offence)",
        ],
        outcome="ICC must act within 90 days. Criminal case is cognizable. "
                "Employer liable if no ICC constituted.",
        severity="critical",
        helplines=["1091 (Women Helpline)", "181 (Women Helpline)", "shebox.nic.in"],
    ),
    "rape": LegalResponse(
        scenario="rape",
        title="Sexual Assault",
        guidance=(
            "IMMEDIATE HELP AVAILABLE.\n\n"
            "1. Call 112 (Emergency) or 1091 (Women Helpline)\n"
            "2. Go to the nearest hospital — treatment is FREE and MANDATORY\n"
            "3. Medical exam must be done by a FEMALE doctor\n"
            "4. FIR MUST be registered — police cannot refuse\n"
            "5. Statement can be recorded at home or hospital\n"
            "6. Free legal aid is your RIGHT — call NALSA 15100\n"
            "7. Your identity will be kept confidential by law"
        ),
        sections=[
            "BNS-63 (Rape: 10 years to life imprisonment)",
            "BNS-64 (Gang rape: 20 years to life)",
            "BNS-65 (Repeat offender: Life or death)",
        ],
        outcome="Non-bailable, cognizable offence. Trial in fast-track court. "
                "Victim identity protected under law.",
        severity="critical",
        helplines=["112 (Emergency)", "1091 (Women Helpline)", "15100 (NALSA)", "181 (Women Helpline)"],
    ),

    # ── Property / Civil ─────────────────────────────────────────────────
    "property_dispute": LegalResponse(
        scenario="property_dispute",
        title="Property Dispute",
        guidance=(
            "What to do:\n\n"
            "1. Verify ownership documents (sale deed, mutation records)\n"
            "2. Check land records on your state's Bhulekh portal\n"
            "3. For encroachment: File police complaint + civil suit\n"
            "4. Send legal notice to the other party\n"
            "5. File civil suit in District Court for possession/declaration\n"
            "6. Mediation is recommended before litigation"
        ),
        sections=[
            "Transfer of Property Act 1882",
            "BNS-329 (Criminal breach of trust: Up to 7 years)",
            "Specific Relief Act (Recovery of possession)",
        ],
        outcome="Civil suits take 2-5 years. Interim injunctions can protect possession.",
        severity="medium",
    ),
    "tenant_landlord": LegalResponse(
        scenario="tenant_landlord",
        title="Tenant-Landlord Dispute",
        guidance=(
            "Key rights:\n\n"
            "Tenant rights:\n"
            "- Cannot be evicted without court order\n"
            "- Security deposit must be returned (minus damages)\n"
            "- Rent cannot be increased arbitrarily\n\n"
            "Landlord rights:\n"
            "- Can seek eviction for non-payment (after notice)\n"
            "- Can seek eviction for personal use\n"
            "- Entitled to fair market rent\n\n"
            "Both: File case in Rent Control Court"
        ),
        sections=[
            "State Rent Control Act (varies by state)",
            "Transfer of Property Act Section 106 (Notice period)",
        ],
        outcome="Eviction requires court order. Rent disputes resolved by Rent Controller.",
        severity="low",
    ),
    "inheritance": LegalResponse(
        scenario="inheritance",
        title="Inheritance / Succession",
        guidance=(
            "Inheritance law depends on religion:\n\n"
            "Hindu/Sikh/Jain/Buddhist:\n"
            "- Hindu Succession Act 1956 (amended 2005)\n"
            "- Daughters have EQUAL right to ancestral property\n"
            "- Will overrides succession law for self-acquired property\n\n"
            "Muslim:\n"
            "- Muslim Personal Law (Shariat)\n"
            "- Will can only cover 1/3 of property\n\n"
            "File succession certificate petition in District Court"
        ),
        sections=[
            "Hindu Succession Act 1956",
            "Indian Succession Act 1925",
        ],
        outcome="Legal heirs get equal share by default. Will can modify distribution of self-acquired property.",
        severity="medium",
    ),

    # ── Consumer / Employment ────────────────────────────────────────────
    "consumer_complaint": LegalResponse(
        scenario="consumer_complaint",
        title="Consumer Complaint",
        guidance=(
            "What to do:\n\n"
            "1. First: Send written complaint to the company/seller\n"
            "2. If no response in 15 days: File on consumerhelpline.gov.in\n"
            "3. Call 1800-11-4000 (National Consumer Helpline)\n"
            "4. File case on edaakhil.nic.in (e-filing for consumer courts)\n\n"
            "Where to file:\n"
            "- Up to Rs 1 crore: District Commission\n"
            "- Rs 1-10 crore: State Commission\n"
            "- Above Rs 10 crore: National Commission"
        ),
        sections=[
            "Consumer Protection Act 2019",
            "Section 35 (Product liability)",
        ],
        outcome="Consumer courts are faster than civil courts. Compensation + refund + damages can be awarded.",
        severity="low",
        complaint_draft=(
            "To,\nThe President\nDistrict Consumer Disputes Redressal Commission\n[District, State]\n\n"
            "Subject: Consumer Complaint\n\n"
            "Complainant: [Your name and address]\n"
            "Opposite Party: [Company/seller name and address]\n\n"
            "Facts:\n"
            "1. I purchased [product/service] on [date] for Rs [amount]\n"
            "2. The [product/service] was [defective/not as described/overcharged]\n"
            "3. I complained to the seller on [date] but received no resolution\n\n"
            "Relief Sought:\n"
            "1. Replacement / Refund of Rs [amount]\n"
            "2. Compensation for mental agony: Rs [amount]\n"
            "3. Cost of litigation\n\n"
            "Attached: [Receipt, photos, complaint copies]\n\n"
            "Date: [date]\nSignature: [your name]"
        ),
        helplines=["1800-11-4000 (Consumer Helpline)"],
    ),
    "employment_issue": LegalResponse(
        scenario="employment_issue",
        title="Employment / Salary Issue",
        guidance=(
            "What to do:\n\n"
            "1. Send written notice to employer demanding unpaid wages\n"
            "2. File complaint with Labour Commissioner\n"
            "3. For PF issues: File on epfigms.gov.in\n"
            "4. For unfair termination: Challenge within 3 months\n"
            "5. Labour courts handle disputes for workers\n"
            "6. Industrial Tribunal for establishment-level disputes"
        ),
        sections=[
            "Payment of Wages Act 1936",
            "Industrial Disputes Act 1947",
            "EPF Act 1952 (Provident Fund)",
        ],
        outcome="Labour Commissioner can order payment. Unfair termination can lead to reinstatement + back wages.",
        severity="medium",
    ),
    "rti": LegalResponse(
        scenario="rti",
        title="Right to Information (RTI)",
        guidance=(
            "How to file RTI:\n\n"
            "1. Online: rtionline.gov.in (for central government)\n"
            "2. Offline: Write on plain paper to the PIO of the department\n"
            "3. Fee: Rs 10 (online) or postal order\n"
            "4. Response deadline: 30 days (48 hours for life/liberty matters)\n"
            "5. If no response: Appeal to First Appellate Authority\n"
            "6. If still no response: Appeal to Information Commission"
        ),
        sections=["Right to Information Act 2005"],
        outcome="Government must respond within 30 days or face penalty. "
                "Rs 250/day fine on PIO for delay.",
        severity="low",
    ),

    # ── Procedures ───────────────────────────────────────────────────────
    "file_fir": LegalResponse(
        scenario="file_fir",
        title="How to File an FIR",
        guidance=(
            "Step-by-step FIR filing:\n\n"
            "1. Go to the nearest police station (any station for Zero FIR)\n"
            "2. Narrate your complaint to the duty officer\n"
            "3. The officer MUST register the FIR — refusal is a punishable offence\n"
            "4. Get a FREE copy of the FIR — this is your right\n"
            "5. Note the FIR number for future reference\n\n"
            "If police refuses:\n"
            "- Send complaint by registered post to SP/SSP\n"
            "- File complaint with Judicial Magistrate under BNSS Section 175\n"
            "- Call 100 and report the refusal"
        ),
        sections=[
            "BNSS Section 173 (Information in cognizable cases — FIR)",
            "BNSS Section 175 (Magistrate can order FIR registration)",
        ],
        outcome="FIR is a legal right. Police must register and investigate.",
        severity="low",
    ),
    "bail": LegalResponse(
        scenario="bail",
        title="Bail Process",
        guidance=(
            "Types of bail:\n\n"
            "1. Regular Bail: Apply to Sessions Court / High Court\n"
            "2. Anticipatory Bail: Apply BEFORE arrest (High Court / Sessions Court)\n"
            "3. Default Bail: If chargesheet not filed within 60/90 days\n\n"
            "For bailable offences:\n"
            "- Bail is a RIGHT — police station itself can grant it\n\n"
            "For non-bailable offences:\n"
            "- Apply to court with surety\n"
            "- Factors: nature of offence, criminal history, flight risk\n\n"
            "Free legal aid available through NALSA (15100)"
        ),
        sections=[
            "BNSS Section 478 (Bail in bailable offences)",
            "BNSS Section 480 (Bail in non-bailable offences)",
            "BNSS Section 482 (Anticipatory bail)",
        ],
        outcome="Bailable: Bail as a matter of right. Non-bailable: Court's discretion based on merits.",
        severity="medium",
    ),
    "legal_aid": LegalResponse(
        scenario="legal_aid",
        title="Free Legal Aid",
        guidance=(
            "FREE legal aid is available to:\n\n"
            "1. Women and children\n"
            "2. SC/ST community members\n"
            "3. Industrial workers\n"
            "4. Persons with disability\n"
            "5. Anyone earning less than Rs 3 lakh/year\n"
            "6. Victims of trafficking, disaster, or ethnic violence\n\n"
            "How to get it:\n"
            "- Call NALSA: 15100\n"
            "- Visit District Legal Services Authority\n"
            "- Apply online: nalsa.gov.in"
        ),
        sections=[
            "Legal Services Authorities Act 1987",
            "Article 39A of the Constitution (Equal justice and free legal aid)",
        ],
        outcome="Eligible persons get free lawyer, court fees waived. Services through NALSA/DLSA.",
        severity="low",
        helplines=["15100 (NALSA)", "nalsa.gov.in"],
    ),
    "fundamental_rights": LegalResponse(
        scenario="fundamental_rights",
        title="Fundamental Rights",
        guidance=(
            "Your Fundamental Rights (Part III of Constitution):\n\n"
            "1. Article 14: Right to Equality\n"
            "2. Article 19: Right to Freedom (speech, assembly, movement, profession)\n"
            "3. Article 21: Right to Life and Personal Liberty\n"
            "4. Article 25: Freedom of Religion\n"
            "5. Article 32: Right to Constitutional Remedies (approach Supreme Court)\n\n"
            "If violated:\n"
            "- File writ petition in High Court (Article 226) or Supreme Court (Article 32)\n"
            "- Types: Habeas Corpus, Mandamus, Certiorari, Prohibition, Quo Warranto"
        ),
        sections=[
            "Constitution of India, Part III (Articles 12-35)",
            "Article 32 (Right to Constitutional Remedies)",
        ],
        outcome="Fundamental rights are enforceable. Court can issue writs for immediate relief.",
        severity="low",
    ),
    "noise_complaint": LegalResponse(
        scenario="noise_complaint",
        title="Noise Complaint",
        guidance=(
            "What to do:\n\n"
            "1. Complain to local police (call 100)\n"
            "2. Noise limits: 75dB day / 70dB night in commercial; 55dB day / 45dB night in residential\n"
            "3. Loudspeakers banned between 10 PM - 6 AM\n"
            "4. File complaint with local pollution control board\n"
            "5. Repeated offence: Fine up to Rs 1 lakh"
        ),
        sections=[
            "Noise Pollution (Regulation and Control) Rules 2000",
            "Environment Protection Act 1986",
            "BNS-290 (Public nuisance)",
        ],
        outcome="Police can seize loudspeakers. Fine imposed on violators.",
        severity="low",
    ),
}


# ── Public API ───────────────────────────────────────────────────────────────

def get_response(scenario: str) -> LegalResponse | None:
    """Get the curated response for a classified scenario."""
    return SCENARIOS.get(scenario)


def get_all_scenarios() -> list[dict]:
    """Return summary of all known scenarios (for frontend display)."""
    return [
        {"id": s.scenario, "title": s.title, "severity": s.severity}
        for s in SCENARIOS.values()
    ]
