from typing import List, Dict, Tuple

class BridgeMath:
    """
    Implements Audrey Grant's 'Better Bridge' evaluation methods.
    Strictly deterministic. No AI involved.
    """

    # TABLE A: High Card Points
    HCP_VALUES = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}

    @staticmethod
    def calculate_hcp(hand: List[str]) -> int:
        """
        Calculates standard High Card Points (4-3-2-1).
        Input: List of 4 strings representing suits [Spades, Hearts, Diamonds, Clubs]
        Example: ['AK95', 'Q2', '...', '...']
        """
        total = 0
        for suit in hand:
            # Uppercase ensures safety if parser missed it
            for card in suit.upper():
                total += BridgeMath.HCP_VALUES.get(card, 0)
        return total

    @staticmethod
    def calculate_length_points(hand: List[str]) -> int:
        """
        Audrey Grant Rule for Opening Bids & No Trump:
        Add 1 point for a 5-card suit, 2 for 6-card, 3 for 7-card, etc.
        """
        points = 0
        for suit in hand:
            length = len(suit)
            if length >= 5:
                points += (length - 4)
        return points

    @staticmethod
    def calculate_support_points(hand: List[str], trump_index: int = -1) -> int:
        """
        Audrey Grant Rule for RESPONDER raising partner's suit.
        Shortness adds value:
        - Void: 5 points
        - Singleton: 3 points
        - Doubleton: 1 point
        
        Args:
            trump_index: 0=Spades, 1=Hearts, 2=Diamonds, 3=Clubs.
                         (Used to ensure we don't count shortness IN the trump suit itself, 
                          though standard practice is just to count outside shortness).
        """
        points = 0
        for idx, suit in enumerate(hand):
            # Do not count distribution for the trump suit itself if specified
            if idx == trump_index:
                continue

            length = len(suit)
            if length == 0:   # Void
                points += 5
            elif length == 1: # Singleton
                points += 3
            elif length == 2: # Doubleton
                points += 1
        return points

    @staticmethod
    def evaluate_hand(hand: List[str]) -> Dict[str, int]:
        """
        Returns a comprehensive dictionary of all possible point counts.
        The UI or AI determines which one is relevant based on the auction context.
        """
        hcp = BridgeMath.calculate_hcp(hand)
        length_pts = BridgeMath.calculate_length_points(hand)
        support_pts = BridgeMath.calculate_support_points(hand)
        
        return {
            "hcp": hcp,
            "distribution_length": length_pts,
            "distribution_support": support_pts,
            "total_opener": hcp + length_pts,
            "total_dummy": hcp + support_pts, # If raising partner
            "pattern": [len(s) for s in hand] # e.g., [5, 3, 3, 2]
        }

    @staticmethod
    def get_distribution_string(hand: List[str]) -> str:
        """Helper to return shape like '5-3-3-2' sorted"""
        lengths = [len(s) for s in hand]
        # Standard bridge notation often sorts shape: 5-3-3-2
        lengths.sort(reverse=True)
        return "-".join(map(str, lengths))

# Quick Verification if run directly
if __name__ == "__main__":
    # Test Hand: Spades=AKJ92 (5), Hearts=Q2 (2), D=865 (3), C=74 (2)
    # HCP: A(4)+K(3)+J(1) + Q(2) = 10 HCP
    # Length: 5 Spades (+1) = 11 Total Opener
    # Support (if H is trump): Doubleton C(+1) = 11 Total Dummy
    
    test_hand = ["AKJ92", "Q2", "865", "74"]
    result = BridgeMath.evaluate_hand(test_hand)
    
    print(f"Hand: {test_hand}")
    print(f"HCP: {result['hcp']} (Expected 10)")
    print(f"Opener Total: {result['total_opener']} (Expected 11)")
    print(f"Dummy Total: {result['total_dummy']} (Expected 11)")