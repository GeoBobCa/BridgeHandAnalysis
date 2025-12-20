import os
from src.core.lin_parser import BridgeParser

# 1. Setup
parser = BridgeParser()
data_folder = "data/lin_files" # <--- MAKE SURE YOUR FILES ARE HERE OR UPDATE PATH

# 2. Grab the first file you find
lin_files = [f for f in os.listdir(".") if f.endswith(".lin")]

if not lin_files:
    print("No .lin files found in root. Please place one here to test.")
else:
    test_file = lin_files[0]
    print(f"Testing Parser on: {test_file}")
    
    with open(test_file, 'r') as f:
        content = f.read()
        
    # 3. Parse
    result = parser.parse_lin_content(test_file, content)
    
    # 4. Print the 'Zero-Trust' Facts
    print("-" * 30)
    print(f"Board: {result.get('board')}")
    print(f"Dealer: {result.get('dealer')}")
    print("-" * 30)
    
    hands = result.get('hands', {})
    for direction in ["North", "South", "East", "West"]:
        data = hands.get(direction, {})
        stats = data.get('stats', {})
        print(f"{direction.ljust(6)} | HCP: {stats.get('hcp')} | Dist: {stats.get('distribution_str')}")
    
    print("-" * 30)
    print(f"Auction Start: {result.get('auction')[:5]} ...")