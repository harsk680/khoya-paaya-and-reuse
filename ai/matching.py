from datetime import datetime


def calculate_match_score(lost_item, found_item):
    score = 0

    # 1. Category match = 30 points
    if lost_item.category.lower() == found_item.category.lower():
        score += 30

    # 2. Title similarity = 30 points
    lost_title = lost_item.title.lower()
    found_title = found_item.title.lower()

    if lost_title == found_title:
        score += 30
    elif lost_title in found_title or found_title in lost_title:
        score += 20

    # 3. Location match = 20 points
    if lost_item.location.lower() == found_item.location.lower():
        score += 20

    # 4. Date closeness = 20 points
    if lost_item.item_date and found_item.item_date:
        difference = abs(
            (lost_item.item_date - found_item.item_date).total_seconds()
        )

        difference_days = difference / (24 * 60 * 60)

        if difference_days <= 1:
            score += 20
        elif difference_days <= 3:
            score += 10

    return score