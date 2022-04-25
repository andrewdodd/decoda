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
