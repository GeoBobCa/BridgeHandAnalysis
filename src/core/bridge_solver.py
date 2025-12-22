import json
from endplay.types import Deal
from endplay.dds import calc_dd_table

class BridgeSolver:
    def solve(self, hands_data):
        pbn_string = "Unknown"
        try:
            # 1. Convert JSON hands to PBN string format
            pbn_parts = []
            order = ['North', 'East', 'South', 'West']
            total_cards = 0
            
            for seat in order:
                hand = hands_data.get(seat, {}).get('stats', {}).get('cards', {})
                
                def clean_suit(cards_str):
                    if not cards_str: return ""
                    return cards_str.replace("10", "T").replace(" ", "")

                s = clean_suit(hand.get('S', ''))
                h = clean_suit(hand.get('H', ''))
                d = clean_suit(hand.get('D', ''))
                c = clean_suit(hand.get('C', ''))
                
                total_cards += len(s) + len(h) + len(d) + len(c)
                pbn_parts.append(f"{s}.{h}.{d}.{c}")
            
            pbn_string = "N:" + " ".join(pbn_parts)
            
            if total_cards != 52:
                print(f"⚠️ DDS Skip: Deck has {total_cards} cards. PBN: {pbn_string}")
                return None

            # 2. Solve
            deal = Deal(pbn_string)
            table = calc_dd_table(deal)
            
            # 3. Escape Hatch: Convert to List
            # raw_data structure is 5 rows (Suits) x 4 columns (Players)
            raw_data = table.to_list()
            
            results = {"N": {}, "S": {}, "E": {}, "W": {}}
            strains = ["C", "D", "H", "S", "NT"]
            
            for i, strain in enumerate(strains):
                row = raw_data[i]
                
                # CORRECTED MAPPING (NESW Standard)
                # 0 = North
                # 1 = East  <-- This index belongs to East
                # 2 = South <-- This index belongs to South
                # 3 = West
                
                results['N'][strain] = row[0]
                results['E'][strain] = row[1] # Fixed: Index 1 is East
                results['S'][strain] = row[2] # Fixed: Index 2 is South
                results['W'][strain] = row[3]
                
            return results

        except Exception as e:
            print(f"❌ Solver Error: {e} | Bad PBN: {pbn_string}")
            return None

if __name__ == "__main__":
    pass