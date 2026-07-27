class Nord:
    polar_night_1 = "#2E3440"
    polar_night_2 = "#3B4252"
    polar_night_3 = "#434C5E"
    polar_night_4 = "#4C566A"

    snow_storm_1 = "#D8DEE9"
    snow_storm_2 = "#E5E9F0"
    snow_storm_3 = "#ECEFF4"

    frost_1 = "#8FBCBB"
    frost_2 = "#88C0D0"
    frost_3 = "#81A1C1"
    frost_4 = "#5E81AC"

    aurora_red    = "#BF616A"
    aurora_orange = "#D08770"
    aurora_yellow = "#EBCB8B"
    aurora_green  = "#A3BE8C"
    aurora_pink   = "#B48EAD"

    bg      = polar_night_1
    bg_alt  = polar_night_2
    bg_sel  = polar_night_3
    fg_dim  = polar_night_4
    fg      = snow_storm_1
    fg_bright = snow_storm_3

    ansi_colors = {
        '30': polar_night_1,   # black
        '31': aurora_red,      # red
        '32': aurora_green,    # green
        '33': aurora_yellow,   # yellow
        '34': frost_4,         # blue
        '35': aurora_pink,     # magenta
        '36': frost_1,         # cyan
        '37': snow_storm_1,    # white
        '90': polar_night_4,   # bright black
        '91': aurora_red,      # bright red
        '92': aurora_green,    # bright green
        '93': aurora_yellow,   # bright yellow
        '94': frost_3,         # bright blue
        '95': aurora_pink,     # bright magenta
        '96': frost_2,         # bright cyan
        '97': snow_storm_3,    # bright white
    }

    ansi_bg = {
        '40': polar_night_1,
        '41': aurora_red,
        '42': aurora_green,
        '43': aurora_yellow,
        '44': frost_4,
        '45': aurora_pink,
        '46': frost_1,
        '47': snow_storm_2,
    }

    terminal_name = "Nord Terminal"
