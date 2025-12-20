import re
from typing import Dict, List, Optional

class BridgeParser:
    """
    Parses LIN files from BBO to extract 'Ground Truth' data.
    """

    def parse_lin_content(self, filename: str, content: str) -> Dict:
        try:
            # 1. Extract Metadata
            board_num = self._extract_tag(content, 'ah') or "Unknown"
            dealer_code = self._extract_dealer(content)
            vul_code = self._extract_tag(content, 'sv') or "0"
            
            # NEW: Extract Player Names
            # pn|South,West,North,East|
            player_names = self._extract_players(content)

            # 2. Extract and Complete Hands
            md_match = re.search(r"md\|(\d)(.*?)\|", content)
            if not md_match:
                raise ValueError("No 'md' (Deal) tag found.")

            dealer_digit = int(md_match.group(1))
            hands_raw = md_match.group(2).split(',')
            compass_map = self._get_compass_rotation(dealer_digit)
            
            full_deal = {}
            all_known_cards = set()

            for i, raw_hand_str in enumerate(hands_raw):
                if i < 4 and raw_hand_str:
                    direction = compass_map[i]
                    parsed_hand = self._parse_hand_string(raw_hand_str)
                    stats = self._calculate_stats(parsed_hand)
                    full_deal[direction] = {
                        "name": player_names.get(direction, "Unknown"), # NEW
                        "cards": parsed_hand,
                        "stats": stats,
                        "raw": raw_hand_str
                    }
                    for suit in parsed_hand:
                        for rank in parsed_hand[suit]:
                            all_known_cards.add(f"{suit}{rank}")

            missing_direction = None
            for direction in ["South", "West", "North", "East"]:
                if direction not in full_deal:
                    missing_direction = direction
                    break
            
            if missing_direction:
                deduced_hand = self._deduct_missing_hand(all_known_cards)
                stats = self._calculate_stats(deduced_hand)
                full_deal[missing_direction] = {
                    "name": player_names.get(missing_direction, "Unknown"), # NEW
                    "cards": deduced_hand,
                    "stats": stats,
                    "raw": "Calculated"
                }

            # 3. Extract Auction & Play
            auction = self._extract_auction(content)
            play = self._extract_play(content)

            return {
                "file": filename,
                "board": board_num,
                "dealer": self._code_to_dealer(dealer_digit),
                "vulnerability": self._code_to_vul(vul_code),
                "hands": full_deal,
                "auction": auction,
                "play": play,
                "raw_lin": content.replace('\n', '').strip() # NEW: For Handviewer
            }

        except Exception as e:
            return {"file": filename, "error": str(e)}

    # --- HELPER FUNCTIONS ---

    def _extract_players(self, content):
        """Extracts names from pn|S,W,N,E| tag."""
        match = re.search(r"pn\|(.*?)\|", content)
        names = {}
        if match:
            # BBO Standard: South, West, North, East
            raw_names = match.group(1).split(',')
            dirs = ["South", "West", "North", "East"]
            for i, name in enumerate(raw_names):
                if i < 4:
                    names[dirs[i]] = name
        return names

    def _get_compass_rotation(self, dealer_digit):
        if dealer_digit == 1: return ["South", "West", "North", "East"]
        if dealer_digit == 2: return ["West", "North", "East", "South"]
        if dealer_digit == 3: return ["North", "East", "South", "West"]
        if dealer_digit == 4: return ["East", "South", "West", "North"]
        return ["South", "West", "North", "East"]

    def _parse_hand_string(self, hand_str):
        suits = {'S': [], 'H': [], 'D': [], 'C': []}
        current_suit = None
        for char in hand_str:
            if char in suits:
                current_suit = char
            elif current_suit:
                suits[current_suit].append(char)
        return suits

    def _calculate_stats(self, hand_dict):
        hcp = 0
        dist = []
        values = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
        for suit in ['S', 'H', 'D', 'C']:
            cards = hand_dict.get(suit, [])
            dist.append(len(cards))
            for card in cards:
                hcp += values.get(card, 0)
        return {
            "hcp": hcp,
            "distribution_counts": dist,
            "distribution_str": "-".join(map(str, dist))
        }

    def _deduct_missing_hand(self, known_cards_set):
        full_deck = []
        ranks = "AKQJT98765432"
        for suit in ['S', 'H', 'D', 'C']:
            for rank in ranks:
                full_deck.append(f"{suit}{rank}")
        missing_cards = {'S': [], 'H': [], 'D': [], 'C': []}
        for card in full_deck:
            if card not in known_cards_set:
                missing_cards[card[0]].append(card[1])
        return missing_cards

    def _extract_auction(self, content):
        bids = re.findall(r"mb\|(.*?)\|", content)
        return [b for b in bids if b]

    def _extract_play(self, content):
        plays = re.findall(r"pc\|(.*?)\|", content)
        return [p for p in plays if p]

    def _extract_tag(self, content, tag):
        match = re.search(rf"{tag}\|(.*?)\|", content)
        return match.group(1) if match else None
        
    def _extract_dealer(self, content):
        match = re.search(r"md\|(\d)", content)
        return int(match.group(1)) if match else 1

    def _code_to_dealer(self, code):
        mapping = {1: "South", 2: "West", 3: "North", 4: "East"}
        return mapping.get(code, "Unknown")
        
    def _code_to_vul(self, code):
        mapping = {'0': 'None', 'b': 'Both', 'n': 'NS', 'e': 'EW'}
        return mapping.get(code, "None")