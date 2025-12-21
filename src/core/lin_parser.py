import re
from typing import Dict, List

class LINParser:
    """
    Parses Bridge Base Online (BBO) .lin files into structured JSON data.
    """
    
    def parse_single_hand(self, raw_lin_data: str, filename: str = "Unknown") -> Dict:
        """
        Main entry point: Converts a raw LIN string into a clean dictionary.
        """
        # 1. Extract Basic Metadata
        data = {
            "board": filename.replace('_', ' ').replace('.lin', ''),
            "dealer": self._get_dealer(raw_lin_data),
            "vulnerability": self._get_vuln(raw_lin_data),
            "contract": self._get_contract(raw_lin_data), # Added specifically for Red Teaming
            "auction": self._parse_auction(raw_lin_data),
            "play": self._parse_play(raw_lin_data),
            "hands": self._parse_hands(raw_lin_data),
            "raw_lin": raw_lin_data
        }
        return data

    def _get_dealer(self, lin: str) -> str:
        # LIN format: 'md|1...' where 1=South, 2=West, 3=North, 4=East
        match = re.search(r'md\|([1-4])', lin)
        if match:
            map_dealer = {'1': 'South', '2': 'West', '3': 'North', '4': 'East'}
            return map_dealer.get(match.group(1), 'Unknown')
        return 'Unknown'

    def _get_vuln(self, lin: str) -> str:
        # LIN format: 'sv|...' where o=None, n=NS, e=EW, b=Both
        match = re.search(r'sv\|([oneb])', lin)
        if match:
            map_vuln = {'o': 'None', 'n': 'N/S', 'e': 'E/W', 'b': 'Both'}
            return map_vuln.get(match.group(1), 'None')
        return 'None'
    
    def _get_contract(self, lin: str) -> str:
        # LIN format for contract often appears in 'mb' (bids). 
        # This is a basic extractor for the final contract.
        # We rely on the auction parser for detailed sequences, 
        # but this helper finds the last significant bid.
        bids = re.findall(r'mb\|([^|]+)\|', lin)
        valid_bids = [b for b in bids if b.lower() not in ['p', 'pass', 'd', 'dbl', 'r', 'rdbl', 'an']]
        if valid_bids:
            return valid_bids[-1] # The last bid made
        return "Pass"

    def _parse_auction(self, lin: str) -> List[str]:
        # Extract all 'mb|...|' tags
        raw_bids = re.findall(r'mb\|([^|]+)\|', lin)
        # Clean them up (remove alerts 'an', etc.)
        clean_bids = [b for b in raw_bids if b != 'an']
        return clean_bids

    def _parse_play(self, lin: str) -> List[str]:
        # Extract all 'pc|...|' tags (Play Card)
        cards = re.findall(r'pc\|([^|]+)\|', lin)
        return cards

    def _parse_hands(self, lin: str) -> Dict:
        # LIN Encode: md|1S...H...D...C...,...|
        # 1=South hand, then West, North, East comma separated.
        match = re.search(r'md\|[1-4]([^|]+)\|', lin)
        if not match:
            return {}

        raw_hands = match.group(1).split(',')
        
        # Helper to convert "SKQJ..." to separate suits
        def parse_hand_string(h_str):
            suits = {'S': '', 'H': '', 'D': '', 'C': ''}
            current_suit = ''
            for char in h_str:
                if char in suits:
                    current_suit = char
                else:
                    suits[current_suit] += char
            
            # Calculate HCP
            hcp = 0
            for s in suits.values():
                for card in s:
                    if card == 'A': hcp += 4
                    elif card == 'K': hcp += 3
                    elif card == 'Q': hcp += 2
                    elif card == 'J': hcp += 1
            
            # Dist string
            dist = f"{len(suits['S'])}={len(suits['H'])}={len(suits['D'])}={len(suits['C'])}"
            return {"cards": suits, "hcp": hcp, "distribution_str": dist}

        # Map properly based on Dealer (LIN is quirky here, but let's assume standard rotation order)
        # If dealer is 1 (South), the string is S,W,N,E
        # Note: BBO LINs often only give 3 hands and rely on logic for the 4th, 
        # but modern files usually include all. We will implement basic parsing here.
        
        hands_dict = {
            "South": {"name": "South", "stats": parse_hand_string(raw_hands[0] if len(raw_hands) > 0 else "")},
            "West":  {"name": "West",  "stats": parse_hand_string(raw_hands[1] if len(raw_hands) > 1 else "")},
            "North": {"name": "North", "stats": parse_hand_string(raw_hands[2] if len(raw_hands) > 2 else "")},
            "East":  {"name": "East",  "stats": parse_hand_string(raw_hands[3] if len(raw_hands) > 3 else "")},
        }
        
        # Try to find player names 'pn|South,West,North,East|'
        name_match = re.search(r'pn\|([^|]+)\|', lin)
        if name_match:
            names = name_match.group(1).split(',')
            if len(names) >= 4:
                hands_dict["South"]["name"] = names[0]
                hands_dict["West"]["name"] = names[1]
                hands_dict["North"]["name"] = names[2]
                hands_dict["East"]["name"] = names[3]

        return hands_dict