from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import xml.etree.ElementTree as ET
from xml.dom import minidom

from ..database import get_database
from ..models.user import User
from ..auth import get_current_user, require_admin
from ..utils.encryption import decrypt_document

router = APIRouter(prefix="/api/admin/exports", tags=["Admin - Exports"])


def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def format_date(date_value) -> str:
    """Format datetime/date to YYYY-MM-DD for COSD."""
    if not date_value:
        return ""
    if isinstance(date_value, str):
        # Try to parse if it's already a string
        try:
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return date_value
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')
    return str(date_value)


def create_patient_xml(patient: dict, episode: dict) -> ET.Element:
    """Create COSD XML patient record."""
    patient_elem = ET.Element("Patient")
    
    # NHS Number (CR0010) - MANDATORY
    if patient.get("nhs_number"):
        nhs = ET.SubElement(patient_elem, "NHSNumber")
        nhs.text = str(patient["nhs_number"])
    
    # Demographics
    demographics = patient.get("demographics", {})
    
    # Date of Birth (CR0100) - MANDATORY
    if demographics.get("date_of_birth"):
        dob = ET.SubElement(patient_elem, "PersonBirthDate")
        dob.text = format_date(demographics["date_of_birth"])
    
    # Gender (CR3170) - MANDATORY
    if demographics.get("gender"):
        gender = ET.SubElement(patient_elem, "PersonStatedGenderCode")
        gender_map = {"male": "1", "female": "2", "other": "9"}
        gender.text = gender_map.get(demographics["gender"].lower(), "9")
    
    # Ethnicity (CR0150) - MANDATORY
    if demographics.get("ethnicity"):
        ethnicity = ET.SubElement(patient_elem, "EthnicCategory")
        ethnicity.text = demographics["ethnicity"]

    # Postcode (CR0080) - MANDATORY
    if demographics.get("postcode"):
        postcode = ET.SubElement(patient_elem, "PostcodeOfUsualAddress")
        postcode.text = demographics["postcode"]
    
    return patient_elem


def create_episode_xml(episode: dict, patient: dict, treatments: list, tumours: list = None) -> ET.Element:
    """Create COSD XML cancer episode record."""
    record = ET.Element("CancerRecord")
    
    # Add patient demographics
    record.append(create_patient_xml(patient, episode))
    
    # Episode details
    episode_elem = ET.SubElement(record, "Episode")
    
    # Episode ID (local identifier)
    ep_id = ET.SubElement(episode_elem, "LocalPatientIdentifier")
    ep_id.text = str(episode.get("_id", ""))
    
    # Provider first seen (CR1410)
    if episode.get("provider_first_seen"):
        provider = ET.SubElement(episode_elem, "ProviderFirstSeen")
        provider.text = episode["provider_first_seen"]
    
    # Referral source (CR1600)
    if episode.get("referral_source"):
        ref_source = ET.SubElement(episode_elem, "SourceOfReferral")
        ref_source.text = episode["referral_source"]
    
    # CNS involved (CR2050)
    if episode.get("cns_involved") is not None:
        cns = ET.SubElement(episode_elem, "CNSIndicationCode")
        cns.text = "01" if episode["cns_involved"] else "02"
    
    # MDT meeting type (CR3190)
    if episode.get("mdt_meeting_type"):
        mdt = ET.SubElement(episode_elem, "MDTMeetingType")
        mdt.text = episode["mdt_meeting_type"]
    
    # Performance status (CR0510)
    if episode.get("performance_status"):
        perf = ET.SubElement(episode_elem, "PerformanceStatusAdult")
        perf_status = episode["performance_status"]
        # Handle both dict format (with ecog_score) and string format
        if isinstance(perf_status, dict):
            perf.text = str(perf_status.get("ecog_score", ""))
        else:
            perf.text = str(perf_status)
    
    # Diagnosis details for bowel cancer
    # Get tumour data from tumours collection
    if episode.get("cancer_type") == "bowel" and tumours:
        # Use the first (primary) tumour for NBOCA export
        tumour = tumours[0]
        
        diagnosis_elem = ET.SubElement(episode_elem, "Diagnosis")
        
        # Diagnosis date (CR2030) - MANDATORY
        if tumour.get("diagnosis_date"):
            diag_date = ET.SubElement(diagnosis_elem, "PrimaryDiagnosisDate")
            diag_date.text = format_date(tumour["diagnosis_date"])
        
        # ICD-10 code (CR0370) - MANDATORY for NBOCA
        if tumour.get("icd10_code"):
            icd = ET.SubElement(diagnosis_elem, "PrimaryDiagnosisICD")
            icd.text = tumour["icd10_code"]
        
        # SNOMED morphology code (CR6400)
        if tumour.get("snomed_morphology_code"):
            snomed = ET.SubElement(diagnosis_elem, "MorphologySNOMED")
            snomed.text = tumour["snomed_morphology_code"]
        
        # Histology type
        if tumour.get("histology_type"):
            histology = ET.SubElement(diagnosis_elem, "HistologyType")
            histology.text = tumour["histology_type"]
        
        # Tumour site (CR0490)
        if tumour.get("site"):
            site = ET.SubElement(diagnosis_elem, "TumourSite")
            site.text = tumour["site"]
        
        # TNM Staging
        tnm_elem = ET.SubElement(diagnosis_elem, "TNMStaging")
        
        # TNM version (CR2070)
        if tumour.get("tnm_version"):
            version = ET.SubElement(tnm_elem, "TNMVersionNumber")
            version.text = str(tumour["tnm_version"])
        
        # Clinical staging date
        if tumour.get("clinical_stage_date"):
            clin_date = ET.SubElement(tnm_elem, "ClinicalStagingDate")
            clin_date.text = format_date(tumour["clinical_stage_date"])
        
        # Clinical T (CR0520)
        if tumour.get("clinical_t"):
            t_cat = ET.SubElement(tnm_elem, "TCategoryFinalPretreatment")
            t_cat.text = tumour["clinical_t"]
        
        # Clinical N (CR0540)
        if tumour.get("clinical_n"):
            n_cat = ET.SubElement(tnm_elem, "NCategoryFinalPretreatment")
            n_cat.text = tumour["clinical_n"]
        
        # Clinical M (CR0560)
        if tumour.get("clinical_m"):
            m_cat = ET.SubElement(tnm_elem, "MCategoryFinalPretreatment")
            m_cat.text = tumour["clinical_m"]
        
        # Pathological staging date
        if tumour.get("pathological_stage_date"):
            path_date = ET.SubElement(tnm_elem, "PathologicalStagingDate")
            path_date.text = format_date(tumour["pathological_stage_date"])
        
        # Pathological T (pCR6820)
        if tumour.get("pathological_t"):
            path_t = ET.SubElement(tnm_elem, "TCategoryPathological")
            path_t.text = tumour["pathological_t"]
        
        # Pathological N (pCR0910)
        if tumour.get("pathological_n"):
            path_n = ET.SubElement(tnm_elem, "NCategoryPathological")
            path_n.text = tumour["pathological_n"]
        
        # Pathological M (pCR0920)
        if tumour.get("pathological_m"):
            path_m = ET.SubElement(tnm_elem, "MCategoryPathological")
            path_m.text = tumour["pathological_m"]
        
        # Pathology details
        pathology_elem = ET.SubElement(diagnosis_elem, "Pathology")
        
        # Differentiation/Grade (pCR0930)
        if tumour.get("grade"):
            grade = ET.SubElement(pathology_elem, "DifferentiationGrade")
            grade.text = tumour["grade"]
        
        # Lymph nodes examined (pCR0890)
        if tumour.get("lymph_nodes_examined") is not None:
            nodes_exam = ET.SubElement(pathology_elem, "NumberOfNodesExamined")
            nodes_exam.text = str(tumour["lymph_nodes_examined"])
        
        # Lymph nodes positive (pCR0900)
        if tumour.get("lymph_nodes_positive") is not None:
            nodes_pos = ET.SubElement(pathology_elem, "NumberOfNodesPositive")
            nodes_pos.text = str(tumour["lymph_nodes_positive"])
        
        # CRM status (pCR1150) - CRITICAL for rectal cancer
        if tumour.get("crm_status"):
            crm = ET.SubElement(pathology_elem, "CircumferentialResectionMargin")
            crm.text = tumour["crm_status"]
        
        # CRM distance
        if tumour.get("crm_distance_mm") is not None:
            crm_dist = ET.SubElement(pathology_elem, "CRMDistanceMM")
            crm_dist.text = str(tumour["crm_distance_mm"])
        
        # Proximal margin
        if tumour.get("proximal_margin_mm") is not None:
            prox = ET.SubElement(pathology_elem, "ProximalMarginMM")
            prox.text = str(tumour["proximal_margin_mm"])
        
        # Distal margin
        if tumour.get("distal_margin_mm") is not None:
            dist = ET.SubElement(pathology_elem, "DistalMarginMM")
            dist.text = str(tumour["distal_margin_mm"])
        
        # Lymphovascular invasion
        if tumour.get("lymphovascular_invasion") is not None:
            lvi = ET.SubElement(pathology_elem, "LymphovascularInvasion")
            lvi.text = "Yes" if tumour["lymphovascular_invasion"] else "No"
        
        # Perineural invasion
        if tumour.get("perineural_invasion") is not None:
            pni = ET.SubElement(pathology_elem, "PerineuralInvasion")
            pni.text = "Yes" if tumour["perineural_invasion"] else "No"
        
        # Molecular markers
        if tumour.get("kras_status"):
            kras = ET.SubElement(pathology_elem, "KRASStatus")
            kras.text = tumour["kras_status"]
        
        if tumour.get("braf_status"):
            braf = ET.SubElement(pathology_elem, "BRAFStatus")
            braf.text = tumour["braf_status"]
        
        if tumour.get("mismatch_repair_status"):
            mmr = ET.SubElement(pathology_elem, "MismatchRepairStatus")
            mmr.text = tumour["mismatch_repair_status"]
    
    # Treatment details
    if treatments:
        treatments_elem = ET.SubElement(episode_elem, "Treatments")
        
        for treatment in treatments:
            treatment_elem = ET.SubElement(treatments_elem, "Treatment")
            
            # Treatment type
            t_type = ET.SubElement(treatment_elem, "TreatmentType")
            t_type.text = treatment.get("treatment_type", "").upper()
            
            # Treatment date (CR0710 for surgery)
            if treatment.get("treatment_date"):
                t_date = ET.SubElement(treatment_elem, "TreatmentDate")
                t_date.text = format_date(treatment["treatment_date"])
            
            # Treatment intent (CR0680)
            if treatment.get("treatment_intent"):
                intent = ET.SubElement(treatment_elem, "TreatmentIntent")
                intent.text = treatment["treatment_intent"]
            
            # Provider organisation (CR1450)
            if treatment.get("provider_organisation"):
                provider_org = ET.SubElement(treatment_elem, "ProviderOrganisation")
                provider_org.text = treatment["provider_organisation"]
            
            # Surgery-specific fields (includes all surgery types: primary, RTT, reversal)
            if treatment.get("treatment_type") in ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]:
                surgery_elem = ET.SubElement(treatment_elem, "Surgery")
                
                # OPCS-4 procedure code (CR0720) - MANDATORY for surgical patients
                if treatment.get("opcs4_code"):
                    opcs = ET.SubElement(surgery_elem, "PrimaryProcedureOPCS")
                    opcs.text = treatment["opcs4_code"]
                
                # ASA score (CR6010) - MANDATORY for surgical patients
                if treatment.get("asa_score"):
                    asa = ET.SubElement(surgery_elem, "ASAScore")
                    asa.text = str(treatment["asa_score"])
                
                # Surgical approach (CR6310)
                classification = treatment.get("classification", {})
                if classification.get("approach"):
                    approach = ET.SubElement(surgery_elem, "SurgicalAccessType")
                    approach_map = {
                        "open": "01",
                        "laparoscopic": "02",
                        "laparoscopic_converted": "03",
                        "robotic": "04"
                    }
                    approach.text = approach_map.get(classification["approach"], "99")

                # Urgency (CO6000)
                if classification.get("urgency"):
                    urgency = ET.SubElement(surgery_elem, "SurgicalUrgencyType")
                    urgency_map = {
                        "elective": "01",
                        "urgent": "02",
                        "emergency": "03"
                    }
                    urgency.text = urgency_map.get(classification["urgency"], "99")
                
                # CRM status (pCR1150) - for resections
                if treatment.get("circumferential_resection_margin") is not None:
                    crm = ET.SubElement(surgery_elem, "CircumferentialResectionMargin")
                    crm.text = "R0" if treatment["circumferential_resection_margin"] else "R1"
            
            # Chemotherapy-specific fields
            elif treatment.get("treatment_type") == "chemotherapy":
                chemo_elem = ET.SubElement(treatment_elem, "Chemotherapy")
                
                if treatment.get("regimen"):
                    regimen = ET.SubElement(chemo_elem, "ChemoRegimen")
                    regimen.text = treatment["regimen"]
                
                if treatment.get("cycles_planned"):
                    cycles = ET.SubElement(chemo_elem, "CyclesPlanned")
                    cycles.text = str(treatment["cycles_planned"])
            
            # Radiotherapy-specific fields
            elif treatment.get("treatment_type") == "radiotherapy":
                radio_elem = ET.SubElement(treatment_elem, "Radiotherapy")
                
                if treatment.get("total_dose_gy"):
                    dose = ET.SubElement(radio_elem, "TotalDose")
                    dose.text = str(treatment["total_dose_gy"])
                
                if treatment.get("fractions"):
                    fractions = ET.SubElement(radio_elem, "Fractions")
                    fractions.text = str(treatment["fractions"])
    
    return record


@router.get("/nboca-xml")
async def export_nboca_xml(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Export NBOCA/COSD data as XML for NatCan submission.
    
    - **start_date**: Filter episodes by diagnosis date (YYYY-MM-DD)
    - **end_date**: Filter episodes by diagnosis date (YYYY-MM-DD)
    
    Returns XML formatted according to COSD v9/v10 standard.
    """
    
    # Build query for cancer episodes (bowel cancer only for NBOCA)
    # Note: Episodes are stored in 'episodes' collection with condition_type='cancer'
    query = {"condition_type": "cancer"}
    
    # Try to filter by bowel cancer if specified, but allow all cancer episodes if no bowel episodes exist
    bowel_count = await db.episodes.count_documents({"condition_type": "cancer", "cancer_type": "bowel"})
    if bowel_count > 0:
        query["cancer_type"] = "bowel"
    
    if start_date or end_date:
        # String date query (for ISO string date fields like "2020-08-15")
        string_date_query = {}
        if start_date:
            string_date_query["$gte"] = start_date
        if end_date:
            string_date_query["$lte"] = end_date

        # Datetime query (for datetime fields like created_at)
        datetime_date_query = {}
        if start_date:
            datetime_date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            datetime_date_query["$lte"] = datetime.fromisoformat(end_date)

        # Check multiple possible date fields (most are strings, created_at is datetime)
        query["$or"] = [
            {"cancer_data.diagnosis_date": string_date_query},
            {"diagnosis_date": string_date_query},
            {"first_seen_date": string_date_query},
            {"referral_date": string_date_query},
            {"created_at": datetime_date_query}
        ]
    
    # Fetch cancer episodes
    episodes_cursor = db.episodes.find(query)
    episodes = []
    async for doc in episodes_cursor:
        doc["_id"] = str(doc["_id"])
        episodes.append(doc)
    
    if not episodes:
        # Try without any filters to see if any cancer episodes exist
        total_cancer_count = await db.episodes.count_documents({"condition_type": "cancer"})
        total_count = await db.episodes.count_documents({})
        if total_cancer_count == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"No cancer episodes found in database (found {total_count} total episodes). Please create cancer episodes using the Episodes page before exporting."
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"No cancer episodes match the specified criteria. Total cancer episodes in database: {total_cancer_count}. Try clearing date filters or check that episodes have cancer_type='bowel'."
            )
    
    # Create root XML element
    root = ET.Element("COSDSubmission")
    root.set("version", "9.0")
    root.set("xmlns", "http://www.datadictionary.nhs.uk/messages/COSD-v9-0")
    
    # Add metadata
    metadata = ET.SubElement(root, "SubmissionMetadata")
    org = ET.SubElement(metadata, "OrganisationCode")
    org.text = "SYSTEM"  # Should be replaced with actual org code
    
    extract_date = ET.SubElement(metadata, "ExtractDate")
    extract_date.text = datetime.now().strftime('%Y-%m-%d')
    
    record_count = ET.SubElement(metadata, "RecordCount")
    record_count.text = str(len(episodes))
    
    # Add patient records
    records = ET.SubElement(root, "Records")
    
    for episode in episodes:
        # Fetch patient details using patient_id
        patient = await db.patients.find_one({"patient_id": episode["patient_id"]})
        if not patient:
            continue

        patient["_id"] = str(patient["_id"])

        # Decrypt sensitive fields (NHS number, MRN, postcode, DOB) for export
        patient = decrypt_document(patient)
        
        # Fetch treatments and tumours from separate collections using episode_id (not _id)
        # Only include treatments with valid OPCS-4 codes
        episode_id = episode.get("episode_id") or str(episode["_id"])
        treatments_cursor = db.treatments.find({
            "episode_id": episode_id,
            "opcs4_code": {"$exists": True, "$ne": ""}
        })
        treatments = await treatments_cursor.to_list(length=None)
        
        tumours_cursor = db.tumours.find({"episode_id": episode_id})
        tumours = await tumours_cursor.to_list(length=None)
        
        # Create episode record with treatments and tumours
        record = create_episode_xml(episode, patient, treatments, tumours)
        records.append(record)
    
    # Generate pretty XML
    xml_string = prettify_xml(root)
    
    # Return as XML response
    return Response(
        content=xml_string,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=nboca_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        }
    )


@router.get("/data-completeness")
async def check_data_completeness(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check NBOCA data completeness for all bowel cancer episodes.
    
    Returns metrics on % complete for mandatory COSD fields.
    """
    
    # Fetch all bowel cancer episodes
    episodes_cursor = db.episodes.find({"condition_type": "cancer", "cancer_type": "bowel"})
    episodes = []
    async for doc in episodes_cursor:
        episodes.append(doc)
    
    total = len(episodes)
    if total == 0:
        return {
            "total_episodes": 0,
            "message": "No bowel cancer episodes found"
        }
    
    # Track completeness for mandatory fields
    completeness = {
        "total_episodes": total,
        "patient_demographics": {
            "nhs_number": 0,
            "date_of_birth": 0,
            "gender": 0,
            "ethnicity": 0,
            "postcode": 0
        },
        "diagnosis": {
            "diagnosis_date": 0,
            "icd10_code": 0,
            "tnm_staging": 0
        },
        "surgery": {
            "total_surgical_episodes": 0,
            "opcs4_code": 0,
            "asa_score": 0
        }
    }
    
    for episode in episodes:
        # Fetch patient using record_number (patient_id field stores record_number, not ObjectId)
        patient = await db.patients.find_one({"record_number": episode["patient_id"]})
        if not patient:
            continue

        # Decrypt sensitive fields for validation
        patient = decrypt_document(patient)

        # Check patient demographics
        if patient.get("nhs_number"):
            completeness["patient_demographics"]["nhs_number"] += 1
        
        demographics = patient.get("demographics", {})
        if demographics.get("date_of_birth"):
            completeness["patient_demographics"]["date_of_birth"] += 1
        if demographics.get("gender"):
            completeness["patient_demographics"]["gender"] += 1
        if demographics.get("ethnicity"):
            completeness["patient_demographics"]["ethnicity"] += 1
        if demographics.get("postcode"):
            completeness["patient_demographics"]["postcode"] += 1
        
        # Check diagnosis
        cancer_data = episode.get("cancer_data") or {}
        if cancer_data.get("diagnosis_date"):
            completeness["diagnosis"]["diagnosis_date"] += 1
        if cancer_data.get("icd10_code"):
            completeness["diagnosis"]["icd10_code"] += 1
        if cancer_data.get("tnm_staging"):
            completeness["diagnosis"]["tnm_staging"] += 1
        
        # Fetch treatments from separate collection using episode_id (not _id)
        # Only include treatments with valid OPCS-4 codes
        episode_id = episode.get("episode_id") or str(episode["_id"])
        treatments_cursor = db.treatments.find({
            "episode_id": episode_id,
            "opcs4_code": {"$exists": True, "$ne": ""}
        })
        treatments = await treatments_cursor.to_list(length=None)
        surgical_treatments = [t for t in treatments if t.get("treatment_type") in ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]]

        if surgical_treatments:
            completeness["surgery"]["total_surgical_episodes"] += 1
            
            # Check for OPCS and ASA in any surgical treatment
            has_opcs = any(t.get("opcs4_code") for t in surgical_treatments)
            has_asa = any(t.get("asa_score") for t in surgical_treatments)
            
            if has_opcs:
                completeness["surgery"]["opcs4_code"] += 1
            if has_asa:
                completeness["surgery"]["asa_score"] += 1
    
    # Calculate percentages
    for category in ["patient_demographics", "diagnosis"]:
        for field in completeness[category]:
            count = completeness[category][field]
            completeness[category][field] = {
                "count": count,
                "percentage": round((count / total) * 100, 1)
            }
    
    # Surgery percentages based on surgical episodes
    surgery_total = completeness["surgery"]["total_surgical_episodes"]
    if surgery_total > 0:
        for field in ["opcs4_code", "asa_score"]:
            count = completeness["surgery"][field]
            completeness["surgery"][field] = {
                "count": count,
                "percentage": round((count / surgery_total) * 100, 1)
            }
    
    return completeness


@router.get("/nboca-validator")
async def validate_nboca_submission(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Validate NBOCA/COSD data readiness before submission.
    
    Checks:
    - All mandatory fields populated
    - Valid ICD-10 and OPCS-4 codes
    - Date logic (diagnosis < treatment)
    - Rectal cancer CRM requirements
    - NHS number format
    
    Returns detailed validation report with errors and warnings per episode.
    """
    
    # Valid ICD-10 codes for bowel cancer
    VALID_ICD10_BOWEL = {
        "C18.0", "C18.1", "C18.2", "C18.3", "C18.4", "C18.5", 
        "C18.6", "C18.7", "C18.8", "C18.9", "C19", "C20"
    }
    
    # Valid OPCS-4 codes for colorectal surgery (common procedures)
    VALID_OPCS4_COLORECTAL = {
        "H01", "H02", "H04", "H05", "H06", "H07", "H08", "H09", 
        "H10", "H11", "H33", "H34", "H35", "H46", "H47", "H48", "H49"
    }
    
    # Rectal cancer ICD-10 codes (CRM mandatory)
    RECTAL_ICD10 = {"C19", "C20"}
    
    validation_report = {
        "summary": {
            "total_episodes": 0,
            "valid_episodes": 0,
            "episodes_with_errors": 0,
            "episodes_with_warnings": 0
        },
        "episodes": []
    }
    
    # Fetch all bowel cancer episodes
    query = {"condition_type": "cancer", "cancer_type": "bowel"}
    episodes_cursor = db.episodes.find(query)
    
    async for episode in episodes_cursor:
        validation_report["summary"]["total_episodes"] += 1
        episode_id = episode.get("episode_id") or str(episode["_id"])
        patient_id = episode.get("patient_id")
        
        episode_validation = {
            "episode_id": episode_id,
            "patient_id": patient_id,
            "errors": [],
            "warnings": []
        }
        
        # Fetch related data using episode_id (not _id)
        # Only include treatments with valid OPCS-4 codes
        patient = await db.patients.find_one({"record_number": patient_id})
        tumours_cursor = db.tumours.find({"episode_id": episode_id})
        tumours = await tumours_cursor.to_list(length=None)
        treatments_cursor = db.treatments.find({
            "episode_id": episode_id,
            "opcs4_code": {"$exists": True, "$ne": ""}
        })
        treatments = await treatments_cursor.to_list(length=None)

        # === PATIENT VALIDATION ===
        if not patient:
            episode_validation["errors"].append("Patient record not found")
        else:
            # Decrypt sensitive fields for validation
            patient = decrypt_document(patient)

            demographics = patient.get("demographics", {})
            
            # NHS Number
            if not patient.get("nhs_number"):
                episode_validation["errors"].append("NHS Number missing")
            else:
                nhs = patient["nhs_number"].replace(" ", "")
                if not nhs.isdigit() or len(nhs) != 10:
                    episode_validation["errors"].append(f"Invalid NHS Number format: {patient['nhs_number']}")
            
            # Date of Birth
            if not demographics.get("date_of_birth"):
                episode_validation["errors"].append("Date of Birth missing")
            
            # Gender
            if not demographics.get("gender"):
                episode_validation["errors"].append("Gender missing")
            elif demographics["gender"] not in ["male", "female", "other"]:
                episode_validation["warnings"].append(f"Unusual gender value: {demographics['gender']}")
            
            # Ethnicity
            if not demographics.get("ethnicity"):
                episode_validation["warnings"].append("Ethnicity missing (recommended)")

            # Postcode
            if not demographics.get("postcode"):
                episode_validation["errors"].append("Postcode missing")
        
        # === EPISODE VALIDATION ===
        
        # Referral source
        if not episode.get("referral_source"):
            episode_validation["warnings"].append("Referral source missing")
        
        # Provider first seen
        if not episode.get("provider_first_seen"):
            episode_validation["warnings"].append("Provider first seen missing")
        
        # MDT discussion
        if not episode.get("mdt_discussion_date"):
            episode_validation["warnings"].append("MDT discussion date missing")
        
        if not episode.get("mdt_type"):
            episode_validation["warnings"].append("MDT type missing")
        
        # Performance status
        if not episode.get("performance_status"):
            episode_validation["warnings"].append("Performance status missing")
        
        # === TUMOUR VALIDATION ===
        
        if not tumours:
            episode_validation["errors"].append("No tumour record found")
        else:
            tumour = tumours[0]  # Primary tumour
            
            # Diagnosis date
            if not tumour.get("diagnosis_date"):
                episode_validation["errors"].append("Diagnosis date missing")
            
            # ICD-10 code
            if not tumour.get("icd10_code"):
                episode_validation["errors"].append("ICD-10 code missing")
            elif tumour["icd10_code"] not in VALID_ICD10_BOWEL:
                episode_validation["warnings"].append(f"Unusual ICD-10 code for bowel cancer: {tumour['icd10_code']}")
            
            # TNM version
            if not tumour.get("tnm_version"):
                episode_validation["errors"].append("TNM version missing")
            elif str(tumour["tnm_version"]) not in ["7", "8"]:
                episode_validation["warnings"].append(f"Unusual TNM version: {tumour['tnm_version']}")
            
            # Clinical TNM
            if not tumour.get("clinical_t"):
                episode_validation["errors"].append("Clinical T stage missing")
            if not tumour.get("clinical_n"):
                episode_validation["errors"].append("Clinical N stage missing")
            if not tumour.get("clinical_m"):
                episode_validation["errors"].append("Clinical M stage missing")
            
            # Pathological TNM
            if not tumour.get("pathological_t"):
                episode_validation["warnings"].append("Pathological T stage missing")
            if not tumour.get("pathological_n"):
                episode_validation["warnings"].append("Pathological N stage missing")
            if not tumour.get("pathological_m"):
                episode_validation["warnings"].append("Pathological M stage missing")
            
            # Grade
            if not tumour.get("grade"):
                episode_validation["errors"].append("Tumour grade/differentiation missing")
            
            # Lymph nodes
            if tumour.get("lymph_nodes_examined") is None:
                episode_validation["warnings"].append("Lymph nodes examined not recorded")
            elif tumour["lymph_nodes_examined"] < 12:
                episode_validation["warnings"].append(f"Low lymph node yield: {tumour['lymph_nodes_examined']} (minimum 12 recommended)")
            
            if tumour.get("lymph_nodes_positive") is None:
                episode_validation["warnings"].append("Lymph nodes positive not recorded")
            
            # CRM for rectal cancer
            is_rectal = tumour.get("icd10_code") in RECTAL_ICD10
            if is_rectal:
                if not tumour.get("crm_status") or tumour.get("crm_status") == "not_applicable":
                    episode_validation["errors"].append("CRM status mandatory for rectal cancer but missing")
                if tumour.get("crm_status") == "clear" and tumour.get("crm_distance_mm") is None:
                    episode_validation["warnings"].append("CRM distance should be recorded when CRM is clear")
        
        # === TREATMENT VALIDATION ===

        surgical_treatments = [t for t in treatments if t.get("treatment_type") in ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]]

        if not surgical_treatments:
            episode_validation["warnings"].append("No surgical treatment recorded")
        else:
            for idx, treatment in enumerate(surgical_treatments):
                treatment_num = f"Treatment {idx + 1}"
                
                # Treatment date
                if not treatment.get("treatment_date"):
                    episode_validation["errors"].append(f"{treatment_num}: Treatment date missing")
                
                # OPCS-4 code
                if not treatment.get("opcs4_code"):
                    episode_validation["errors"].append(f"{treatment_num}: OPCS-4 code missing")
                elif treatment["opcs4_code"] not in VALID_OPCS4_COLORECTAL:
                    episode_validation["warnings"].append(f"{treatment_num}: OPCS-4 code {treatment['opcs4_code']} not in common colorectal list")
                
                # ASA score
                if not treatment.get("asa_score"):
                    episode_validation["errors"].append(f"{treatment_num}: ASA score missing")
                elif not (1 <= treatment["asa_score"] <= 5):
                    episode_validation["errors"].append(f"{treatment_num}: Invalid ASA score {treatment['asa_score']} (must be 1-5)")
                
                # Surgical approach
                classification = treatment.get("classification", {})
                if not classification.get("approach"):
                    episode_validation["warnings"].append(f"{treatment_num}: Surgical approach missing")

                # Urgency
                if not classification.get("urgency"):
                    episode_validation["warnings"].append(f"{treatment_num}: Urgency missing")
                
                # Date logic validation
                if tumours and treatment.get("treatment_date") and tumours[0].get("diagnosis_date"):
                    try:
                        diag_date = datetime.fromisoformat(tumours[0]["diagnosis_date"])
                        treat_date = datetime.fromisoformat(treatment["treatment_date"])
                        if treat_date < diag_date:
                            episode_validation["errors"].append(f"{treatment_num}: Treatment date before diagnosis date")
                    except:
                        pass
        
        # Update summary counts
        if episode_validation["errors"]:
            validation_report["summary"]["episodes_with_errors"] += 1
        elif episode_validation["warnings"]:
            validation_report["summary"]["episodes_with_warnings"] += 1
        else:
            validation_report["summary"]["valid_episodes"] += 1
        
        # Only include episodes with issues in the report
        if episode_validation["errors"] or episode_validation["warnings"]:
            validation_report["episodes"].append(episode_validation)
    
    # Calculate percentages
    total = validation_report["summary"]["total_episodes"]
    if total > 0:
        validation_report["summary"]["valid_percentage"] = round(
            (validation_report["summary"]["valid_episodes"] / total) * 100, 1
        )
        validation_report["summary"]["submission_ready"] = (
            validation_report["summary"]["episodes_with_errors"] == 0
        )
    else:
        validation_report["summary"]["valid_percentage"] = 0.0
        validation_report["summary"]["submission_ready"] = False
    
    return validation_report
