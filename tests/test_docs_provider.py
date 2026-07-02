import os
from src.core.docs_provider import DocumentationProvider

def test_docs_provider_loads_xml():
    """Verify the documentation provider can load and parse the XML definition."""
    # Find the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path = os.path.join(project_root, "edf-hex-map.xml")
    
    provider = DocumentationProvider(xml_path)
    
    # We know 'IdleRPMLogic' exists in the XML
    block_def = provider.get_documentation("IdleRPMLogic")
    assert block_def is not None
    assert "IdleRPMLogic" in block_def
    assert "24 4D 23 97 54" in block_def # The exact signature varies (A2 vs 52)
    assert "type=\"int32\"" in block_def

def test_docs_provider_translation_fallback():
    """Verify that if something isn't in the XML, it falls back to the Translation txt file."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path = os.path.join(project_root, "edf-hex-map.xml")
    txt_path = os.path.join(project_root, "Translation_for_EngineEDFBIN_Shiimis_Rangeyrover_V1.5.txt")
    
    provider = DocumentationProvider(xml_path, txt_path)
    
    # We know RPMTorque exists in the Translation file
    tq_def = provider.get_documentation("RPMTorque")
    assert tq_def is not None
    assert "RPMTorque" in tq_def
    
def test_docs_provider_p2p_hardcoded():
    """Verify P2P gets a hardcoded explanation since it's missing from docs."""
    provider = DocumentationProvider("", "")
    p2p_def = provider.get_documentation("P2PTable")
    assert p2p_def is not None
    assert "Reverse engineered" in p2p_def
