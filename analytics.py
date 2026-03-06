import csv
from collections import defaultdict

def get_bad_food_by_day():
    bad_count = defaultdict(int)

    with open("data/sample_feedback.csv", newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["rating"] in ["Poor", "Average"]:
                bad_count[row["day"]] += 1

    return bad_count
