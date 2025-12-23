"""
OPCS-4 code validation service for colorectal surgery procedures
Based on NBOCA COSD requirements
"""
from typing import Dict, List, Optional, Tuple


class OPCS4Validator:
    """Validate and lookup OPCS-4 codes for colorectal surgery"""
    
    # OPCS-4 codes for colorectal surgery (NBOCA COSD compliant)
    VALID_CODES = {
        # Major resections (H04-H11)
        "H04.1": "Total excision of colon and rectum and excision of anal sphincter",
        "H04.2": "Total excision of colon and rectum NEC",
        "H04.3": "Extended excision of right hemicolon",
        "H04.4": "Excision of right hemicolon",
        "H04.5": "Excision of transverse colon",
        "H04.6": "Extended excision of left hemicolon",
        "H04.7": "Excision of left hemicolon",
        "H04.8": "Other specified excision of colon",
        "H04.9": "Unspecified excision of colon",
        
        "H05.1": "Total excision of colon",
        "H05.2": "Extended excision of colon",
        "H05.3": "Excision of sigmoid colon",
        "H05.4": "Excision of caecum",
        "H05.8": "Other specified total excision of colon",
        "H05.9": "Unspecified total excision of colon",
        
        "H06.1": "Total excision of colon and ileum",
        "H06.2": "Excision of colon and terminal ileum",
        "H06.3": "Panproctocolectomy with ileostomy",
        "H06.4": "Panproctocolectomy with ileoanal pouch",
        "H06.5": "Panproctocolectomy with continent ileostomy",
        "H06.8": "Other specified total excision of colon and rectum",
        "H06.9": "Unspecified total excision of colon and rectum",
        
        "H07.1": "Subtotal excision of colon with anastomosis of ileum to rectum",
        "H07.2": "Subtotal excision of colon with anastomosis of ileum to sigmoid colon",
        "H07.3": "Subtotal excision of colon NEC",
        "H07.8": "Other specified subtotal excision of colon",
        "H07.9": "Unspecified subtotal excision of colon",
        
        "H08.1": "Anterior resection of rectum",
        "H08.2": "Anterior resection of rectum with synchronous abdominoperineal excision",
        "H08.3": "Ultra-low anterior resection of rectum",
        "H08.4": "Pan-proctal excision of rectum",
        "H08.5": "Excision of rectum and colon with restoration of continuity NEC",
        "H08.8": "Other specified excision of rectum",
        "H08.9": "Unspecified excision of rectum",
        
        "H09.1": "Abdominoperineal excision of rectum",
        "H09.2": "Perineal excision of rectum",
        "H09.3": "Transabdominal excision of rectum NEC",
        "H09.8": "Other specified abdominoperineal excision of rectum",
        "H09.9": "Unspecified abdominoperineal excision of rectum",
        
        "H10.1": "Hartmann operation",
        "H10.2": "Excision of rectosigmoid",
        "H10.3": "Excision of rectum NEC",
        "H10.8": "Other specified excision of rectosigmoid",
        "H10.9": "Unspecified excision of rectosigmoid",
        
        "H11.1": "Excision of lesion of colon",
        "H11.2": "Excision of lesion of rectum",
        "H11.3": "Excision of polyp of colon",
        "H11.4": "Excision of polyp of rectum",
        "H11.8": "Other specified therapeutic endoscopic operations on colon",
        "H11.9": "Unspecified therapeutic endoscopic operations on colon",
        
        # Stoma operations (H33-H35)
        "H33.1": "Permanent ileostomy",
        "H33.2": "Temporary ileostomy",
        "H33.3": "Defunctioning loop ileostomy",
        "H33.4": "End ileostomy",
        "H33.5": "Ileostomy NEC",
        "H33.8": "Other specified exteriorisation of small intestine",
        "H33.9": "Unspecified exteriorisation of small intestine",
        
        "H34.1": "Permanent colostomy",
        "H34.2": "Temporary colostomy",
        "H34.3": "Defunctioning loop colostomy",
        "H34.4": "End colostomy",
        "H34.5": "Colostomy NEC",
        "H34.8": "Other specified exteriorisation of large intestine",
        "H34.9": "Unspecified exteriorisation of large intestine",
        
        "H35.1": "Closure of ileostomy",
        "H35.2": "Closure of colostomy",
        "H35.3": "Closure of stoma of large intestine NEC",
        "H35.8": "Other specified closure of stoma of intestine",
        "H35.9": "Unspecified closure of stoma of intestine",
        
        # Laparoscopic procedures (H46-H49)
        "H46.1": "Laparoscopic excision of right hemicolon",
        "H46.2": "Laparoscopic excision of left hemicolon",
        "H46.3": "Laparoscopic excision of sigmoid colon",
        "H46.4": "Laparoscopic total excision of colon",
        "H46.5": "Laparoscopic anterior resection of rectum",
        "H46.8": "Other specified laparoscopic excision of colon",
        "H46.9": "Unspecified laparoscopic excision of colon",
        
        "H47.1": "Laparoscopic excision of lesion of colon",
        "H47.2": "Laparoscopic ileostomy",
        "H47.3": "Laparoscopic colostomy",
        "H47.8": "Other specified laparoscopic operations on colon",
        "H47.9": "Unspecified laparoscopic operations on colon",
        
        "H48.1": "Laparoscopic mobilisation of colon",
        "H48.2": "Laparoscopic mobilisation of rectum",
        "H48.3": "Laparoscopic adhesiolysis of colon",
        "H48.8": "Other specified laparoscopic operations on large intestine",
        "H48.9": "Unspecified laparoscopic operations on large intestine",
        
        "H49.1": "Robotic assisted excision of colon",
        "H49.2": "Robotic assisted excision of rectum",
        "H49.8": "Other specified robotic assisted operations on large intestine",
        "H49.9": "Unspecified robotic assisted operations on large intestine",
        
        # Additional relevant procedures
        "H01.1": "Bypass of colon",
        "H01.2": "Bypass of rectum",
        "H01.8": "Other specified bypass of large intestine",
        "H01.9": "Unspecified bypass of large intestine",
        
        "H02.1": "Anastomosis of colon to colon",
        "H02.2": "Anastomosis of ileum to colon",
        "H02.3": "Anastomosis of ileum to rectum",
        "H02.4": "Ileo-anal pouch",
        "H02.8": "Other specified connection of large intestine",
        "H02.9": "Unspecified connection of large intestine",
        
        "H03.1": "Repair of colon",
        "H03.2": "Repair of rectum",
        "H03.3": "Suture of perforation of colon",
        "H03.4": "Suture of perforation of rectum",
        "H03.8": "Other specified repair of large intestine",
        "H03.9": "Unspecified repair of large intestine",
    }
    
    # Procedure type groupings
    PROCEDURE_GROUPS = {
        "right_hemicolectomy": ["H04.3", "H04.4", "H46.1"],
        "left_hemicolectomy": ["H04.6", "H04.7", "H46.2"],
        "sigmoid_colectomy": ["H05.3", "H46.3"],
        "anterior_resection": ["H08.1", "H08.3", "H46.5"],
        "apr": ["H09.1", "H09.2", "H09.3"],  # Abdominoperineal resection
        "hartmann": ["H10.1"],
        "total_colectomy": ["H05.1", "H06.3", "H06.4", "H06.5", "H46.4"],
        "ileostomy": ["H33.1", "H33.2", "H33.3", "H33.4", "H47.2"],
        "colostomy": ["H34.1", "H34.2", "H34.3", "H34.4", "H47.3"],
        "stoma_closure": ["H35.1", "H35.2", "H35.3"],
        "laparoscopic": ["H46.1", "H46.2", "H46.3", "H46.4", "H46.5", "H47.1", "H47.2", "H47.3", "H48.1", "H48.2", "H48.3"],
        "robotic": ["H49.1", "H49.2"],
    }
    
    @classmethod
    def validate(cls, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an OPCS-4 code
        
        Returns:
            (is_valid, error_message)
        """
        if not code:
            return False, "OPCS-4 code is required"
        
        # Remove any whitespace and convert to uppercase
        code = code.strip().upper()
        
        # Check if code exists
        if code not in cls.VALID_CODES:
            return False, f"Invalid OPCS-4 code: {code}"
        
        return True, None
    
    @classmethod
    def lookup(cls, code: str) -> Optional[str]:
        """
        Look up the description for an OPCS-4 code
        
        Returns:
            Description string or None if not found
        """
        code = code.strip().upper()
        return cls.VALID_CODES.get(code)
    
    @classmethod
    def search(cls, query: str) -> List[Dict[str, str]]:
        """
        Search for OPCS-4 codes by keyword
        
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
    def get_procedure_codes(cls, procedure_type: str) -> List[str]:
        """
        Get all codes for a specific procedure type
        
        Args:
            procedure_type: One of the keys in PROCEDURE_GROUPS
        
        Returns:
            List of OPCS-4 codes for that procedure type
        """
        return cls.PROCEDURE_GROUPS.get(procedure_type.lower(), [])
    
    @classmethod
    def is_major_resection(cls, code: str) -> bool:
        """Check if code represents a major colorectal resection"""
        code = code.strip().upper()
        # Major resections are H04-H10
        return any(code.startswith(f"H0{i}") for i in range(4, 11))
    
    @classmethod
    def is_laparoscopic(cls, code: str) -> bool:
        """Check if code represents a laparoscopic procedure"""
        code = code.strip().upper()
        return code.startswith(("H46", "H47", "H48"))
    
    @classmethod
    def is_robotic(cls, code: str) -> bool:
        """Check if code represents a robotic procedure"""
        code = code.strip().upper()
        return code.startswith("H49")
    
    @classmethod
    def get_all_codes(cls) -> List[Dict[str, str]]:
        """Get all valid OPCS-4 codes with descriptions"""
        return [
            {"code": code, "description": description}
            for code, description in cls.VALID_CODES.items()
        ]
    
    @classmethod
    def get_resection_codes(cls) -> List[Dict[str, str]]:
        """Get only major resection codes (H04-H10)"""
        resection_codes = []
        for code, description in cls.VALID_CODES.items():
            if cls.is_major_resection(code):
                resection_codes.append({
                    "code": code,
                    "description": description
                })
        return resection_codes
