def clean_sensor_readings(readings):
    cleaned = []

    for item in readings:
        try:
            val = float(item)
            # Ignore negative numbers
            if val >= 0:
                # Cap the value at 500.0 and add to list
                cleaned.append(min(val, 500.0))
        except (ValueError, TypeError):
            # Skip invalid types (None, strings like "abc")
            pass

    return cleaned
