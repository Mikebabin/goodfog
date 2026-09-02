from goodfog.viewpoints import VIEWPOINTS, viewpoint_by_id


def test_eight_viewpoints_in_original_order():
    assert [v.id for v in VIEWPOINTS] == [
        "hawk-hill", "battery-spencer", "conzelman-pullouts", "twin-peaks-vantage",
        "point-bonita", "trojan-point", "west-peak", "east-peak",
    ]


def test_east_peak_values():
    v = viewpoint_by_id("east-peak")
    assert v.elev_ft == 2571
    assert v.green_ft == (200, 2400)
    assert v.yellow_ft == (2400, 2571)
    assert v.dawn_gated is True
    assert v.desc == "2,571 ft · Mt. Tamalpais"


def test_only_tam_summits_are_dawn_gated():
    assert {v.id for v in VIEWPOINTS if v.dawn_gated} == {"trojan-point", "west-peak", "east-peak"}


def test_bands_are_contiguous():
    for v in VIEWPOINTS:
        assert v.green_ft[0] < v.green_ft[1] == v.yellow_ft[0] < v.yellow_ft[1]
