from typing import Dict

class BridgeMath:
    """
    Performs deterministic calculations (HCP, Distribution) 
    so the AI doesn't have to guess.
    """
    
    def calculate_stats(self, hand_data: Dict) -> Dict:
        """
        Aggregates math stats for all 4 hands.
        """
        results = {}
        
        # Iterate through North, South, East, West
        for seat, details in hand_data.get('hands', {}).items():
            stats = details.get('stats', {})
            
            # Extract what we already parsed in LINParser
            hcp = stats.get('hcp', 0)
            total_points = stats.get('total_points', 0)
            dist_str = stats.get('distribution_str', 'Unknown')
            
            results[seat] = {
                "hcp": hcp,
                "total_points": total_points,
                "distribution": dist_str,
                "is_balanced": self._check_balanced(dist_str)
            }
            
        return results

    def _check_balanced(self, dist_str: str) -> bool:
        """
        Returns True if the hand is 4-3-3-3, 4-4-3-2, or 5-3-3-2.
        Input format example: "5=3=3=2"
        """
        try:
            # Parse "5=3=3=2" into [5, 3, 3, 2]
            counts = [int(x) for x in dist_str.split('=')]
            counts.sort(reverse=True) # Sort to compare against standard shapes
            
            # Standard balanced shapes (sorted)
            # 4-3-3-3 -> [4, 3, 3, 3]
            # 4-4-3-2 -> [4, 4, 3, 2]
            # 5-3-3-2 -> [5, 3, 3, 2]
            
            if counts in [[4,3,3,3], [4,4,3,2], [5,3,3,2]]:
                return True
            return False
            
        except:
            return False