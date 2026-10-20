
import math


def calculate_required_units(required_contribution, price, variable_cost):
    contribution_per_unit = price - variable_cost

    if contribution_per_unit <= 0:
        return None

    required_units = math.ceil(
        required_contribution / contribution_per_unit
    )

    return {
        "contribution_per_unit": contribution_per_unit,
        "required_units": required_units
    }


def calculate_financials(price, variable_cost, fixed_cost):
    contribution_per_unit = price - variable_cost

    if contribution_per_unit <= 0:
        return {
            "error": (
                "Selling price must be greater than variable cost."
            )
        }

    break_even_units = math.ceil(
        fixed_cost / contribution_per_unit
    )

    return {
        "contribution_per_unit": contribution_per_unit,
        "break_even_units": break_even_units
    }
