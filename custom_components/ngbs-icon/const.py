from textwrap import dedent
print(dedent('''
DOMAIN = "ngbs_icon"
PLATFORMS = ["climate"]

DEFAULT_SCAN_INTERVAL = 300  # seconds
SESSION_REFRESH_INTERVAL = 3600  # seconds  # retained for possible future use

# Preset modes for Eco/Manual
PRESET_ECO = "eco"
PRESET_COMFORT = "comfort"
PRESET_NONE = "none"

# CE (Mode) values based on observed platform behavior:
# 0 => run/auto, 1 => off, 2 => eco
CE_AUTO_RUN = 0
CE_OFF = 1
CE_ECO = 2
'''))