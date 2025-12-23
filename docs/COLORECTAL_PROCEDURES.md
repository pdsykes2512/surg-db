# Colorectal Surgery OPCS-4 Procedure Reference

This document maps the standardized procedure names to their OPCS-4 codes and provides clinical context.

## Major Resection Procedures

### Right-Sided Resections

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Right hemicolectomy | H07.9 | Excision of caecum and ascending colon | Used for tumours in caecum, ascending colon, or hepatic flexure |
| Extended right hemicolectomy | H06.9 | Right hemicolectomy extended to include transverse colon | For tumours at hepatic flexure or proximal transverse colon |
| Transverse colectomy | H08.9 | Excision of transverse colon | For mid-transverse colon tumours |

### Left-Sided Resections

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Left hemicolectomy | H09.9 | Excision of descending colon | For splenic flexure or descending colon tumours |
| Sigmoid colectomy | H10.9 | Excision of sigmoid colon | For sigmoid colon tumours |

### Rectal Resections

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Anterior resection | H33.4 | Anterior resection of rectum with anastomosis | For upper/mid rectal tumours, sphincter-preserving |
| Abdominoperineal excision of rectum (APER) | H33.1 | Excision of rectum and anus with permanent colostomy | For low rectal tumours, sphincter-sacrificing |
| Hartmann's procedure | H33.5 | Anterior resection with end colostomy | Emergency/staged procedure, no anastomosis |

### Extended Resections

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Subtotal colectomy | H04.2 | Excision of most of colon | For synchronous tumours or familial polyposis |
| Total colectomy | H04.1 | Excision of entire colon | For colonic polyposis or severe colitis |
| Panproctocolectomy | H05.1 | Excision of entire colon and rectum | For extensive disease |

## Stoma Procedures

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Stoma formation | H09.9 (various) | Creation of ileostomy or colostomy | Protective, defunctioning, or permanent |
| Reversal of stoma | H20.1 | Closure of stoma | After healing of anastomosis |

## Limited Procedures

| Procedure | OPCS-4 Code | Description | Clinical Context |
|-----------|-------------|-------------|------------------|
| Polypectomy | H23.9 | Endoscopic removal of polyp | Malignant polyps with incomplete excision |
| Local excision | H24.3 | Trans-anal or laparoscopic local excision | T1 rectal tumours, selected cases |
| Colonic stent insertion | G74.9 | Endoscopic stent placement | Palliation of obstruction |

## Anatomical Context

### Anterior Resection Types
- **High AR**: Anastomosis >12cm from anal verge, above peritoneal reflection
- **Low AR**: Anastomosis <12cm from anal verge, below peritoneal reflection, often with total mesorectal excision (TME)

### Stoma Types
- **Temporary ileostomy**: Protective stoma, typically reversed at 8-12 weeks
- **Permanent ileostomy**: With proctectomy (APER, panproctocolectomy)
- **Temporary colostomy**: Loop colostomy for obstruction/perforation
- **Permanent colostomy**: End colostomy with APER or Hartmann's

## Surgical Approaches

| Approach | Description | Advantages | Disadvantages |
|----------|-------------|-----------|---------------|
| Open | Traditional laparotomy | Better access, familiar | Larger incision, longer recovery |
| Laparoscopic | Minimally invasive ports | Less pain, faster recovery | Longer operative time, learning curve |
| Laparoscopic converted | Started laparoscopic, converted to open | Safety first approach | Combined morbidity |
| Robotic | Da Vinci robotic system | 3D vision, articulated instruments | Cost, longer operative time |

## ASA Physical Status Classification

| ASA | Description | Example |
|-----|-------------|---------|
| 1 | Normal healthy patient | No systemic disease |
| 2 | Mild systemic disease | Well-controlled hypertension, diabetes |
| 3 | Severe systemic disease | Poorly controlled diabetes, COPD |
| 4 | Severe systemic disease that is a constant threat to life | Recent MI, severe cardiac failure |
| 5 | Moribund patient not expected to survive without operation | Ruptured AAA, massive trauma |

## Surgical Intent

| Intent | Description | Clinical Context |
|--------|-------------|------------------|
| Curative | Aim to remove all cancer | R0 resection expected, no distant metastases |
| Palliative | Symptom control, not curative | Distant metastases, local obstruction/bleeding |
| Uncertain | Intent not clearly defined | Unexpected findings at operation |

## Data Sources and Migration Notes

**Source**: Legacy Microsoft Access database exported to `surgeries_export_new.csv`

**Cleaning performed**:
1. Removed numeric prefixes from procedure names (e.g., "1 Right hemicolectomy" → "Right hemicolectomy")
2. Standardized ASA scores from Roman numerals to numbers (II → 2)
3. Mapped to consistent surgical intent, approach, and stoma type values
4. Added colorectal-specific fields: stoma information, anastomosis details, surgical team
5. Flattened nested surgery subdocuments to top-level fields

**Data quality notes**:
- ~400 treatments (5%) successfully matched and enriched with detailed CSV data
- Procedure names now align with OPCS-4 descriptions
- Some legacy ASA scores (7, 99) indicate data quality issues in source database
- OPCS-4 codes are standardized and validated

**Database statistics** (as of 2025-12-23):
- Total surgery treatments: 7,957
- Procedures with OPCS-4 codes: 6,143 (77%)
- Treatments with colorectal-specific data: 400
- Top procedures: Anterior resection (28%), Right hemicolectomy (21%), Extended right hemicolectomy (5%)
