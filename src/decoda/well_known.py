# Copyright Andrew Dodd
from decoda import spec_provider
from decoda.main import UnknownReferenceError


def location_fmt(value, *args, **kwargs):
    if value >= 0xFF:
        return "Not available"
    axle = 1 + (0x0F & (value >> 4))
    tire = 1 + (0x0F & value)

    ordinals = {1: "st", 2: "nd", 3: "rd"}
    axle = f"{axle}{ordinals.get(axle, 'th')}"
    tire = f"{tire}{ordinals.get(tire, 'th')}"

    return f"{axle} axle, {tire} tire"


def refers_to_spn(value, *args, **kwargs):
    try:
        found = spec_provider.provide().SPNs.get_by_id(value)
        return f"SPN {value} - {found.name}"
    except UnknownReferenceError:
        return f"SPN {value}"


def conditionally_applies(
    value,
    *args,
    already_decoded=None,
    custom_args=None,
    non_custom_alternative=None,
    original_value=None,
    **kwargs,
):
    if (
        not custom_args
        or not custom_args.get("conditional_on_spn")
        or not custom_args.get("applies_if")
    ):
        raise ValueError("bad config")

    conditional_on_spn_id = custom_args["conditional_on_spn"]

    if not already_decoded:
        raise ValueError("no values decoded")

    try:
        decoded = next(
            d for d in already_decoded if d.id == conditional_on_spn_id
        )
    except StopIteration:
        raise ValueError(
            f"conditional on SPN {conditional_on_spn_id}, but not found"
        )

    if decoded.value != custom_args["applies_if"]:
        return None

    alternative_value = non_custom_alternative.decode_from_raw(
        value=original_value,
        already_decoded=already_decoded,
        custom_args=custom_args,
        non_custom_alternative=non_custom_alternative,
        **kwargs,
    )
    return alternative_value[0]["value"]


def fmi_ce(value, *args, **kwargs):
    if not 0 <= value <= 31:
        raise ValueError("Only 5-bit value allowed")
    # yapf:disable
    return [
        "Data Valid But Above Normal Operational Range - Most Severe Level",  # 0
        "Data Valid But Below Normal Operational Range - Most Severe Level",  # 1
        "Data Erratic, Intermittent Or Incorrect",  # 2
        "Voltage Above Normal, Or Shorted To High Source",  # 3
        "Voltage Below Normal, Or Shorted To Low Source",  # 4
        "Current Below Normal Or Open Circuit",  # 5
        "Current Above Normal Or Grounded Circuit",  # 6
        "Mechanical System Not Responding Or Out Of Adjustment",  # 7
        "Abnormal Frequency Or Pulse Width Or Period",  # 8
        "Abnormal Update Rate",  # 9
        "Abnormal Rate Of Change",  # 10
        "Root Cause Not Known",  # 11
        "Bad Intelligent Device Or Component",  # 12
        "Out Of Calibration",  # 13
        "Special Instructions",  # 14
        "Data Valid But Above Normal Operating Range - Least Severe Level",  # 15
        "Data Valid But Above Normal Operating Range - Moderately Severe Level",  # 16
        "Data Valid But Below Normal Operating Range - Least Severe Level",  # 17
        "Data Valid But Below Normal Operating Range - Moderately Severe Level",  # 18
        "Received Network Data In Error",  # 19
        "Data Drifted High",  # 20
        "Data Drifted Low",  # 21
        "Reserved For SAE Assignment",  # 22
        "Reserved For SAE Assignment",  # 23
        "Reserved For SAE Assignment",  # 24
        "Reserved For SAE Assignment",  # 25
        "Reserved For SAE Assignment",  # 26
        "Reserved For SAE Assignment",  # 27
        "Reserved For SAE Assignment",  # 28
        "Reserved For SAE Assignment",  # 29
        "Reserved For SAE Assignment",  # 30
        "Condition Exists",  # 31
    ][value]
    # yapf:enable


def fmi_na(value, *args, **kwargs):
    if value == 31:
        return "Not available" # Casing similar to other not available encodings
    return fmi_ce(value, *args, **kwargs)


def fmi_zero(value, *args, **kwargs):
    if not 0 <= value <= 31:
        raise ValueError("Only 5-bit value allowed")
    # Some FMIs seemt to define 0 as "no problem". It is not clear what the other encodings should be.
    return "No fault active" if value == 0 else "Fault present"


fmi = fmi_ce  # By default use te condition exists variant
