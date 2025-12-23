"""
ICD-10 code validation service for colorectal and bowel cancer
Based on NBOCA COSD requirements
"""
from typing import Dict, List, Optional, Tuple


class ICD10Validator:
    """Validate and lookup ICD-10 codes for colorectal cancer"""
    
    # ICD-10 codes for colorectal cancer (NBOCA COSD compliant)
    VALID_CODES = {
        # Colon cancer (C18.x)
        "C18.0": "Malignant neoplasm of caecum",
        "C18.1": "Malignant neoplasm of appendix",
        "C18.2": "Malignant neoplasm of ascending colon",
        "C18.3": "Malignant neoplasm of hepatic flexure",
        "C18.4": "Malignant neoplasm of transverse colon",
        "C18.5": "Malignant neoplasm of splenic flexure",
        "C18.6": "Malignant neoplasm of descending colon",
        "C18.7": "Malignant neoplasm of sigmoid colon",
        "C18.8": "Malignant neoplasm of overlapping sites of colon",
        "C18.9": "Malignant neoplasm of colon, unspecified",
        
        # Rectosigmoid junction (C19)
        "C19": "Malignant neoplasm of rectosigmoid junction",
        "C19.9": "Malignant neoplasm of rectosigmoid junction",
        
        # Rectum (C20)
        "C20": "Malignant neoplasm of rectum",
        "C20.9": "Malignant neoplasm of rectum",
        
        # Anus and anal canal (C21.x) - related conditions
        "C21.0": "Malignant neoplasm of anus, unspecified",
        "C21.1": "Malignant neoplasm of anal canal",
        "C21.2": "Malignant neoplasm of cloacogenic zone",
        "C21.8": "Malignant neoplasm of overlapping sites of rectum, anus and anal canal",
        
        # Secondary malignant neoplasms (common metastases)
        "C78.6": "Secondary malignant neoplasm of retroperitoneum and peritoneum",
        "C78.7": "Secondary malignant neoplasm of liver and intrahepatic bile duct",
        "C78.8": "Secondary malignant neoplasm of other and unspecified digestive organs",
        "C79.5": "Secondary malignant neoplasm of bone and bone marrow",
        "C79.7": "Secondary malignant neoplasm of adrenal gland",
        "C79.8": "Secondary malignant neoplasm of other specified sites",
        "C79.9": "Secondary malignant neoplasm of unspecified site",
        
        # Related benign conditions
        "D12.0": "Benign neoplasm of caecum",
        "D12.2": "Benign neoplasm of ascending colon",
        "D12.3": "Benign neoplasm of transverse colon",
        "D12.4": "Benign neoplasm of descending colon",
        "D12.5": "Benign neoplasm of sigmoid colon",
        "D12.6": "Benign neoplasm of colon, unspecified",
        "D12.7": "Benign neoplasm of rectosigmoid junction",
        "D12.8": "Benign neoplasm of rectum",
        "D12.9": "Benign neoplasm of anus and anal canal",
        
        # Carcinoma in situ
        "D01.0": "Carcinoma in situ of colon",
        "D01.1": "Carcinoma in situ of rectosigmoid junction",
        "D01.2": "Carcinoma in situ of rectum",
        "D01.3": "Carcinoma in situ of anus and anal canal",
    }
    
    # Anatomical site groupings
    SITE_GROUPS = {
        "colon": ["C18.0", "C18.1", "C18.2", "C18.3", "C18.4", "C18.5", "C18.6", "C18.7", "C18.8", "C18.9"],
        "right_colon": ["C18.0", "C18.1", "C18.2", "C18.3"],  # Caecum to hepatic flexure
        "left_colon": ["C18.4", "C18.5", "C18.6", "C18.7"],   # Transverse to sigmoid
        "rectosigmoid": ["C19", "C19.9"],
        "rectum": ["C20", "C20.9"],
        "anus": ["C21.0", "C21.1", "C21.2"],
        "colorectal": ["C18.0", "C18.1", "C18.2", "C18.3", "C18.4", "C18.5", "C18.6", "C18.7", "C18.8", "C18.9", "C19", "C20"],
    }
    
    @classmethod
    def validate(cls, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an ICD-10 code
        
        Returns:
            (is_valid, error_message)
        """
        if not code:
            return False, "ICD-10 code is required"
        
        # Remove any whitespace and convert to uppercase
        code = code.strip().upper()
        
        # Check if code exists
        if code not in cls.VALID_CODES:
            return False, f"Invalid ICD-10 code: {code}"
        
        return True, None
    
    @classmethod
    def lookup(cls, code: str) -> Optional[str]:
        """
        Look up the description for an ICD-10 code
        
        Returns:
            Description string or None if not found
        """
        code = code.strip().upper()
        return cls.VALID_CODES.get(code)
    
    @classmethod
    def search(cls, query: str) -> List[Dict[str, str]]:
        """
        Search for ICD-10 codes by keyword
        
        Returns:
            List of matching codes with descriptions
        """
        query = query.lower()
        results = []
        
        for code, description in cls.VALID_CODES.items():
            if query in code.lower() or query in description.lower():
                results.append({
                    "code": code,
                    "description": description
                })
        
        return results
    
    @classmethod
    def get_site_codes(cls, site: str) -> List[str]:
        """
        Get all codes for a specific anatomical site
        
        Args:
            site: One of 'colon', 'right_colon', 'left_colon', 'rectosigmoid', 'rectum', 'anus', 'colorectal'
        
        Returns:
            List of ICD-10 codes for that site
        """
        return cls.SITE_GROUPS.get(site.lower(), [])
    
    @classmethod
    def is_rectal_cancer(cls, code: str) -> bool:
        """Check if code represents rectal cancer (important for CRM requirement)"""
        code = code.strip().upper()
        return code in ["C19", "C19.9", "C20", "C20.9"]
    
    @classmethod
    def is_colon_cancer(cls, code: str) -> bool:
        """Check if code represents colon cancer"""
        code = code.strip().upper()
        return code.startswith("C18.")
    
    @classmethod
    def get_all_codes(cls) -> List[Dict[str, str]]:
        """Get all valid ICD-10 codes with descriptions"""
        return [
            {"code": code, "description": description}
            for code, description in cls.VALID_CODES.items()
        ]
    
    @classmethod
    def get_primary_cancer_codes(cls) -> List[Dict[str, str]]:
        """Get only primary colorectal cancer codes (excludes metastases and benign)"""
        primary_codes = []
        for code, description in cls.VALID_CODES.items():
            if code.startswith(("C18", "C19", "C20", "C21")):
                primary_codes.append({
                    "code": code,
                    "description": description
                })
        return primary_codes
