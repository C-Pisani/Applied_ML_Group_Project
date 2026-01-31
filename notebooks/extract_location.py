"""
Location extraction for Maltese police press releases.
Extracts road names and towns from content.
"""

import pandas as pd
import re
from typing import Optional, List, Tuple, Dict


def load_towns(locations_path: str) -> pd.DataFrame:
    """Load the locations reference file."""
    return pd.read_csv(locations_path, encoding='utf-8-sig')


def create_town_variations(town: str) -> List[str]:
    """
    Create variations of a town name for matching.
    Handles Maltese article prefixes and maintains original case.
    """
    variations = [town]
    
    # Common Maltese article prefixes (with space or hyphen)
    prefixes = [
        "Il-", "L-", "Ħal ", "Ħaż-", "Ħ'", 
        "Is-", "Iż-", "In-", "Ir-", "Ix-",
        "Ta' ", "Tal-", "Tas-"
    ]
    
    for prefix in prefixes:
        if town.startswith(prefix):
            base_name = town[len(prefix):]
            if base_name and base_name not in variations:
                variations.append(base_name)
            break
    
    return variations


def create_ascii_mapping() -> dict:
    """Mapping from Maltese special characters to ASCII equivalents."""
    return {
        'Ħ': 'H', 'ħ': 'h',
        'Ġ': 'G', 'ġ': 'g', 
        'Ż': 'Z', 'ż': 'z',
        'Ċ': 'C', 'ċ': 'c',
        'À': 'A', 'à': 'a',
        'È': 'E', 'è': 'e',
        'Ì': 'I', 'ì': 'i',
        'Ò': 'O', 'ò': 'o',
        'Ù': 'U', 'ù': 'u',
        '\u2018': "'",
        '\u2019': "'",
    }


def to_ascii(text: str) -> str:
    """Convert Maltese text to ASCII equivalent."""
    mapping = create_ascii_mapping()
    result = text
    for maltese, ascii_char in mapping.items():
        result = result.replace(maltese, ascii_char)
    return result


def normalize_apostrophes(text: str) -> str:
    """Normalize all apostrophe variants to standard ASCII apostrophe."""
    apostrophes = ['\u2018', '\u2019', '\u0060', '\u00B4', '\u2032']
    for apos in apostrophes:
        text = text.replace(apos, "'")
    return text


def get_english_aliases() -> dict:
    """Map official Maltese town names to common English aliases."""
    return {
        "Raħal Ġdid": ["Paola"],
        "Bormla": ["Cospicua"],
        "Il-Birgu": ["Vittoriosa"],
        "L-Isla": ["Senglea"],
        "San Pawl Il-Baħar": ["St Paul's Bay", "St. Paul's Bay", "St Pauls Bay", "Buġibba", "Bugibba", "Qawra", "St Paul\u2019s Bay", "St. Paul\u2019s Bay"],
        "L-Imtarfa": ["Mtarfa"],
        "Il-Gżira": ["Gzira"],
        "L-Imġarr": ["Mgarr", "Mġarr"],
        "Ħal Ghaxaq": ["Għaxaq", "Ghaxaq"],
        "Ir-Rabat": ["Victoria"],
        "San Ġiljan": ["St Julian's", "St. Julian's", "St Julians", "St. Julians", "St Julian\u2019s", "St. Julian\u2019s"],
        "Tal-Pieta'": ["Tal-Pietà", "Pietà", "Pieta", "Gwardamanġa", "Gwardamanga"],
        "Marsaskala": ["Marsascala"],
        "Ħ'Attard": ["Attard"],
        "Il-Mellieħa": ["Mellieha", "Mellieħa"],
        "L-Imsida": ["Msida"],
        "Is-Swieqi": ["Swieqi"],
        "Ħal Balzan": ["Balzan"],
        "Ta' Xbiex": ["Xbiex"],
    }


def build_town_lookup(locations_df: pd.DataFrame) -> List[Tuple[str, List[str]]]:
    """Build a lookup structure with official town names and their variations."""
    lookup = []
    english_aliases = get_english_aliases()
    
    for _, row in locations_df.iterrows():
        town = row['Town']
        variations = create_town_variations(town)
        
        if town in english_aliases:
            variations.extend(english_aliases[town])
        
        ascii_variations = []
        for var in variations:
            ascii_var = to_ascii(var)
            if ascii_var != var and ascii_var not in variations and ascii_var not in ascii_variations:
                ascii_variations.append(ascii_var)
        
        all_variations = variations + ascii_variations
        lookup.append((town, all_variations))
    
    lookup.sort(key=lambda x: max(len(v) for v in x[1]), reverse=True)
    return lookup


def extract_town(content: str, locations_df: pd.DataFrame) -> Optional[str]:
    """
    Extract the PRIMARY town from police press release content.
    Returns the town that appears FIRST in the text.
    """
    if not content or pd.isna(content):
        return None
    
    normalized_content = normalize_apostrophes(content)
    lookup = build_town_lookup(locations_df)
    matches = []
    
    for official_name, variations in lookup:
        for variation in variations:
            normalized_variation = normalize_apostrophes(variation)
            pattern = r'\b' + re.escape(normalized_variation) + r'\b'
            match = re.search(pattern, normalized_content)
            if match:
                matches.append((match.start(), official_name))
                break
    
    if not matches:
        return None
    
    matches.sort(key=lambda x: x[0])
    return matches[0][1]


def extract_all_towns(content: str, locations_df: pd.DataFrame) -> List[str]:
    """Extract ALL towns mentioned in the content."""
    if not content or pd.isna(content):
        return []
    
    normalized_content = normalize_apostrophes(content)
    lookup = build_town_lookup(locations_df)
    found_towns = []
    
    for official_name, variations in lookup:
        if official_name in found_towns:
            continue
        for variation in variations:
            normalized_variation = normalize_apostrophes(variation)
            pattern = r'\b' + re.escape(normalized_variation) + r'\b'
            if re.search(pattern, normalized_content):
                found_towns.append(official_name)
                break
    
    return found_towns


def extract_road_and_town(content: str, locations_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract the road name and town where the incident occurred.
    
    Args:
        content: The text content of the press release
        locations_df: DataFrame with 'Town' column
        
    Returns:
        Tuple of (road, town) - either can be None if not found
    """
    if not content or pd.isna(content):
        return (None, None)
    
    normalized_content = normalize_apostrophes(content)
    
    # Build list of all town variations for matching
    lookup = build_town_lookup(locations_df)
    all_town_variations = []
    for official_name, variations in lookup:
        for var in variations:
            all_town_variations.append((normalize_apostrophes(var), official_name))
    
    # Sort by length (longest first) to match specific towns first
    all_town_variations.sort(key=lambda x: len(x[0]), reverse=True)
    
    # Common Maltese road prefixes
    maltese_prefixes = ["Triq", "Vjal", "Telgħa", "Telgha", "Sqaq", "Misraħ", 
                        "Misrah", "Dawret", "Xatt", "Pjazza", "Piazza"]
    
    # English-style road suffixes
    english_suffixes = ["Road", "Street", "Avenue", "Drive", "Lane", "Square",
                        "Wharf", "Seafront", "Hill", "Promenade", "Gardens", "Place"]
    
    road = None
    town = None
    
    # Strategy: Find the location phrase "in [ROAD], [TOWN]" pattern
    for town_var, official_town in all_town_variations:
        town_escaped = re.escape(town_var)
        
        # Pattern 1: Maltese prefix - "Triq [Name], Town"
        for prefix in maltese_prefixes:
            # Match: prefix + any words until comma + town
            pattern = r'\b(' + re.escape(prefix) + r'[^,]+),\s*' + town_escaped + r'\b'
            match = re.search(pattern, normalized_content)
            if match:
                road = match.group(1).strip()
                # Clean trailing prepositions
                road = re.sub(r'\s+(?:in|at|near|by)$', '', road, flags=re.IGNORECASE)
                town = official_town
                return (road, town)
        
        # Pattern 2: English suffix - "[Name] Road, Town"
        for suffix in english_suffixes:
            # Use character class that includes apostrophes and word chars
            # Match 1-4 "words" (including apostrophes) before the suffix
            pattern = r"(?:^|in\s+|at\s+|along\s+(?:the\s+)?)((?:[\w']+\s+){0,4}" + re.escape(suffix) + r'),\s*' + town_escaped + r'\b'
            match = re.search(pattern, normalized_content, re.IGNORECASE)
            if match:
                road = match.group(1).strip()
                town = official_town
                return (road, town)
        
        # Pattern 3: "along the [Road] in Town"
        pattern = r'along\s+(?:the\s+)?(.+?),?\s+in\s+' + town_escaped + r'\b'
        match = re.search(pattern, normalized_content, re.IGNORECASE)
        if match:
            road = match.group(1).strip()
            town = official_town
            return (road, town)
    
    # If no road+town combo found, get town separately
    town = extract_town(content, locations_df)
    
    # Then try to find any road name in the text
    # Maltese-style roads
    for prefix in maltese_prefixes:
        pattern = r'\b(' + re.escape(prefix) + r"\s+[\w\s'''\\-]+?)(?:,|\.|\s+corner)"
        match = re.search(pattern, normalized_content)
        if match:
            road = match.group(1).strip()
            road = re.sub(r'\s+(?:in|at|near|by)$', '', road, flags=re.IGNORECASE)
            return (road, town)
    
    # English-style roads (include apostrophes in word matching)
    for suffix in english_suffixes:
        pattern = r"\b((?:[\w']+\s+){1,4}" + re.escape(suffix) + r')\b'
        match = re.search(pattern, normalized_content)
        if match:
            road = match.group(1).strip()
            return (road, town)
    
    return (road, town)


def extract_location(content: str, locations_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience alias for extract_road_and_town.
    Returns tuple of (road, town).
    """
    return extract_road_and_town(content, locations_df)


# Example usage and testing
if __name__ == "__main__":
    locations_df = load_towns('/mnt/user-data/uploads/locations.csv')
    press_df = pd.read_csv('/mnt/user-data/uploads/police_press_releases.csv')
    
    print("=" * 70)
    print("Testing road and town extraction")
    print("=" * 70)
    
    # Test on sample content
    for idx, row in press_df.head(15).iterrows():
        road, town = extract_road_and_town(row['content'], locations_df)
        print(f"\nTitle: {row['title'][:60]}...")
        print(f"  Road: {road}")
        print(f"  Town: {town}")
    
    # Apply to full dataset
    print("\n" + "=" * 70)
    print("Applying to full dataset")
    print("=" * 70)
    
    # Extract as tuples and unpack into columns
    press_df['road'], press_df['town'] = zip(*press_df['content'].apply(
        lambda x: extract_road_and_town(x, locations_df)
    ))
    
    # Stats
    roads_found = press_df['road'].notna().sum()
    towns_found = press_df['town'].notna().sum()
    total = len(press_df)
    
    print(f"\nRoad extraction rate: {roads_found}/{total} ({100*roads_found/total:.1f}%)")
    print(f"Town extraction rate: {towns_found}/{total} ({100*towns_found/total:.1f}%)")
    
    # Show sample
    print("\nSample results:")
    print(press_df[['title', 'road', 'town']].head(20).to_string())
    
    # Check St Luke's Square specifically
    print("\n" + "=" * 70)
    print("Checking St Luke's Square case:")
    print("=" * 70)
    for idx, row in press_df.iterrows():
        if "Luke" in str(row['content']) or "Gwardaman" in str(row['content']):
            road, town = extract_road_and_town(row['content'], locations_df)
            print(f"Title: {row['title']}")
            print(f"  Road: {road}")
            print(f"  Town: {town}")
