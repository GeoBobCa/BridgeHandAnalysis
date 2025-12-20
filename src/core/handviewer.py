from typing import Dict
import urllib.parse

class HandViewer:
    """
    Generates Bridge Base Online (BBO) HandViewer URLs.
    Ref: http://www.bridgebase.com/tools/handviewer.html
    """
    
    BASE_URL = "http://www.bridgebase.com/tools/handviewer.html"

    @staticmethod
    def generate_url(hand_data: Dict) -> str:
        """
        Converts a hand dictionary into a BBO Viewer URL.
        Input format: {'North': ['SAK...', 'H...', ...], ...}
        """
        # 1. Map Compass to URL parameters (n, s, e, w)
        # BBO format: n=spades...hearts...diams...clubs...
        # We need to join the 4 suit strings into one string per hand.
        params = {}
        
        # Mapping our keys 'North' -> BBO param 'n'
        compass_map = {'North': 'n', 'South': 's', 'East': 'e', 'West': 'w'}
        
        hands = hand_data.get('hands', {})
        if not hands:
            # Fallback if the dict structure is flattened
            hands = hand_data 
            
        for direction, url_key in compass_map.items():
            suits = hands.get(direction, [])
            if suits:
                # Join ['AK', 'QJ', 'T9', '87'] -> "AKQJT987" (No spaces/dots for standard lin-style)
                # Actually BBO often wants standard PBN-ish or LIN style. 
                # Simplest BBO format is just the full string: "SAKHQD..."
                # But handviewer.html often accepts just the string of cards if passed cleanly.
                # Let's try the safer "SpadesHeartsDiamondsClubs" concatenation logic.
                
                # Check if suits are full strings "SAK..." or just "AK..."
                # Our Parser output is just "AK..." (clean ranks)
                
                # BBO Handviewer param structure: s=skqjhkqjdkqjckqj (Spades, Hearts, Diamonds, Clubs)
                joined_hand = f"s{suits[0]}h{suits[1]}d{suits[2]}c{suits[3]}"
                params[url_key] = joined_hand

        # 2. Dealer & Vul
        # d: n, s, e, w
        # v: n (none), b (both/all), e (ew), n (ns - wait, ns is usually 's' or 'n'?)
        # BBO codes: v=n (None), v=b (Both), v=e (EW), v=s (NS)
        
        dealer_map = {'N': 'n', 'S': 's', 'E': 'e', 'W': 'w'}
        params['d'] = dealer_map.get(hand_data.get('dealer', 'N'), 'n')
        
        vul_raw = hand_data.get('vulnerability', 'None').lower()
        vul_code = 'n'
        if 'all' in vul_raw or 'both' in vul_raw: vul_code = 'b'
        elif 'ew' in vul_raw: vul_code = 'e'
        elif 'ns' in vul_raw: vul_code = 's'
        params['v'] = vul_code
        
        # 3. Construct Query
        query_string = urllib.parse.urlencode(params)
        return f"{HandViewer.BASE_URL}?{query_string}"

if __name__ == "__main__":
    # Test
    test_hand = {
        "dealer": "N",
        "vulnerability": "None",
        "hands": {
            "North": ["AK", "QJ", "T9", "87"],
            "South": ["23", "45", "65", "43"],
            "East":  ["", "", "", ""],
            "West":  ["", "", "", ""]
        }
    }
    print(HandViewer.generate_url(test_hand))