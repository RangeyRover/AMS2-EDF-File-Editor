import os
import xml.etree.ElementTree as ET

class DocumentationProvider:
    def __init__(self, xml_path: str, txt_path: str = None):
        self.xml_path = xml_path
        self.txt_path = txt_path
        self.cache = {}
        self._load_xml()
        if self.txt_path:
            self._load_txt()

    def _load_xml(self):
        if not os.path.exists(self.xml_path):
            return
        
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            # Map parameters by name
            for params in root.findall('parameters'):
                for block in params.findall('block'):
                    name = block.get('name')
                    if name:
                        # Reconstruct the raw XML string roughly
                        raw_xml = ET.tostring(block, encoding='unicode', method='xml').strip()
                        self.cache[name] = raw_xml
                        
        except Exception as e:
            print(f"Error parsing XML docs: {e}")

    def _load_txt(self):
        if not os.path.exists(self.txt_path):
            return
            
        try:
            with open(self.txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines:
                if "=" in line and "[" in line and "]" in line:
                    # e.g. [24 8B 0A B7 71 83 02] RPMTorque=({byte}0, {float}-58.40)
                    parts = line.split('=')
                    left_side = parts[0]
                    # extract the name
                    if ']' in left_side:
                        name = left_side.split(']')[-1].strip()
                        if name and name not in self.cache:
                            self.cache[name] = line.strip()
                        
        except Exception as e:
            print(f"Error parsing txt docs: {e}")

    def get_documentation(self, key: str) -> str:
        """Get the raw documentation string for a given key"""
        if key == "P2PTable" or key == "P2P_ZERO_STRUCT":
            return "Reverse engineered: 441-row structure consisting of Mode (Byte), RPM (Float), Throttle (Float), Multiplier (Float), Pad (Byte)."
        return self.cache.get(key)
