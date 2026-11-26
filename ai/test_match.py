from matching import calculate_match_score


class Item:
    def __init__(self, title, category, location, item_date):
        self.title = title
        self.category = category
        self.location = location
        self.item_date = item_date


lost_item = Item(
    "Black Wallet",
    "Wallet",
    "Central Library",
    None
)

found_item = Item(
    "Black Wallet",
    "Wallet",
    "Central Library",
    None
)

score = calculate_match_score(
    lost_item,
    found_item
)

print("Match Score:", score)