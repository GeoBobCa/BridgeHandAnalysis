import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from loguru import logger

class BridgeParser:
    """
    Parses .lin (BBO) and .pbn files into a standardized dictionary format.
    """

    # Map LIN dealer numbers to Compass directions
    LIN_DEALER_MAP = {'1': 'S', '2': 'W', '3': 'N', '4': 'E'}
    
    # Standard 52 card deck for validation/deduction
    FULL_DECK = set([
        f"{r}{s}" for s in "SHDC" for r in "23456789TJQKA"
    ])

    @staticmethod
    def parse_file(file_path: Path) -> List[Dict]:
        """
        Auto-detects file type and dispatches to the correct parser.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []

        suffix = file_path.suffix.lower()
        if suffix == '.lin':
            return BridgeParser.parse_lin(file_path)
        elif suffix == '.pbn':
            return BridgeParser.parse_pbn(file_path)
        else:
            logger.warning(f"Unsupported file format: {suffix}")
            return []

    @staticmethod
    def parse_lin(file_path: Path) -> List[Dict]:
        """
        Parses a Bridge Base Online .lin file.
        Handling: Extracts 'md' (Make Deal), 'qx' (Board ID), 'pn' (Players).
        Logic: LIN hands are often S,W,N (East implied). We calculate East.
        """
        hands_data = []
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read LIN file {file_path}: {e}")
            return []

        # Split file into "lines" (LIN files are pipe-delimited records)
        # We assume a new board usually starts with 'qx|' (Board ID) or is a separate line
        # Simple approach: Split by 'qx|' which marks a new board in Vugraph files
        segments = content.split('qx|')
        
        # If no qx tags, try splitting by newline if it's a bulk export
        if len(segments) < 2 and '\n' in content:
            segments = content.split('\n')

        for segment in segments:
            if 'md|' not in segment:
                continue

            try:
                # Extract Board ID (o1 = open room board 1, c1 = closed room)
                board_id = "Unknown"
                if segment.startswith('o') or segment.startswith('c'):
                     board_id = re.match(r'([oc]\d+)', segment).group(1)

                # Extract Players 'pn|South,West,North,East|'
                players = ["Unknown"] * 4
                pn_match = re.search(r'pn\|([^|]+)\|', segment)
                if pn_match:
                    p_str = pn_match.group(1).split(',')
                    players = [p.strip() for p in p_str] + ["Unknown"] * (4 - len(p_str))

                # Extract Deal 'md|3SA...|'
                # Format: md|DealerDigits(1-4)SouthHand,WestHand,NorthHand|
                md_match = re.search(r'md\|([1-4])([^|]+)\|', segment)
                if not md_match:
                    continue

                dealer_num = md_match.group(1)
                cards_str = md_match.group(2)
                
                deal_dict = BridgeParser._process_lin_hands(dealer_num, cards_str)
                
                # Extract Auction (bidding)
                # LIN auction is usually 'mb|1N|mb|P|...'
                auction = []
                bids = re.findall(r'mb\|([^|]+)\|', segment)
                # Cleanup: remove alerts 'an|...' and explanations
                # For now, just simplistic capture of bids
                for bid in bids:
                    auction.append(bid)

                # Construct Final Object
                hand_record = {
                    "source_file": file_path.name,
                    "board_id": board_id,
                    "dealer": BridgeParser.LIN_DEALER_MAP.get(dealer_num, 'N'),
                    "vulnerability": BridgeParser._determine_vul(board_id), # Helper needed
                    "players": {
                        "South": players[0], "West": players[1], 
                        "North": players[2], "East": players[3]
                    },
                    "hands": deal_dict,
                    "auction": auction,
                    "original_string": segment[:100] + "..." # Snippet for debug
                }
                hands_data.append(hand_record)

            except Exception as e:
                logger.warning(f"Error parsing LIN segment in {file_path.name}: {e}")
                continue

        logger.info(f"Parsed {len(hands_data)} hands from {file_path.name}")
        return hands_data

    @staticmethod
    def _process_lin_hands(dealer_digit: str, cards_str: str) -> Dict[str, List[str]]:
        """
        Converts LIN 'S...H...D...C...,...' string into full 4-hand dictionary.
        LIN order is ALWAYS: South, West, North, (East often missing).
        """
        # 1. Split the hands (comma separated)
        # LIN format removes the 'S', 'H' etc prefixes sometimes, but usually looks like:
        # SAJ5... or just AJ5...
        # Standard BBO: S...H...D...C..., S...H...D...C...
        
        raw_hands = cards_str.split(',')
        
        # We need 4 hands. If < 4, we must deduce the remaining cards.
        parsed_hands = {}
        directions = ['South', 'West', 'North'] # LIN order
        
        used_cards = set()

        for idx, raw_hand in enumerate(raw_hands):
            if idx >= 3: break # Should only be S, W, N
            
            # Extract suits using Regex. 
            # Note: LIN uses S, H, D, C as delimiters. 
            # Example: SAJTH432... -> Spades: AJT, Hearts: 432...
            
            # Helper to extract specific suit holdings
            def get_suit(suit_char, text):
                pattern = f"{suit_char}([^SHDC]*)"
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
                return ""

            # Standardize LIN sometimes omitting the first 'S' if it's implicit? 
            # Safer to ensure capital letters.
            raw_hand = raw_hand.upper()
            
            # If the string doesn't start with a suit letter, it's messy. 
            # Assuming standard BBO LIN export for now.
            
            spades = get_suit('S', raw_hand)
            hearts = get_suit('H', raw_hand)
            diamonds = get_suit('D', raw_hand)
            clubs = get_suit('C', raw_hand)
            
            # Store full cards for Used List (e.g., "SA", "SK") to calculate East
            for r in spades: used_cards.add(f"S{r}")
            for r in hearts: used_cards.add(f"H{r}")
            for r in diamonds: used_cards.add(f"D{r}")
            for r in clubs: used_cards.add(f"C{r}")

            parsed_hands[directions[idx]] = [spades, hearts, diamonds, clubs]

        # Calculate East (The missing cards)
        remaining = BridgeParser.FULL_DECK - used_cards
        e_spades, e_hearts, e_diamonds, e_clubs = [], [], [], []
        
        for card in remaining:
            suit, rank = card[0], card[1]
            if suit == 'S': e_spades.append(rank)
            elif suit == 'H': e_hearts.append(rank)
            elif suit == 'D': e_diamonds.append(rank)
            elif suit == 'C': e_clubs.append(rank)

        # Sort ranks (high to low) for consistency (AKQ...)
        rank_order = "AKQJT98765432"
        def sort_hand(cards):
            return sorted(cards, key=lambda x: rank_order.index(x) if x in rank_order else 99)

        parsed_hands['East'] = [
            "".join(sort_hand(e_spades)),
            "".join(sort_hand(e_hearts)),
            "".join(sort_hand(e_diamonds)),
            "".join(sort_hand(e_clubs))
        ]
        
        # Ensure S, W, N are also sorted
        for d in directions:
            if d in parsed_hands:
                h = parsed_hands[d]
                parsed_hands[d] = ["".join(sort_hand(s)) for s in h]

        return parsed_hands

    @staticmethod
    def _determine_vul(board_id_str: str) -> str:
        """
        Simple heuristic to guess vulnerability from board number.
        Standard Bridge Pattern:
        1: None, 2: NS, 3: EW, 4: All
        5: NS, 6: EW, 7: All, 8: None ...
        """
        try:
            # Extract number from "o1", "12", "Board 1"
            num_match = re.search(r'\d+', board_id_str)
            if not num_match: return "None"
            
            bn = int(num_match.group(0))
            mod = (bn - 1) % 16
            
            vul_pattern = [
                "None", "NS", "EW", "All",
                "NS", "EW", "All", "None",
                "EW", "All", "None", "NS",
                "All", "None", "NS", "EW"
            ]
            return vul_pattern[mod]
        except:
            return "None"

    @staticmethod
    def parse_pbn(file_path: Path) -> List[Dict]:
        """
        Basic PBN parser. Looks for [Deal "N:shdc..."] tags.
        """
        # NOTE: This is a simplified implementation. 
        # Robust PBN parsing is complex; this handles the standard 'Deal' tag.
        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return []
            
        deals = []
        # Regex to find Deal tags: [Deal "N:AK.Q.J.T ..."]
        matches = re.finditer(r'\[Deal "(N|S|E|W):([^"]+)"\]', content)
        
        for m in matches:
            dealer_char = m.group(1)
            hands_str = m.group(2) # "AK.Q.J.T 43.5.6.7 ..."
            
            # PBN hands are space separated. Order is clockwise from dealer.
            hand_strings = hands_str.split(' ')
            
            compass = ['N', 'E', 'S', 'W']
            start_idx = compass.index(dealer_char)
            
            deal_dict = {}
            for i, h_str in enumerate(hand_strings):
                if i >= 4: break
                direction = compass[(start_idx + i) % 4]
                # PBN suits are dot separated: S.H.D.C
                suits = h_str.split('.')
                # Convert to full names
                dir_name = {'N':'North', 'S':'South', 'E':'East', 'W':'West'}[direction]
                deal_dict[dir_name] = suits if len(suits) == 4 else [[],[],[],[]]

            deals.append({
                "source_file": file_path.name,
                "dealer": dealer_char,
                "hands": deal_dict,
                "vulnerability": "Unknown" # Need to parse [Vulnerable "NS"] tag separately
            })
            
        logger.info(f"Parsed {len(deals)} hands from {file_path.name} (PBN)")
        return deals

if __name__ == "__main__":
    # Quick Test
    print("Parser Module Loaded. Run via main.py or pytest.")