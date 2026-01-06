#!/usr/bin/env python3
"""
Test COSD/Somerset XML export by directly calling the export logic.
This bypasses authentication to generate a sample XML file.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom


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
    
    # Episode ID
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
    
    # Diagnosis details
    if episode.get("cancer_type") == "bowel" and tumours:
        tumour = tumours[0]
        diagnosis_elem = ET.SubElement(episode_elem, "Diagnosis")
        
        # Diagnosis date (CR2030)
        if tumour.get("diagnosis_date"):
            diag_date = ET.SubElement(diagnosis_elem, "PrimaryDiagnosisDate")
            diag_date.text = format_date(tumour["diagnosis_date"])
        
        # ICD-10 code (CR0370)
        if tumour.get("icd10_code"):
            icd = ET.SubElement(diagnosis_elem, "PrimaryDiagnosisICD")
            icd.text = tumour["icd10_code"]
        
        # TNM Staging
        tnm_elem = ET.SubElement(diagnosis_elem, "TNMStaging")
        
        if tumour.get("tnm_version"):
            version = ET.SubElement(tnm_elem, "TNMVersionNumber")
            version.text = str(tumour["tnm_version"])
        
        if tumour.get("clinical_t"):
            t_cat = ET.SubElement(tnm_elem, "TCategoryFinalPretreatment")
            t_cat.text = tumour["clinical_t"]
        
        if tumour.get("clinical_n"):
            n_cat = ET.SubElement(tnm_elem, "NCategoryFinalPretreatment")
            n_cat.text = tumour["clinical_n"]
        
        if tumour.get("clinical_m"):
            m_cat = ET.SubElement(tnm_elem, "MCategoryFinalPretreatment")
            m_cat.text = tumour["clinical_m"]
        
        # Pathology
        pathology_elem = ET.SubElement(diagnosis_elem, "Pathology")
        
        if tumour.get("grade"):
            grade = ET.SubElement(pathology_elem, "DifferentiationGrade")
            grade.text = tumour["grade"]
        
        if tumour.get("lymph_nodes_examined") is not None:
            nodes_exam = ET.SubElement(pathology_elem, "NumberOfNodesExamined")
            nodes_exam.text = str(tumour["lymph_nodes_examined"])
        
        if tumour.get("lymph_nodes_positive") is not None:
            nodes_pos = ET.SubElement(pathology_elem, "NumberOfNodesPositive")
            nodes_pos.text = str(tumour["lymph_nodes_positive"])
        
        if tumour.get("crm_status"):
            crm = ET.SubElement(pathology_elem, "CircumferentialResectionMargin")
            crm.text = tumour["crm_status"]
    
    # Treatments
    if treatments:
        treatments_elem = ET.SubElement(episode_elem, "Treatments")
        
        for treatment in treatments:
            treatment_elem = ET.SubElement(treatments_elem, "Treatment")

            # Treatment type - normalize for COSD (all surgery types export as "SURGERY")
            t_type = ET.SubElement(treatment_elem, "TreatmentType")
            treatment_type = treatment.get("treatment_type", "")
            # Normalize internal surgery types to COSD standard
            if treatment_type in ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]:
                t_type.text = "SURGERY"
            else:
                t_type.text = treatment_type.upper()
            
            if treatment.get("treatment_date"):
                t_date = ET.SubElement(treatment_elem, "TreatmentDate")
                t_date.text = format_date(treatment["treatment_date"])

            # Surgery-specific (includes all surgery types: primary, RTT, reversal)
            if treatment.get("treatment_type") in ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]:
                surgery_elem = ET.SubElement(treatment_elem, "Surgery")
                
                if treatment.get("opcs4_code"):
                    opcs = ET.SubElement(surgery_elem, "PrimaryProcedureOPCS")
                    opcs.text = treatment["opcs4_code"]
                
                if treatment.get("asa_score"):
                    asa = ET.SubElement(surgery_elem, "ASAScore")
                    asa.text = str(treatment["asa_score"])
                
                if treatment.get("approach"):
                    approach = ET.SubElement(surgery_elem, "SurgicalAccessType")
                    approach_map = {"open": "01", "laparoscopic": "02", "robotic": "04"}
                    approach.text = approach_map.get(treatment["approach"], "99")
                
                if treatment.get("urgency"):
                    urgency = ET.SubElement(surgery_elem, "SurgicalUrgencyType")
                    urgency_map = {"elective": "01", "urgent": "02", "emergency": "03"}
                    urgency.text = urgency_map.get(treatment["urgency"], "99")
    
    return record


async def main():
    """Generate COSD/Somerset XML export."""
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient('mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin')
    db = client['surgdb']
    
    # Check for cancer episodes
    cancer_count = await db.episodes.count_documents({"condition_type": "cancer"})
    print(f"Found {cancer_count} cancer episodes")
    
    if cancer_count == 0:
        print("\nNo cancer episodes found. Cannot generate export.")
        print("Please create cancer episodes in the application first.")
        return
    
    # Build query
    query = {"condition_type": "cancer"}
    bowel_count = await db.episodes.count_documents({"condition_type": "cancer", "cancer_type": "bowel"})
    if bowel_count > 0:
        query["cancer_type"] = "bowel"
        print(f"Found {bowel_count} bowel cancer episodes")
    
    # Fetch episodes (limit to 5 for testing)
    episodes = []
    async for doc in db.episodes.find(query).limit(5):
        doc["_id"] = str(doc["_id"])
        episodes.append(doc)
    
    print(f"\nGenerating XML for {len(episodes)} episodes...")
    
    # Create root XML
    root = ET.Element("COSDSubmission")
    root.set("version", "9.0")
    root.set("xmlns", "http://www.datadictionary.nhs.uk/messages/COSD-v9-0")
    
    # Metadata
    metadata = ET.SubElement(root, "SubmissionMetadata")
    org = ET.SubElement(metadata, "OrganisationCode")
    org.text = "RBA"  # Somerset NHS Foundation Trust code
    
    extract_date = ET.SubElement(metadata, "ExtractDate")
    extract_date.text = datetime.now().strftime('%Y-%m-%d')
    
    record_count = ET.SubElement(metadata, "RecordCount")
    record_count.text = str(len(episodes))
    
    # Records
    records = ET.SubElement(root, "Records")
    
    for episode in episodes:
        # Fetch patient
        patient = await db.patients.find_one({"patient_id": episode["patient_id"]})
        if not patient:
            print(f"Warning: Patient not found for episode {episode['_id']}")
            continue
        
        patient["_id"] = str(patient["_id"])
        
        # Fetch treatments and tumours
        episode_id = episode.get("episode_id") or str(episode["_id"])
        treatments = await db.treatments.find({"episode_id": episode_id}).to_list(length=None)
        tumours = await db.tumours.find({"episode_id": episode_id}).to_list(length=None)
        
        print(f"  Episode {episode_id}: {len(treatments)} treatments, {len(tumours)} tumours")
        
        # Create record
        record = create_episode_xml(episode, patient, treatments, tumours)
        records.append(record)
    
    # Generate XML
    xml_string = prettify_xml(root)
    
    # Save to file
    output_file = Path.home() / ".tmp" / "somerset_cosd_export.xml"
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(xml_string)
    
    print(f"\n✅ XML export saved to: {output_file}")
    print(f"   Size: {len(xml_string)} bytes")
    print(f"   Records: {len(episodes)}")
    
    # Show first 50 lines
    print("\n" + "="*80)
    print("Sample XML Output (first 50 lines):")
    print("="*80)
    lines = xml_string.split('\n')
    for line in lines[:50]:
        print(line)
    
    if len(lines) > 50:
        print(f"\n... ({len(lines) - 50} more lines)")


if __name__ == "__main__":
    asyncio.run(main())
