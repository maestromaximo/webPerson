def classify_transaction_simple(entry, set_misc=False):
    description = entry.message.lower()

    # Define keywords for each category
    food_keywords = ['metro', 'freshco', 'shoppers', 'nofrills', 'food basic', 'food', 'eats', 'takeout']
    transport_keywords = ['uber', 'ubertrip','presto', 'taxi']
    insurance_keywords = ['belair']
    entertainment_keywords = ['indigo']

    # Check if any keyword is in the description
    if any(keyword in description for keyword in food_keywords):
        return 'food'
    elif any(keyword in description for keyword in transport_keywords):
        return 'transport'
    elif any(keyword in description for keyword in insurance_keywords):
        return 'insurance'
    elif any(keyword in description for keyword in entertainment_keywords):
        return 'entertainment'
    if set_misc:
        return 'miscellaneous'
    else:
        return None