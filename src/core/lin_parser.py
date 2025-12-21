import re
from typing import Dict, List, Set

class LINParser:
    """
    Parses LIN files, infers missing hands, and calculates Bridge stats.
    """
    
    # Standard Bridge Order for sorting
    CARD_RANKS = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
    SUITS = ['S', 'H', 'D', 'C']

    def parse_single_hand(self, raw_lin_data: str, filename: str = "Unknown") -> Dict:
        board_name = filename.replace('_', ' ').replace('.lin', '')
        ah_match = re.search(r'ah\|([^|]+)\|', raw_lin_data)
        if ah_match:
            board_name = ah_match.group(1).strip()

        # Parse Hands
        hands_dict = self._parse_hands(raw_lin_data)

        data = {
            "board": board_name,
            "dealer": self._get_dealer(raw_lin_data),
            "vulnerability": self._get_vuln(raw_lin_data),
            "contract": self._get_contract(raw_lin_data),
            "auction": self._parse_auction(raw_lin_data),
            "play": self._parse_play(raw_lin_data),
            "hands": hands_dict,
            "raw_lin": raw_lin_data
        }
        return data

    def _get_dealer(self, lin: str) -> str:
        match = re.search(r'md\|([1-4])', lin)
        if match:
            map_dealer = {'1': 'South', '2': 'West', '3': 'North', '4': 'East'}
            return map_dealer.get(match.group(1), 'Unknown')
        return 'Unknown'

    def _get_vuln(self, lin: str) -> str:
        match = re.search(r'sv\|([oneb])', lin)
        if match:
            map_vuln = {'o': 'None', 'n': 'N/S', 'e': 'E/W', 'b': 'Both'}
            return map_vuln.get(match.group(1), 'None')
        return 'None'
    
    def _get_contract(self, lin: str) -> str:
        bids = re.findall(r'mb\|([^|]+)\|', lin)
        valid_bids = [b for b in bids if b.lower() not in ['p', 'pass', 'd', 'dbl', 'r', 'rdbl', 'an']]
        return valid_bids[-1] if valid_bids else "Pass"

    def _parse_auction(self, lin: str) -> List[str]:
        raw_bids = re.findall(r'mb\|([^|]+)\|', lin)
        return [b for b in raw_bids if b != 'an']

    def _parse_play(self, lin: str) -> List[str]:
        return re.findall(r'pc\|([^|]+)\|', lin)

    def _parse_hands(self, lin: str) -> Dict:
        # Extract the 'md' tag
        match = re.search(r'md\|[1-4]([^|]+)\|', lin)
        if not match:
            return {}

        # Split hands. Note: Last comma might be missing or trailing.
        # Format: S...H...D...C..., S...H... etc
        raw_hands_list = [h for h in match.group(1).split(',') if h]

        parsed_hands = {}
        
        # 1. Parse the known hands (South, West, North)
        # BBO 'md|1...' implies order: South, West, North, East
        seat_order = ["South", "West", "North", "East"]
        
        known_cards = set()

        for i in range(len(raw_hands_list)):
            seat = seat_order[i]
            hand_obj = self._parse_single_hand_string(raw_hands_list[i])
            parsed_hands[seat] = hand_obj
            
            # Track all known cards to infer the 4th hand later
            for s in self.SUITS:
                for rank in hand_obj['stats']['cards'][s]:
                    known_cards.add(s + rank)

        # 2. Check for missing East (or any missing hand)
        if len(parsed_hands) < 4:
            missing_seat = seat_order[len(parsed_hands)] # Usually East
            inferred_hand = self._infer_missing_hand(known_cards)
            parsed_hands[missing_seat] = inferred_hand

        # 3. Add Player Names
        name_match = re.search(r'pn\|([^|]+)\|', lin)
        if name_match:
            names = name_match.group(1).split(',')
            for i, seat in enumerate(seat_order):
                if seat in parsed_hands and i < len(names):
                    parsed_hands[seat]["name"] = names[i]
                elif seat in parsed_hands:
                    parsed_hands[seat]["name"] = seat # Default to seat name

        return parsed_hands

    def _parse_single_hand_string(self, h_str: str) -> Dict:
        suits = {'S': [], 'H': [], 'D': [], 'C': []}
        current_suit = ''
        
        # Parse characters
        for char in h_str:
            if char in suits:
                current_suit = char
            else:
                suits[current_suit].append(char)
        
        # Sort suits High to Low (A -> 2)
        for s in suits:
            suits[s].sort(key=lambda x: self.CARD_RANKS.get(x, 0), reverse=True)
            # Rejoin list to string for display
            suits[s] = "".join(suits[s])

        # Calculate Stats
        hcp = self._calculate_hcp(suits)
        total_points = self._calculate_total_points(suits, hcp)
        dist_str = f"{len(suits['S'])}={len(suits['H'])}={len(suits['D'])}={len(suits['C'])}"

        return {
            "stats": {
                "cards": suits, 
                "hcp": hcp, 
                "total_points": total_points,
                "distribution_str": dist_str
            }
        }

    def _infer_missing_hand(self, known_cards: Set[str]) -> Dict:
        # Create full deck
        full_deck = set()
        for s in self.SUITS:
            for r in self.CARD_RANKS.keys():
                full_deck.add(s + r)
        
        # Subtract known
        missing_cards_set = full_deck - known_cards
        
        # Build structure
        suits = {'S': [], 'H': [], 'D': [], 'C': []}
        for card in missing_cards_set:
            suit = card[0]
            rank = card[1]
            suits[suit].append(rank)
            
        # Sort
        for s in suits:
            suits[s].sort(key=lambda x: self.CARD_RANKS.get(x, 0), reverse=True)
            suits[s] = "".join(suits[s])
            
        hcp = self._calculate_hcp(suits)
        total_points = self._calculate_total_points(suits, hcp)
        dist_str = f"{len(suits['S'])}={len(suits['H'])}={len(suits['D'])}={len(suits['C'])}"

        return {
            "name": "East", # Default
            "stats": {
                "cards": suits, 
                "hcp": hcp, 
                "total_points": total_points,
                "distribution_str": dist_str
            }
        }

    def _calculate_hcp(self, suits: Dict) -> int:
        hcp = 0
        for s in suits.values():
            for card in s:
                hcp += self.CARD_RANKS.get(card, 0) - 10 if self.CARD_RANKS.get(card, 0) > 10 else 0
        return hcp

    def _calculate_total_points(self, suits: Dict, hcp: int) -> int:
        # Standard Valuation: HCP + Length Points
        # Add 1 point for every card over 4 in a suit
        length_points = 0
        for s in suits.values():
            if len(s) > 4:
                length_points += (len(s) - 4)
        return hcp + length_points