# Chikungunya Virus Disease — Surveillance Case Definitions

Reference for the case definitions used to classify cases in this project.
Machine-readable form: [`config/case_definitions.yaml`](../config/case_definitions.yaml).

_Last reviewed: 2026-06-03._

> The CDC criteria below are quoted from the live NNDSS case-definition page.
> The WHO/PAHO tiers are the long-standing standardized surveillance
> definitions; confirm exact wording against the linked WHO/PAHO documents.

---

## WHO / PAHO (standardized surveillance definition)

Used in outbreak surveillance (incl. the Americas). Three tiers:

| Tier | Criteria |
|------|----------|
| **Suspected** | Acute onset of **fever** **and** **severe arthralgia/arthritis** not explained by another condition, in a person **living in or having visited an area with transmission within ~15 days** before onset. |
| **Probable** | A suspected case **with a positive CHIKV IgM** (single acute serum) pending confirmation; **or**, during a declared outbreak, a suspected case **epidemiologically linked** to a confirmed case. |
| **Confirmed** | A suspected case with **≥1** positive lab test: **RT‑PCR** viral RNA; **virus isolation**; **IgM seroconversion**; or a **≥4‑fold rise** in CHIKV‑specific (neutralizing/IgG) antibodies in paired sera. |

---

## CDC / CSTE (United States, NNDSS)

Chikungunya is nationally notifiable (since 2015) under the **Arboviral Diseases,
Non‑neuroinvasive — 2015 case definition**. There is **no "suspected" tier**.

**Clinical criteria:** acute onset of **fever** plus (for chikungunya)
**polyarthralgia/arthritis**, with no more‑likely alternative diagnosis.

| Tier | Laboratory requirement |
|------|------------------------|
| **Probable** | Presumptive: **CHIKV IgM in serum with no other (confirmatory) testing**. |
| **Confirmed** | Confirmatory: virus isolation or antigen/**nucleic acid (RT‑PCR)**; **or** a **≥4‑fold change** in virus‑specific antibody titers in paired sera; **or** **IgM in serum *with* confirmatory neutralizing (PRNT) antibodies**. |

**Testing/timing guidance:** RT‑PCR in the **first ~week** (viraemia, ~0–8 days);
**serology after week 1**; a **positive IgM must be confirmed by neutralizing
antibody (PRNT)** because of cross‑reactivity with other alphaviruses
(e.g., Mayaro, o'nyong‑nyong) and false positives.

**Key difference vs WHO/PAHO:** WHO/PAHO formalize a clinical **Suspected** tier
(and allow epi‑linked Probable cases in outbreaks); CDC/NNDSS starts at Probable
and requires laboratory evidence.

---

## Applying this to the dataset

Derivation rules (see `dataset_mapping` in the YAML) for a `case_classification`
field over `chikungunya_analysis`:

| Signal (column) | Contributes to |
|-----------------|----------------|
| `pcr_result = Positive` | **Confirmed** (RT‑PCR) |
| `epi_linkage` populated + clinical | **Probable** (epi‑linked, outbreak) |
| `symptoms` includes fever + arthralgia | **Suspected** (clinical criterion) |
| `date_of_onset_symptoms` | ~15‑day exposure window; RT‑PCR‑vs‑serology timing |
| `past_history_of_chikungunya` | interpreting IgM/serology |

Default scheme: **who_paho** (configurable in the YAML). First matching rule wins:
`pcr_positive → Confirmed`, else `clinical + epi link → Probable`, else
`clinical → Suspected`, else `Unclassified`.

---

## Sources

- [CDC NNDSS — Arboviral Diseases (Neuroinvasive & Non‑neuroinvasive), 2015 Case Definition](https://ndc.services.cdc.gov/case-definitions/arboviral-diseases-neuroinvasive-and-non-neuroinvasive-2015/)
- [CDC NNDSS — Chikungunya Virus Disease (conditions page)](https://ndc.services.cdc.gov/conditions/chikungunya-virus-disease/)
- [CDC — Clinical Testing and Diagnosis for Chikungunya](https://www.cdc.gov/chikungunya/hcp/diagnosis-testing/index.html)
- [CDC Yellow Book — Chikungunya](https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/chikungunya.html)
- [WHO — Chikungunya Global Rapid Risk Assessment (2026, PDF)](https://cdn.who.int/media/docs/default-source/_sage-2026/who-rapid-risk-assessment_chikungunya-virus_global_v1.pdf)
- [PAHO — Epidemiological Alert: Chikungunya & Oropouche (Aug 2025, PDF)](https://www.paho.org/sites/default/files/2025-09/2025-ago-28-phe-alerta-chkvorovengfinal.pdf)
- [WHO — Chikungunya virus disease, Global situation (DON581)](https://www.who.int/emergencies/disease-outbreak-news/item/2025-DON581)
